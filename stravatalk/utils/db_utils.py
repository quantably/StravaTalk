import os
import psycopg2
import psycopg2.extras
import requests
import time
from dotenv import load_dotenv

from ..agents.sql_agent import TableDefinition

# Load environment variables from .env file
load_dotenv()

# TODO: Hack to overcome not having column descriptions in the DB yet.
# In PostgreSQL, it's better to add these as comments directly on the columns.
COLUMN_DESCRIPTIONS = {
    "activities": {
        "description": "Table containing a user's Strava activity records",
        "columns": {
            "id": "unique identifier for each activity",
            "name": "name of the activity",
            "distance": "total distance covered in meters (convert to km with distance / 1000)",
            "moving_time": "time spent moving in seconds (display in HH:MM:SS format)",
            "elapsed_time": "total elapsed time in seconds (display in HH:MM:SS format)",
            "total_elevation_gain": "total elevation gain in meters",
            "type": "type of activity (e.g., Run, Ride, Swim)",
            "start_date": "when the activity started",
            "_derived_pace": "calculated pace in minutes per mile: (moving_time / 60) / (distance / 1609.34) AS pace_min_mi",
        },
    },
    "tokens": {
        "description": "Table containing a user's Strava token records",
        "columns": {
            "id": "Unique identifier for the record (auto-incrementing integer)",
            "access_token": "OAuth access token for Strava API authentication",
            "refresh_token": "OAuth refresh token used to obtain new access tokens",
            "created_at": "Timestamp when the record was created",
        },
    },
}

def get_db_connection():
    """Establishes a connection to the PostgreSQL database."""
    database_url = os.getenv("DATABASE_URL")
    if not database_url:
        # Fallback to local SQLite for development if no remote DB is configured
        local_db_path = os.getenv("STRAVA_DB_PATH")
        if local_db_path:
            return None  # Sentinel to indicate SQLite should be used
        raise ValueError("Neither DATABASE_URL nor STRAVA_DB_PATH environment variables are set.")
    return psycopg2.connect(database_url)

def get_table_definitions():
    """Extract table definitions from the database."""
    conn = get_db_connection()
    if conn is None:
        # Fallback to original SQLite implementation
        import sqlite3
        db_path = os.getenv("STRAVA_DB_PATH")
        conn = sqlite3.connect(db_path)
        cursor = conn.cursor()
        cursor.execute("SELECT name FROM sqlite_master WHERE type='table';")
        tables = cursor.fetchall()
        table_definitions = []
        for table_name_tuple in tables:
            table_name = table_name_tuple[0]
            if table_name not in COLUMN_DESCRIPTIONS:
                continue
            cursor.execute(f"PRAGMA table_info({table_name});")
            columns = cursor.fetchall()
            column_definitions = [
                {"name": col[1], "type": col[2], "description": COLUMN_DESCRIPTIONS.get(table_name, {}).get("columns", {}).get(col[1], "")}
                for col in columns
            ]
            table_definitions.append(TableDefinition(name=table_name, columns=column_definitions, description=COLUMN_DESCRIPTIONS.get(table_name, {}).get("description", "")))
        conn.close()
        return table_definitions

    # PostgreSQL implementation
    cursor = conn.cursor()
    cursor.execute("SELECT table_name FROM information_schema.tables WHERE table_schema = 'public' AND table_type = 'BASE TABLE';")
    tables = cursor.fetchall()
    table_definitions = []
    for table_name_tuple in tables:
        table_name = table_name_tuple[0]
        if table_name not in COLUMN_DESCRIPTIONS:
            continue
        cursor.execute("SELECT column_name, data_type FROM information_schema.columns WHERE table_name = %s;", (table_name,))
        columns = cursor.fetchall()
        column_definitions = [
            {"name": col[0], "type": col[1], "description": COLUMN_DESCRIPTIONS.get(table_name, {}).get("columns", {}).get(col[0], "No description available.")}
            for col in columns
        ]
        table_definitions.append(TableDefinition(name=table_name, columns=column_definitions, description=COLUMN_DESCRIPTIONS.get(table_name, {}).get("description", "No description available.")))
    cursor.close()
    conn.close()
    return table_definitions

