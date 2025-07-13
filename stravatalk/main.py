"""
Main FastAPI application combining OAuth and Webhook services.
This serves as the entry point for production deployment.
"""

from fastapi import FastAPI, Request, Query
import os

# Create main application
app = FastAPI(
    title="StravaTalk API Services",
    description="Combined OAuth and Webhook services for StravaTalk",
    version="1.0.0"
)

# Import individual services from same package
from . import oauth_server
from . import webhook_handler
from . import auth_server

# Root endpoint - redirect to documentation or return simple message
@app.get("/")
async def root():
    return {"message": "trackin.pro API Services", "status": "running"}

@app.get("/oauth/authorize") 
async def oauth_authorize(scope: str = "read", session_token: str = None):
    return await oauth_server.initiate_oauth(scope, session_token)

@app.get("/oauth/callback")
async def oauth_callback(request: Request, code: str = None, error: str = None, state: str = None):
    return await oauth_server.oauth_callback(request, code, error, state)

# Include webhook routes
@app.get("/webhook")
async def verify_webhook(request: Request):
    return await webhook_handler.verify_webhook(request)

@app.post("/webhook")
async def handle_webhook(request: Request):
    return await webhook_handler.handle_webhook_event(request)

# Include authentication routes directly
@app.post("/auth/send-magic-link")
async def send_magic_link(request_data: auth_server.MagicLinkRequest):
    return await auth_server.send_magic_link(request_data)

@app.get("/auth/verify-magic-link")
async def verify_magic_link(token: str = Query(...)):
    return await auth_server.verify_magic_link(token)

@app.post("/auth/logout")
async def logout(session_token: str):
    return await auth_server.logout(session_token)

@app.get("/auth/session-info")
async def get_session_info(session_token: str = Query(...)):
    return await auth_server.get_session_info(session_token)

@app.post("/auth/cleanup")
async def cleanup_tokens():
    return await auth_server.cleanup_tokens()

@app.get("/auth/health")
async def auth_health_check():
    return await auth_server.health_check()

# Add health check endpoint
@app.get("/health")
async def health_check():
    return {"status": "healthy", "services": ["oauth", "webhook", "auth"], "version": "1.0.0"}

if __name__ == "__main__":
    import uvicorn
    port = int(os.getenv("PORT", 8000))
    uvicorn.run(app, host="0.0.0.0", port=port)