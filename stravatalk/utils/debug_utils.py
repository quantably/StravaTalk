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
    try:
        # Try modern Streamlit API first
        query_params = st.query_params
    except AttributeError:
        # Fallback for older Streamlit versions
        query_params = st.experimental_get_query_params()
    
    debug_mode = query_params.get('debug', [False])[0] == 'true' if isinstance(query_params.get('debug', [False]), list) else query_params.get('debug') == 'true'
    st.session_state.debug_mode = debug_mode
    return debug_mode

def show_debug_header():
    """Show debug information in the header/sidebar if in debug mode"""
    if not is_debug_mode():
        return
    
    st.sidebar.success("Debug mode is ON")
    st.sidebar.info("Debug information will be shown throughout the interface.")
    try:
        query_params = st.query_params
    except AttributeError:
        query_params = st.experimental_get_query_params()
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

def show_agent_debug(agent_name, input_data, output_data, container=st):
    """Show agent input/output debug information"""
    if not is_debug_mode():
        return
    
    with container.expander(f"🤖 {agent_name} Debug", expanded=False):
        container.write("**Input:**")
        if hasattr(input_data, '__dict__'):
            # Pydantic model
            container.json(input_data.model_dump())
        else:
            container.write(str(input_data))
        
        container.write("**Output:**")
        if hasattr(output_data, '__dict__'):
            # Pydantic model
            container.json(output_data.model_dump())
        else:
            container.write(str(output_data))

def show_sql_debug(sql_query, execution_result, container=st):
    """Show SQL query and execution debug information"""
    if not is_debug_mode():
        return
    
    with container.expander("🗄️ SQL Debug", expanded=False):
        container.write("**Generated SQL:**")
        container.code(sql_query, language="sql")
        
        container.write("**Execution Result:**")
        container.write(f"- Success: {execution_result.get('success', False)}")
        container.write(f"- Row count: {execution_result.get('row_count', 0)}")
        
        if execution_result.get('error_message'):
            container.error(f"Error: {execution_result['error_message']}")
        
        if execution_result.get('column_names'):
            container.write(f"- Columns: {execution_result['column_names']}")

def show_orchestrator_debug(query, classification, sql_output, execution_result, response_output, container=st):
    """Show complete orchestrator debug information"""
    if not is_debug_mode():
        return
    
    with container.expander("🎯 Complete Agent Pipeline Debug", expanded=True):
        container.write("**User Query:**")
        container.write(f"'{query}'")
        
        container.write("**1. Classification Result:**")
        container.json({
            "query_type": str(classification.query_type),
            "explanation": classification.explanation,
            "needs_visualization": getattr(classification, 'needs_visualization', False)
        })
        
        if sql_output:
            container.write("**2. SQL Generation:**")
            container.code(sql_output.sql_query, language="sql")
            
            container.write("**3. SQL Execution:**")
            container.json({
                "success": execution_result.get('success', False),
                "row_count": execution_result.get('row_count', 0),
                "columns": execution_result.get('column_names', []),
                "error": execution_result.get('error_message')
            })
        
        container.write("**4. Response Generation:**")
        container.write(f"Response: {response_output.response[:200]}..." if len(response_output.response) > 200 else response_output.response)
