# models/project.py
import streamlit as st
import geopandas as gpd

class Project:
    """
    Class representing a suitability analysis project.
    """
    
    def __init__(self):
        self.title = "Suitability Analysis Project"
        self.description = "Find the most suitable areas based on your criteria and datasets."
        self.datasets = {}  # Dictionary to store datasets
        self.criteria = []  # List to store criteria
        self.boundary_dataset = None
        self.result = None
        
    def set_boundary(self, dataset, name):
        """Set the boundary dataset."""
        self.boundary_dataset = dataset
        self.boundary_dataset_name = name
        self.datasets[name] = dataset
        
    def add_criterion(self, criterion):
        """Add a criterion to the project."""
        self.criteria.append(criterion)
        
    def remove_criterion(self, criterion_id):
        """Remove a criterion from the project."""
        self.criteria = [c for c in self.criteria if c.id != criterion_id]
        
    def set_result(self, result):
        """Set the analysis result."""
        self.result = result
        
    def add_dataset(self, name, gdf):
        """Add a dataset to the project with robust handling for complex datasets"""
        try:
            # Make a copy to avoid modifying the original
            gdf_copy = gdf.copy()
            
            # Handle problematic data types
            for col in gdf_copy.columns:
                if col != 'geometry':
                    try:
                        # Handle different data types that might cause issues
                        dtype_str = str(gdf_copy[col].dtype).lower()
                        
                        # Convert timestamps to strings
                        if 'datetime' in dtype_str or 'timestamp' in dtype_str:
                            gdf_copy[col] = gdf_copy[col].astype(str)
                        
                        # Handle object columns that might contain complex data
                        elif 'object' in dtype_str:
                            # Test if the column is JSON serializable
                            import json
                            try:
                                # Test with first non-null value
                                test_val = gdf_copy[col].dropna().iloc[0] if not gdf_copy[col].isna().all() else None
                                json.dumps({"test": test_val})
                            except:
                                # Convert to strings if not serializable
                                gdf_copy[col] = gdf_copy[col].apply(lambda x: str(x) if x is not None else None)
                    except Exception as col_err:
                        # If column processing fails, convert the entire column to strings
                        try:
                            gdf_copy[col] = gdf_copy[col].astype(str)
                        except:
                            # If that fails too, drop the problematic column
                            gdf_copy = gdf_copy.drop(columns=[col])
            
            # Store in the datasets dictionary
            self.datasets[name] = gdf_copy
            
            # For debugging, print confirmation
            print(f"Successfully added dataset '{name}' with {len(gdf_copy)} features to project")
            print(f"Current datasets: {list(self.datasets.keys())}")
            
            return True
        except Exception as e:
            print(f"Error adding dataset: {str(e)}")
            import traceback
            print(traceback.format_exc())
            return False

    def get_dataset(self, name):
        """Get a dataset by name."""
        return self.datasets.get(name)
    
    def display_summary(self):
        """Display a project summary in Streamlit."""
        st.write(f"**Title:** {self.title}")
        st.write(f"**Description:** {self.description}")
        
        if self.boundary_dataset is not None:
            st.write(f"**Boundary Dataset:** {self.boundary_dataset_name}")
            st.write(f"**Number of Boundary Features:** {len(self.boundary_dataset)}")
        
        st.write(f"**Number of Criteria:** {len(self.criteria)}")
        
        if self.result is not None:
            st.write("**Analysis Results Available:** Yes")
        else:
            st.write("**Analysis Results Available:** No")
            
        # Display all datasets
        if self.datasets:
            st.write("**Available Datasets:**")
            for name, dataset in self.datasets.items():
                st.write(f"- {name}: {len(dataset)} features")
                
    def to_dict(self):
        """Convert the project to a dictionary."""
        return {
            'title': self.title,
            'description': self.description,
            'boundary_dataset_name': self.boundary_dataset_name,
            'criteria': [c.to_dict() for c in self.criteria]
        }
    
    def to_geojson(self):
        """Export the project boundary as GeoJSON."""
        if self.boundary_dataset is not None:
            return self.boundary_dataset.to_json()
        return None
    
    @classmethod
    def from_dict(cls, data, datasets=None):
        """Create a project from a dictionary."""
        project = cls(
            title=data['title'],
            description=data['description']
        )
        
        # Add datasets if provided
        if datasets:
            project.datasets = datasets
            if data['boundary_dataset_name'] in datasets:
                project.set_boundary(
                    datasets[data['boundary_dataset_name']],
                    data['boundary_dataset_name']
                )
        
        # Add criteria
        from models.criterion import Criterion
        for criterion_data in data.get('criteria', []):
            project.add_criterion(Criterion.from_dict(criterion_data))
            
        return project
    
    @classmethod
    def from_session_state(cls, session_state):
        """
        Create a project from Streamlit session state.
        This helps with persistence between Streamlit reruns.
        """
        if 'project' in session_state:
            old_project = session_state.project
            project = cls(
                title=old_project.title,
                description=old_project.description
            )
            project.boundary_dataset = old_project.boundary_dataset
            project.boundary_dataset_name = old_project.boundary_dataset_name
            project.criteria = old_project.criteria
            project.result = old_project.result
            project.datasets = old_project.datasets
            return project
        return cls()  # Return a new project if none exists