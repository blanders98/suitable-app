# utils/geo_processing.py
import geopandas as gpd
import numpy as np
import streamlit as st

def normalize_values(series, inverse=False):
    """
    Normalize a series of values to a 0-1 scale.
    
    Args:
        series: pandas Series of values to normalize
        inverse: If True, invert the normalization (1 becomes 0, 0 becomes 1)
        
    Returns:
        pandas Series: Normalized values
    """
    # Replace NaN values with 0
    series = series.fillna(0)
    
    # Check if all values are the same
    if series.min() == series.max():
        return series.map(lambda x: 1.0)  # All equal values get normalized to 1
    
    # Normalize
    min_val = series.min()
    max_val = series.max()
    normalized = (series - min_val) / (max_val - min_val)
    
    # Invert if needed
    if inverse:
        normalized = 1 - normalized
        
    return normalized

@st.cache_data
def spatial_operation(boundary_feature, dataset, operation, column=None):
    """
    Perform a spatial operation between a boundary feature and a dataset.
    Cached to improve performance in Streamlit.
    
    Args:
        boundary_feature: GeoSeries representing a single boundary feature
        dataset: GeoDataFrame containing features to analyze
        operation: String indicating the operation to perform
        column: Column name to use for value-based operations
        
    Returns:
        float: Result of the spatial operation
    """
    # Filter dataset to only features that intersect with the boundary
    intersecting = dataset[dataset.intersects(boundary_feature)]
    
    if len(intersecting) == 0 and operation not in ['Distance to Nearest']:
        return 0  # No intersecting features
    
    # Perform the requested operation
    if operation == 'Count Features':
        return len(intersecting)
    
    elif operation == 'Sum Values':
        return intersecting[column].sum() if len(intersecting) > 0 else 0
    
    elif operation == 'Average Values':
        return intersecting[column].mean() if len(intersecting) > 0 else 0
    
    elif operation == 'Minimum Value':
        return intersecting[column].min() if len(intersecting) > 0 else np.nan
    
    elif operation == 'Maximum Value':
        return intersecting[column].max() if len(intersecting) > 0 else np.nan
    
    elif operation == 'Area Within Boundary':
        return intersecting.area.sum()
    
    elif operation == 'Length Within Boundary':
        if hasattr(intersecting.iloc[0].geometry, 'length') if len(intersecting) > 0 else False:
            return intersecting.length.sum()
        return 0
    
    elif operation == 'Distance to Nearest':
        return boundary_feature.distance(dataset.unary_union)
    
    elif operation == 'Percent Coverage':
        if boundary_feature.area > 0:
            return intersecting.area.sum() / boundary_feature.area * 100
        return 0
    
    else:
        raise ValueError(f"Unknown operation: {operation}")

def create_color_scale(min_val, max_val, palette='viridis'):
    """
    Create a color scale function for mapping values to colors.
    Useful for visualizing values in Streamlit.
    
    Args:
        min_val: Minimum value in the scale
        max_val: Maximum value in the scale
        palette: Color palette name (viridis, plasma, inferno, etc.)
        
    Returns:
        function: A function that takes a value and returns a color
    """
    import matplotlib.pyplot as plt
    import matplotlib.colors as mcolors
    
    # Create a colormap
    cmap = plt.get_cmap(palette)
    
    # Create a normalization function
    norm = mcolors.Normalize(vmin=min_val, vmax=max_val)
    
    # Create a color mapper function
    def get_color(value):
        # Convert the normalized value to a color
        rgba = cmap(norm(value))
        # Convert to hex
        hex_color = mcolors.to_hex(rgba)
        return hex_color
    
    return get_color