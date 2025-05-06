import streamlit as st
from streamlit_folium import st_folium
import geopandas as gpd
import pandas as pd
import numpy as np
import json
from datetime import datetime
import matplotlib.pyplot as plt

# Import components
from models.project import Project
from models.criterion import Criterion
from components.data_loader import DataLoader
from components.analysis import SuitabilityAnalyzer
from components.results_export import ResultsExporter

# Import utility modules
from utils.file_utils import generate_unique_id, ensure_valid_geodataframe, find_name_field, find_id_field
from utils.map_utils import display_map_with_st_folium, add_map_layer, add_results_layer
from utils.boundary_utils import process_boundary_upload

# Set page configuration
st.set_page_config(
    page_title="Suitable - The Suitability Analysis Tool",
    page_icon="🗺️",
    layout="wide"
)

# Initialize session state to store app state between reruns
if 'project' not in st.session_state:
    st.session_state.project = Project.from_session_state(st.session_state) if hasattr(Project, 'from_session_state') else Project()
    st.session_state.data_loader = DataLoader()
    st.session_state.analyzer = SuitabilityAnalyzer()
    st.session_state.criteria_count = 0
    st.session_state.has_boundary = False
    st.session_state.has_result = False

# Initialize map-related session state variables
if 'map_layers' not in st.session_state:
    st.session_state.map_layers = {}
if 'map_center' not in st.session_state:
    # Always initialize as a list, not a dict
    st.session_state.map_center = [39.8283, -98.5795]  # Default to center of US
if 'map_zoom' not in st.session_state:
    st.session_state.map_zoom = 3
if 'force_map_refresh' not in st.session_state:
    st.session_state.force_map_refresh = False
if 'last_boundary_file' not in st.session_state:
    st.session_state.last_boundary_file = None
if 'dataset_upload_processed' not in st.session_state:
    st.session_state.dataset_upload_processed = {}
if 'used_colors' not in st.session_state:
    st.session_state.used_colors = []
if 'last_clicked' not in st.session_state:
    st.session_state.last_clicked = {}
# Key addition for tab state tracking
if 'active_tab' not in st.session_state:
    st.session_state.active_tab = 0  # Default to first tab
if 'zoom_to_boundary_requested' not in st.session_state:
    st.session_state.zoom_to_boundary_requested = False

# Function to track UI interactions
def track_click(widget_id):
    st.session_state.last_clicked = widget_id

# Function to handle tab changes
def handle_tab_change(tab_index):
    st.session_state.active_tab = tab_index

# App title and description
st.title("Suitable - The Suitability Analysis Tool")
st.write("Find the most suitable areas based on your criteria and datasets.")

# Create a two-column layout for the app
map_col, controls_col = st.columns([3, 2])

with map_col:
    st.subheader("Interactive Map")
    
    # Display the map and get refresh status
    force_refresh = display_map_with_st_folium()
    
    # Add map control buttons in two columns
    button_col1, button_col2 = st.columns(2)
    
    # Add refresh button in first column
    with button_col1:
        if st.button("Refresh Map", key="refresh_map_btn"):
            st.session_state.force_map_refresh = True
            st.rerun()  # Using rerun for better state preservation
    
    # Add zoom to boundary button in second column 
    with button_col2:
        zoom_boundary = st.button("🏠 Zoom to Boundary", key="zoom_boundary_btn")
        if 'boundary_bounds' in st.session_state and zoom_boundary:
            st.session_state.force_map_refresh = True
            st.session_state.zoom_to_boundary_requested = True
            st.rerun() # Using rerun for better state preservation
    
    # If the map was just refreshed, inform the user
    if force_refresh:
        st.success("Map updated!")

