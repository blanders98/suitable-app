# Suitable: Interactive Suitability Analysis Tool

A geospatial web application for suitability analysis that guides users through the process with an intuitive interface, allowing them to input their own datasets, and eliminating the need for specialized geospatial knowledge.

## Overview

Suitable is a streamlined geospatial analysis tool that helps users identify optimal locations based on custom criteria. Whether you're looking for the best areas for solar panel installation, evaluating land for agricultural purposes, or analyzing urban development potential, Suitable provides a powerful yet accessible framework for geographic decision-making.

## Features

- **Interactive Map Interface**: Continuous map display throughout the analysis process
- **Flexible Data Handling**: Upload boundary datasets and criteria in common formats (GeoJSON, Shapefile)
- **Multiple Analysis Methods**: Choose between weighted sum and boolean approaches
- **Customizable Criteria**: Define and weight various spatial factors
- **Dynamic Visualization**: Real-time preview of datasets with intelligent styling
- **Comprehensive Results**: Color-coded results with detailed statistics and distribution analysis
- **Export Options**: Save results as GeoJSON, Shapefile, or CSV for further use

## Getting Started

### Prerequisites

- Python 3.8+
- Required packages: streamlit, folium, streamlit-folium, geopandas, pandas, numpy, matplotlib, branca

### Local Installation

1. Clone this repository:
   ```bash
   git clone https://github.com/blanders98/suitable-app.git
   cd suitable-app

2. Install dependencies:
   ```bash
   pip install -r requirements.txt

3. Run the streamlit application:
    ```bash
    streamlit run app.py

## Project Structure

Suitable/
├── app.py                      # Main entry point with UI components
├── app_testing.ipynb           # Jupyter notebook for testing
├── README.md                   # Documentation
├── requirements.txt            # Dependencies
├── .streamlit/                 # Streamlit configuration
│   └── config.toml             # Theme and behavior settings
├── components/                 # Core components
│   ├── init.py
│   ├── data_loader.py          # Data loading functionality
│   ├── analysis.py             # Analysis methods
│   ├── map_display.py          # Map visualization (using folium)
│   └── results_export.py       # Results export functionality
├── models/                     # Data models
│   ├── init.py
│   ├── criterion.py            # Criterion class
│   └── project.py              # Project configuration
└── utils/                      # Utility functions
    ├── init.py
    ├── boundary_utils.py       # Boundary processing functions
    ├── file_utils.py           # File handling utilities
    ├── geo_processing.py       # Geospatial operations
    └── map_utils.py            # Map display and interaction

## Usage Guide

### 1. Project Information
- Define your project title and description
- This metadata will be included in your exported results

### 2. Define Boundary
- Upload a boundary dataset (GeoJSON or zipped Shapefile)
- This defines the area of interest for your analysis
- View boundary information and preview on the map

### 3. Define Criteria
- Add analysis criteria by either:
  - Uploading new datasets
  - Using previously loaded datasets
- Configure each criterion with:
  - Processing method (direct value, count features, distance, etc.)
  - Column selection (when applicable)
  - Weight (importance factor)
  - Preference (higher/lower is better)
- Review and manage your defined criteria

### 4. Run Analysis
- Choose analysis type:
  - Weighted Sum: Combines all criteria based on their weights
  - Boolean: Identifies areas meeting specific conditions
- Customize analysis parameters
- Review weight distribution and impact percentages
- Run the analysis to generate results

### 5. Export Results
- Review results statistics and distribution
- Export results in your preferred format:
  - GeoJSON for web applications
  - Shapefile for desktop GIS
  - CSV for tabular analysis

## Development Status

The project has completed the following phases:
- ✅ Phase 1: Modularization
- ✅ Phase 2: Enhanced Analysis Methods
- ✅ Phase 3: Interactive Map
- ✅ Phase 4: Streamlit Integration
- ✅ Phase 5: Deployment