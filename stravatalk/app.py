"""
Streamlit interface for StravaTalk.
"""

import logging
import streamlit as st
from dotenv import load_dotenv
import pandas as pd
import traceback

# Set up logging for the main app
logger = logging.getLogger(__name__)
logger.info("🎯 Loading Streamlit app.py - starting imports...")

try:
    from atomic_agents.lib.components.agent_memory import AgentMemory
    logger.info("✅ Imported AgentMemory")
    
    from .orchestrator import initialize_agents, process_query
    logger.info("✅ Imported orchestrator")
    
    from .visualization import create_visualization, display_visualization, validate_chart_inputs
    logger.info("✅ Imported visualization")
    
    from .agents.classify_agent import QueryType
    logger.info("✅ Imported classify_agent")
    
    from .utils.db_utils import get_user_from_token, get_user_activity_count
    from .utils.auth_utils import get_user_strava_connection
    logger.info("✅ Imported db_utils and auth_utils")
    
    from .utils.debug_utils import (
        setup_debug_mode, 
        show_debug_header, 
        show_data_debug, 
        show_chart_debug, 
        show_error_debug,
        debug_visualization,
        is_debug_mode
    )
    logger.info("✅ Imported debug_utils")
    logger.info("🎉 All imports successful in app.py")
    
except Exception as e:
    logger.error(f"❌ Import failed in app.py: {e}")
    logger.error(traceback.format_exc())
    st.error(f"Failed to load application: {e}")
    st.stop()


def create_interface():
    """Create the Streamlit interface for StravaTalk."""
    st.set_page_config(page_title="StravaTalk", page_icon="🏃‍♂️", layout="centered", initial_sidebar_state="collapsed")  # Configure Streamlit page
    
    if "is_processing" not in st.session_state:
        st.session_state.is_processing = False
    
    debug_mode = setup_debug_mode()
    
    if debug_mode:
        st.title("StravaTalk 🏃‍♂️ 🐛")
        show_debug_header()
    else:
        st.title("StravaTalk 🏃‍♂️")
        
    load_dotenv()
    
    # Check for user authentication
    if not st.session_state.get("authenticated", False):
        st.warning("⚠️ No authenticated user found. Please log in first.")
        st.info("You need to be logged in to access StravaTalk.")
        
        if st.button("🔐 Go to Login"):
            st.query_params["login"] = "true"
            st.rerun()
        st.stop()
    
    # Get user info from session
    user_id = st.session_state.get("user_id")
    user_email = st.session_state.get("user_email")
    
    if not user_id:
        st.error("Session error. Please log in again.")
        st.stop()
    
    # Check if we're in development mode
    import os
    dev_mode = not os.getenv("RESEND_API_KEY")
    
    if dev_mode:
        # Development mode - use any existing token as current user
        from .utils.db_utils import get_user_from_token
        current_user = get_user_from_token()
        
        if not current_user:
            st.warning("⚠️ No Strava data found in development mode.")
            st.info("Make sure you have some activity data in your database.")
            
            # Show available users/tokens for development
            with st.expander("🛠️ Development Info"):
                st.code(f"""
Development Mode Active (no RESEND_API_KEY)
Authentication bypassed
User ID: {user_id}
User Email: {user_email}

To connect Strava data, you can:
1. Set RESEND_API_KEY to enable full auth flow
2. Or manually populate the database with activity data
                """)
            st.stop()
        
        st.sidebar.info(f"🛠️ Development Mode")
        st.sidebar.success(f"👤 Dev User: {user_email}")
        
    else:
        # Production mode - check Strava connection
        strava_connection = get_user_strava_connection(user_id)
        if not strava_connection:
            st.warning("⚠️ No Strava account connected.")
            st.info("Connect your Strava account to start analyzing your activities.")
            
            session_token = st.session_state.get("session_token")
            if session_token:
                oauth_url = f"https://stravatalk-api2.onrender.com/oauth/authorize?scope=read_all&session_token={session_token}"
                st.markdown(f"[🔗 Connect Strava Account]({oauth_url})")
                
                # Debug info
                with st.expander("🔧 Debug - OAuth Info"):
                    st.code(f"""
Session Token: {session_token[:30]}...
OAuth URL: {oauth_url}
User ID: {user_id}
User Email: {user_email}
                    """)
            else:
                st.error("Session error. Please log in again.")
            st.stop()
        
        current_user = strava_connection["athlete_id"]
    
    # Display user info
    activity_count = get_user_activity_count(current_user)
    st.sidebar.success(f"👤 {user_email}")
    st.sidebar.info(f"📊 Activities: {activity_count}")
    
    # Add logout button
    if st.sidebar.button("🚪 Logout"):
        # Clear session state
        for key in list(st.session_state.keys()):
            del st.session_state[key]
        
        # Clear session cookie
        st.markdown("""
        <script>
            document.cookie = "strava_session=; path=/; expires=Thu, 01 Jan 1970 00:00:00 GMT";
        </script>
        """, unsafe_allow_html=True)
        
        # Clear all URL parameters and redirect to login
        st.query_params.clear()
        st.query_params["login"] = "true"
        st.rerun()
    
    # Store current user in session state
    if "current_user" not in st.session_state:
        st.session_state.current_user = current_user

    if "chat_history" not in st.session_state:
        st.session_state.chat_history = [
            {
                "role": "assistant",
                "text": "Welcome to the Strava Data Assistant! I can help you analyze your Strava activities. How can I assist you today?",
            }
        ]

    if "shared_memory" not in st.session_state:
        # Create AgentMemory without persistence to avoid serialization issues
        st.session_state.shared_memory = AgentMemory(max_messages=0)

    if "agents" not in st.session_state:
        st.session_state.agents = initialize_agents(st.session_state.shared_memory)

    for message in st.session_state.chat_history:
        with st.chat_message(message["role"]):
            st.markdown(message["text"])

            if st.session_state.is_processing:
                continue

            if (
                message["role"] == "assistant"
                and "chart_data" in message
                and "chart_info" in message
            ):
                try:
                    data = message["chart_data"]
                    if isinstance(data, list):
                        data = pd.DataFrame(data)

                    chart_info = message["chart_info"]
                    
                    if is_debug_mode():
                        debug_visualization(data, chart_info, st)
                    
                    is_valid, valid_y_columns, error_message = validate_chart_inputs(
                        data, chart_info["x_column"], chart_info["y_columns"]
                    )
                    
                    if not is_valid:
                        st.warning(error_message)
                        continue
                    
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

    if prompt := st.chat_input("Ask me anything about your Strava activities..."):
        handle_query(prompt)