def execute_sql_query(sql_query, athlete_id=None):
    """Execute a SQL query against the database with optional user filtering."""
    conn = get_db_connection()
    if not conn:
        return {"success": False, "rows": None, "column_names": None, "row_count": 0, "error_message": "Database connection failed"}

    cursor = conn.cursor(cursor_factory=psycopg2.extras.DictCursor)
    result = {"success": False, "rows": None, "column_names": None, "row_count": 0, "error_message": None}
    
    try:
        # Convert SQLite-style placeholders to PostgreSQL style first
        if '?' in sql_query:
            # Replace ? placeholders with %s for PostgreSQL
            placeholder_count = sql_query.count('?')
            for i in range(placeholder_count):
                sql_query = sql_query.replace('?', '%s', 1)
        
        # If athlete_id is provided, automatically add user filtering for SELECT queries
        query_params = ()
        if athlete_id and sql_query.strip().upper().startswith('SELECT'):
            # Add athlete_id filtering to the query if it mentions activities table
            if 'FROM activities' in sql_query.upper() or 'JOIN activities' in sql_query.upper():
                # Remove any existing athlete_id filters that might have been generated by AI
                import re
                sql_query = re.sub(r'\s*WHERE\s+athlete_id\s*=\s*%s\s*', ' ', sql_query, flags=re.IGNORECASE)
                sql_query = re.sub(r'\s*AND\s+athlete_id\s*=\s*%s\s*', ' ', sql_query, flags=re.IGNORECASE)
                
                # Use parameterized query to prevent SQL injection
                if 'WHERE' in sql_query.upper():
                    sql_query += f" AND activities.athlete_id = %s"
                else:
                    sql_query += f" WHERE activities.athlete_id = %s"
                query_params = (athlete_id,)
        
        # Debug: Print final SQL query being executed
        print(f"🔍 Final SQL being executed: {sql_query}")
        print(f"🔍 Query parameters: {query_params}")
        
        cursor.execute(sql_query, query_params)
        if cursor.description:
            result["column_names"] = [col.name for col in cursor.description]
            rows = cursor.fetchall()
            result["rows"] = [dict(row) for row in rows]
            result["row_count"] = len(rows)
        else:
            conn.commit()
        result["success"] = True
    except psycopg2.Error as e:
        result["error_message"] = f"Database error: {e}"
        conn.rollback()
    finally:
        cursor.close()
        conn.close()
    return result

def execute_user_query(sql_query, athlete_id):
    """Execute a user-scoped query with automatic athlete_id filtering."""
    return execute_sql_query(sql_query, athlete_id=athlete_id)

def get_user_activities(athlete_id, limit=None):
    """Get activities for a specific user."""
    query = "SELECT * FROM activities WHERE athlete_id = %s ORDER BY start_date DESC"
    if limit:
        query += f" LIMIT {limit}"
    
    conn = get_db_connection()
    if not conn:
        return []
    
    cursor = conn.cursor(cursor_factory=psycopg2.extras.DictCursor)
    try:
        cursor.execute(query, (athlete_id,))
        rows = cursor.fetchall()
        return [dict(row) for row in rows]
    except Exception as e:
        print(f"Error fetching user activities: {e}")
        return []
    finally:
        cursor.close()
        conn.close()

def get_user_activity_count(athlete_id):
    """Get total activity count for a user."""
    conn = get_db_connection()
    if not conn:
        return 0
    
    cursor = conn.cursor()
    try:
        cursor.execute("SELECT COUNT(*) FROM activities WHERE athlete_id = %s", (athlete_id,))
        return cursor.fetchone()[0]
    except Exception as e:
        print(f"Error counting user activities: {e}")
        return 0
    finally:
        cursor.close()
        conn.close()

