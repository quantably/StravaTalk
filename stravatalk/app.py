"""
Simplified Streamlit interface for StravaTalk.
"""

import streamlit as st
from dotenv import load_dotenv
import pandas as pd

from atomic_agents.lib.components.agent_memory import AgentMemory
from orchestrator import initialize_agents, process_query
from visualization import create_visualization, display_visualization
from agents.classify_agent import QueryType


def create_interface():
    """Create the Streamlit interface for StravaTalk."""
    # Must be the first Streamlit command
    st.set_page_config(page_title="StravaTalk", page_icon="🏃‍♂️", layout="centered")
    
    # Flag to track when we're processing a query (to prevent unwanted visualizations)
    if "is_processing" not in st.session_state:
        st.session_state.is_processing = False
    
    # Check for debug mode in query parameters
    query_params = st.query_params
    debug_from_url = query_params.get('debug') == 'true'
    
    # Add debug toggle in sidebar, default to URL param if present
    debug_sidebar = st.sidebar.checkbox("Debug Mode", value=debug_from_url)
    
    # Set debug mode based on sidebar or URL
    st.session_state.debug_mode = debug_sidebar
    
    # Show title with debug indicator if in debug mode
    if st.session_state.debug_mode:
        st.title("StravaTalk 🏃‍♂️ 🐛")
        st.sidebar.success("Debug mode is ON")
        st.sidebar.info("Debug information will be shown throughout the interface.")
        # Update URL if debug was turned on from sidebar but not in URL
        if not debug_from_url and debug_sidebar:
            query_params['debug'] = 'true'
        # Show query parameters in debug mode
        st.sidebar.write("Query parameters:", query_params)
    else:
        st.title("StravaTalk 🏃‍♂️")
        
    load_dotenv()

    # Initialize chat history if not already in session state
    if "chat_history" not in st.session_state:
        st.session_state.chat_history = [
            {
                "role": "assistant",
                "text": "Welcome to the Strava Data Assistant! I can help you analyze your Strava activities. How can I assist you today?",
            }
        ]

    # Initialize shared memory for agents if needed
    if "shared_memory" not in st.session_state:
        st.session_state.shared_memory = AgentMemory()

    # Initialize agents if not already in session state
    if "agents" not in st.session_state:
        st.session_state.agents = initialize_agents(st.session_state.shared_memory)

    # Display chat history
    for message in st.session_state.chat_history:
        with st.chat_message(message["role"]):
            # Display text message
            st.markdown(message["text"])

            # Skip visualization if we're currently processing a query
            if st.session_state.is_processing:
                continue

            # Display visualization if present
            if (
                message["role"] == "assistant"
                and "chart_data" in message
                and "chart_info" in message
            ):
                try:
                    # Convert data to DataFrame if it's stored as records
                    data = message["chart_data"]
                    if isinstance(data, list):
                        data = pd.DataFrame(data)

                    # Ensure columns exist
                    x_column = message["chart_info"]["x_column"]
                    y_columns = message["chart_info"]["y_columns"]
                    chart_type = message["chart_info"].get("chart_type", "line")

                    # Debug info
                    if st.session_state.get("debug_mode", False):
                        st.write("Debug Information:")
                        st.write("Visualization data shape:", data.shape)
                        st.write("X-column:", x_column)
                        st.write("Y-columns:", y_columns)
                        st.write("Chart type:", chart_type)
                        st.write("Data types:")
                        st.write(data.dtypes)
                        st.write("Data Preview:")
                        st.dataframe(data.head(10))

                    if x_column not in data.columns:
                        st.warning(
                            f"X-axis column '{x_column}' not in data columns: {list(data.columns)}"
                        )
                        continue

                    valid_y_columns = [col for col in y_columns if col in data.columns]
                    if not valid_y_columns:
                        st.warning(
                            f"None of the Y-axis columns {y_columns} found in data columns: {list(data.columns)}"
                        )
                        continue

                    # Create and display chart
                    chart = create_visualization(
                        data, x_column, valid_y_columns, chart_type
                    )
                    display_visualization(chart)
                except Exception as e:
                    st.error(f"Error displaying visualization: {str(e)}")
                    
                    # Show detailed error information in debug mode
                    if st.session_state.get("debug_mode", False):
                        import traceback
                        st.error("Debug traceback:")
                        st.code(traceback.format_exc())
                        
                        # Additional debugging information
                        st.warning("Visualization parameters causing the error:")
                        st.write(f"- X column: {x_column}")
                        st.write(f"- Y columns: {y_columns}")
                        st.write(f"- Chart type: {chart_type}")
                        
                        # Check if specific columns exist
                        if x_column not in data.columns:
                            st.error(f"X-axis column '{x_column}' not found in data!")
                        
                        missing_y = [c for c in y_columns if c not in data.columns]
                        if missing_y:
                            st.error(f"These Y-axis columns are missing: {missing_y}")

    # Query input
    if prompt := st.chat_input("Ask me anything about your Strava activities..."):
        handle_query(prompt)


