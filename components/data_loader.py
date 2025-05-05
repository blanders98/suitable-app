# components/data_loader.py
import geopandas as gpd
import os
import tempfile
import streamlit as st

class DataLoader:
    """
    Class for loading and processing geospatial data for Streamlit.
    """
    
    def __init__(self):
        """Initialize the data loader."""
        self.temp_directories = []  # Track temp directories to clean up later
    
    # In data_loader.py, modify the load_dataset method:

    def load_dataset(self, file_obj):
        """
        Load a dataset with improved handling for complex files.
        """
        # Get the file name
        file_name = file_obj.name
        tmp_path = None
        
        try:
            # Make a temporary directory
            with tempfile.TemporaryDirectory() as tmp_dir:
                # Save the file to the temp directory
                tmp_path = os.path.join(tmp_dir, file_name)
                with open(tmp_path, 'wb') as f:
                    f.write(file_obj.getvalue())
                
                st.info(f"Loading {file_name}...")
                
                # Handle different file types
                if file_name.endswith('.zip'):
                    # For zipped shapefiles, don't specify the driver explicitly
                    gdf = gpd.read_file(f"zip://{tmp_path}")
                    dataset_name = file_name.replace('.zip', '')
                    
                elif file_name.endswith('.geojson') or file_name.endswith('.json'):
                    gdf = gpd.read_file(tmp_path)
                    dataset_name = file_name.replace('.geojson', '').replace('.json', '')
                    
                else:
                    raise ValueError(f"Unsupported file type: {file_name}")
                
                # Check if we have valid data
                if gdf is None or len(gdf) == 0:
                    st.warning("The dataset appears to be empty.")
                    return None, None
                    
                # Print some information about the dataset to help with debugging
                st.write(f"Dataset loaded with {len(gdf)} features")
                st.write(f"Geometry types: {gdf.geometry.type.unique().tolist()}")
                
                return gdf, dataset_name
                
        except Exception as e:
            st.error(f"Error loading dataset: {str(e)}")
            import traceback
            st.write(traceback.format_exc())
            return None, None
        finally:
            # Clean up the temporary file
            if tmp_path:
                try:
                    os.unlink(tmp_path)
                except:
                    pass
                
    def load_boundary(self, uploaded_file):
        """
        Load a boundary dataset from a Streamlit uploaded file.
        
        Args:
            uploaded_file: Streamlit UploadedFile object
            
        Returns:
            tuple: (gdf, dataset_name) where gdf is a GeoDataFrame and dataset_name is a string
        """
        gdf, dataset_name = self.load_dataset(uploaded_file)
        return gdf, f"Boundary: {dataset_name}"
    
    def cleanup(self):
        """Remove temporary directories."""
        for temp_dir in self.temp_directories:
            try:
                import shutil
                shutil.rmtree(temp_dir)
            except Exception:
                pass
        self.temp_directories = []