# Place the workflow tabs in the right column
with controls_col:
    # Create tabs for the workflow
    tab1, tab2, tab3, tab4, tab5 = st.tabs([
        "1. Project Info", 
        "2. Boundary", 
        "3. Criteria", 
        "4. Analysis", 
        "5. Export"
    ])

    # Tab 1: Project Information
    with tab1:
        st.header("Project Information")
        
        # Project title and description inputs
        project_title = st.text_input("Project Title", value=st.session_state.project.title if hasattr(st.session_state.project, 'title') else 'Suitability Analysis Project')
        project_description = st.text_area("Project Description", value=st.session_state.project.description if hasattr(st.session_state.project, 'description') else 'Find the most suitable areas based on your criteria and datasets.')
        
        # Update project when inputs change
        if project_title != st.session_state.project.title:
            st.session_state.project.title = project_title
        
        if project_description != st.session_state.project.description:
            st.session_state.project.description = project_description
        
        # Show project summary (if available)
        if hasattr(st.session_state.project, 'display_summary'):
            st.subheader("Project Summary")
            st.session_state.project.display_summary()

    # Tab 2: Define Boundary
    with tab2:
        st.header("Define Boundary Dataset")
        
        # No need for columns since the map is already displayed
        st.write("Upload a boundary dataset or draw directly on the map.")
        
        # Upload boundary file
        boundary_file = st.file_uploader(
            "Upload Boundary Dataset (GeoJSON, Shapefile)",
            type=["geojson", "json", "zip"],
            help="Upload a GeoJSON file or zipped Shapefile that defines your area of interest."
        )
        
        # Check if a new file has been uploaded
        if boundary_file is not None:
            if st.session_state.last_boundary_file != boundary_file.name:
                st.session_state.last_boundary_file = boundary_file.name
                if process_boundary_upload(boundary_file):
                    # Add a rerun button that will appear after successful upload
                    if st.button("Update Map with Boundary"):
                        # Reset the has_fitted_bounds flag to ensure zooming occurs
                        st.session_state.has_fitted_bounds = False 
                        # Set active tab to Boundary (index 1)
                        st.session_state.active_tab = 1
                        st.write("Updating map...")
                        # Use rerun for better state preservation
                        st.rerun()
        elif boundary_file is None:
            # Reset the tracking when file is cleared
            st.session_state.last_boundary_file = None
        
        # Show current boundary info if available
        if st.session_state.has_boundary and hasattr(st.session_state.project, 'boundary_dataset'):
            with st.expander("Current Boundary Info", expanded=False):
                gdf = st.session_state.project.boundary_dataset
                st.write(f"Boundary has {len(gdf)} features")
                st.write(f"CRS: {gdf.crs}")
                # Display a few records
                try:
                    # Try to show a sample without the geometry column
                    preview_df = gdf.drop(columns=['geometry']).head(3)
                    st.dataframe(preview_df)
                except:
                    # Fall back to just displaying column names
                    st.write(f"Columns: {', '.join([c for c in gdf.columns if c != 'geometry'])}")

    # Tab 3: Define Criteria
    with tab3:
        st.header("Define Criteria")
        
        # Enable/disable based on boundary
        if not st.session_state.has_boundary:
            st.warning("Please define a boundary dataset first.")
        else:
            st.write("Add criteria for your analysis using the boundary dataset or other datasets.")
            
            # Initialize session state variables if they don't exist
            if 'criterion_name' not in st.session_state:
                st.session_state.criterion_name = f"Criterion {st.session_state.criteria_count + 1}"
            if 'data_source' not in st.session_state:
                st.session_state.data_source = "+ Upload New Dataset"
            if 'processing_method' not in st.session_state:
                st.session_state.processing_method = 'Direct Value'
            if 'column' not in st.session_state:
                st.session_state.column = "None/NA"
            if 'weight' not in st.session_state:
                st.session_state.weight = 0.5
            if 'preference' not in st.session_state:
                st.session_state.preference = 'Higher is better'
            
            # Define which methods require a column selection
            methods_requiring_column = [
                'Direct Value',
                'Sum Values',
                'Average Values',
                'Minimum Value',
                'Maximum Value',
            ]
            
            # Create columns for the criterion form
            col1, col2 = st.columns(2)
            
            # First column
            with col1:
                st.session_state.criterion_name = st.text_input(
                    "Criterion Name", 
                    value=st.session_state.criterion_name
                )
                
                # Data source options - Make sure this is refreshing properly
                data_source_options = ["+ Upload New Dataset"]
                if hasattr(st.session_state.project, 'datasets'):
                    # Get the dataset names from the project
                    dataset_names = list(st.session_state.project.datasets.keys())
                    data_source_options.extend(dataset_names)

                # Ensure data_source has a valid value
                if st.session_state.data_source not in data_source_options:
                    if len(data_source_options) > 1:
                        st.session_state.data_source = data_source_options[1]  # First real dataset
                    else:
                        st.session_state.data_source = data_source_options[0]  # Upload option

                # Display dropdown with all available datasets
                st.session_state.data_source = st.selectbox(
                    "Data Source", 
                    data_source_options,
                    index=data_source_options.index(st.session_state.data_source)
                )

                # File uploader
                dataset_file = None
                if st.session_state.data_source == "+ Upload New Dataset":
                    dataset_file = st.file_uploader(
                        "Upload Dataset",
                        type=["geojson", "json", "zip"],
                        key=f"criterion_upload_{st.session_state.criteria_count}"
                    )
                    
                    # Process the uploaded file right away
                    if dataset_file is not None:
                        upload_key = f"criterion_upload_{st.session_state.criteria_count}"
                        file_identifier = f"{dataset_file.name}_{dataset_file.size}"
                        
                        if upload_key not in st.session_state.dataset_upload_processed or st.session_state.dataset_upload_processed[upload_key] != file_identifier:
                            try:
                                # Mark as processed with file identifier
                                st.session_state.dataset_upload_processed[upload_key] = file_identifier
                                
                                with st.spinner(f"Processing {dataset_file.name}..."):
                                    # Check if this is a polygon dataset that needs special handling
                                    if "public_water" in dataset_file.name.lower():
                                        # Use the boundary loading method for this dataset
                                        gdf, dataset_name = st.session_state.data_loader.load_boundary(dataset_file)
                                        # Remove the "Boundary: " prefix
                                        dataset_name = dataset_name.replace("Boundary: ", "")
                                    else:
                                        # Standard loading for other datasets
                                        gdf, dataset_name = st.session_state.data_loader.load_dataset(dataset_file)
                                    
                                    # Generate unique name
                                    unique_dataset_name = f"{dataset_name}_{datetime.now().strftime('%Y%m%d%H%M%S')}"
                                    
                                    # Add to project
                                    st.session_state.project.datasets[unique_dataset_name] = gdf
                                    
                                    # Update data source
                                    st.session_state.data_source = unique_dataset_name
                                    
                                    # Try to display on map
                                    add_map_layer(gdf, unique_dataset_name)
                                    
                                    # Set active tab to ensure we stay on criteria tab
                                    st.session_state.active_tab = 2
                                    
                                    # Force UI refresh
                                    st.success(f"Dataset loaded: {dataset_name}")
                                    st.rerun()  # Using rerun for better state preservation
                                
                            except Exception as e:
                                st.error(f"Error loading dataset: {str(e)}")
                                st.session_state.dataset_upload_processed[upload_key] = None
                            
            # Second column
            with col2:
                # Processing methods
                processing_methods = [
                    'Direct Value',
                    'Count Features',
                    'Sum Values',
                    'Average Values',
                    'Minimum Value',
                    'Maximum Value',
                    'Area Within Boundary',
                    'Length Within Boundary',
                    'Distance to Nearest',
                    'Percent Coverage',
                ]
                
                # Add key to force re-render with tracking for tab state preservation
                st.session_state.processing_method = st.selectbox(
                    "Processing Method", 
                    processing_methods,
                    index=processing_methods.index(st.session_state.processing_method),
                    key="processing_method_selector",
                    on_change=track_click,
                    args=("processing_method_selector",)
                )
                
                # Determine if column selection is needed
                column_required = st.session_state.processing_method in methods_requiring_column
                
                # Show column selection only if required
                if column_required:
                    column_options = []
                    if st.session_state.data_source != "+ Upload New Dataset" and st.session_state.data_source in st.session_state.project.datasets:
                        df = st.session_state.project.datasets[st.session_state.data_source]
                        column_options = [col for col in df.columns if col != 'geometry']
                    
                    if column_options:
                        st.session_state.column = st.selectbox(
                            "Column", 
                            column_options,
                            index=0 if st.session_state.column not in column_options else column_options.index(st.session_state.column)
                        )
                    else:
                        st.warning("No columns available in the selected dataset")
                        st.session_state.column = "None/NA"
                else:
                    # Set to None/NA but don't display
                    st.session_state.column = "None/NA"
                
                # Weight
                st.session_state.weight = st.slider("Weight", 0.0, 1.0, st.session_state.weight, 0.1)
                
                # Preference
                preferences = ['Higher is better', 'Lower is better']
                st.session_state.preference = st.selectbox(
                    "Preference", 
                    preferences,
                    index=preferences.index(st.session_state.preference)
                )
            
            # Add button (outside the columns) with key fix for state preservation
            if st.button("Add Criterion", key="add_criterion_btn"):
                # Set active tab to Criteria (index 2) to ensure we stay on this tab after rerun
                st.session_state.active_tab = 2
                
                # Only proceed if data source is valid
                if st.session_state.data_source and st.session_state.data_source != "+ Upload New Dataset":
                    try:
                        # Create criterion
                        criterion = Criterion(
                            id=f"criterion_{st.session_state.criteria_count}",
                            name=st.session_state.criterion_name,
                            data_source=st.session_state.data_source,
                            processing_method=st.session_state.processing_method,
                            column=st.session_state.column if st.session_state.column != "None/NA" else "",
                            weight=st.session_state.weight,
                            preference=st.session_state.preference
                        )
                        
                        # Add to project
                        st.session_state.project.add_criterion(criterion)
                        
                        # Increment counter
                        st.session_state.criteria_count += 1
                        
                        # Store added criterion name for success message
                        added_name = criterion.name
                        
                        # Reset name field but keep the same data source for convenience
                        st.session_state.criterion_name = f"Criterion {st.session_state.criteria_count + 1}"
                        # st.session_state.data_source remains unchanged
                        
                        # Force stay on criteria tab before rerun
                        st.session_state.active_tab = 2
                        
                        # Success message
                        st.success(f"Added criterion: {added_name}")
                        
                        # Use rerun which is more reliable for state preservation
                        st.rerun()
                    except Exception as e:
                        st.error(f"Error adding criterion: {str(e)}")
                else:
                    st.error("Please select a valid data source before adding the criterion")
            
            # Display existing criteria
            if hasattr(st.session_state.project, 'criteria') and st.session_state.project.criteria:
                st.subheader("Defined Criteria")
                
                for criterion in st.session_state.project.criteria:
                    with st.expander(f"{criterion.name} ({criterion.data_source})"):
                        # Use the display_info method if available
                        if hasattr(criterion, 'display_info'):
                            criterion.display_info()
                        else:
                            st.write(f"**Processing Method:** {criterion.processing_method}")
                            st.write(f"**Column:** {criterion.column if criterion.column else 'N/A'}")
                            st.write(f"**Weight:** {criterion.weight}")
                            st.write(f"**Preference:** {criterion.preference}")
                        
                        # Option to remove criterion with tab state preservation
                        if st.button("Remove", key=f"remove_{criterion.id}"):
                            # Set active tab before removing
                            st.session_state.active_tab = 2
                            st.session_state.project.remove_criterion(criterion.id)
                            st.rerun()  # Using rerun for better state preservation

    # Tab 4: Run Analysis
    with tab4:
        st.header("Run Suitability Analysis")
        
        # Check if analysis can be run
        if not st.session_state.has_boundary:
            st.warning("Please define a boundary dataset first.")
        elif not st.session_state.project.criteria:
            st.warning("Please define at least one criterion first.")
        else:
            # Analysis settings
            st.subheader("Analysis Settings")
            
            # Analysis type selection
            analysis_type = st.selectbox(
                "Analysis Type",
                options=['weighted_sum', 'boolean'],
                format_func=lambda x: 'Weighted Sum' if x == 'weighted_sum' else 'Boolean'
            )
            
            # Boolean analysis options (shown only for boolean analysis)
            boolean_mode = None
            threshold = None
            if analysis_type == 'boolean':
                boolean_mode = st.selectbox(
                    "Boolean Mode",
                    options=['all', 'any', 'majority', 'percentage'],
                    format_func=lambda x: {
                        'all': 'All Criteria',
                        'any': 'Any Criterion',
                        'majority': 'Majority of Criteria',
                        'percentage': 'Percentage of Criteria'
                    }.get(x, x)
                )
                
                threshold = st.slider("Threshold", 0.0, 1.0, 0.5, 0.05)
            
            # Enhanced weights summary table
            st.subheader("Criteria Weights Summary")
            
            if hasattr(st.session_state.project, 'criteria') and st.session_state.project.criteria:
                # Create a DataFrame to display criteria weights
                weights_data = {
                    'Criterion': [c.name for c in st.session_state.project.criteria],
                    'Data Source': [c.data_source for c in st.session_state.project.criteria],
                    'Weight': [c.weight for c in st.session_state.project.criteria],
                    'Processing Method': [c.processing_method for c in st.session_state.project.criteria],
                    'Preference': [c.preference for c in st.session_state.project.criteria]
                }
                
                weights_df = pd.DataFrame(weights_data)
                
                # Calculate normalized weights
                total_weight = weights_df['Weight'].sum()
                if total_weight > 0:
                    weights_df['Normalized Weight'] = weights_df['Weight'] / total_weight
                    weights_df['Percent Impact'] = weights_df['Normalized Weight'].apply(lambda x: f"{x:.1%}")
                else:
                    # If all weights are 0, use equal weighting
                    equal_weight = 1.0 / len(weights_df)
                    weights_df['Normalized Weight'] = equal_weight
                    weights_df['Percent Impact'] = f"{equal_weight:.1%}"
                
                # Create a colored bar visualization of weights
                weights_df['Visual Weight'] = weights_df['Normalized Weight'].apply(
                    lambda x: '█' * int(x * 20)  # Scale to 20 characters max
                )
                
                # Display the weights table with nice formatting
                formatted_weights = weights_df[['Criterion', 'Data Source', 'Weight', 'Percent Impact', 'Visual Weight', 'Processing Method', 'Preference']]
                st.dataframe(
                    formatted_weights.style.format({
                        'Weight': '{:.2f}',
                        'Normalized Weight': '{:.3f}'
                    }),
                    use_container_width=True
                )
                
                # Add a pie chart to visualize weight distribution
                if st.checkbox("Show Weight Distribution Chart", value=True):
                    fig, ax = plt.subplots(figsize=(5, 5))
                    wedges, texts, autotexts = ax.pie(
                        weights_df['Normalized Weight'], 
                        labels=weights_df['Criterion'],
                        autopct='%1.1f%%',
                        startangle=90,
                        wedgeprops={'linewidth': 1, 'edgecolor': 'white'}
                    )
                    ax.set_title('Criteria Weight Distribution')
                    st.pyplot(fig)
            
            # Run analysis button with tab state preservation
            run_analysis = st.button("Run Suitability Analysis", key="run_analysis_btn")

            if run_analysis:
                # Set active tab to Analysis tab (index 3)
                st.session_state.active_tab = 3
                
                with st.spinner("Running analysis..."):
                    try:
                        # Create analyzer with selected options
                        analyzer = SuitabilityAnalyzer(analysis_type)
                        
                        # Set boolean options if applicable
                        if analysis_type == 'boolean':
                            analyzer.boolean_mode = boolean_mode
                            analyzer.threshold = threshold
                        
                        # Run the analysis
                        result = analyzer.run_analysis(st.session_state.project)
                        
                        # Store the result
                        st.session_state.project.set_result(result)
                        st.session_state.has_result = True
                        
                        # Set the force refresh flag
                        st.session_state.force_map_refresh = True
                        
                        # Add results to map layers
                        add_results_layer(
                            st.session_state.project.result,
                            value_column='suitability_score',
                            title='Suitability Results'
                        )
                        
                        # Success message
                        st.success("Analysis complete! Results displayed on the map.")
                        
                        # Force UI refresh with rerun
                        st.rerun()
                        
                    except Exception as e:
                        st.error(f"Error running analysis: {str(e)}")
                        import traceback
                        st.write(traceback.format_exc())
            
            # Also display existing results if available (but weren't just created)
            elif st.session_state.has_result:
                st.success("Analysis previously completed.")
                
                # Display the results
                add_results_layer(
                    st.session_state.project.result,
                    value_column='suitability_score',
                    title='Suitability Results'
                )
                
                # Create a table of top results
                # Try to find a name field for identification
                result_gdf = st.session_state.project.result
                
                # Round suitability scores to 2 decimal places
                result_gdf['suitability_score'] = result_gdf['suitability_score'].round(2)
                
                # Look for county/feature name - be more specific about the patterns
                name_field = find_name_field(result_gdf)
                
                # Set up columns to display
                display_columns = ['suitability_score']
                
                # If we found a name field, use it
                if name_field:
                    display_columns.insert(0, name_field)
                    st.info(f"Using '{name_field}' column for feature names")
                else:
                    # Try to find an ID field
                    id_field = find_id_field(result_gdf)
                    if id_field:
                        display_columns.insert(0, id_field)
                        st.info(f"Using '{id_field}' identifier column")
                    else:
                        # Use index as last resort
                        result_gdf = result_gdf.reset_index().rename(columns={'index': 'feature_id'})
                        display_columns.insert(0, 'feature_id')
                        st.info("Using index as feature identifier")
                
                # Add criterion-specific columns
                criterion_score_columns = [col for col in result_gdf.columns if col.endswith('_score') and col != 'suitability_score']
                display_columns.extend(criterion_score_columns)
                
                # Add boolean-specific columns if applicable
                if 'criteria_met_count' in result_gdf.columns:
                    display_columns.append('criteria_met_count')
                    if 'is_suitable' in result_gdf.columns:
                        display_columns.append('is_suitable')
                
                # Format the results DataFrame
                results_df = result_gdf[display_columns].sort_values('suitability_score', ascending=False)
                
                # Make the display nicer with formatting
                fmt_results = results_df.copy()
                for col in fmt_results.columns:
                    if col.endswith('_score'):
                        # Format scores to 2 decimal places
                        fmt_results[col] = fmt_results[col].apply(lambda x: f"{x:.2f}")
                
                # Display the results with a caption
                st.subheader("Top Results")
                st.write("Showing top areas by suitability score:")
                st.dataframe(fmt_results.head(10), use_container_width=True)
                
                # Add statistics about the results
                st.subheader("Results Statistics")
                
                # Create two columns for statistics
                stat_col1, stat_col2 = st.columns(2)
                
                with stat_col1:
                    st.metric("Average Suitability Score", f"{result_gdf['suitability_score'].mean():.2f}")
                    st.metric("Minimum Score", f"{result_gdf['suitability_score'].min():.2f}")
                    st.metric("Maximum Score", f"{result_gdf['suitability_score'].max():.2f}")
                
                with stat_col2:
                    # Get count of features in different suitability ranges
                    low_count = len(result_gdf[result_gdf['suitability_score'] < 0.33])
                    med_count = len(result_gdf[(result_gdf['suitability_score'] >= 0.33) & 
                                            (result_gdf['suitability_score'] < 0.66)])
                    high_count = len(result_gdf[result_gdf['suitability_score'] >= 0.66])
                    
                    st.metric("Low Suitability Areas (< 0.33)", low_count)
                    st.metric("Medium Suitability Areas (0.33-0.66)", med_count)
                    st.metric("High Suitability Areas (> 0.66)", high_count)
                
                # Add histogram of suitability scores
                st.subheader("Distribution of Suitability Scores")
                
                # Create histogram data
                hist_data = np.histogram(
                    result_gdf['suitability_score'], 
                    bins=10, 
                    range=(0, 1)
                )
                hist_values = hist_data[0]
                hist_bins = hist_data[1][:-1]  # exclude the last bin edge
                
                # Create a DataFrame for the histogram
                hist_df = pd.DataFrame({
                    'Score Range': [f"{round(bin, 1)}-{round(bin+0.1, 1)}" for bin in hist_bins],
                    'Count': hist_values
                })
                
                # Display the histogram
                st.bar_chart(hist_df.set_index('Score Range'))
                        
    # Tab 5: Export Results
    with tab5:
        st.header("Export Results")
        
        if not st.session_state.get("has_result", False):
            st.warning("Please run an analysis first to generate results.")
        else:
            st.write("Export your suitability analysis results in your preferred format.")
            
            # File name input
            safe_name = ''.join(c if c.isalnum() else '_' for c in st.session_state.project.title)
            filename_base = st.text_input("Base Filename", value=f"suitability_results_{safe_name}")
            
            # Create columns for download buttons
            col1, col2, col3 = st.columns(3)
            
            # GeoJSON download button
            with col1:
                if st.button("Prepare GeoJSON Download"):
                    # Set active tab to Export tab (index 4)
                    st.session_state.active_tab = 4
                    
                    with st.spinner("Preparing GeoJSON..."):
                        # Only create exporter and process result when button is clicked
                        exporter = ResultsExporter()
                        result_gdf = st.session_state.project.result
                        geojson_data = exporter.export_geojson(result_gdf, filename_base)
                        geojson_str = json.dumps(geojson_data)
                        
                        # Store in session state for the download button
                        st.session_state.geojson_download_data = geojson_str
                        st.session_state.geojson_filename = f"{filename_base}.geojson"
                        
                        st.success("GeoJSON prepared!")
                
                # Only show download button if data is prepared
                if st.session_state.get("geojson_download_data") is not None:
                    st.download_button(
                        label="Download GeoJSON",
                        data=st.session_state.geojson_download_data,
                        file_name=st.session_state.geojson_filename,
                        mime="application/json"
                    )
            
            # Shapefile download button
            with col2:
                if st.button("Prepare Shapefile Download"):
                    # Set active tab to Export tab (index 4)
                    st.session_state.active_tab = 4
                    
                    with st.spinner("Preparing Shapefile..."):
                        try:
                            # Only create exporter and process when button is clicked
                            exporter = ResultsExporter()
                            result_gdf = st.session_state.project.result
                            zip_data, zip_filename = exporter.export_shapefile(result_gdf, filename_base)
                            
                            # Store in session state for the download button
                            st.session_state.shapefile_download_data = zip_data
                            st.session_state.shapefile_filename = zip_filename
                            
                            st.success("Shapefile prepared!")
                        except Exception as e:
                            st.error(f"Error creating shapefile: {str(e)}")
                
                # Only show download button if data is prepared
                if st.session_state.get("shapefile_download_data") is not None:
                    st.download_button(
                        label="Download Shapefile (ZIP)",
                        data=st.session_state.shapefile_download_data,
                        file_name=st.session_state.shapefile_filename,
                        mime="application/zip"
                    )
            
            # CSV download button
            with col3:
                if st.button("Prepare CSV Download"):
                    # Set active tab to Export tab (index 4)
                    st.session_state.active_tab = 4
                    
                    with st.spinner("Preparing CSV..."):
                        # Only create exporter and process when button is clicked
                        exporter = ResultsExporter()
                        result_gdf = st.session_state.project.result
                        csv_data = exporter.export_csv(result_gdf, filename_base)
                        
                        # Store in session state for the download button
                        st.session_state.csv_download_data = csv_data
                        st.session_state.csv_filename = f"{filename_base}.csv"
                        
                        st.success("CSV prepared!")
                
                # Only show download button if data is prepared
                if st.session_state.get("csv_download_data") is not None:
                    st.download_button(
                        label="Download CSV",
                        data=st.session_state.csv_download_data,
                        file_name=st.session_state.csv_filename,
                        mime="text/csv"
                    )
            
            # Display data preview
            preview_expander = st.expander("Preview Data")
            with preview_expander:
                if st.button("Load Preview Data", key="load_preview"):
                    # Set active tab to Export tab (index 4)
                    st.session_state.active_tab = 4
                    
                    st.write("Top 5 rows of the results:")
                    # Display top 5 rows without geometry column
                    result_gdf = st.session_state.project.result
                    preview_df = result_gdf.drop(columns=['geometry']).head(5)
                    st.dataframe(preview_df)