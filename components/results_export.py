# components/results_export.py
import tempfile
import os
import json
import zipfile
import streamlit as st

class ResultsExporter:
    """
    Class for exporting suitability analysis results in a Streamlit app.
    """
    
    def export_geojson(self, result_gdf, filename_base):
        with tempfile.NamedTemporaryFile(suffix='.geojson', delete=False) as tmp:
            # Close the file handle before writing to it with geopandas
            tmp_name = tmp.name
        
        # Now write to it with the file handle closed
        result_gdf.to_file(tmp_name, driver='GeoJSON')
        
        # Read the file contents
        with open(tmp_name, 'r') as f:
            geojson_data = json.load(f)
        
        # Delete the temporary file after reading
        try:
            os.remove(tmp_name)
        except:
            pass  # If we can't delete it now, it will be cleaned up later
            
        return geojson_data
    
    def export_shapefile(self, result_gdf, filename):
        """
        Export results as Shapefile (zipped) for Streamlit download.
        
        Args:
            result_gdf (GeoDataFrame): Analysis results
            filename (str): Base filename without extension
            
        Returns:
            bytes: Data for Streamlit download button
        """
        if not filename.endswith('.shp'):
            filename += '.shp'
        
        # Create a temporary directory for the shapefile components
        temp_dir = tempfile.mkdtemp()
        shp_base = os.path.join(temp_dir, 'temp_shapefile')
        
        # Export to Shapefile
        result_gdf.to_file(shp_base + '.shp', driver='ESRI Shapefile')
        
        # Create a temporary ZIP file
        zip_filename = filename.replace('.shp', '.zip')
        with tempfile.NamedTemporaryFile(delete=False, suffix='.zip') as tmp:
            # Create the ZIP file
            with zipfile.ZipFile(tmp.name, 'w') as zipf:
                for f in os.listdir(temp_dir):
                    zipf.write(os.path.join(temp_dir, f), arcname=f)
            
            # Read the file for download
            with open(tmp.name, 'rb') as f:
                data = f.read()
            
            # Clean up
            try:
                os.unlink(tmp.name)
                import shutil
                shutil.rmtree(temp_dir)
            except:
                pass
        
        return data, zip_filename
    
    def export_csv(self, result_gdf, filename):
        """
        Export results as CSV (without geometry) for Streamlit download.
        
        Args:
            result_gdf (GeoDataFrame): Analysis results
            filename (str): Base filename without extension
            
        Returns:
            bytes: Data for Streamlit download button
        """
        if not filename.endswith('.csv'):
            filename += '.csv'
        
        # Export to CSV (excluding geometry)
        result_df = result_gdf.drop(columns=['geometry'])
        
        # Convert to CSV string then to bytes
        csv_data = result_df.to_csv(index=False).encode()
        
        return csv_data