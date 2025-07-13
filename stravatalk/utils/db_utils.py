import os
import psycopg2
import psycopg2.extras
import requests
import time
import logging
from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv()

# Configure logger
logger = logging.getLogger(__name__)

# Column descriptions for the activities table (only table exposed to LLM)
ACTIVITIES_DESCRIPTION = {
    "name": "activities",
    "description": "Table containing a user's Strava activity records",
    "columns": {
        "id": "unique identifier for each activity",
        "name": "name of the activity",
        "distance": "total distance covered in meters",
        "moving_time": "time spent moving in seconds",
        "elapsed_time": "total elapsed time in seconds",
        "total_elevation_gain": "total elevation gain in meters",
        "type": "type of activity (e.g., Run, Ride, Swim)",
        "start_date": "when the activity started",
    },
}


def get_db_connection():
    """Establishes a connection to the PostgreSQL database."""
    database_url = os.getenv("DATABASE_URL")
    if not database_url:
        raise ValueError("DATABASE_URL environment variable is required.")
    
    return psycopg2.connect(database_url)


def get_table_definitions():
    """Get activities table definition for LLM (only table exposed to agents)."""
    conn = get_db_connection()
    cursor = conn.cursor()

    try:
        # Get activities table schema from PostgreSQL
        cursor.execute(
            "SELECT column_name, data_type FROM information_schema.columns WHERE table_name = 'activities' and column_name != 'athlete_id' ORDER BY ordinal_position;"
        )
        columns = cursor.fetchall()

        column_definitions = [
            {
                "name": col[0],
                "type": col[1],
                "description": ACTIVITIES_DESCRIPTION["columns"].get(col[0], ""),
            }
            for col in columns
        ]

        # Return simple dict instead of Pydantic object to avoid serialization issues
        return [
            {
                "name": "activities",
                "columns": column_definitions,
                "description": ACTIVITIES_DESCRIPTION["description"],
            }
        ]

    finally:
        cursor.close()
        conn.close()


def execute_sql_query_with_user_context(sql_query, user_id, query_params=None):
    """
    Execute a SQL query with RLS user context using session variables.
    """
    conn = get_db_connection()
    if not conn:
        return {
            "success": False,
            "rows": None,
            "column_names": None,
            "row_count": 0,
            "error_message": "Database connection failed",
        }

    cursor = conn.cursor(cursor_factory=psycopg2.extras.DictCursor)
    result = {
        "success": False,
        "rows": None,
        "column_names": None,
        "row_count": 0,
        "error_message": None,
    }

    try:
        # Initialize parameters
        if query_params is None:
            query_params = ()

        # Set user context for RLS
        if user_id:
            cursor.execute("SET app.current_user_id = %s", (user_id,))
            logger.info(f"🔒 Set RLS user context: {user_id}")

        # Execute the query - RLS will automatically filter
        logger.info(f"🔍 Executing SQL with RLS: {sql_query}")
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
    except Exception as e:
        result["error_message"] = f"Unexpected error: {e}"
        conn.rollback()
    finally:
        cursor.close()
        conn.close()
        
    return result


def execute_sql_query(sql_query, athlete_id=None, query_params=None):
    """Execute a SQL query with RLS user context."""
    if athlete_id:
        # Use RLS user context
        return execute_sql_query_with_user_context(sql_query, athlete_id, query_params)
    else:
        # No user context - execute without RLS filtering (admin queries)
        conn = get_db_connection()
        if not conn:
            return {
                "success": False,
                "rows": None,
                "column_names": None,
                "row_count": 0,
                "error_message": "Database connection failed",
            }

        cursor = conn.cursor(cursor_factory=psycopg2.extras.DictCursor)
        result = {
            "success": False,
            "rows": None,
            "column_names": None,
            "row_count": 0,
            "error_message": None,
        }

        try:
            if query_params is None:
                query_params = ()

            logger.info(f"🔍 Executing SQL without user context: {sql_query}")
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
    """Execute a user-scoped query with RLS context."""
    return execute_sql_query(sql_query, athlete_id=athlete_id)


def get_user_activities(athlete_id, limit=None):
    """Get activities for a specific user using transaction-level RLS."""
    # RLS automatically filters to user's activities, no WHERE clause needed
    query = "SELECT * FROM activities ORDER BY start_date DESC"
    if limit:
        query += f" LIMIT {limit}"

    result = execute_sql_query_with_user_context(query, athlete_id)
    
    if result["success"]:
        return result["rows"]
    else:
        print(f"Error fetching user activities: {result['error_message']}")
        return []


def get_user_activity_count(athlete_id):
    """Get total activity count for a user using transaction-level RLS."""
    result = execute_sql_query_with_user_context("SELECT COUNT(*) FROM activities", athlete_id)
    
    if result["success"] and result["rows"]:
        return result["rows"][0]["count"]
    else:
        print(f"Error counting user activities: {result.get('error_message', 'Unknown error')}")
        return 0


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
        if result["expires_at"] < current_time:
            print(
                f"Token expired, attempting refresh for athlete {result['athlete_id']}"
            )
            success = refresh_user_token(result["athlete_id"])
            if not success:
                print("Failed to refresh token")
                return None

        return result["athlete_id"]
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
        cursor.execute(
            """
            SELECT refresh_token FROM user_tokens 
            WHERE athlete_id = %s
        """,
            (athlete_id,),
        )
        result = cursor.fetchone()
        if not result:
            print(f"No refresh token found for athlete {athlete_id}")
            return False

        refresh_token = result["refresh_token"]

        # Call Strava token refresh endpoint
        token_url = "https://www.strava.com/oauth/token"
        data = {
            "client_id": os.getenv("CLIENT_ID"),
            "client_secret": os.getenv("CLIENT_SECRET"),
            "refresh_token": refresh_token,
            "grant_type": "refresh_token",
        }

        response = requests.post(token_url, data=data)

        if response.status_code == 200:
            token_data = response.json()

            # Update the token in database
            cursor.execute(
                """
                UPDATE user_tokens 
                SET access_token = %s, 
                    refresh_token = %s, 
                    expires_at = %s,
                    updated_at = CURRENT_TIMESTAMP
                WHERE athlete_id = %s
            """,
                (
                    token_data["access_token"],
                    token_data["refresh_token"],
                    token_data["expires_at"],
                    athlete_id,
                ),
            )
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
        cursor.execute(
            """
            SELECT access_token, refresh_token, expires_at 
            FROM user_tokens 
            WHERE athlete_id = %s
        """,
            (athlete_id,),
        )
        result = cursor.fetchone()
        if not result:
            return None

        # Check if token is expired
        current_time = int(time.time())
        if result["expires_at"] < current_time:
            # Try to refresh the token
            if refresh_user_token(athlete_id):
                # Re-fetch the updated token
                cursor.execute(
                    """
                    SELECT access_token FROM user_tokens 
                    WHERE athlete_id = %s
                """,
                    (athlete_id,),
                )
                updated_result = cursor.fetchone()
                return updated_result["access_token"] if updated_result else None
            else:
                return None

        return result["access_token"]
    except Exception as e:
        print(f"Error getting valid access token: {e}")
        return None
    finally:
        cursor.close()
        conn.close()
