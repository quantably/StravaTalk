"""
Authentication server for trackin.pro magic link system.
"""

from fastapi import FastAPI, Request, HTTPException, Query
from fastapi.responses import HTMLResponse, RedirectResponse, JSONResponse
from fastapi.templating import Jinja2Templates
from pydantic import BaseModel, EmailStr
import os
from dotenv import load_dotenv

from .utils.auth_utils import (
    generate_magic_token, 
    store_magic_token, 
    validate_and_consume_magic_token,
    get_or_create_user,
    create_user_session,
    validate_session_token,
    invalidate_session,
    cleanup_expired_tokens
)
from .utils.email_service import send_magic_link_email, send_welcome_email

load_dotenv()

app = FastAPI(title="trackin.pro Auth Server")
templates = Jinja2Templates(directory="templates")

STREAMLIT_URL = os.getenv("STREAMLIT_URL", "http://localhost:8501")

# Request models
class MagicLinkRequest(BaseModel):
    email: EmailStr

class SessionInfo(BaseModel):
    user_id: int
    email: str
    expires_at: str

# Authentication endpoints

@app.post("/auth/send-magic-link")
async def send_magic_link(request_data: MagicLinkRequest):
    """Generate and send a magic link to the user's email."""
    import traceback
    
    try:
        email = str(request_data.email).lower().strip()
        print(f"🚀 Starting magic link process for email: {email}")
        
        # Generate magic token
        print(f"🎯 Generating magic token...")
        magic_token = generate_magic_token(email)
        print(f"✅ Magic token generated: {magic_token[:20]}...")
        
        # Store token in database
        print(f"💾 Storing token in database...")
        if not store_magic_token(email, magic_token):
            print(f"❌ Failed to store magic token in database")
            raise HTTPException(status_code=500, detail="Failed to store magic token")
        print(f"✅ Token stored in database successfully")
        
        # Send email
        print(f"📧 Attempting to send email...")
        email_result = send_magic_link_email(email, magic_token)
        print(f"📧 Email send result: {email_result}")
        
        if not email_result:
            print(f"❌ Failed to send email")
            raise HTTPException(status_code=500, detail="Failed to send email")
        
        print(f"🎉 Magic link process completed successfully")
        return {
            "success": True,
            "message": f"Magic link sent to {email}",
            "expires_in_minutes": 10
        }
        
    except HTTPException:
        # Re-raise HTTP exceptions as-is
        raise
    except Exception as e:
        print(f"💥 Unexpected error in send_magic_link: {e}")
        print(f"📋 Traceback: {traceback.format_exc()}")
        raise HTTPException(status_code=500, detail=f"Failed to send magic link: {str(e)}")

@app.get("/auth/verify-magic-link")
async def verify_magic_link(token: str = Query(...)):
    """Verify a magic link token and create a user session."""
    try:
        # Clean up expired tokens first
        cleanup_expired_tokens()
        
        # Validate and consume the magic token
        email = validate_and_consume_magic_token(token)
        if not email:
            raise HTTPException(status_code=400, detail="Invalid or expired token")
        
        # Get or create user
        user_id = get_or_create_user(email)
        if not user_id:
            raise HTTPException(status_code=500, detail="Failed to create user account")
        
        # Create session
        session_token = create_user_session(user_id)
        if not session_token:
            raise HTTPException(status_code=500, detail="Failed to create session")
        
        # Check if this is a new user for welcome email
        # (In a real app, you'd track this better, but for simplicity we'll skip the welcome email for now)
        
        # Redirect to Streamlit with session token
        redirect_url = f"{STREAMLIT_URL}?session_token={session_token}"
        return RedirectResponse(url=redirect_url, status_code=302)
        
    except HTTPException:
        raise
    except Exception as e:
        print(f"Error verifying magic link: {e}")
        raise HTTPException(status_code=500, detail="Authentication failed")

@app.post("/auth/logout")
async def logout(session_token: str):
    """Logout user by invalidating their session."""
    try:
        success = invalidate_session(session_token)
        return {
            "success": success,
            "message": "Logged out successfully" if success else "Session not found"
        }
    except Exception as e:
        print(f"Error during logout: {e}")
        raise HTTPException(status_code=500, detail="Logout failed")

@app.get("/auth/session-info")
async def get_session_info(session_token: str = Query(...)):
    """Get information about the current session."""
    try:
        session_info = validate_session_token(session_token)
        if not session_info:
            raise HTTPException(status_code=401, detail="Invalid or expired session")
        
        return SessionInfo(
            user_id=session_info["user_id"],
            email=session_info["email"],
            expires_at=session_info["expires_at"].isoformat()
        )
        
    except HTTPException:
        raise
    except Exception as e:
        print(f"Error getting session info: {e}")
        raise HTTPException(status_code=500, detail="Failed to get session info")

# Utility endpoints

@app.post("/auth/cleanup")
async def cleanup_tokens():
    """Clean up expired tokens and sessions (can be called by cron job)."""
    try:
        cleanup_expired_tokens()
        return {"success": True, "message": "Cleanup completed"}
    except Exception as e:
        print(f"Error during cleanup: {e}")
        raise HTTPException(status_code=500, detail="Cleanup failed")

@app.get("/auth/health")
async def health_check():
    """Health check for the auth service."""
    return {
        "status": "healthy",
        "service": "trackin.pro Auth Server",
        "version": "1.1.0"
    }

# Error handlers

@app.exception_handler(404)
async def not_found_handler(request: Request, exc):
    return JSONResponse(
        status_code=404,
        content={"error": "Endpoint not found"}
    )

@app.exception_handler(500)
async def internal_error_handler(request: Request, exc):
    return JSONResponse(
        status_code=500,
        content={"error": "Internal server error"}
    )