def handle_query(user_query):
    """Process a user query and update the interface."""
    if not user_query:
        return

    try:
        st.session_state.is_processing = True
        
        st.session_state.chat_history.append({"role": "user", "text": user_query})

        with st.chat_message("user"):
            st.markdown(user_query)

        classify_agent, sql_agent, response_agent = st.session_state.agents

        with st.status("Processing your query...", expanded=False) as status:
            logger.info(f"🚀 Processing query: {user_query}")
            logger.info(f"👤 Current user: {st.session_state.current_user}")
            
            result = process_query(
                classify_agent, sql_agent, response_agent, user_query, st.session_state.current_user
            )
            
            logger.info(f"✅ Query processing completed")

            classification = result["classification"]
            status.write(f"Query type: {classification.query_type}")

            if classification.query_type in [QueryType.SQL, QueryType.VIZ]:
                if result.get("sql_query"):
                    status.write("SQL Query:")
                    status.code(result["sql_query"], language="sql")

                if result["success"]:
                    if result.get("data") is not None:
                        status.write(f"Query returned {len(result['data'])} rows")

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

        assistant_message = {
            "role": "assistant",
            "text": result["response_text"],
            "sql_query": result.get("sql_query"),
        }

        if (
            result["chart_info"]
            and result["data"] is not None
            and not result["data"].empty
        ):
            chart_info = result["chart_info"]
            x_column = chart_info["x_column"]
            y_columns = chart_info["y_columns"]
            chart_type = chart_info.get("chart_type", "line")

            is_valid, valid_y_columns, _ = validate_chart_inputs(result["data"], x_column, y_columns)
            
            if is_valid:
                assistant_message["chart_data"] = result["data"].to_dict("records")
                assistant_message["chart_info"] = {
                    "x_column": x_column,
                    "y_columns": valid_y_columns,
                    "chart_type": chart_type,
                }

                if "date" in x_column.lower() or "time" in x_column.lower():
                    try:
                        result["data"][x_column] = pd.to_datetime(
                            result["data"][x_column]
                        )
                    except:
                        pass

        st.session_state.chat_history.append(assistant_message)
        
        st.session_state.is_processing = False

        with st.chat_message("assistant"):
            st.markdown(result["response_text"])

            if "chart_data" in assistant_message and "chart_info" in assistant_message:
                try:
                    data = pd.DataFrame(assistant_message["chart_data"])

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
        # Log the full error details
        logger.error(f"💥 Error in handle_query: {str(e)}")
        logger.error(f"📋 Full traceback: {traceback.format_exc()}")
        logger.error(f"🔍 Error type: {type(e).__name__}")
        logger.error(f"📝 User query: {user_query}")
        
        error_message = f"Error: {str(e)}"
        st.session_state.chat_history.append(
            {"role": "assistant", "text": error_message}
        )

        with st.chat_message("assistant"):
            st.error(error_message)
            
            # Always show the full traceback in an expander for debugging
            with st.expander("🔧 Debug - Full Error Details"):
                st.code(f"""
Error Type: {type(e).__name__}
Error Message: {str(e)}
User Query: {user_query}

Full Traceback:
{traceback.format_exc()}
                """)

        if is_debug_mode():
            st.error(traceback.format_exc())
        
    finally:
        st.session_state.is_processing = False


def main():
    create_interface()


if __name__ == "__main__":
    main()
