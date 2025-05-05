# Suitable: Interactive Suitability Analysis Tool

A comprehensive web application that guides users through the suitability analysis process with a simple interface, eliminating the need for specialized GIS knowledge.

## Features

- Interactive user prompts for suitability criteria selection
- Loading and visualization of geospatial data
- Multiple analysis types (weighted overlay and boolean)
- Real-time visualization of datasets and results
- Customizable weighting for different criteria
- Export functionality for GeoJSON, Shapefile, and CSV

## Getting Started

### Prerequisites

- Python 3.8+
- Required packages: geopandas, pandas, numpy, matplotlib, folium, ipywidgets

### Installation

1. Clone this repository:
- git clone https://github.com/yourusername/suitable.git
- cd suitable

2. Install dependencies
- pip install -r requirements.txt

3. Run the Jupyter notebook version:
- jupyter notebook app.ipynb

## Project Structure
suitable/
├── app.py                      # Main entry point
├── components/                 # Core components
│   ├── data_loader.py          # Data loading functionality
│   ├── analysis.py             # Analysis methods
│   ├── map_display.py          # Map visualization
│   └── results_export.py       # Results export functionality
├── models/                     # Data models
│   ├── criterion.py            # Criterion class
│   └── project.py              # Project configuration
└── utils/                      # Utility functions
├── geo_processing.py           # Geospatial operations
└── file_utils.py               # File handling utilities

## Usage

1. Define a boundary dataset by uploading a GeoJSON or zipped Shapefile
2. Add criteria by selecting datasets and defining processing methods
3. Run the analysis with your preferred method
4. Explore the results on the interactive map
5. Export the results in your preferred format

## Contributing

Contributions are welcome! Please feel free to submit a Pull Request.