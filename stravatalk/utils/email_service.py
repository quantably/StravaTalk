"""
Email service integration using Resend for magic link authentication.
"""

import os
import resend
from typing import Optional
from dotenv import load_dotenv

load_dotenv()

# Resend configuration
RESEND_API_KEY = os.getenv("RESEND_API_KEY")
FROM_EMAIL = os.getenv("FROM_EMAIL", "noreply@yourdomain.com")
STREAMLIT_URL = os.getenv("STREAMLIT_URL", "http://localhost:8501")
FASTAPI_URL = os.getenv("FASTAPI_URL", "http://localhost:8000")

def initialize_resend():
    """Initialize Resend with API key."""
    print(f"🔧 Initializing Resend...")
    print(f"🔑 RESEND_API_KEY present: {bool(RESEND_API_KEY)}")
    print(f"📧 FROM_EMAIL: {FROM_EMAIL}")
    print(f"🌐 STREAMLIT_URL: {STREAMLIT_URL}")
    
    if not RESEND_API_KEY:
        print("⚠️ RESEND_API_KEY not set - email functionality will be disabled")
        return False
    
    print(f"🔑 Setting Resend API key: {RESEND_API_KEY[:10]}...")
    resend.api_key = RESEND_API_KEY
    print(f"✅ Resend initialized successfully")
    return True

def send_magic_link_email(email: str, magic_token: str) -> bool:
    """Send a magic link email to the user."""
    print(f"📧 send_magic_link_email called for: {email}")
    
    if not initialize_resend():
        print(f"📧 Email service not available - simulating success")
        print(f"🔗 Magic link URL would be: {FASTAPI_URL}/auth/verify-magic-link?token={magic_token[:20]}...")
        return True  # Return True for development
    
    # The magic link should go to the FastAPI verification endpoint
    # which will then redirect to Streamlit with a session token
    magic_link = f"{FASTAPI_URL}/auth/verify-magic-link?token={magic_token}"
    
    html_content = f"""
    <!DOCTYPE html>
    <html>
    <head>
        <meta charset="utf-8">
        <meta name="viewport" content="width=device-width, initial-scale=1.0">
        <title>Your StravaTalk Login Link</title>
        <style>
            body {{
                font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif;
                line-height: 1.6;
                color: #333;
                max-width: 600px;
                margin: 0 auto;
                padding: 20px;
            }}
            .container {{
                background: #f8f9fa;
                padding: 30px;
                border-radius: 10px;
                text-align: center;
            }}
            .logo {{
                font-size: 24px;
                font-weight: bold;
                color: #fc4c02;
                margin-bottom: 20px;
            }}
            .login-button {{
                display: inline-block;
                background: #fc4c02;
                color: white;
                padding: 15px 30px;
                text-decoration: none;
                border-radius: 6px;
                font-weight: 600;
                margin: 20px 0;
            }}
            .login-button:hover {{
                background: #e63900;
            }}
            .security-note {{
                background: #e7f3ff;
                padding: 15px;
                border-radius: 6px;
                margin-top: 20px;
                font-size: 14px;
                text-align: left;
            }}
            .footer {{
                margin-top: 30px;
                padding-top: 20px;
                border-top: 1px solid #eee;
                font-size: 12px;
                color: #666;
            }}
        </style>
    </head>
    <body>
        <div class="container">
            <div class="logo">StravaTalk 🏃‍♂️</div>
            
            <h1>Your Login Link is Ready!</h1>
            
            <p>Click the button below to securely log into your StravaTalk account:</p>
            
            <a href="{magic_link}" class="login-button">🔐 Log In to StravaTalk</a>
            
            <div class="security-note">
                <strong>🔒 Security Note:</strong>
                <ul style="margin: 10px 0; padding-left: 20px; text-align: left;">
                    <li>This link expires in 10 minutes</li>
                    <li>It can only be used once</li>
                    <li>Never share this link with anyone</li>
                </ul>
            </div>
            
            <p style="margin-top: 20px;">
                If you didn't request this login link, you can safely ignore this email.
            </p>
            
            <div class="footer">
                <p>This email was sent to {email}</p>
                <p>If the button doesn't work, copy and paste this link into your browser:</p>
                <p style="word-break: break-all; color: #666;">{magic_link}</p>
            </div>
        </div>
    </body>
    </html>
    """
    
    text_content = f"""
    StravaTalk - Your Login Link
    
    Hi! Here's your secure login link for StravaTalk:
    
    {magic_link}
    
    This link expires in 10 minutes and can only be used once.
    
    If you didn't request this login, you can safely ignore this email.
    """
    
    try:
        response = resend.Emails.send({
            "from": FROM_EMAIL,
            "to": email,
            "subject": "🏃‍♂️ Your StravaTalk Login Link",
            "html": html_content,
            "text": text_content
        })
        
        print(f"✅ Magic link email sent to {email}")
        return True
        
    except Exception as e:
        print(f"❌ Failed to send email to {email}: {e}")
        return False

def send_welcome_email(email: str) -> bool:
    """Send a welcome email to new users."""
    if not initialize_resend():
        print(f"📧 Would send welcome email to {email} (email disabled in development)")
        return True
    
    html_content = f"""
    <!DOCTYPE html>
    <html>
    <head>
        <meta charset="utf-8">
        <meta name="viewport" content="width=device-width, initial-scale=1.0">
        <title>Welcome to StravaTalk!</title>
        <style>
            body {{
                font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif;
                line-height: 1.6;
                color: #333;
                max-width: 600px;
                margin: 0 auto;
                padding: 20px;
            }}
            .container {{
                background: #f8f9fa;
                padding: 30px;
                border-radius: 10px;
                text-align: center;
            }}
            .logo {{
                font-size: 32px;
                margin-bottom: 20px;
            }}
            .features {{
                text-align: left;
                background: white;
                padding: 20px;
                border-radius: 6px;
                margin: 20px 0;
            }}
            .feature {{
                margin-bottom: 15px;
                padding-left: 25px;
                position: relative;
            }}
            .feature:before {{
                content: "✅";
                position: absolute;
                left: 0;
            }}
        </style>
    </head>
    <body>
        <div class="container">
            <div class="logo">🏃‍♂️ StravaTalk</div>
            
            <h1>Welcome to StravaTalk!</h1>
            
            <p>Your account has been created successfully. You're now ready to explore your Strava data with natural language queries!</p>
            
            <div class="features">
                <div class="feature">Ask questions about your activities in plain English</div>
                <div class="feature">Generate beautiful visualizations of your training data</div>
                <div class="feature">Track your progress over time</div>
                <div class="feature">Secure, private access to only your data</div>
            </div>
            
            <p><strong>Next Steps:</strong></p>
            <ol style="text-align: left;">
                <li>Connect your Strava account (if you haven't already)</li>
                <li>Start asking questions about your activities</li>
                <li>Explore your training patterns and achievements</li>
            </ol>
            
            <p style="margin-top: 30px;">
                Happy training! 🚀
            </p>
        </div>
    </body>
    </html>
    """
    
    try:
        response = resend.Emails.send({
            "from": FROM_EMAIL,
            "to": email,
            "subject": "🎉 Welcome to StravaTalk!",
            "html": html_content
        })
        
        print(f"✅ Welcome email sent to {email}")
        return True
        
    except Exception as e:
        print(f"❌ Failed to send welcome email to {email}: {e}")
        return False