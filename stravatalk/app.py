"""
Simplified Streamlit interface for StravaTalk.
"""

import streamlit as st
from dotenv import load_dotenv
import pandas as pd
import traceback

from atomic_agents.lib.components.agent_memory import AgentMemory
from orchestrator import initialize_agents, process_query
from visualization import create_visualization, display_visualization, validate_chart_inputs
from agents.classify_agent import QueryType
from utils.debug_utils import (
    setup_debug_mode, 
    show_debug_header, 
    show_data_debug, 
    show_chart_debug, 
    show_error_debug,
    debug_visualization,
    is_debug_mode
)


def create_interface():
    """Create the Streamlit interface for StravaTalk."""
    # Must be the first Streamlit command
    st.set_page_config(page_title="StravaTalk", page_icon="🏃‍♂️", layout="centered", initial_sidebar_state="collapsed")
    
    # Flag to track when we're processing a query (to prevent unwanted visualizations)
    if "is_processing" not in st.session_state:
        st.session_state.is_processing = False
    
    # Setup debug mode from URL parameters
    debug_mode = setup_debug_mode()
    
    # Show title with debug indicator if in debug mode
    if debug_mode:
        st.title("StravaTalk 🏃‍♂️ 🐛")
        show_debug_header()
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

                    chart_info = message["chart_info"]
                    
                    # Show debug info if needed
                    if is_debug_mode():
                        debug_visualization(data, chart_info, st)
                    
                    # Validate chart inputs
                    is_valid, valid_y_columns, error_message = validate_chart_inputs(
                        data, chart_info["x_column"], chart_info["y_columns"]
                    )
                    
                    if not is_valid:
                        st.warning(error_message)
                        continue
                    
                    # Create and display chart
                    chart = create_visualization(
                        data, 
                        chart_info["x_column"], 
                        valid_y_columns, 
                        chart_info.get("chart_type", "line")
                    )
                    display_visualization(chart)
                    
                except Exception as e:
                    st.error(f"Error displaying visualization: {str(e)}")
                    if is_debug_mode():
                        show_error_debug(e, data, chart_info, st)

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
                        if is_debug_mode():
                            show_data_debug(result["data"], status)
                            if result.get("chart_info"):
                                show_chart_debug(result["chart_info"], status)

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

            # Validate columns exist using the validation function
            is_valid, valid_y_columns, _ = validate_chart_inputs(result["data"], x_column, y_columns)
            
            if is_valid:
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
                    if is_debug_mode():
                        show_error_debug(e, data, assistant_message["chart_info"], st)

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
        if is_debug_mode():
            st.error(traceback.format_exc())
        
    finally:
        # Always turn off processing mode when done
        st.session_state.is_processing = False


def main():
    create_interface()


if __name__ == "__main__":
    main()
