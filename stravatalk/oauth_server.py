from fastapi import FastAPI, Request, HTTPException
from fastapi.responses import HTMLResponse, RedirectResponse
from fastapi.templating import Jinja2Templates
import os
import requests
from dotenv import load_dotenv
from .utils.db_utils import get_db_connection
from .utils.auth_utils import store_strava_connection

load_dotenv()

app = FastAPI(title="StravaTalk OAuth Server")
templates = Jinja2Templates(directory="templates")

CLIENT_ID = os.getenv("CLIENT_ID")
CLIENT_SECRET = os.getenv("CLIENT_SECRET")
REDIRECT_URI = os.getenv("OAUTH_REDIRECT_URI", "http://localhost:8001/oauth/callback")
STREAMLIT_URL = os.getenv("STREAMLIT_URL", "http://localhost:8501")

@app.get("/", response_class=HTMLResponse)
async def home(request: Request):
    """Home page with OAuth initiation."""
    return templates.TemplateResponse("oauth_home.html", {
        "request": request,
        "client_id": CLIENT_ID,
        "redirect_uri": REDIRECT_URI
    })

@app.get("/oauth/authorize")
async def initiate_oauth(scope: str = "read", session_token: str = None):
    """Initiate OAuth flow by redirecting to Strava with user-selected scope."""
    # Import here to avoid circular imports
    from .utils.auth_utils import validate_session_token
    
    print(f"🔐 OAuth authorize called with scope: {scope}")
    print(f"🎫 Session token provided: {bool(session_token)}")
    if session_token:
        print(f"🎫 Session token: {session_token[:20]}...")
    
    # Check if user has valid session
    if not session_token:
        print(f"❌ No session token provided - redirecting to login")
        return RedirectResponse(url=f"{STREAMLIT_URL}?login=true")
    
    print(f"🔍 Validating session token...")
    session_info = validate_session_token(session_token)
    if not session_info:
        print(f"❌ Invalid session token - redirecting to login")
        return RedirectResponse(url=f"{STREAMLIT_URL}?login=true")
    
    print(f"✅ Valid session for user: {session_info['email']}")
    
    # Validate scope parameter
    valid_scopes = {
        "read": "read",  # Public activities only
        "read_all": "read,activity:read_all"  # Public + private activities
    }
    
    scopes = valid_scopes.get(scope, "read")
    
    # Include session token in state parameter for callback
    state = f"session_token={session_token}"
    
    auth_url = (
        f"https://www.strava.com/oauth/authorize"
        f"?client_id={CLIENT_ID}"
        f"&response_type=code"
        f"&redirect_uri={REDIRECT_URI}"
        f"&approval_prompt=force"
        f"&scope={scopes}"
        f"&state={state}"
    )
    
    return RedirectResponse(url=auth_url)

@app.get("/oauth/callback")
async def oauth_callback(request: Request, code: str = None, error: str = None, state: str = None):
    """Handle OAuth callback from Strava."""
    # Import here to avoid circular imports
    from .utils.auth_utils import validate_session_token
    
    if error:
        return templates.TemplateResponse("oauth_error.html", {
            "request": request,
            "error": error
        })
    
    if not code:
        raise HTTPException(status_code=400, detail="No authorization code provided")
    
    # Extract session token from state parameter
    session_token = None
    if state and state.startswith("session_token="):
        session_token = state.split("session_token=")[1]
    
    if not session_token:
        return templates.TemplateResponse("oauth_error.html", {
            "request": request,
            "error": "Missing session information. Please log in first."
        })
    
    # Validate session
    session_info = validate_session_token(session_token)
    if not session_info:
        return templates.TemplateResponse("oauth_error.html", {
            "request": request,
            "error": "Invalid or expired session. Please log in again."
        })
    
    try:
        # Exchange authorization code for access token
        token_data = exchange_code_for_token(code)
        
        if not token_data:
            raise HTTPException(status_code=400, detail="Failed to exchange code for token")
        
        # Store Strava connection for this user
        athlete_id = token_data["athlete"]["id"]
        success = store_strava_connection(
            user_id=session_info["user_id"],
            athlete_id=athlete_id,
            access_token=token_data["access_token"],
            refresh_token=token_data["refresh_token"],
            expires_at=token_data["expires_at"],
            scope=token_data.get("scope", "read")
        )
        
        if not success:
            raise HTTPException(status_code=500, detail="Failed to store Strava connection")
        
        # Ensure webhook subscription exists (idempotent)
        webhook_status = ensure_webhook_subscription()
        print(f"Webhook subscription status: {webhook_status}")
        
        # Redirect back to Streamlit with session token
        redirect_url = f"{STREAMLIT_URL}?session_token={session_token}&strava_connected=true"
        return RedirectResponse(url=redirect_url, status_code=302)
        
    except Exception as e:
        print(f"OAuth callback error: {e}")
        print(f"Token data received: {token_data if 'token_data' in locals() else 'No token data'}")
        return templates.TemplateResponse("oauth_error.html", {
            "request": request,
            "error": str(e)
        })

