import os
import psycopg2
import psycopg2.extras
import requests
import time
from dotenv import load_dotenv

# No longer need TableDefinition - using simple dicts

# Load environment variables from .env file
load_dotenv()


def inject_athlete_filter(sql_query, athlete_id):
    """
    Wrap SQL query in a CTE and apply athlete_id filter.

    Args:
        sql_query (str): Original SQL query
        athlete_id (int): Athlete ID to filter by

    Returns:
        tuple: (modified_sql_query, query_params)
    """
    if not athlete_id or not sql_query.strip().upper().startswith("SELECT"):
        return sql_query, ()

    if "activities" not in sql_query.lower():
        return sql_query, ()

    # Clean the query - remove trailing semicolons
    sql_query = sql_query.strip().rstrip(";")
    
    # Parse the original SELECT to preserve user's column selection
    import re
    select_match = re.search(r'SELECT\s+(.*?)\s+FROM', sql_query, re.IGNORECASE | re.DOTALL)
    
    # Check if this is an aggregate query (contains COUNT, SUM, AVG, etc.)
    is_aggregate_query = bool(re.search(r'\b(COUNT|SUM|AVG|MIN|MAX|GROUP\s+BY)\b', sql_query, re.IGNORECASE))
    
    if is_aggregate_query:
        # For aggregate queries, add athlete_id filter to WHERE clause instead of CTE
        # This is simpler and avoids GROUP BY issues
        if 'WHERE' in sql_query.upper():
            # Add to existing WHERE clause
            modified_query = re.sub(
                r'\bWHERE\b', 
                'WHERE athlete_id = %s AND', 
                sql_query, 
                count=1, 
                flags=re.IGNORECASE
            )
        else:
            # Add WHERE clause before ORDER BY, GROUP BY, HAVING, LIMIT
            clause_pattern = r'\s+(ORDER\s+BY|GROUP\s+BY|HAVING|LIMIT)\s+'
            match = re.search(clause_pattern, sql_query, re.IGNORECASE)
            if match:
                insert_pos = match.start()
                modified_query = sql_query[:insert_pos] + ' WHERE athlete_id = %s' + sql_query[insert_pos:]
            else:
                modified_query = sql_query + ' WHERE athlete_id = %s'
        
        return modified_query, (athlete_id,)
    
    # For non-aggregate queries, use a simpler approach - just add athlete_id to WHERE clause
    # This avoids the complexity of CTE column aliasing issues
    if 'WHERE' in sql_query.upper():
        # Add to existing WHERE clause
        modified_query = re.sub(
            r'\bWHERE\b', 
            'WHERE athlete_id = %s AND', 
            sql_query, 
            count=1, 
            flags=re.IGNORECASE
        )
    else:
        # Add WHERE clause before ORDER BY, GROUP BY, HAVING, LIMIT
        clause_pattern = r'\s+(ORDER\s+BY|GROUP\s+BY|HAVING|LIMIT)\s+'
        match = re.search(clause_pattern, sql_query, re.IGNORECASE)
        if match:
            insert_pos = match.start()
            modified_query = sql_query[:insert_pos] + ' WHERE athlete_id = %s' + sql_query[insert_pos:]
        else:
            modified_query = sql_query + ' WHERE athlete_id = %s'
    
    wrapped_query = modified_query

    return wrapped_query, (athlete_id,)


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


def execute_sql_query(sql_query, athlete_id=None, query_params=None):
    """Execute a SQL query against the database with optional user filtering."""
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

        # If athlete_id is provided, automatically add user filtering for SELECT queries
        if athlete_id:
            sql_query, athlete_params = inject_athlete_filter(sql_query, athlete_id)
            query_params = query_params + athlete_params

        # Debug: Log final SQL query being executed
        import logging

        logger = logging.getLogger(__name__)
        logger.info(f"🔍 Final SQL being executed: {sql_query}")
        logger.info(f"🔍 Query parameters: {query_params}")
        logger.info(f"🔍 Parameter count in SQL: {sql_query.count('%s')}")
        logger.info(f"🔍 Parameters provided: {len(query_params)}")

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
        cursor.execute(
            "SELECT COUNT(*) FROM activities WHERE athlete_id = %s", (athlete_id,)
        )
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
