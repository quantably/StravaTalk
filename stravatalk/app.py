"""
Streamlit interface for StravaTalk.
"""

import logging
import streamlit as st
from dotenv import load_dotenv
import pandas as pd
import traceback
import base64
import os
import time

# Set up logging for the main app
logger = logging.getLogger(__name__)
logger.info("🎯 Loading Streamlit app.py - starting imports...")

try:
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


def get_logo_html():
    """Get HTML for displaying the logo."""
    try:
        logo_path = os.path.join(os.path.dirname(os.path.dirname(__file__)), "static", "trackin-pro.png")
        with open(logo_path, "rb") as f:
            logo_data = base64.b64encode(f.read()).decode()
        
        return f"""
        <div style="text-align: center; margin-bottom: 20px;">
            <img src="data:image/png;base64,{logo_data}" alt="trackin.pro" style="max-height: 80px;">
        </div>
        """
    except Exception as e:
        print(f"Could not load logo: {e}")
        return ""

def get_favicon():
    """Get favicon from logo file."""
    try:
        logo_path = os.path.join(os.path.dirname(os.path.dirname(__file__)), "static", "trackin-pro.png")
        return logo_path
    except Exception as e:
        print(f"Could not load favicon: {e}")
        return None

def show_sync_interface(user_id: int, sync_service):
    """Show the historical activities sync interface."""
    st.markdown("## 🔄 Sync Your Activities")
    st.markdown("Welcome! Let's sync your historical Strava activities so you can start asking questions about your training data.")
    
    sync_status = sync_service.check_sync_status(user_id)
    current_count = sync_status.get("activity_count", 0)
    
    if current_count > 0:
        st.info(f"📊 You currently have {current_count} activities. Syncing will fetch your complete history.")
    else:
        st.info("📊 No activities found. Let's fetch your complete Strava history!")
    
    col1, col2 = st.columns([1, 1])
    
    with col1:
        if st.button("🚀 Start Sync", type="primary", use_container_width=True):
            st.session_state.sync_started = True
            st.rerun()
    
    with col2:
        if st.button("⏭️ Skip Sync", use_container_width=True):
            # Mark as completed to skip sync
            sync_service._complete_sync_status(user_id, current_count)
            st.success("✅ Sync skipped. You can sync later from settings.")
            st.rerun()
    
    # Show sync progress if started
    if st.session_state.get("sync_started", False):
        st.markdown("### 🔄 Syncing Activities...")
        
        # Create progress containers
        progress_bar = st.progress(0)
        status_text = st.empty()
        
        def update_progress(count, message):
            """Update progress bar and status text."""
            # Estimate progress (we don't know total upfront)
            estimated_total = max(100, count + 50)  # Rough estimate
            progress = min(count / estimated_total, 0.95)  # Never reach 100% until done
            progress_bar.progress(progress)
            status_text.text(message)
        
        # Run the sync
        with st.spinner("Fetching your activities from Strava..."):
            result = sync_service.sync_historical_activities(user_id, update_progress)
        
        if result["success"]:
            progress_bar.progress(1.0)
            status_text.text(f"✅ Completed! Synced {result['activities_synced']} activities.")
            st.success(f"🎉 Successfully synced {result['activities_synced']} activities!")
            st.balloons()
            
            # Clear sync state and refresh
            if 'sync_started' in st.session_state:
                del st.session_state.sync_started
            
            time.sleep(2)  # Show success message briefly
            st.rerun()
        else:
            st.error(f"❌ Sync failed: {result.get('error', 'Unknown error')}")
            if 'sync_started' in st.session_state:
                del st.session_state.sync_started

