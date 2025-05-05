# utils/map_utils.py
import folium
from streamlit_folium import st_folium
import json
import time
import streamlit as st
import pandas as pd
import numpy as np
from utils.file_utils import safe_to_json, ensure_valid_geodataframe, get_random_color, find_name_field, find_id_field

def add_map_layer(gdf, name, style=None):
    """
    Add a GeoDataFrame as a layer to the map with better handling for layer types.
    
    Args:
        gdf: GeoDataFrame to add to the map
        name: Name for the layer
        style: Optional style dictionary for the layer
        
    Returns:
        bool: True if successful, False otherwise
    """
    if gdf is None or len(gdf) == 0:
        return False
    
    try:
        # Convert to WGS84 if needed
        if gdf.crs and str(gdf.crs) != "EPSG:4326":
            gdf = gdf.to_crs(epsg=4326)
        
        # Handle large datasets by simplifying
        gdf_to_display = gdf.copy()
        if len(gdf) > 1000:
            gdf_to_display['geometry'] = gdf_to_display.geometry.simplify(tolerance=0.001)
            
        # Handle timestamp columns to ensure proper serialization
        for col in gdf_to_display.columns:
            if col != 'geometry':
                dtype_str = str(gdf_to_display[col].dtype).lower()
                if 'datetime' in dtype_str or 'timestamp' in dtype_str:
                    gdf_to_display[col] = gdf_to_display[col].astype(str)
        
        # Create GeoJSON with manageable size
        if len(gdf) > 500:
            # For very large datasets, use random sampling
            sample_size = min(500, len(gdf))
            sample_gdf = gdf_to_display.sample(sample_size)
            geo_data = json.loads(sample_gdf.to_json())
        else:
            geo_data = json.loads(gdf_to_display.to_json())
        
        # Determine if this is a point dataset based on the first geometry
        is_point_dataset = False
        if 'geometry' in gdf.columns and len(gdf) > 0:
            first_geom_type = gdf.geometry.iloc[0].geom_type
            is_point_dataset = first_geom_type == 'Point'
        
        # If it's a point dataset, use circle markers with random colors
        if is_point_dataset:
            # Generate a random color not used before
            color = get_random_color()
            while color in st.session_state.used_colors and len(st.session_state.used_colors) < 10:
                color = get_random_color()
            
            # Add to used colors
            st.session_state.used_colors.append(color)
            
            # Create point style
            point_style = {
                'radius': 5,
                'weight': 1,
                'color': color,
                'fillColor': color,
                'fillOpacity': 0.7
            }
            
            # Add to map layers
            st.session_state.map_layers[name] = {
                'data': geo_data,
                'point_style': point_style
            }
        else:
            # Default style if none provided for non-point datasets
            if style is None:
                # Check if it might be water related
                if any(water_term in name.lower() for water_term in ['water', 'hydro', 'river', 'lake']):
                    style = {
                        'fillColor': '#0066ff',  # Blue for water
                        'color': '#0044cc',
                        'weight': 2,
                        'fillOpacity': 0.5
                    }
                else:
                    style = {
                        'fillColor': '#ff7800',
                        'color': '#000000',
                        'weight': 1,
                        'fillOpacity': 0.5
                    }
            
            # Add to map layers
            st.session_state.map_layers[name] = {
                'data': geo_data,
                'style': style
            }
        
        # Update map center if this is the first layer
        if len(st.session_state.map_layers) == 1:
            try:
                bounds = gdf_to_display.total_bounds
                st.session_state.map_center = [(bounds[1] + bounds[3]) / 2, (bounds[0] + bounds[2]) / 2]
            except:
                pass
        
        # Force map refresh on next render
        st.session_state.force_map_refresh = True
        
        return True
    except Exception as e:
        return False

