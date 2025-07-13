"""
Login page for StravaTalk magic link authentication.
"""

import streamlit as st
import requests
import os
from urllib.parse import urlparse, parse_qs
from dotenv import load_dotenv

load_dotenv()

# Configuration
FASTAPI_URL = os.getenv("FASTAPI_URL", "http://localhost:8000")

def show_login_page():
    """Display the login page with email entry."""
    st.set_page_config(
        page_title="StravaTalk Login",
        page_icon="🏃‍♂️",
        layout="centered",
        initial_sidebar_state="collapsed"
    )
    
    # Custom CSS for better styling
    st.markdown("""
    <style>
    .main-header {
        text-align: center;
        padding: 2rem 0;
    }
    .login-container {
        max-width: 400px;
        margin: 0 auto;
        padding: 2rem;
        border-radius: 10px;
        background: #f8f9fa;
        box-shadow: 0 2px 10px rgba(0,0,0,0.1);
    }
    .stButton > button {
        width: 100%;
        background: #fc4c02;
        color: white;
        border: none;
        padding: 0.75rem;
        border-radius: 6px;
        font-weight: 600;
    }
    .stButton > button:hover {
        background: #e63900;
    }
    </style>
    """, unsafe_allow_html=True)
    
    # Main header
    st.markdown("""
    <div class="main-header">
        <h1>🏃‍♂️ StravaTalk</h1>
        <p>Your AI-powered Strava data assistant</p>
    </div>
    """, unsafe_allow_html=True)
    
    # Check for session token in URL parameters
    query_params = st.query_params
    
    if "session_token" in query_params:
        # User has a session token, validate it
        session_token = query_params["session_token"]
        if validate_session(session_token):
            # Valid session, redirect to main app
            st.query_params.clear()  # Clear URL params
            st.success("✅ Successfully logged in!")
            
            if "strava_connected" in query_params:
                st.success("🎉 Strava account connected successfully!")
            
            st.info("Redirecting to main application...")
            # Store session in session state
            st.session_state.session_token = session_token
            st.session_state.authenticated = True
            
            # Use st.rerun() to refresh the page
            st.rerun()
            return
    
    # Login form
    with st.container():
        st.markdown('<div class="login-container">', unsafe_allow_html=True)
        
        st.markdown("### 📧 Sign In")
        st.markdown("Enter your email to receive a secure login link")
        
        with st.form("login_form"):
            email = st.text_input(
                "Email Address",
                placeholder="your.email@example.com",
                help="We'll send you a magic link to sign in securely"
            )
            
            submitted = st.form_submit_button("Send Magic Link")
            
            if submitted:
                if not email:
                    st.error("Please enter your email address")
                elif not "@" in email or not "." in email:
                    st.error("Please enter a valid email address")
                else:
                    # Send magic link
                    if send_magic_link(email):
                        st.success(f"✅ Magic link sent to {email}")
                        st.info("📱 Check your email and click the link to sign in")
                        st.markdown("*The link expires in 10 minutes*")
                    else:
                        st.error("❌ Failed to send magic link. Please try again.")
        
        st.markdown('</div>', unsafe_allow_html=True)
    
    # Additional info
    st.markdown("---")
    
    # Debug info (show in development only)
    dev_mode = os.getenv("ENVIRONMENT") != "production"
    if dev_mode:
        with st.expander("🔧 Debug Info"):
            st.code(f"""
Environment Configuration:
FASTAPI_URL: {FASTAPI_URL}
            """)
    
    st.markdown("""
    **🔒 Secure & Private**
    - No passwords to remember
    - One-time magic links via email
    - Your data stays private and secure
    
    **🚀 What you can do:**
    - Connect your Strava account
    - Ask questions about your activities
    - Generate beautiful data visualizations
    - Track your training progress
    """)

def send_magic_link(email: str) -> bool:
    """Send magic link to user's email."""
    try:
        url = f"{FASTAPI_URL}/auth/send-magic-link"
        payload = {"email": email}
        
        # Only show debug info in development
        dev_mode = os.getenv("ENVIRONMENT") != "production"
        if dev_mode:
            st.info(f"🔗 Sending request to: {url}")
            st.info(f"📧 Email: {email}")
        
        response = requests.post(
            url,
            json=payload,
            timeout=10
        )
        
        if dev_mode:
            st.info(f"📡 Response status: {response.status_code}")
        
        if response.status_code == 200:
            result = response.json()
            if dev_mode:
                st.success(f"✅ Server response: {result}")
            return True
        else:
            error_detail = "Unknown error"
            try:
                error_data = response.json()
                error_detail = error_data.get("detail", error_data)
            except:
                error_detail = response.text
            
            st.error(f"❌ Server error ({response.status_code}): {error_detail}")
            return False
            
    except requests.exceptions.ConnectionError as e:
        st.error(f"🌐 Connection error: Cannot reach {FASTAPI_URL}")
        st.error(f"Details: {str(e)}")
        return False
    except requests.exceptions.Timeout as e:
        st.error(f"⏰ Timeout error: Request took too long")
        st.error(f"Details: {str(e)}")
        return False
    except Exception as e:
        st.error(f"💥 Unexpected error: {str(e)}")
        st.error(f"Error type: {type(e).__name__}")
        return False

def validate_session(session_token: str) -> bool:
    """Validate session token with FastAPI backend."""
    try:
        response = requests.get(
            f"{FASTAPI_URL}/auth/session-info",
            params={"session_token": session_token},
            timeout=10
        )
        return response.status_code == 200
    except Exception as e:
        print(f"Error validating session: {e}")
        return False

if __name__ == "__main__":
    show_login_page()