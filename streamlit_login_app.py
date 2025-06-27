#!/usr/bin/env python3
"""
Entry point for Streamlit application with magic link authentication.
Handles routing between login page and main app based on authentication state.
"""

import sys
import os
import logging
import streamlit as st
from urllib.parse import urlparse, parse_qs

# Set up logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

logger.info("🚀 Starting StravaTalk Streamlit application with authentication...")

# Add the current directory to Python path so stravatalk package can be imported
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
logger.info(f"✅ Added to Python path: {os.path.dirname(os.path.abspath(__file__))}")

def main():
    """Main application entry point with authentication routing."""
    # Check for URL parameters
    query_params = st.query_params
    
    # Check if we're on the login route
    if "login" in query_params or not is_authenticated():
        # Show login page
        from stravatalk.pages.login import show_login_page
        show_login_page()
    else:
        # Show main app
        try:
            logger.info("📦 Importing stravatalk.app module...")
            import stravatalk.app
            logger.info("✅ Successfully imported stravatalk.app")
            
            # Actually run the Streamlit app
            logger.info("🚀 Calling main() to start Streamlit interface...")
            stravatalk.app.main()
            logger.info("✅ Streamlit app main() completed")
            
        except Exception as e:
            logger.error(f"❌ Failed to run stravatalk.app: {e}")
            import traceback
            logger.error(traceback.format_exc())
            
            st.error("Failed to load main application")
            st.info("Please try logging in again")
            
            if st.button("Go to Login"):
                st.query_params["login"] = "true"
                st.rerun()

def is_authenticated():
    """Check if user is authenticated."""
    # Check for session token in URL parameters first
    query_params = st.query_params
    
    if "session_token" in query_params:
        session_token = query_params["session_token"]
        # Validate session with backend
        if validate_session_token(session_token):
            # Store in session state
            st.session_state.session_token = session_token
            st.session_state.authenticated = True
            # DON'T clear URL params - keep session_token in URL for persistence
            return True
    
    # Check if we have a valid session in session state
    if st.session_state.get("authenticated", False):
        session_token = st.session_state.get("session_token")
        if session_token:
            # Re-validate session token to make sure it's still valid
            if validate_session_token(session_token):
                return True
            else:
                # Session expired, clear state
                st.session_state.clear()
                return False
    
    return False

def validate_session_token(session_token: str) -> bool:
    """Validate session token with FastAPI backend."""
    import requests
    from dotenv import load_dotenv
    
    load_dotenv()
    FASTAPI_URL = os.getenv("FASTAPI_URL", "http://localhost:8000")
    
    try:
        response = requests.get(
            f"{FASTAPI_URL}/auth/session-info",
            params={"session_token": session_token},
            timeout=10
        )
        
        if response.status_code == 200:
            session_info = response.json()
            # Store user info in session state
            st.session_state.user_id = session_info["user_id"]
            st.session_state.user_email = session_info["email"]
            return True
        return False
        
    except Exception as e:
        logger.error(f"Error validating session: {e}")
        return False

if __name__ == "__main__":
    main()

logger.info("🎉 StravaTalk app entry point completed!")