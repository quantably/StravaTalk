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
import time

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
    
    dev_mode = os.getenv("ENVIRONMENT") != "production"
    
    if dev_mode:
        # Development mode - skip authentication
        logger.info("🛠️ Development mode detected (ENVIRONMENT != production) - skipping authentication")
        
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
            cookie_set = set_session_cookie(session_token)
            
            if cookie_set:
                # Clear URL parameters only if cookie was set successfully
                st.query_params.clear()
            else:
                # If cookie wasn't set, keep trying on next page load
                st.session_state.pending_cookie_set = session_token
            
            return True
    
    # Check if we have a pending cookie to set
    if "pending_cookie_set" in st.session_state:
        if set_session_cookie(st.session_state.pending_cookie_set):
            del st.session_state.pending_cookie_set
            st.query_params.clear()
    
    # Check if we have a valid session in session state AND validate it's still valid
    if st.session_state.get("authenticated", False) and "session_token" in st.session_state:
        # Periodically validate session (every 10 minutes)
        last_validation = st.session_state.get("last_validation", 0)
        current_time = time.time()
        
        if current_time - last_validation > 600:  # 10 minutes
            if validate_session_token(st.session_state.session_token):
                st.session_state.last_validation = current_time
                return True
            else:
                # Session expired, clear everything
                clear_session_cookie()
                st.session_state.clear()
                return False
        else:
            return True
    
    # Try to get session from cookie
    session_token = get_session_cookie()
    if session_token:
        # Validate session token
        if validate_session_token(session_token):
            st.session_state.session_token = session_token
            st.session_state.authenticated = True
            st.session_state.last_validation = time.time()
            return True
        else:
            # Session expired, clear cookie
            clear_session_cookie()
            st.session_state.clear()
    
    return False

def set_session_cookie(session_token):
    """Set session token in secure cookie."""
    try:
        import streamlit_cookies_manager
        import os
        
        # Initialize with proper encryption
        cookies = streamlit_cookies_manager.EncryptedCookieManager(
            prefix="stravatalk/",
            password=os.getenv("COOKIES_PASSWORD", "stravatalk-secret-key-2024")
        )
        
        if cookies.ready():
            cookies['strava_session'] = session_token
            cookies.save()  # Force immediate save
            return True
        else:
            return False  # Cookie manager not ready yet
    except ImportError:
        pass
    
    # Fallback to JavaScript approach
    st.markdown(f"""
    <script>
        document.cookie = "strava_session={session_token}; path=/; secure; samesite=strict; max-age=604800";
    </script>
    """, unsafe_allow_html=True)
    return True

def get_session_cookie():
    """Get session token from cookie using streamlit-cookies-manager."""
    try:
        import streamlit_cookies_manager
        import os
        
        # Initialize with proper encryption
        cookies = streamlit_cookies_manager.EncryptedCookieManager(
            prefix="stravatalk/",
            password=os.getenv("COOKIES_PASSWORD", "stravatalk-secret-key-2024")
        )
        
        # Check if cookies are ready
        if not cookies.ready():
            return None  # Don't stop, just return None if not ready
        
        return cookies.get('strava_session')
        
    except ImportError:
        # Fallback to JavaScript approach if streamlit-cookies-manager is not available
        if not hasattr(st.session_state, 'cookie_check_done'):
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
            st.session_state.cookie_check_done = True
        
        return None

def clear_session_cookie():
    """Clear session cookie."""
    try:
        import streamlit_cookies_manager
        import os
        
        # Initialize with proper encryption
        cookies = streamlit_cookies_manager.EncryptedCookieManager(
            prefix="stravatalk/",
            password=os.getenv("COOKIES_PASSWORD", "stravatalk-secret-key-2024")
        )
        
        if cookies.ready():
            if 'strava_session' in cookies:
                del cookies['strava_session']
            cookies.save()  # Force immediate save
            return
    except ImportError:
        pass
    
    # Fallback to JavaScript approach
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