def get_user_from_token():
    """Get current user's athlete_id from most recent valid token."""
    conn = get_db_connection()
    if not conn:
        return None
    
    cursor = conn.cursor(cursor_factory=psycopg2.extras.DictCursor)
    try:
        cursor.execute("""
            SELECT athlete_id, access_token, refresh_token, expires_at 
            FROM user_tokens 
            ORDER BY updated_at DESC LIMIT 1
        """)
        result = cursor.fetchone()
        if not result:
            return None
        
        # Check if token is expired
        current_time = int(time.time())
        if result['expires_at'] < current_time:
            print(f"Token expired, attempting refresh for athlete {result['athlete_id']}")
            success = refresh_user_token(result['athlete_id'])
            if not success:
                print("Failed to refresh token")
                return None
        
        return result['athlete_id']
    except Exception as e:
        print(f"Error getting user from token: {e}")
        return None
    finally:
        cursor.close()
        conn.close()

def refresh_user_token(athlete_id):
    """Refresh an expired access token using the refresh token."""
    conn = get_db_connection()
    if not conn:
        return False
    
    cursor = conn.cursor(cursor_factory=psycopg2.extras.DictCursor)
    try:
        # Get current refresh token
        cursor.execute("""
            SELECT refresh_token FROM user_tokens 
            WHERE athlete_id = %s
        """, (athlete_id,))
        result = cursor.fetchone()
        if not result:
            print(f"No refresh token found for athlete {athlete_id}")
            return False
        
        refresh_token = result['refresh_token']
        
        # Call Strava token refresh endpoint
        token_url = "https://www.strava.com/oauth/token"
        data = {
            "client_id": os.getenv("CLIENT_ID"),
            "client_secret": os.getenv("CLIENT_SECRET"),
            "refresh_token": refresh_token,
            "grant_type": "refresh_token"
        }
        
        response = requests.post(token_url, data=data)
        
        if response.status_code == 200:
            token_data = response.json()
            
            # Update the token in database
            cursor.execute("""
                UPDATE user_tokens 
                SET access_token = %s, 
                    refresh_token = %s, 
                    expires_at = %s,
                    updated_at = CURRENT_TIMESTAMP
                WHERE athlete_id = %s
            """, (
                token_data["access_token"],
                token_data["refresh_token"], 
                token_data["expires_at"],
                athlete_id
            ))
            conn.commit()
            
            print(f"Successfully refreshed token for athlete {athlete_id}")
            return True
        else:
            print(f"Token refresh failed: {response.status_code} - {response.text}")
            return False
            
    except Exception as e:
        print(f"Error refreshing token: {e}")
        return False
    finally:
        cursor.close()
        conn.close()

def get_valid_access_token(athlete_id):
    """Get a valid access token for the athlete, refreshing if necessary."""
    conn = get_db_connection()
    if not conn:
        return None
    
    cursor = conn.cursor(cursor_factory=psycopg2.extras.DictCursor)
    try:
        cursor.execute("""
            SELECT access_token, refresh_token, expires_at 
            FROM user_tokens 
            WHERE athlete_id = %s
        """, (athlete_id,))
        result = cursor.fetchone()
        if not result:
            return None
        
        # Check if token is expired
        current_time = int(time.time())
        if result['expires_at'] < current_time:
            # Try to refresh the token
            if refresh_user_token(athlete_id):
                # Re-fetch the updated token
                cursor.execute("""
                    SELECT access_token FROM user_tokens 
                    WHERE athlete_id = %s
                """, (athlete_id,))
                updated_result = cursor.fetchone()
                return updated_result['access_token'] if updated_result else None
            else:
                return None
        
        return result['access_token']
    except Exception as e:
        print(f"Error getting valid access token: {e}")
        return None
    finally:
        cursor.close()
        conn.close()