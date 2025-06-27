"""
Authentication utilities for StravaTalk magic link system.
"""

import os
import jwt
import secrets
import time
from datetime import datetime, timedelta
from typing import Optional, Dict, Any
import psycopg2
import psycopg2.extras
from dotenv import load_dotenv

from .db_utils import get_db_connection

load_dotenv()

# JWT configuration
JWT_SECRET = os.getenv("JWT_SECRET", secrets.token_urlsafe(32))
JWT_ALGORITHM = "HS256"
MAGIC_LINK_EXPIRY_MINUTES = 10
SESSION_EXPIRY_HOURS = 24 * 7  # 1 week

class AuthenticationError(Exception):
    """Custom exception for authentication errors."""
    pass

# Magic Link Token Management

def generate_magic_token(email: str) -> str:
    """Generate a secure magic link token for email authentication."""
    payload = {
        "email": email,
        "exp": datetime.utcnow() + timedelta(minutes=MAGIC_LINK_EXPIRY_MINUTES),
        "iat": datetime.utcnow(),
        "type": "magic_link"
    }
    return jwt.encode(payload, JWT_SECRET, algorithm=JWT_ALGORITHM)

def verify_magic_token(token: str) -> Optional[str]:
    """Verify a magic link token and return the email if valid."""
    try:
        payload = jwt.decode(token, JWT_SECRET, algorithms=[JWT_ALGORITHM])
        
        if payload.get("type") != "magic_link":
            return None
            
        return payload.get("email")
    except jwt.ExpiredSignatureError:
        return None
    except jwt.InvalidTokenError:
        return None

def store_magic_token(email: str, token: str) -> bool:
    """Store a magic token in the database."""
    conn = get_db_connection()
    if not conn:
        return False
    
    try:
        cursor = conn.cursor()
        expires_at = datetime.utcnow() + timedelta(minutes=MAGIC_LINK_EXPIRY_MINUTES)
        
        cursor.execute("""
            INSERT INTO magic_tokens (email, token, expires_at) 
            VALUES (%s, %s, %s)
        """, (email, token, expires_at))
        
        conn.commit()
        return True
        
    except Exception as e:
        print(f"Error storing magic token: {e}")
        conn.rollback()
        return False
    finally:
        cursor.close()
        conn.close()

def validate_and_consume_magic_token(token: str) -> Optional[str]:
    """Validate a magic token and mark it as used. Returns email if valid."""
    conn = get_db_connection()
    if not conn:
        return None
    
    try:
        cursor = conn.cursor(cursor_factory=psycopg2.extras.DictCursor)
        
        # Check if token exists and is not used
        cursor.execute("""
            SELECT email, expires_at, used 
            FROM magic_tokens 
            WHERE token = %s
        """, (token,))
        
        result = cursor.fetchone()
        if not result:
            return None
        
        # Check if token is expired or already used
        if result['used'] or result['expires_at'] < datetime.utcnow():
            return None
        
        # Mark token as used
        cursor.execute("""
            UPDATE magic_tokens 
            SET used = TRUE 
            WHERE token = %s
        """, (token,))
        
        conn.commit()
        
        # Also verify JWT signature
        email = verify_magic_token(token)
        if email != result['email']:
            return None
            
        return email
        
    except Exception as e:
        print(f"Error validating magic token: {e}")
        conn.rollback()
        return None
    finally:
        cursor.close()
        conn.close()

# User Management

def get_or_create_user(email: str) -> Optional[int]:
    """Get existing user or create new user. Returns user_id."""
    conn = get_db_connection()
    if not conn:
        return None
    
    try:
        cursor = conn.cursor(cursor_factory=psycopg2.extras.DictCursor)
        
        # Try to get existing user
        cursor.execute("SELECT id FROM users WHERE email = %s", (email,))
        result = cursor.fetchone()
        
        if result:
            # Update last login
            cursor.execute("""
                UPDATE users SET last_login = NOW() WHERE id = %s
            """, (result['id'],))
            conn.commit()
            return result['id']
        
        # Create new user
        cursor.execute("""
            INSERT INTO users (email, last_login) 
            VALUES (%s, NOW()) 
            RETURNING id
        """, (email,))
        
        result = cursor.fetchone()
        conn.commit()
        return result['id'] if result else None
        
    except Exception as e:
        print(f"Error getting/creating user: {e}")
        conn.rollback()
        return None
    finally:
        cursor.close()
        conn.close()

# Session Management

def generate_session_token() -> str:
    """Generate a secure session token."""
    return secrets.token_urlsafe(32)

def create_user_session(user_id: int) -> Optional[str]:
    """Create a new session for the user. Returns session token."""
    conn = get_db_connection()
    if not conn:
        return None
    
    try:
        cursor = conn.cursor()
        
        session_token = generate_session_token()
        expires_at = datetime.utcnow() + timedelta(hours=SESSION_EXPIRY_HOURS)
        
        cursor.execute("""
            INSERT INTO user_sessions (user_id, session_token, expires_at) 
            VALUES (%s, %s, %s)
        """, (user_id, session_token, expires_at))
        
        conn.commit()
        return session_token
        
    except Exception as e:
        print(f"Error creating session: {e}")
        conn.rollback()
        return None
    finally:
        cursor.close()
        conn.close()

