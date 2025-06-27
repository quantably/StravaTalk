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
    # Check if we're in development mode (no email service)
    from dotenv import load_dotenv
    import os
    load_dotenv()
    
    dev_mode = not os.getenv("RESEND_API_KEY")
    
    if dev_mode:
        # Development mode - skip authentication
        logger.info("🛠️ Development mode detected (no RESEND_API_KEY) - skipping authentication")
        
        # Set up minimal session state for development
        if "authenticated" not in st.session_state:
            st.session_state.authenticated = True
            st.session_state.session_token = "dev-mode-token"
            st.session_state.user_id = 1  # Default dev user
            st.session_state.user_email = "dev@localhost"
        
        # Show main app directly
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
        
        return
    
    # Production mode - full authentication flow
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
    # Check for session token in URL parameters first (for initial login)
    query_params = st.query_params
    
    if "session_token" in query_params:
        session_token = query_params["session_token"]
        # Validate session with backend
        if validate_session_token(session_token):
            # Store in session state
            st.session_state.session_token = session_token
            st.session_state.authenticated = True
            
            # Store in secure cookie and clear URL for security
            set_session_cookie(session_token)
            st.query_params.clear()
            st.rerun()
            return True
    
    # Check if we have a valid session in session state
    if st.session_state.get("authenticated", False):
        return True
    
    # Try to get session from cookie
    session_token = get_session_cookie()
    if session_token:
        # Validate session token
        if validate_session_token(session_token):
            st.session_state.session_token = session_token
            st.session_state.authenticated = True
            return True
        else:
            # Session expired, clear cookie
            clear_session_cookie()
            st.session_state.clear()
    
    return False

def set_session_cookie(session_token):
    """Set session token in secure cookie."""
    st.markdown(f"""
    <script>
        document.cookie = "strava_session={session_token}; path=/; secure; samesite=strict; max-age=604800";
    </script>
    """, unsafe_allow_html=True)

def get_session_cookie():
    """Get session token from cookie."""
    cookie_script = """
    <script>
        function getCookie(name) {
            const value = "; " + document.cookie;
            const parts = value.split("; " + name + "=");
            if (parts.length === 2) {
                const token = parts.pop().split(";").shift();
                // Send token via URL parameter for Streamlit to access
                if (token && !window.location.search.includes('session_token')) {
                    window.location.href = window.location.pathname + '?session_token=' + token;
                }
            }
        }
        getCookie('strava_session');
    </script>
    """
    st.markdown(cookie_script, unsafe_allow_html=True)
    return None  # Streamlit can't directly access cookies, so we redirect with token

def clear_session_cookie():
    """Clear session cookie."""
    st.markdown("""
    <script>
        document.cookie = "strava_session=; path=/; expires=Thu, 01 Jan 1970 00:00:00 GMT";
    </script>
    """, unsafe_allow_html=True)

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