def exchange_code_for_token(auth_code: str):
    """Exchange authorization code for access token."""
    token_url = "https://www.strava.com/oauth/token"
    
    data = {
        "client_id": CLIENT_ID,
        "client_secret": CLIENT_SECRET,
        "code": auth_code,
        "grant_type": "authorization_code"
    }
    
    response = requests.post(token_url, data=data)
    
    if response.status_code == 200:
        token_data = response.json()
        print(f"Token exchange successful: {token_data}")
        return token_data
    else:
        print(f"Token exchange failed: {response.status_code} - {response.text}")
        return None

def ensure_webhook_subscription():
    """Ensure webhook subscription exists for the application (idempotent)."""
    import requests
    
    CLIENT_ID = os.getenv("CLIENT_ID")
    CLIENT_SECRET = os.getenv("CLIENT_SECRET")
    STRAVA_WEBHOOK_VERIFY_TOKEN = os.getenv("STRAVA_WEBHOOK_VERIFY_TOKEN")
    WEBHOOK_CALLBACK_URL = os.getenv("WEBHOOK_CALLBACK_URL")
    
    if not all([CLIENT_ID, CLIENT_SECRET, STRAVA_WEBHOOK_VERIFY_TOKEN, WEBHOOK_CALLBACK_URL]):
        return "Missing webhook configuration"
    
    # First, check if subscription already exists
    list_url = "https://www.strava.com/api/v3/push_subscriptions"
    params = {
        "client_id": CLIENT_ID,
        "client_secret": CLIENT_SECRET
    }
    
    response = requests.get(list_url, params=params)
    
    if response.status_code == 200:
        subscriptions = response.json()
        if subscriptions:
            print(f"Existing webhook subscriptions found: {len(subscriptions)}")
            return f"Existing subscription active (ID: {subscriptions[0]['id']})"
    
    # If no subscription exists, create one
    subscription_url = "https://www.strava.com/api/v3/push_subscriptions"
    data = {
        "client_id": CLIENT_ID,
        "client_secret": CLIENT_SECRET,
        "callback_url": WEBHOOK_CALLBACK_URL,
        "verify_token": STRAVA_WEBHOOK_VERIFY_TOKEN,
    }
    
    response = requests.post(subscription_url, json=data)
    
    if response.status_code == 201:
        subscription = response.json()
        print(f"Webhook subscription created successfully: {subscription}")
        return f"New subscription created (ID: {subscription['id']})"
    else:
        error_msg = f"Subscription failed: {response.status_code} - {response.text}"
        print(error_msg)
        return error_msg

def store_user_tokens(athlete_id: int, access_token: str, refresh_token: str, expires_at: int, scope: str):
    """Store user tokens in PostgreSQL database with athlete association."""
    conn = get_db_connection()
    if not conn:
        raise Exception("Database connection failed - PostgreSQL required")
        
    cursor = conn.cursor()
    
    # Create user_tokens table if it doesn't exist
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS user_tokens (
            id SERIAL PRIMARY KEY,
            athlete_id INTEGER UNIQUE NOT NULL,
            access_token TEXT NOT NULL,
            refresh_token TEXT NOT NULL,
            expires_at INTEGER NOT NULL,
            scope TEXT NOT NULL,
            created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
            updated_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
        )
    """)
    
    # Insert or update user tokens
    cursor.execute("""
        INSERT INTO user_tokens 
        (athlete_id, access_token, refresh_token, expires_at, scope)
        VALUES (%s, %s, %s, %s, %s)
        ON CONFLICT (athlete_id) 
        DO UPDATE SET 
            access_token = EXCLUDED.access_token,
            refresh_token = EXCLUDED.refresh_token,
            expires_at = EXCLUDED.expires_at,
            scope = EXCLUDED.scope,
            updated_at = CURRENT_TIMESTAMP
        RETURNING id
    """, (athlete_id, access_token, refresh_token, expires_at, scope))
    
    result = cursor.fetchone()
    token_id = result[0] if result else None
    
    conn.commit()
    cursor.close()
    conn.close()
    
    print(f"Stored tokens for athlete {athlete_id} (token ID: {token_id})")
    return token_id

@app.get("/tokens")
async def list_stored_tokens():
    """List all stored tokens (for debugging)."""
    conn = get_db_connection()
    if not conn:
        raise HTTPException(status_code=500, detail="Database connection failed")
        
    cursor = conn.cursor()
    
    cursor.execute("""
        SELECT athlete_id, scope, created_at,
               CASE WHEN expires_at > EXTRACT(epoch FROM NOW()) THEN 'valid' ELSE 'expired' END as status
        FROM user_tokens ORDER BY created_at DESC
    """)
    
    tokens = cursor.fetchall()
    cursor.close()
    conn.close()
    
    return {
        "tokens": [
            {
                "athlete_id": token[0],
                "scope": token[1], 
                "created_at": token[2],
                "status": token[3]
            }
            for token in tokens
        ]
    }

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8001)