def validate_session_token(session_token: str) -> Optional[Dict[str, Any]]:
    """Validate a session token and return user info if valid."""
    conn = get_db_connection()
    if not conn:
        return None
    
    try:
        cursor = conn.cursor(cursor_factory=psycopg2.extras.DictCursor)
        
        cursor.execute("""
            SELECT s.user_id, s.expires_at, u.email 
            FROM user_sessions s
            JOIN users u ON s.user_id = u.id
            WHERE s.session_token = %s AND s.expires_at > NOW()
        """, (session_token,))
        
        result = cursor.fetchone()
        if not result:
            return None
        
        # Update last used timestamp
        cursor.execute("""
            UPDATE user_sessions 
            SET last_used = NOW() 
            WHERE session_token = %s
        """, (session_token,))
        
        conn.commit()
        
        return {
            "user_id": result['user_id'],
            "email": result['email'],
            "expires_at": result['expires_at']
        }
        
    except Exception as e:
        print(f"Error validating session: {e}")
        return None
    finally:
        cursor.close()
        conn.close()

def invalidate_session(session_token: str) -> bool:
    """Invalidate a session token (logout)."""
    conn = get_db_connection()
    if not conn:
        return False
    
    try:
        cursor = conn.cursor()
        
        cursor.execute("""
            DELETE FROM user_sessions 
            WHERE session_token = %s
        """, (session_token,))
        
        conn.commit()
        return cursor.rowcount > 0
        
    except Exception as e:
        print(f"Error invalidating session: {e}")
        return False
    finally:
        cursor.close()
        conn.close()

def cleanup_expired_tokens():
    """Clean up expired magic tokens and sessions."""
    conn = get_db_connection()
    if not conn:
        return
    
    try:
        cursor = conn.cursor()
        
        # Clean up expired magic tokens
        cursor.execute("DELETE FROM magic_tokens WHERE expires_at < NOW()")
        magic_deleted = cursor.rowcount
        
        # Clean up expired sessions
        cursor.execute("DELETE FROM user_sessions WHERE expires_at < NOW()")
        sessions_deleted = cursor.rowcount
        
        conn.commit()
        
        if magic_deleted > 0 or sessions_deleted > 0:
            print(f"Cleaned up {magic_deleted} expired magic tokens and {sessions_deleted} expired sessions")
        
    except Exception as e:
        print(f"Error cleaning up expired tokens: {e}")
    finally:
        cursor.close()
        conn.close()

# Strava Connection Management

def store_strava_connection(user_id: int, athlete_id: int, access_token: str, 
                          refresh_token: str, expires_at: int, scope: str = "read") -> bool:
    """Store or update Strava connection for a user."""
    conn = get_db_connection()
    if not conn:
        return False
    
    try:
        cursor = conn.cursor()
        
        # Convert timestamp to datetime
        expires_at_dt = datetime.utcfromtimestamp(expires_at)
        
        # Use UPSERT to handle existing connections
        cursor.execute("""
            INSERT INTO strava_connections (user_id, athlete_id, access_token, refresh_token, expires_at, scope)
            VALUES (%s, %s, %s, %s, %s, %s)
            ON CONFLICT (athlete_id) 
            DO UPDATE SET 
                user_id = EXCLUDED.user_id,
                access_token = EXCLUDED.access_token,
                refresh_token = EXCLUDED.refresh_token,
                expires_at = EXCLUDED.expires_at,
                scope = EXCLUDED.scope,
                updated_at = NOW()
        """, (user_id, athlete_id, access_token, refresh_token, expires_at_dt, scope))
        
        conn.commit()
        return True
        
    except Exception as e:
        print(f"Error storing Strava connection: {e}")
        conn.rollback()
        return False
    finally:
        cursor.close()
        conn.close()

def get_user_strava_connection(user_id: int) -> Optional[Dict[str, Any]]:
    """Get user's Strava connection details."""
    conn = get_db_connection()
    if not conn:
        return None
    
    try:
        cursor = conn.cursor(cursor_factory=psycopg2.extras.DictCursor)
        
        cursor.execute("""
            SELECT athlete_id, access_token, refresh_token, expires_at, scope, connected_at
            FROM strava_connections 
            WHERE user_id = %s
        """, (user_id,))
        
        result = cursor.fetchone()
        if not result:
            return None
        
        return dict(result)
        
    except Exception as e:
        print(f"Error getting Strava connection: {e}")
        return None
    finally:
        cursor.close()
        conn.close()

def disconnect_strava_account(user_id: int) -> bool:
    """Disconnect user's Strava account."""
    conn = get_db_connection()
    if not conn:
        return False
    
    try:
        cursor = conn.cursor()
        
        cursor.execute("""
            DELETE FROM strava_connections 
            WHERE user_id = %s
        """, (user_id,))
        
        conn.commit()
        return cursor.rowcount > 0
        
    except Exception as e:
        print(f"Error disconnecting Strava account: {e}")
        return False
    finally:
        cursor.close()
        conn.close()

def delete_user_account(user_id: int) -> bool:
    """Delete user account and all associated data."""
    conn = get_db_connection()
    if not conn:
        return False
    
    try:
        cursor = conn.cursor()
        
        # Delete user (CASCADE will handle strava_connections, user_sessions)
        cursor.execute("DELETE FROM users WHERE id = %s", (user_id,))
        
        # Also clean up magic tokens for this user's email
        cursor.execute("""
            DELETE FROM magic_tokens 
            WHERE email = (SELECT email FROM users WHERE id = %s)
        """, (user_id,))
        
        conn.commit()
        return cursor.rowcount > 0
        
    except Exception as e:
        print(f"Error deleting user account: {e}")
        conn.rollback()
        return False
    finally:
        cursor.close()
        conn.close()