# utils/file_utils.py
import uuid
import tempfile
import os
import zipfile
import streamlit as st
import json
import geopandas as gpd
import random

def generate_unique_id():
    """Generate a unique ID for datasets or criteria."""
    return str(uuid.uuid4())[:8]

def extract_shapefile(uploaded_file):
    """
    Extract a shapefile from an uploaded ZIP file.
    
    Args:
        uploaded_file: Streamlit UploadedFile object
        
    Returns:
        str: Path to the extracted shapefile
    """
    # Create a temporary directory
    temp_dir = tempfile.mkdtemp()
    
    # Save the zip file
    zip_path = os.path.join(temp_dir, uploaded_file.name)
    with open(zip_path, 'wb') as f:
        f.write(uploaded_file.getbuffer())
    
    # Extract the zip file
    with zipfile.ZipFile(zip_path, 'r') as zip_ref:
        zip_ref.extractall(temp_dir)
    
    # Find all .shp files in the extracted directory
    shp_files = [f for f in os.listdir(temp_dir) if f.endswith('.shp')]
    
    if not shp_files:
        raise ValueError("No shapefile found in the zip archive")
    
    # Return the path to the first shapefile
    return os.path.join(temp_dir, shp_files[0]), temp_dir

# Update the get_random_color function in file_utils.py

def get_random_color():
    """
    Generate a vibrant, high-contrast color for point datasets.
    
    Returns:
        str: Hex color code
    """
    # List of vibrant colors that are easy to see
    vibrant_colors = [
        '#FF5733',  # Bright orange/red
        '#33A8FF',  # Bright blue
        '#47D147',  # Bright green
        '#D147D1',  # Bright purple
        '#FFD700',  # Gold
        '#FF33A8',  # Bright pink
        '#A833FF',  # Bright violet
        '#33FFD1',  # Bright teal
        '#FF3333',  # Bright red
        '#3366FF',  # Royal blue
        '#8833FF',  # Purple
        '#FF8C00',  # Dark orange
        '#1E90FF',  # Dodger blue
        '#32CD32',  # Lime green
        '#FF1493',  # Deep pink
        '#00CED1',  # Dark turquoise
        '#FF6347',  # Tomato
        '#4169E1',  # Royal blue
        '#8A2BE2',  # Blue violet
        '#228B22'   # Forest green
    ]
    
    # If we've used all colors, use random selection with constraints
    if hasattr(st.session_state, 'used_colors') and len(st.session_state.used_colors) >= len(vibrant_colors):
        # Find unused colors first
        unused_colors = [c for c in vibrant_colors if c not in st.session_state.used_colors]
        if unused_colors:
            return random.choice(unused_colors)
        
        # Fall back to creating a vibrant random color
        # Using HSV color space to ensure vibrant colors
        # Hue: 0-360, Saturation: 70-100%, Value: 80-100%
        import colorsys
        h = random.random()  # 0-1 (represents 0-360 degrees)
        s = random.uniform(0.7, 1.0)  # High saturation for vibrant colors
        v = random.uniform(0.8, 1.0)  # High value for brightness
        
        # Convert HSV to RGB
        r, g, b = colorsys.hsv_to_rgb(h, s, v)
        
        # Convert to hex
        return f'#{int(r*255):02x}{int(g*255):02x}{int(b*255):02x}'
    else:
        # Get a color we haven't used yet
        used_colors = getattr(st.session_state, 'used_colors', [])
        available_colors = [c for c in vibrant_colors if c not in used_colors]
        
        if not available_colors:  # If all used, recycle through them
            return random.choice(vibrant_colors)
        
        return random.choice(available_colors)