def add_results_layer(result_gdf, value_column='suitability_score', title='Suitability Results'):
    """
    Add analysis results as a layer on the map with a more intuitive color gradient.
    
    Args:
        result_gdf: GeoDataFrame containing the results
        value_column: Column name to use for coloring
        title: Title for the layer
    """
    if result_gdf is None or len(result_gdf) == 0:
        st.warning("No results to display")
        return
    
    # Convert to WGS84 if needed
    if result_gdf.crs and str(result_gdf.crs) != "EPSG:4326":
        result_gdf = result_gdf.to_crs(epsg=4326)
    
    # Get min and max values for coloring
    min_val = result_gdf[value_column].min()
    max_val = result_gdf[value_column].max()
    
    # Round suitability scores to 2 decimal places
    result_gdf[value_column] = result_gdf[value_column].round(2)
    
    # Try to find a name column for features
    name_field = find_name_field(result_gdf)
    
    # Skip if min and max are the same (no variation)
    if min_val == max_val:
        st.info(f"All areas have the same {value_column} value: {min_val:.2f}")
    
    # Create style function for the results with improved color ramp
    def style_function(feature):
        value = feature['properties'].get(value_column, min_val)
        
        # Normalize value
        if min_val == max_val:
            normalized = 1.0  # If all values are the same, use full color
        else:
            normalized = (value - min_val) / (max_val - min_val)
        
        # Color ramp: light red (#ffcccc) to yellow (#ffff99) to green (#66cc66)
        if normalized < 0.5:
            # First half: light red to yellow
            # Map 0-0.5 to 0-1
            local_norm = normalized * 2
            # Interpolate between light red and yellow
            r = 255
            g = int(204 + local_norm * (255 - 204))
            b = int(204 + local_norm * (153 - 204))
        else:
            # Second half: yellow to green
            # Map 0.5-1 to 0-1
            local_norm = (normalized - 0.5) * 2
            # Interpolate between yellow and green
            r = int(255 - local_norm * (255 - 102))
            g = int(255 - local_norm * (255 - 204))
            b = int(153 - local_norm * (153 - 102))
        
        color = f'#{r:02x}{g:02x}{b:02x}'
        
        return {
            'fillColor': color,
            'color': '#666666',  # darker grey border
            'weight': 1,
            'fillOpacity': 0.8
        }
    
    # Add results to map layers with better handling for edge cases
    try:
        # Handle large results with simplification
        result_for_display = result_gdf.copy()
        if len(result_for_display) > 500:
            result_for_display['geometry'] = result_for_display.geometry.simplify(tolerance=0.001)
        
        # Make sure all properties are serializable
        for col in result_for_display.columns:
            if col != 'geometry':
                try:
                    # Try to convert complex data types to string
                    if result_for_display[col].dtype.name == 'object':
                        result_for_display[col] = result_for_display[col].astype(str)
                except:
                    # If conversion fails, drop the column
                    result_for_display = result_for_display.drop(columns=[col])
        
        # Convert to GeoJSON
        result_geo_json = safe_to_json(result_for_display)
        
        # Create tooltip fields based on available columns
        tooltip_fields = [value_column]
        tooltip_aliases = ['Suitability Score:']
        
        # Add name field to tooltip if available
        if name_field:
            tooltip_fields.insert(0, name_field)
            tooltip_aliases.insert(0, 'Name:')
        else:
            # Use ID field as fallback
            id_field = find_id_field(result_for_display)
            if id_field:
                tooltip_fields.insert(0, id_field)
                tooltip_aliases.insert(0, 'ID:')
        
        # Add to session state map layers
        st.session_state.map_layers[title] = {
            'data': result_geo_json,
            'style_function': style_function,
            'is_results': True,  # Flag to identify results layer
            'tooltip_fields': tooltip_fields,
            'tooltip_aliases': tooltip_aliases
        }
        
        # Update map center based on the results
        bounds = result_for_display.total_bounds
        st.session_state.map_center = [(bounds[1] + bounds[3]) / 2, (bounds[0] + bounds[2]) / 2]
        
        # Force map refresh
        st.session_state.force_map_refresh = True
        
        # Success message
        st.success(f"Results displayed on map with color gradient from low (red) to high (green).")
        
        # Display legend
        st.markdown(f"""
        ### Results Legend
        <div style="display: flex; align-items: center; margin-bottom: 5px;">
            <div style="width: 20px; height: 20px; background-color: #ffcccc; margin-right: 10px;"></div>
            <div>Lower suitability (Score: {min_val:.2f})</div>
        </div>
        <div style="display: flex; align-items: center; margin-bottom: 5px;">
            <div style="width: 20px; height: 20px; background-color: #ffff99; margin-right: 10px;"></div>
            <div>Medium suitability (Score: {(min_val + max_val)/2:.2f})</div>
        </div>
        <div style="display: flex; align-items: center;">
            <div style="width: 20px; height: 20px; background-color: #66cc66; margin-right: 10px;"></div>
            <div>Higher suitability (Score: {max_val:.2f})</div>
        </div>
        """, unsafe_allow_html=True)
        
    except Exception as e:
        st.error(f"Error displaying results on map: {str(e)}")
        import traceback
        st.write(traceback.format_exc())

