# components/map_display.py
import streamlit as st
import folium
from streamlit_folium import folium_static
import geopandas as gpd
import json
import branca.colormap as cm

class MapDisplay:
    """
    Interactive map display component using Folium and Streamlit.
    """
    
    def __init__(self, center=None, zoom=5):
        """
        Initialize the map display.
        
        Args:
            center (tuple, optional): Center coordinates as (lat, lon)
            zoom (int): Initial zoom level
        """
        # Use default center if none provided
        if center is None:
            center = [39.8283, -98.5795]  # Center of US
        
        # Initialize session state variables for map
        if 'map_center' not in st.session_state:
            st.session_state.map_center = center
        if 'map_zoom' not in st.session_state:
            st.session_state.map_zoom = zoom
        if 'map_layers' not in st.session_state:
            st.session_state.map_layers = {}
    
    def display(self):
        """Display the map in the Streamlit app."""
        # Create a base map
        m = folium.Map(
            location=st.session_state.map_center,
            zoom_start=st.session_state.map_zoom,
            tiles="OpenStreetMap",
            control_scale=True
        )
        
        # Add layer control
        folium.LayerControl().add_to(m)
        
        # Add all stored layers to the map
        for name, layer_info in st.session_state.map_layers.items():
            if layer_info['type'] == 'geojson':
                folium.GeoJson(
                    data=layer_info['geojson_data'],
                    name=name,
                    style_function=lambda x, style=layer_info['style']: style
                ).add_to(m)
            elif layer_info['type'] == 'choropleth':
                # Create a copy of the colormap
                colormap = cm.LinearColormap(
                    layer_info['colors'],
                    vmin=layer_info['vmin'],
                    vmax=layer_info['vmax']
                )
                colormap.caption = layer_info['caption']
                colormap.add_to(m)
                
                # Add the choropleth layer
                folium.GeoJson(
                    data=layer_info['geojson_data'],
                    name=name,
                    style_function=layer_info['style_function']
                ).add_to(m)
        
        # Display the map
        folium_static(m)
    
    def add_dataset_layer(self, gdf, name, style=None):
        """
        Add a dataset as a layer to the map.
        
        Args:
            gdf (GeoDataFrame): Dataset to add
            name (str): Name for the layer
            style (dict, optional): Style properties for the layer
        """
        if gdf is None or len(gdf) == 0:
            return
        
        # Convert to WGS84 if needed
        if gdf.crs and str(gdf.crs) != "EPSG:4326":
            gdf = gdf.to_crs(epsg=4326)
        
        # Clean up any timestamp columns
        gdf_to_display = gdf.copy()
        for col in gdf_to_display.columns:
            if col != 'geometry':
                dtype_str = str(gdf_to_display[col].dtype).lower()
                if 'datetime' in dtype_str or 'timestamp' in dtype_str:
                    gdf_to_display[col] = gdf_to_display[col].astype(str)
        
        # Default style if none provided
        if style is None:
            style = {
                'fillColor': '#3388ff',
                'color': '#3388ff',
                'weight': 2,
                'fillOpacity': 0.2
            }
        
        # Convert to GeoJSON
        geojson_data = json.loads(gdf_to_display.to_json())
        
        # Store layer info in session state
        st.session_state.map_layers[name] = {
            'type': 'geojson',
            'geojson_data': geojson_data,
            'style': style
        }
        
        # Update map center
        bounds = gdf.total_bounds
        st.session_state.map_center = [(bounds[1] + bounds[3]) / 2, (bounds[0] + bounds[2]) / 2]
    
    def remove_dataset_layer(self, name):
        """
        Remove a dataset layer from the map.
        
        Args:
            name (str): Name of the layer to remove
        """
        if name in st.session_state.map_layers:
            del st.session_state.map_layers[name]
    
    def display_results(self, result_gdf, value_column='suitability_score', title=None):
        """
        Display analysis results on the map.
        
        Args:
            result_gdf (GeoDataFrame): Results GeoDataFrame
            value_column (str): Column to use for coloring
            title (str, optional): Title for the layer
        """
        if result_gdf is None or len(result_gdf) == 0:
            return
        
        # Convert to WGS84 if needed
        if result_gdf.crs and str(result_gdf.crs) != "EPSG:4326":
            result_gdf = result_gdf.to_crs(epsg=4326)
        
        # Clean up any timestamp columns
        gdf_to_display = result_gdf.copy()
        for col in gdf_to_display.columns:
            if col != 'geometry':
                dtype_str = str(gdf_to_display[col].dtype).lower()
                if 'datetime' in dtype_str or 'timestamp' in dtype_str:
                    gdf_to_display[col] = gdf_to_display[col].astype(str)
        
        # Create color map
        min_val = result_gdf[value_column].min()
        max_val = result_gdf[value_column].max()
        colors = ['red', 'yellow', 'green']
        
        # Create style function
        def style_function(feature):
            # Safe access to properties
            props = feature.get('properties', {})
            value = props.get(value_column, min_val)
            
            # Calculate color (simple linear interpolation)
            if min_val == max_val:
                normalized = 1.0
            else:
                normalized = (value - min_val) / (max_val - min_val)
            
            # Use green for highest values
            color = '#ff0000' if normalized < 0.33 else '#ffff00' if normalized < 0.66 else '#00ff00'
            
            return {
                'fillColor': color,
                'color': 'black',
                'weight': 1,
                'fillOpacity': 0.7
            }
        
        # Create layer name
        layer_name = title if title else 'Suitability Results'
        
        # Store as choropleth in session state
        st.session_state.map_layers[layer_name] = {
            'type': 'choropleth',
            'geojson_data': json.loads(gdf_to_display.to_json()),
            'style_function': style_function,
            'colors': colors,
            'vmin': min_val,
            'vmax': max_val,
            'caption': value_column
        }
        
        # Update map center
        bounds = result_gdf.total_bounds
        st.session_state.map_center = [(bounds[1] + bounds[3]) / 2, (bounds[0] + bounds[2]) / 2]