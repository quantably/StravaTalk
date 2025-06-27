"""
Main FastAPI application combining OAuth and Webhook services.
This serves as the entry point for production deployment.
"""

from fastapi import FastAPI, Request
from fastapi.templating import Jinja2Templates
from fastapi.responses import HTMLResponse
import os

# Create main application
app = FastAPI(
    title="StravaTalk API Services",
    description="Combined OAuth and Webhook services for StravaTalk",
    version="1.0.0"
)

# Initialize templates
templates = Jinja2Templates(directory="../templates")

# Import individual services from same package
from . import oauth_server
from . import webhook_handler
from . import auth_server

# Mount OAuth routes at root level (since OAuth expects specific paths)
@app.get("/", response_class=HTMLResponse)
async def oauth_home(request: Request):
    return await oauth_server.home(request)

@app.get("/oauth/authorize") 
async def oauth_authorize(scope: str = "read"):
    return await oauth_server.initiate_oauth(scope)

@app.get("/oauth/callback")
async def oauth_callback(request: Request, code: str = None, error: str = None):
    return await oauth_server.oauth_callback(request, code, error)

# Include webhook routes
@app.get("/webhook")
async def verify_webhook(request: Request):
    return await webhook_handler.verify_webhook(request)

@app.post("/webhook")
async def handle_webhook(request: Request):
    return await webhook_handler.handle_webhook_event(request)

# Mount authentication routes
app.mount("/auth", auth_server.app)

# Add health check endpoint
@app.get("/health")
async def health_check():
    return {"status": "healthy", "services": ["oauth", "webhook", "auth"], "version": "1.0.0"}

if __name__ == "__main__":
    import uvicorn
    port = int(os.getenv("PORT", 8000))
    uvicorn.run(app, host="0.0.0.0", port=port)