def display_map_with_st_folium():
    """
    Display the interactive map with all layers and smooth zoom/pan interaction.
    """
    # Add CSS for responsive map display
    st.markdown("""
    <style>
    [title~="st.iframe"] { width: 100% }
    .stApp iframe { width: 100% }

    /* Customize the layer control */
    .leaflet-control-layers {
        border-radius: 4px;
        box-shadow: 0 1px 5px rgba(0,0,0,0.4);
        background: rgba(255,255,255,0.9);
        overflow: hidden;
    }
    .leaflet-control-layers-expanded {
        padding: 6px 10px 6px 6px;
        max-height: 350px;
        overflow-y: auto;
    }
    .leaflet-control-layers-selector {
        margin-right: 5px;
    }
    </style>
    """, unsafe_allow_html=True)
    
    # Initialize session state variables only once
    if 'map_initialized' not in st.session_state:
        st.session_state.map_initialized = False
        st.session_state.current_map_key = "initial_map"
        st.session_state.last_boundary_key = None
    
    # Create a stable key that doesn't change on regular reruns
    # Only change the key when forcing a refresh
    key_to_use = st.session_state.current_map_key
    if st.session_state.force_map_refresh:
        key_to_use = f"map_{len(st.session_state.map_layers.keys())}_{st.session_state.has_result}_{time.time()}"
        st.session_state.current_map_key = key_to_use
    
    # Determine location and zoom
    location = st.session_state.map_center
    if isinstance(location, dict) and 'lat' in location and 'lng' in location:
        location = [location['lat'], location['lng']]
    zoom_start = st.session_state.map_zoom
    
    # Create the base map
    m = folium.Map(
        location=location,
        zoom_start=zoom_start,
        tiles="OpenStreetMap"
    )
    
    # Add fullscreen control
    from folium.plugins import Fullscreen, MousePosition
    Fullscreen(
        position='topleft',
        title='Expand map',
        title_cancel='Exit fullscreen',
        force_separate_button=True
    ).add_to(m)
    
    # Add mouse position control to show coordinates
    MousePosition().add_to(m)
    
    # Store boundary bounds for fit_bounds
    boundary_bounds = None
    should_fit_bounds = False
    fit_bounds_to = None
    
    # Store boundary for home button functionality
    if hasattr(st.session_state.project, 'boundary_dataset') and st.session_state.project.boundary_dataset is not None:
        try:
            # Get the boundary dataset and ensure it's valid
            gdf = ensure_valid_geodataframe(st.session_state.project.boundary_dataset)
            
            # Get bounds for later use
            bounds = gdf.total_bounds
            boundary_bounds = [
                [bounds[1], bounds[0]],  # SW corner
                [bounds[3], bounds[2]]   # NE corner
            ]
            
            # Store the bounds in session state for the home button
            st.session_state.boundary_bounds = boundary_bounds
        except Exception as e:
            pass
    
    # Sort layers into categories
    regular_layers = {}
    result_layers = {}
    if hasattr(st.session_state, 'map_layers') and st.session_state.map_layers:
        for layer_name, layer_info in st.session_state.map_layers.items():
            if layer_info.get('is_results', False) or 'Suitability' in layer_name:
                result_layers[layer_name] = layer_info
            else:
                regular_layers[layer_name] = layer_info
    
    # Add boundary if available
    if hasattr(st.session_state.project, 'boundary_dataset') and st.session_state.project.boundary_dataset is not None:
        try:
            # Get the boundary dataset and ensure it's valid
            gdf = ensure_valid_geodataframe(st.session_state.project.boundary_dataset)
            
            # Try to find a name field for the boundary
            name_field = find_name_field(gdf)
            
            # Handle large boundaries by simplifying
            if len(gdf) > 100:
                gdf = gdf.copy()
                gdf['geometry'] = gdf.geometry.simplify(tolerance=0.001)
                
            # Convert to GeoJSON
            geo_json_data = json.loads(gdf.to_json())
            
            # Create boundary GeoJSON layer
            boundary_layer = folium.GeoJson(
                data=geo_json_data,
                name="Boundary",
                style_function=lambda x: {
                    'fillColor': '#a9a9a9',
                    'color': '#404040',
                    'weight': 2,
                    'fillOpacity': 0.5,
                    'opacity': 0.8
                }
            )
            
            # Add tooltip if name field is available
            if name_field:
                boundary_layer.add_child(folium.GeoJsonTooltip(
                    fields=[name_field],
                    aliases=['Name:'],
                    style="""
                        background-color: #F0EFEF;
                        border: 2px solid black;
                        border-radius: 3px;
                        box-shadow: 3px;
                    """
                ))
            
            boundary_layer.add_to(m)
            
            # Check if this is a new boundary or we need to force zoom
            current_boundary_key = f"{id(st.session_state.project.boundary_dataset)}"
            if (current_boundary_key != st.session_state.last_boundary_key or 
                st.session_state.force_map_refresh):
                should_fit_bounds = True
                fit_bounds_to = gdf
                st.session_state.last_boundary_key = current_boundary_key
                
        except Exception as e:
            st.error(f"Error adding boundary layer: {str(e)}")

    # Add regular layers next
    for layer_name, layer_info in regular_layers.items():
        try:
            if 'style_function' in layer_info:
                folium.GeoJson(
                    data=layer_info['data'],
                    name=layer_name,
                    style_function=layer_info['style_function']
                ).add_to(m)
                
            elif 'point_style' in layer_info:
                # For point layers, use CircleMarker
                point_style = layer_info['point_style']
                
                folium.GeoJson(
                    data=layer_info['data'],
                    name=layer_name,
                    marker=folium.CircleMarker(
                        radius=point_style.get('radius', 5),
                        weight=point_style.get('weight', 1),
                        color=point_style.get('color', '#000000'),
                        fill_color=point_style.get('fillColor', '#000000'),
                        fill_opacity=point_style.get('fillOpacity', 0.7)
                    )
                ).add_to(m)
                
            else:
                style = layer_info.get('style', {})
                folium.GeoJson(
                    data=layer_info['data'],
                    name=layer_name,
                    style_function=lambda x: style
                ).add_to(m)
        except Exception as e:
            # More informative error handling
            st.warning(f"Could not add layer '{layer_name}': {str(e)}")
    
    # Add result layers last (so they're on top)
    for layer_name, layer_info in result_layers.items():
        try:
            if 'style_function' in layer_info:
                # Create a dedicated feature group for results
                result_layer = folium.FeatureGroup(name=layer_name)
                
                # Get tooltip fields and aliases
                tooltip_fields = layer_info.get('tooltip_fields', ['suitability_score'])
                tooltip_aliases = layer_info.get('tooltip_aliases', ['Suitability Score:'])
                
                # Add the GeoJSON layer with styling function and tooltips
                folium.GeoJson(
                    data=layer_info['data'],
                    name=layer_name,
                    style_function=layer_info['style_function'],
                    tooltip=folium.GeoJsonTooltip(
                        fields=tooltip_fields,
                        aliases=tooltip_aliases,
                        localize=True,
                        sticky=False,
                        labels=True,
                        style="""
                            background-color: #F0EFEF;
                            border: 2px solid black;
                            border-radius: 3px;
                            box-shadow: 3px;
                            font-size: 12px;
                            font-family: Arial, sans-serif;
                        """,
                        max_width=300,
                    )
                ).add_to(result_layer)
                
                # Add the feature group to the map
                result_layer.add_to(m)
                
                # If new results, maybe fit bounds to them
                if st.session_state.force_map_refresh and hasattr(st.session_state.project, 'result'):
                    if not should_fit_bounds:  # Only if we're not already fitting to boundary
                        should_fit_bounds = True
                        fit_bounds_to = st.session_state.project.result
            else:
                # Fallback for results without style function
                folium.GeoJson(
                    data=layer_info['data'],
                    name=layer_name,
                    style_function=lambda x: {
                        'fillColor': '#66cc66',  # Light green
                        'color': '#666666',  # Dark grey border
                        'weight': 1,
                        'fillOpacity': 0.7
                    }
                ).add_to(m)
                
        except Exception as e:
            st.warning(f"Could not add result layer '{layer_name}': {str(e)}")
    
    # Add layer control with collapsed=True
    folium.LayerControl(
        collapsed=True,
        position='topright',
        autoZIndex=True,
        hideSingleBase=True
    ).add_to(m)
    
    # Apply bounds if needed and we're forcing a refresh
    if should_fit_bounds and fit_bounds_to is not None and st.session_state.force_map_refresh:
        try:
            bounds = fit_bounds_to.total_bounds
            m.fit_bounds([
                [bounds[1], bounds[0]],  # SW corner
                [bounds[3], bounds[2]]   # NE corner
            ])
            
            # Update center in session state based on bounds
            st.session_state.map_center = [(bounds[1] + bounds[3]) / 2, (bounds[0] + bounds[2]) / 2]
        except Exception as e:
            st.error(f"Error fitting bounds: {str(e)}")
    
    # Reset force refresh flag
    force_refresh = st.session_state.force_map_refresh
    if st.session_state.force_map_refresh:
        st.session_state.force_map_refresh = False
    
    # Use st_folium with the critical key parameter
    map_data = st_folium(
        m,
        use_container_width=True,
        height=500,
        key=key_to_use,
        # Set returned_objects to prevent auto reruns
        returned_objects=["last_active_drawing"],
    )
    
    # If this is initialization or a forced refresh,
    # we allow the map data to be processed without triggering rerun
    if not st.session_state.map_initialized or force_refresh:
        st.session_state.map_initialized = True
        
        # Process any map data from initialization
        if map_data and 'center' in map_data and map_data['center'] is not None:
            if isinstance(map_data['center'], dict) and 'lat' in map_data['center'] and 'lng' in map_data['center']:
                st.session_state.map_center = [map_data['center']['lat'], map_data['center']['lng']]
            else:
                st.session_state.map_center = map_data['center']
                
        if map_data and 'zoom' in map_data and map_data['zoom'] is not None:
            st.session_state.map_zoom = map_data['zoom']
    
    return force_refresh

