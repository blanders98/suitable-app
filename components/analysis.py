# components/analysis.py
import geopandas as gpd
import pandas as pd
import numpy as np
import streamlit as st
from shapely.geometry import Point, Polygon, MultiPolygon
import time

class SuitabilityAnalyzer:
    """
    Class for performing suitability analysis on geospatial data.
    """
    
    def __init__(self, analysis_type='weighted_sum'):
        """
        Initialize the analyzer with the selected analysis type.
        
        Args:
            analysis_type (str): Type of analysis ('weighted_sum' or 'boolean')
        """
        self.analysis_type = analysis_type
        self.boolean_mode = 'all'  # Default boolean mode
        self.threshold = 0.5  # Default threshold for boolean mode
    
    def run_analysis(self, project):
        """
        Run the suitability analysis based on the project criteria.
        
        Args:
            project: Project object containing boundary and criteria
            
        Returns:
            GeoDataFrame: Boundary dataset with suitability scores
        """
        # Check if boundary dataset exists
        if project.boundary_dataset is None:
            raise ValueError("Boundary dataset is required for analysis")
        
        # Check if criteria exist
        if not project.criteria:
            raise ValueError("At least one criterion is required for analysis")
        
        # Get a copy of the boundary dataset
        result_gdf = project.boundary_dataset.copy()
        
        # Process each criterion
        criterion_results = {}
        
        st.info("Starting analysis...")
        progress_bar = st.progress(0.0)
        
        # Process each criterion
        for i, criterion in enumerate(project.criteria):
            # Update progress
            progress = (i / len(project.criteria)) * 0.7
            progress_bar.progress(progress)
            
            # Display processing message
            st.write(f"Processing: {criterion.name}")
            
            # Get the dataset
            dataset = project.datasets.get(criterion.data_source)
            if dataset is None:
                raise ValueError(f"Dataset not found for criterion: {criterion.name}")
            
            # Process the criterion
            criterion_scores = self._process_criterion(result_gdf, dataset, criterion)
            
            # Store results
            criterion_results[criterion.id] = {
                'scores': criterion_scores,
                'criterion': criterion
            }
        
        # Calculate final scores based on analysis type
        st.write("Calculating final scores...")
        progress_bar.progress(0.8)
        
        if self.analysis_type == 'weighted_sum':
            result_gdf = self._apply_weighted_sum(result_gdf, criterion_results)
        else:  # boolean
            result_gdf = self._apply_boolean(result_gdf, criterion_results)
        
        progress_bar.progress(1.0)
        
        # Return the result
        return result_gdf
    
    def _process_criterion(self, boundary_gdf, dataset, criterion):
        """
        Process a single criterion.
        
        Args:
            boundary_gdf: GeoDataFrame containing boundary features
            dataset: GeoDataFrame containing dataset for the criterion
            criterion: Criterion object
            
        Returns:
            pandas.Series: Scores for each boundary feature
        """
        method = criterion.processing_method
        column = criterion.column

        # Check datasets CRS
        print(f"Boundary CRS: {boundary_gdf.crs}")
        print(f"Dataset CRS: {dataset.crs}")

        # Ensure both are in same CRS
        if dataset.crs != boundary_gdf.crs:
            dataset = dataset.to_crs(boundary_gdf.crs)
            print(f"Converted dataset to CRS: {dataset.crs}")

        # Initialize scores
        scores = pd.Series(0.0, index=boundary_gdf.index)
        
        # Apply the appropriate processing method
        if method == 'Direct Value':
            if not column:
                raise ValueError(f"Column required for 'Direct Value' method in criterion: {criterion.name}")
            
            # Copy the column directly from the boundary dataset
            scores = boundary_gdf[column].copy()
        
        elif method == 'Count Features':
            # Count features within each boundary
            for i, boundary in boundary_gdf.iterrows():
                # Try buffer to handle precision issues
                buffered = boundary.geometry.buffer(0.00001)  # Small buffer
                count = dataset[dataset.intersects(buffered)].shape[0]
                name_field = next((col for col in boundary_gdf.columns if 'name' in col.lower()), None)
                name = boundary[name_field] if name_field else f"Feature {i}"
                print(f"County: {name}, Count: {count}")
                scores.iloc[i] = count
        
        elif method == 'Sum Values':
            if not column:
                raise ValueError(f"Column required for 'Sum Values' method in criterion: {criterion.name}")
            
            # Sum values for features within each boundary
            for i, boundary in boundary_gdf.iterrows():
                intersecting = dataset[dataset.intersects(boundary.geometry)]
                if not intersecting.empty:
                    scores.iloc[i] = intersecting[column].sum()
        
        elif method == 'Average Values':
            if not column:
                raise ValueError(f"Column required for 'Average Values' method in criterion: {criterion.name}")
            
            # Average values for features within each boundary
            for i, boundary in boundary_gdf.iterrows():
                intersecting = dataset[dataset.intersects(boundary.geometry)]
                if not intersecting.empty:
                    scores.iloc[i] = intersecting[column].mean()
        
        elif method == 'Minimum Value':
            if not column:
                raise ValueError(f"Column required for 'Minimum Value' method in criterion: {criterion.name}")
            
            # Find minimum value for features within each boundary
            for i, boundary in boundary_gdf.iterrows():
                intersecting = dataset[dataset.intersects(boundary.geometry)]
                if not intersecting.empty:
                    scores.iloc[i] = intersecting[column].min()
        
        elif method == 'Maximum Value':
            if not column:
                raise ValueError(f"Column required for 'Maximum Value' method in criterion: {criterion.name}")
            
            # Find maximum value for features within each boundary
            for i, boundary in boundary_gdf.iterrows():
                intersecting = dataset[dataset.intersects(boundary.geometry)]
                if not intersecting.empty:
                    scores.iloc[i] = intersecting[column].max()
        
        elif method == 'Area Within Boundary':
            # Convert to a projected CRS for accurate area calculations
            local_boundary_gdf = boundary_gdf.to_crs("EPSG:3857")  # Web Mercator projection
            local_dataset = dataset.to_crs("EPSG:3857")  
            
            # Calculate area of features within each boundary
            for i, boundary in local_boundary_gdf.iterrows():
                intersecting = local_dataset[local_dataset.intersects(boundary.geometry)]
                if not intersecting.empty:
                    area = sum(intersecting.geometry.intersection(boundary.geometry).area)
                    scores.iloc[i] = area
        
        elif method == 'Length Within Boundary':
            # Calculate length of features within each boundary
            for i, boundary in boundary_gdf.iterrows():
                intersecting = dataset[dataset.intersects(boundary.geometry)]
                if not intersecting.empty:
                    length = sum(intersecting.geometry.intersection(boundary.geometry).length)
                    scores.iloc[i] = length
        
        elif method == 'Distance to Nearest':
            # Calculate distance to nearest feature
            for i, boundary in boundary_gdf.iterrows():
                # Get the centroid of the boundary
                centroid = boundary.geometry.centroid
                
                # Calculate distances
                distances = dataset.geometry.distance(centroid)
                
                # Get minimum distance
                if not distances.empty:
                    scores.iloc[i] = distances.min()
        
        elif method == 'Percent Coverage':
            # Calculate percent coverage of boundary
            for i, boundary in boundary_gdf.iterrows():
                intersecting = dataset[dataset.intersects(boundary.geometry)]
                if not intersecting.empty:
                    # Calculate intersection area
                    intersection_area = sum(intersecting.geometry.intersection(boundary.geometry).area)
                    
                    # Calculate boundary area
                    boundary_area = boundary.geometry.area
                    
                    # Calculate percent coverage
                    if boundary_area > 0:
                        percent_coverage = (intersection_area / boundary_area) * 100
                        scores.iloc[i] = percent_coverage
        
        # Add before normalization in _process_criterion
        print(f"Pre-normalized scores for {criterion.name}: Min={scores.min()}, Max={scores.max()}, Mean={scores.mean()}")
        
        # Normalize scores (0 to 1 range) with better handling of zeros and equal values
        if not scores.empty:
            # Print detailed diagnostics
            print(f"Raw scores for {criterion.name}: Min={scores.min()}, Max={scores.max()}, Mean={scores.mean()}")
            
            if scores.max() != scores.min():
                # Normal case - different values exist
                if criterion.preference == 'Lower is better':
                    # Invert the scores (max becomes min, min becomes max)
                    scores = scores.max() - scores + scores.min()
                    print(f"After inversion: Min={scores.min()}, Max={scores.max()}, Mean={scores.mean()}")
                
                # Normalize to 0-1 range
                scores = (scores - scores.min()) / (scores.max() - scores.min())
                print(f"After normalization: Min={scores.min()}, Max={scores.max()}, Mean={scores.mean()}")
            
            elif scores.max() == 0 and scores.min() == 0:
                # All zeros case - likely no intersections found
                print(f"WARNING: All features have score 0 for {criterion.name}. Check if datasets intersect.")
                # Keep zeros to indicate no data
                scores = pd.Series(0.0, index=scores.index)
                
                # Add error message to the streamlit app
                st.warning(f"No features from {criterion.name} dataset intersect with boundary. Check coordinate systems and data.")
            
            else:
                # All values are equal but non-zero
                print(f"All features have the same score ({scores.mean()}) for {criterion.name}")
                
                # For percentages, keep actual values if they're already in a reasonable range
                if method in ['Percent Coverage'] and 0 <= scores.max() <= 100:
                    # Convert to 0-1 scale if values are percentages
                    scores = scores / 100.0
                    print(f"Percentage values normalized to: {scores.mean()}")
                elif scores.max() <= 1.0 and scores.min() >= 0.0:
                    # If values already in 0-1 range, keep them
                    print(f"Values already in 0-1 range: {scores.mean()}")
                else:
                    # Otherwise use the criterion preference
                    value = 0.5  # Use 0.5 as middle ground for equal values
                    if criterion.preference == 'Lower is better':
                        value = 0.0  # Lower is better gets 0
                    else:
                        value = 1.0  # Higher is better gets 1
                    
                    print(f"Using {value} for all features based on preference")
                    scores = pd.Series(value, index=scores.index)

        return scores
    
    def _apply_weighted_sum(self, result_gdf, criterion_results):
        """
        Apply weighted sum analysis.
        
        Args:
            result_gdf: GeoDataFrame containing boundary features
            criterion_results: Dictionary of criterion results
            
        Returns:
            GeoDataFrame: Result with suitability scores
        """
        # Calculate total weight
        total_weight = sum(cr['criterion'].weight for cr in criterion_results.values())
        
        # Initialize suitability score column
        result_gdf['suitability_score'] = 0.0
        
        # Add individual criterion score columns for transparency
        for criterion_id, data in criterion_results.items():
            criterion = data['criterion']
            scores = data['scores']
            
            # Add criterion score column
            column_name = f"{criterion.name}_score"
            result_gdf[column_name] = scores
            
            # Add to weighted sum
            if total_weight > 0:
                # Calculate normalized weight
                normalized_weight = criterion.weight / total_weight
                
                # Apply weight to scores
                result_gdf['suitability_score'] += scores * normalized_weight
            else:
                # If total weight is 0, use equal weights
                result_gdf['suitability_score'] += scores / len(criterion_results)
        
        return result_gdf
    
    def _apply_boolean(self, result_gdf, criterion_results):
        """
        Apply boolean analysis.
        
        Args:
            result_gdf: GeoDataFrame containing boundary features
            criterion_results: Dictionary of criterion results
            
        Returns:
            GeoDataFrame: Result with suitability scores
        """
        # Add individual criterion suitability columns
        for criterion_id, data in criterion_results.items():
            criterion = data['criterion']
            scores = data['scores']
            
            # Add criterion score column
            column_name = f"{criterion.name}_score"
            result_gdf[column_name] = scores
            
            # Add boolean suitable column
            suitable_column = f"{criterion.name}_suitable"
            result_gdf[suitable_column] = scores >= self.threshold
        
        # Count criteria met
        criterion_suitable_columns = [f"{data['criterion'].name}_suitable" for data in criterion_results.values()]
        result_gdf['criteria_met_count'] = result_gdf[criterion_suitable_columns].sum(axis=1)
        
        # Apply boolean mode
        if self.boolean_mode == 'all':
            # All criteria must be met
            result_gdf['is_suitable'] = result_gdf['criteria_met_count'] == len(criterion_results)
        
        elif self.boolean_mode == 'any':
            # At least one criterion must be met
            result_gdf['is_suitable'] = result_gdf['criteria_met_count'] > 0
        
        elif self.boolean_mode == 'majority':
            # Majority of criteria must be met
            result_gdf['is_suitable'] = result_gdf['criteria_met_count'] > (len(criterion_results) / 2)
        
        elif self.boolean_mode == 'percentage':
            # Percentage of criteria must be met
            threshold_count = max(1, round(len(criterion_results) * self.threshold))
            result_gdf['is_suitable'] = result_gdf['criteria_met_count'] >= threshold_count
        
        # Set suitability score
        result_gdf['suitability_score'] = result_gdf['criteria_met_count'] / len(criterion_results)
        
        return result_gdf