def safe_to_json(gdf):
    """
    Safely convert a GeoDataFrame to GeoJSON with better handling of timestamps and data types.
    
    Args:
        gdf (GeoDataFrame): GeoDataFrame to convert
        
    Returns:
        dict: GeoJSON dictionary
    """
    try:
        # Make a copy to avoid modifying the original
        gdf_copy = gdf.copy()
        
        # Convert any timestamp columns to strings
        for col in gdf_copy.columns:
            if col != 'geometry':
                # Check data type
                dtype_str = str(gdf_copy[col].dtype).lower()
                if 'datetime' in dtype_str or 'timestamp' in dtype_str:
                    gdf_copy[col] = gdf_copy[col].astype(str)
                
                # Also handle any array-like or complex objects
                if 'object' in dtype_str:
                    # Try to convert to string if it's a complex object
                    try:
                        gdf_copy[col] = gdf_copy[col].apply(lambda x: str(x) if x is not None else None)
                    except:
                        # If conversion fails, drop the column
                        gdf_copy = gdf_copy.drop(columns=[col])
        
        # First attempt: standard to_json method with the cleaned dataframe
        return json.loads(gdf_copy.to_json())
        
    except Exception as e:
        # Try alternative conversion with simplified geometries
        try:
            simplified = gdf.copy()
            
            # Simplify geometries
            simplified['geometry'] = simplified.geometry.simplify(tolerance=0.001)
            
            # Convert timestamp columns to strings
            for col in simplified.columns:
                if col != 'geometry':
                    dtype_str = str(simplified[col].dtype).lower()
                    if 'datetime' in dtype_str or 'timestamp' in dtype_str:
                        simplified[col] = simplified[col].astype(str)
            
            return json.loads(simplified.to_json())
                
        except Exception as simplify_err:
            raise ValueError("Unable to convert GeoDataFrame to GeoJSON")

def ensure_valid_geodataframe(gdf):
    """
    Ensure the GeoDataFrame is valid and properly formatted.
    Returns a cleaned GeoDataFrame.
    
    Args:
        gdf (GeoDataFrame): Input GeoDataFrame
        
    Returns:
        GeoDataFrame: Cleaned GeoDataFrame
    """
    if not isinstance(gdf, gpd.GeoDataFrame):
        raise ValueError("Input is not a GeoDataFrame")
    
    # Check if the geometry column exists
    if 'geometry' not in gdf.columns:
        raise ValueError("GeoDataFrame does not have a geometry column")
    
    # Check for empty or null geometries and remove them
    valid_gdf = gdf[~gdf.geometry.isna() & ~gdf.geometry.is_empty].copy()
    
    # Simplify geometries if the dataset is large
    if len(valid_gdf) > 500:
        valid_gdf['geometry'] = valid_gdf.geometry.simplify(tolerance=0.001)
    
    # Ensure the CRS is set
    if valid_gdf.crs is None:
        # Default to WGS84 if no CRS
        valid_gdf.crs = "EPSG:4326"
    
    # Convert to WGS84 if needed
    if str(valid_gdf.crs) != "EPSG:4326":
        valid_gdf = valid_gdf.to_crs(epsg=4326)
    
    return valid_gdf

# Enhanced find_name_field function for file_utils.py

