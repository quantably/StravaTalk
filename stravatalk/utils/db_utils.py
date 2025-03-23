import sqlite3

from agents.sql_agent import TableDefinition


# TODO: Hack to overcome sqlite3 not supporting column descriptions
COLUMN_DESCRIPTIONS = {
    "activities": {
        "description": "Table containing a users Strava activity records",
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
        "description": "Table containing a users Strava token records",
        "columns": {
            "id": "Unique identifier for the record (auto-incrementing integer)",
            "access_token": "OAuth access token for Strava API authentication",
            "refresh_token": "OAuth refresh token used to obtain new access tokens",
            "created_at": "Timestamp when the record was created",
        },
    },
}


def get_table_definitions(db_path):
    """Extract table definitions from the SQLite database."""
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()

    cursor.execute("SELECT name FROM sqlite_master WHERE type='table';")
    tables = cursor.fetchall()

    table_definitions = []
    for table_name in tables:
        table_name = table_name[0]
        cursor.execute(f"PRAGMA table_info({table_name});")
        columns = cursor.fetchall()
        column_definitions = [
            {
                "name": col[1],
                "type": col[2],
                "description": COLUMN_DESCRIPTIONS[table_name]["columns"][col[1]],
            }
            for col in columns
        ]
        table_definitions.append(
            TableDefinition(
                name=table_name,
                columns=column_definitions,
                description=COLUMN_DESCRIPTIONS[table_name]["description"],
            )
        )

    conn.close()
    return table_definitions


def execute_sql_query(db_path, sql_query):
    """Execute a SQL query against the SQLite database."""
    conn = sqlite3.connect(db_path)
    conn.row_factory = sqlite3.Row
    cursor = conn.cursor()

    result = {
        "success": False,
        "rows": None,
        "column_names": None,
        "row_count": 0,
        "error_message": None,
    }

    try:
        cursor.execute(sql_query)

        # Get column names
        if cursor.description:
            result["column_names"] = [col[0] for col in cursor.description]

        # Fetch all rows
        rows = cursor.fetchall()

        # Convert to list of dicts
        if result["column_names"]:
            result["rows"] = [dict(row) for row in rows]
            result["row_count"] = len(rows)

        result["success"] = True

    except sqlite3.Error as e:
        result["error_message"] = str(e)
    finally:
        conn.close()

    return result
