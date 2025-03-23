"""
Debug utilities for StravaTalk application.
"""

import streamlit as st
import pandas as pd
import traceback

def is_debug_mode():
    """Check if debug mode is enabled"""
    return st.session_state.get("debug_mode", False)

def setup_debug_mode():
    """Setup debug mode from URL parameters"""
    query_params = st.query_params
    debug_mode = query_params.get('debug') == 'true'
    st.session_state.debug_mode = debug_mode
    return debug_mode

def show_debug_header():
    """Show debug information in the header/sidebar if in debug mode"""
    if not is_debug_mode():
        return
    
    st.sidebar.success("Debug mode is ON")
    st.sidebar.info("Debug information will be shown throughout the interface.")
    query_params = st.query_params
    st.sidebar.write("Query parameters:", query_params)

def show_data_debug(data, container=st):
    """Show debug information for DataFrame data"""
    if not is_debug_mode() or data is None:
        return
    
    container.write("Data information:")
    container.write(f"- Shape: {data.shape}")
    container.write(f"- Columns: {list(data.columns)}")
    container.write(f"- Data types:\n{data.dtypes}")
    container.write("Data Preview:")
    container.dataframe(data.head(10))

def debug_visualization(data, chart_info, container=st):
    """Show debug information for visualization data and configuration.
    
    Displays data information, chart parameters, and validation checks
    in a single, organized debug section.
    """
    if not is_debug_mode():
        return
    
    container.write("Debug Information:")
    show_data_debug(data, container)
    
    # Show chart configuration
    if chart_info:
        x_column = chart_info.get("x_column", "")
        y_columns = chart_info.get("y_columns", [])
        chart_type = chart_info.get("chart_type", "line")
        
        container.write(f"X-column: {x_column}")
        container.write(f"Y-columns: {y_columns}")
        container.write(f"Chart type: {chart_type}")
        
        # Check for missing columns if data is available
        if data is not None and isinstance(data, pd.DataFrame):
            if x_column and x_column not in data.columns:
                container.error(f"X-axis column '{x_column}' not found in data!")
                
            if y_columns:
                missing_y = [c for c in y_columns if c not in data.columns]
                if missing_y:
                    container.error(f"These Y-axis columns are missing: {missing_y}")

def show_chart_debug(chart_info, container=st):
    """Show debug information for chart configuration"""
    if not is_debug_mode() or chart_info is None:
        return
    
    container.write("Chart configuration:")
    for key, value in chart_info.items():
        container.write(f"- {key}: {value}")

def show_error_debug(error, data=None, chart_info=None, container=st):
    """Show detailed error information in debug mode"""
    if not is_debug_mode():
        return
    
    container.error("Debug traceback:")
    container.code(traceback.format_exc())
    
    if chart_info:
        container.warning("Visualization parameters causing the error:")
        for key, value in chart_info.items():
            container.write(f"- {key}: {value}")
    
    if data is not None and isinstance(data, pd.DataFrame):
        container.write("Data information:")
        container.write(f"- Columns: {list(data.columns)}")
        container.write(f"- Data types:\n{data.dtypes}")
        
        # Check for missing columns in chart_info
        if chart_info and "x_column" in chart_info and "y_columns" in chart_info:
            x_col = chart_info["x_column"]
            y_cols = chart_info["y_columns"]
            
            if x_col not in data.columns:
                container.error(f"X-axis column '{x_col}' not found in data!")
            
            missing_y = [c for c in y_cols if c not in data.columns]
            if missing_y:
                container.error(f"These Y-axis columns are missing: {missing_y}")