def create_interface():
    """Create the Streamlit interface for trackin.pro."""
    # Try to use logo as favicon, fallback to emoji
    favicon = get_favicon() or "📊"
    st.set_page_config(page_title="trackin.pro", page_icon=favicon, layout="centered", initial_sidebar_state="collapsed")  # Configure Streamlit page
    
    if "is_processing" not in st.session_state:
        st.session_state.is_processing = False
    
    debug_mode = setup_debug_mode()
    
    # Display logo and title
    logo_html = get_logo_html()
    if logo_html:
        st.markdown(logo_html, unsafe_allow_html=True)
    else:
        # Fallback to text if logo fails to load
        if debug_mode:
            st.title("trackin.pro 📊 🐛")
        else:
            st.title("trackin.pro 📊")
    
    if debug_mode:
        show_debug_header()
        
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
    dev_mode = os.getenv("ENVIRONMENT") != "production"
    
    if dev_mode:
        # Development mode - use athlete with actual data
        current_user = 149225109  # Use the athlete ID that has data in the database
        
        st.sidebar.info(f"🛠️ Development Mode")
        st.sidebar.success(f"👤 Dev User: {user_email}")
        st.sidebar.success(f"📊 Using athlete data: {current_user}")
        
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
                
                # Debug info (dev mode only)
                if dev_mode:
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
        
        # Check if user has synced their historical activities
        from .utils.strava_sync import StravaSyncService
        sync_service = StravaSyncService()
        sync_status = sync_service.check_sync_status(user_id)
        
        if not sync_status.get("synced", False):
            show_sync_interface(user_id, sync_service)
            st.stop()
    
    # Display user info
    activity_count = get_user_activity_count(current_user)
    st.sidebar.success(f"👤 {user_email}")
    st.sidebar.info(f"📊 Activities: {activity_count}")
    
    # Add disconnect Strava button (only if not in dev mode)
    if not dev_mode:
        st.sidebar.markdown("---")
        if st.sidebar.button("🔗 Disconnect Strava Account", type="secondary"):
            from .utils.auth_utils import disconnect_strava_account
            
            if disconnect_strava_account(user_id):
                st.sidebar.success("✅ Strava account disconnected")
                st.rerun()
            else:
                st.sidebar.error("❌ Failed to disconnect Strava account")
    
    # Add conversation management buttons
    st.sidebar.markdown("---")
    if st.sidebar.button("🗑️ Clear Conversation"):
        from .utils.conversation_persistence import clear_conversation_history
        from .utils.memory import ConversationMemory
        
        # Clear from database
        session_id = st.session_state.get("session_id")
        clear_conversation_history(user_id, session_id)
        
        # Clear from session state
        st.session_state.chat_history = [
            {
                "role": "assistant",
                "text": "Welcome to the Strava Data Assistant! I can help you analyze your Strava activities. How can I assist you today?",
            }
        ]
        st.session_state.conversation_memory = ConversationMemory(max_entries=5)
        st.session_state.session_id = None
        
        st.sidebar.success("✅ Conversation cleared")
        st.rerun()
    
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

    # Initialize or load conversation history and memory
    if "chat_history" not in st.session_state or "conversation_memory" not in st.session_state:
        from .utils.conversation_persistence import load_conversation_history, load_conversation_memory
        from .utils.memory import ConversationMemory
        
        # Try to load existing conversation
        loaded_history, session_id = load_conversation_history(user_id)
        loaded_memory = load_conversation_memory(user_id, session_id)
        
        if loaded_history:
            # Restore from database
            st.session_state.chat_history = loaded_history
            st.session_state.session_id = session_id
            st.session_state.conversation_memory = loaded_memory or ConversationMemory(max_entries=5)
            
            # Restore memory from chat history if memory wasn't found
            if not loaded_memory and loaded_history:
                st.session_state.conversation_memory = ConversationMemory(max_entries=5)
                # Rebuild memory from assistant messages in history
                for msg in loaded_history:
                    if (msg["role"] == "assistant" and 
                        msg.get("sql_query") and 
                        msg.get("data_summary")):
                        st.session_state.conversation_memory.add_entry(
                            user_query="Previous query",  # We don't store user queries separately
                            sql_query=msg["sql_query"],
                            data_summary=msg["data_summary"],
                            result_count=msg.get("result_count", 0),
                            query_type=msg.get("query_type", "TEXT")
                        )
        else:
            # Start fresh
            st.session_state.chat_history = [
                {
                    "role": "assistant",
                    "text": "Welcome to the Strava Data Assistant! I can help you analyze your Strava activities. How can I assist you today?",
                }
            ]
            st.session_state.conversation_memory = ConversationMemory(max_entries=5)
            st.session_state.session_id = None

    if "shared_memory" not in st.session_state:
        # Disable atomic agents memory to avoid serialization issues in Docker
        st.session_state.shared_memory = None

    if "agents" not in st.session_state:
        st.session_state.agents = initialize_agents(st.session_state.shared_memory)

    for message in st.session_state.chat_history:
        with st.chat_message(message["role"]):
            st.markdown(message["text"])
            
            # Display table if applicable for assistant messages
            if (message["role"] == "assistant" and 
                message.get("show_table") and 
                message.get("data") is not None):
                st.dataframe(message["data"], use_container_width=True)

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

        classify_agent, sql_agent, response_agent, table_response_agent, clarify_agent = st.session_state.agents

        with st.status("Processing your query...", expanded=False) as status:
            logger.info(f"🚀 Processing query: {user_query}")
            logger.info(f"👤 Current user: {st.session_state.current_user}")
            
            
            # Pass status container for debug output in dev mode and memory for context
            result = process_query(
                classify_agent, sql_agent, response_agent, table_response_agent, clarify_agent, user_query, st.session_state.current_user, 
                debug_container=status if is_debug_mode() else None,
                memory=st.session_state.conversation_memory
            )
            
            logger.info(f"✅ Query processing completed")

            classification = result["classification"]
            if is_debug_mode():
                status.write(f"Query type: {classification.query_type}")

            if classification.query_type in [QueryType.TEXT, QueryType.TEXT_AND_TABLE]:
                if result.get("sql_query") and is_debug_mode():
                    status.write("SQL Query:")
                    status.code(result["sql_query"], language="sql")

                if result["success"]:
                    if result.get("data") is not None and is_debug_mode():
                        status.write(f"Query returned {len(result['data'])} rows")

                        if is_debug_mode():
                            show_data_debug(result["data"], status)

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
            "show_table": result.get("show_table", False),
            "data": result.get("data"),
        }

        st.session_state.chat_history.append(assistant_message)
        
        # Update conversation memory with this interaction
        if result["success"]:
            from .utils.memory import create_data_summary
            
            # Create summary of the results
            data_summary = create_data_summary(
                result.get("data"), 
                str(classification.query_type), 
                len(result["data"]) if result.get("data") is not None else 0
            )
            
            # Add to memory
            st.session_state.conversation_memory.add_entry(
                user_query=user_query,
                sql_query=result.get("sql_query"),
                data_summary=data_summary,
                result_count=len(result["data"]) if result.get("data") is not None else 0,
                query_type=str(classification.query_type)
            )
            
            # Add data summary and metadata to assistant message for persistence
            assistant_message["data_summary"] = data_summary
            assistant_message["result_count"] = len(result["data"]) if result.get("data") is not None else 0
            assistant_message["query_type"] = str(classification.query_type)
        
        # Save conversation to database
        from .utils.conversation_persistence import save_conversation_history, save_conversation_memory
        session_id = save_conversation_history(
            user_id, 
            st.session_state.chat_history, 
            st.session_state.get("session_id")
        )
        if session_id:
            st.session_state.session_id = session_id
            save_conversation_memory(user_id, st.session_state.conversation_memory, session_id)
        
        st.session_state.is_processing = False

        with st.chat_message("assistant"):
            # Display supporting text
            st.markdown(result["response_text"])
            
            # Display table if applicable
            if result.get("show_table") and result.get("data") is not None:
                st.dataframe(result["data"], use_container_width=True)

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