def find_name_field(gdf):
    """
    Find the most likely column containing feature names with enhanced detection.
    
    Args:
        gdf: GeoDataFrame to search
        
    Returns:
        str: Name of column with feature names, or None if not found
    """
    if gdf is None or len(gdf) == 0:
        return None
    
    # Debug the dataframe columns
    print(f"Looking for name field in columns: {gdf.columns.tolist()}")
    
    # Common name field patterns in GIS datasets - expanded list
    name_patterns = [
        # Exact matches (case variations)
        'name', 'NAME', 'Name',
        'county', 'COUNTY', 'County',
        'label', 'LABEL', 'Label',
        'title', 'TITLE', 'Title',
        'city', 'CITY', 'City',
        'state', 'STATE', 'State',
        'place', 'PLACE', 'Place',
        'location', 'LOCATION', 'Location',
        
        # Combined patterns
        'countyname', 'COUNTYNAME', 'CountyName', 'county_name', 'COUNTY_NAME',
        'statename', 'STATENAME', 'StateName', 'state_name', 'STATE_NAME',
        'cityname', 'CITYNAME', 'CityName', 'city_name', 'CITY_NAME',
        'placename', 'PLACENAME', 'PlaceName', 'place_name', 'PLACE_NAME',
        
        # Prefixes and suffixes
        'name_', 'NAME_', 'Name_',
        '_name', '_NAME', '_Name',
        'nam', 'NAM', 'Nam',
        
        # Additional county variations
        'county_nm', 'cnty_name', 'co_name', 'cnty', 'co_nm',
        'COUNTY_NM', 'CNTY_NAME', 'CO_NAME', 'CNTY', 'CO_NM'
    ]
    
    # Check for direct exact matches first
    for pattern in name_patterns:
        if pattern in gdf.columns:
            print(f"Found exact match: {pattern}")
            return pattern
    
    # Check for columns containing the patterns
    for col in gdf.columns:
        col_lower = col.lower()
        # Check if any of the patterns appear in the column name
        for pattern in ['name', 'county', 'city', 'label', 'title']:
            if pattern in col_lower and 'geom' not in col_lower and 'id' not in col_lower:
                print(f"Found pattern match: {col} contains '{pattern}'")
                return col
    
    # Look for string columns that might contain names
    string_columns = []
    for col in gdf.columns:
        if col != 'geometry' and gdf[col].dtype == 'object':
            # Sample value formats
            sample = gdf[col].dropna().head(5)
            if len(sample) > 0:
                # Count string-like characteristics
                score = 0
                for val in sample:
                    if isinstance(val, str):
                        # Check for characteristics that suggest it's a name
                        if ' ' in val:  # Contains spaces
                            score += 2
                        if val.istitle() or val.isupper():  # Title case or all caps
                            score += 2
                        if any(c.isalpha() for c in val):  # Contains letters
                            score += 1
                        if len(val) > 3:  # More than 3 characters
                            score += 1
                
                if score > 5:  # Higher threshold for confidence
                    string_columns.append((col, score))
    
    # Sort string columns by score
    if string_columns:
        string_columns.sort(key=lambda x: x[1], reverse=True)
        best_col, score = string_columns[0]
        print(f"Found string column match: {best_col} with score {score}")
        return best_col
    
    # If all else fails, try to find the first non-numeric column
    for col in gdf.columns:
        if col != 'geometry' and not pd.api.types.is_numeric_dtype(gdf[col]):
            print(f"Falling back to non-numeric column: {col}")
            return col
    
    # No suitable field found
    print("No name field found")
    return None

def find_id_field(gdf):
    """
    Find the most likely column containing feature IDs.
    
    Args:
        gdf: GeoDataFrame to search
        
    Returns:
        str: Name of ID column, or None if not found
    """
    if gdf is None or len(gdf) == 0:
        return None
    
    # Common ID field patterns
    id_patterns = [
        'id', 'fid', 'gid', 'objectid', 'feature_id', 'featureid',
        'ID', 'FID', 'GID', 'OBJECTID', 'FEATURE_ID', 'FEATUREID',
        'Id', 'Fid', 'Gid', 'ObjectId', 'FeatureId', 'feature_id'
    ]
    
    # Check for direct matches
    for col in gdf.columns:
        if col.lower() in [p.lower() for p in id_patterns]:
            return col
    
    # Check for partial matches with _id
    for col in gdf.columns:
        if '_id' in col.lower() or 'id_' in col.lower():
            return col
    
    # Check for index column
    if 'index' in gdf.columns:
        return 'index'
    
    # Fallback to first numeric column that has unique values
    for col in gdf.columns:
        if col != 'geometry':
            if pd.api.types.is_numeric_dtype(gdf[col]):
                if gdf[col].nunique() == len(gdf):
                    return col
    
    # No ID field found, create a new one as last resort
    return None