def handle_query(user_query):
    """Process a user query and update the interface."""
    if not user_query:
        return

    try:
        # Mark that we're processing a query (to prevent chart duplication)
        st.session_state.is_processing = True
        
        # Add user message to chat history
        st.session_state.chat_history.append({"role": "user", "text": user_query})

        # Display user message
        with st.chat_message("user"):
            st.markdown(user_query)

        # Get agents from session state
        classify_agent, sql_agent, response_agent = st.session_state.agents

        # Process the query with status indicator
        with st.status("Processing your query...", expanded=False) as status:
            result = process_query(
                classify_agent, sql_agent, response_agent, user_query
            )

            # Update status based on classification
            classification = result["classification"]
            status.write(f"Query type: {classification.query_type}")

            if classification.query_type in [QueryType.SQL, QueryType.VIZ]:
                if result.get("sql_query"):
                    status.write("SQL Query:")
                    status.code(result["sql_query"], language="sql")

                if result["success"]:
                    if result.get("data") is not None:
                        status.write(f"Query returned {len(result['data'])} rows")

                        # Debug mode - show data info
                        if st.session_state.get("debug_mode", False):
                            status.write("Data information:")
                            status.write(f"- Shape: {result['data'].shape}")
                            status.write(f"- Columns: {list(result['data'].columns)}")
                            status.write(f"- Data types:\n{result['data'].dtypes}")
                            
                            status.write("Data Preview:")
                            status.dataframe(result['data'].head(10))

                            if result.get("chart_info"):
                                status.write("Chart configuration:")
                                for key, value in result["chart_info"].items():
                                    status.write(f"- {key}: {value}")

                    status.update(
                        label="Query processed successfully!", state="complete"
                    )
                else:
                    status.update(label="Error executing query", state="error")
            else:
                status.update(label="Query processed", state="complete")

        # Prepare assistant message for chat history
        assistant_message = {
            "role": "assistant",
            "text": result["response_text"],
            "sql_query": result.get("sql_query"),
        }

        # Add chart data if visualization is needed
        if (
            result["chart_info"]
            and result["data"] is not None
            and not result["data"].empty
        ):
            # Ensure all required columns exist in the data
            chart_info = result["chart_info"]
            x_column = chart_info["x_column"]
            y_columns = chart_info["y_columns"]
            chart_type = chart_info.get("chart_type", "line")

            # Validate columns exist
            if x_column in result["data"].columns:
                # Filter y_columns to only those that exist
                valid_y_columns = [
                    col for col in y_columns if col in result["data"].columns
                ]

                if valid_y_columns:
                    assistant_message["chart_data"] = result["data"].to_dict("records")
                    assistant_message["chart_info"] = {
                        "x_column": x_column,
                        "y_columns": valid_y_columns,
                        "chart_type": chart_type,
                    }

                    # Handle date-like columns for conversion
                    if "date" in x_column.lower() or "time" in x_column.lower():
                        # Ensure date columns are properly formatted
                        try:
                            result["data"][x_column] = pd.to_datetime(
                                result["data"][x_column]
                            )
                        except:
                            pass  # Continue if conversion fails

        # Add to chat history
        st.session_state.chat_history.append(assistant_message)
        
        # Turn off processing mode to re-enable chart rendering
        st.session_state.is_processing = False

        # Display assistant response
        with st.chat_message("assistant"):
            st.markdown(result["response_text"])

            # Display visualization if needed
            if "chart_data" in assistant_message and "chart_info" in assistant_message:
                try:
                    # Convert data to DataFrame
                    data = pd.DataFrame(assistant_message["chart_data"])

                    # Create and display chart
                    chart = create_visualization(
                        data,
                        assistant_message["chart_info"]["x_column"],
                        assistant_message["chart_info"]["y_columns"],
                        assistant_message["chart_info"].get("chart_type", "line"),
                    )
                    display_visualization(chart)
                except Exception as e:
                    st.error(f"Error displaying visualization: {str(e)}")
                    if st.session_state.get("debug_mode", False):
                        import traceback
                        st.error("Debug traceback:")
                        st.code(traceback.format_exc())
                        
                        # Visualization debugging information
                        x_col = assistant_message["chart_info"]["x_column"]
                        y_cols = assistant_message["chart_info"]["y_columns"]
                        c_type = assistant_message["chart_info"].get("chart_type", "line")
                        
                        st.warning("Visualization parameters causing the error:")
                        st.write(f"- X column: {x_col}")
                        st.write(f"- Y columns: {y_cols}")
                        st.write(f"- Chart type: {c_type}")
                        
                        # Data information
                        st.write("Data information:")
                        st.write(f"- Columns: {list(data.columns)}")
                        st.write(f"- Data types:\n{data.dtypes}")
                        
                        # Check if specific columns exist
                        if x_col not in data.columns:
                            st.error(f"X-axis column '{x_col}' not found in data!")
                        
                        missing_y = [c for c in y_cols if c not in data.columns]
                        if missing_y:
                            st.error(f"These Y-axis columns are missing: {missing_y}")

    except Exception as e:
        # Add error message to chat history
        error_message = f"Error: {str(e)}"
        st.session_state.chat_history.append(
            {"role": "assistant", "text": error_message}
        )

        # Display error
        with st.chat_message("assistant"):
            st.error(error_message)

        # Log detailed error
        import traceback
        st.error(traceback.format_exc())
        
    finally:
        # Always turn off processing mode when done
        st.session_state.is_processing = False


def main():
    create_interface()


if __name__ == "__main__":
    main()
