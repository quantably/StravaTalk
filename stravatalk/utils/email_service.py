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
    """Send a simple text magic link email to the user."""
    print(f"📧 send_magic_link_email called for: {email}")
    
    if not initialize_resend():
        print(f"📧 Email service not available - simulating success")
        print(f"🔗 Magic link URL would be: {FASTAPI_URL}/auth/verify-magic-link?token={magic_token[:20]}...")
        return True  # Return True for development
    
    # The magic link should go to the FastAPI verification endpoint
    # which will then redirect to Streamlit with a session token
    magic_link = f"{FASTAPI_URL}/auth/verify-magic-link?token={magic_token}"
    
    # Simple text content only
    text_content = f"""Hi! Here's your secure login link for trackin.pro:

{magic_link}

This link expires in 10 minutes and can only be used once.

If you didn't request this login link, you can safely ignore this email.

Thanks,
The trackin.pro Team"""
    
    try:
        response = resend.Emails.send({
            "from": FROM_EMAIL,
            "to": email,
            "subject": "📊 Your trackin.pro Login Link",
            "text": text_content
        })
        
        print(f"✅ Magic link email sent to {email}")
        return True
        
    except Exception as e:
        print(f"❌ Failed to send email to {email}: {e}")
        return False

def send_welcome_email(email: str) -> bool:
    """Send a simple welcome email to new users."""
    if not initialize_resend():
        print(f"📧 Would send welcome email to {email} (email disabled in development)")
        return True
    
    text_content = f"""Welcome to trackin.pro!

Your account has been created successfully. You're now ready to explore your fitness data with natural language queries!

What you can do:
• Ask questions about your activities in plain English
• Generate insights from your training data  
• Track your progress over time
• Secure, private access to only your data

Next Steps:
1. Connect your Strava account (if you haven't already)
2. Start asking questions about your activities
3. Explore your training patterns and achievements

Happy training!

The trackin.pro Team"""
    
    try:
        response = resend.Emails.send({
            "from": FROM_EMAIL,
            "to": email,
            "subject": "🎉 Welcome to trackin.pro!",
            "text": text_content
        })
        
        print(f"✅ Welcome email sent to {email}")
        return True
        
    except Exception as e:
        print(f"❌ Failed to send welcome email to {email}: {e}")
        return False