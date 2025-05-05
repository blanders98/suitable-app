# utils/boundary_utils.py
import streamlit as st
from utils.file_utils import ensure_valid_geodataframe

def process_boundary_upload(boundary_file):
    """
    Process a boundary file upload and update the map.
    
    Args:
        boundary_file: Streamlit UploadedFile object
        
    Returns:
        bool: True if successful, False otherwise
    """
    try:
        # Load the boundary
        gdf, dataset_name = st.session_state.data_loader.load_boundary(boundary_file)
        
        # Make it valid and consistent
        valid_gdf = ensure_valid_geodataframe(gdf)
        
        # Store in session state
        st.session_state.project.set_boundary(valid_gdf, dataset_name)
        st.session_state.has_boundary = True
        
        # Set a flag to force the map to zoom to the boundary
        bounds = valid_gdf.total_bounds
        st.session_state.map_center = [(bounds[1] + bounds[3]) / 2, (bounds[0] + bounds[2]) / 2]
        
        # Important: Force map refresh
        st.session_state.force_map_refresh = True
        
        # Set a flag for the first zoom
        if 'has_fitted_bounds' not in st.session_state:
            st.session_state.has_fitted_bounds = False
        
        # Also update the boundary key to ensure we recognize this as a new boundary
        if 'last_boundary_key' not in st.session_state:
            st.session_state.last_boundary_key = None
        
        # Use a more reliable boundary identification that persists across reruns
        st.session_state.last_boundary_key = f"{id(valid_gdf)}_{dataset_name}"
        
        st.success(f"Boundary dataset '{dataset_name}' loaded successfully!")
        return True
        
    except Exception as e:
        st.error(f"Error loading boundary dataset: {str(e)}")
        return False