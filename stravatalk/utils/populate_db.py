import requests
import os
import psycopg2
from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv()

ACTIVITIES_URL = "https://www.strava.com/api/v3/athlete/activities"

def get_db_connection():
    """Establishes a connection to the PostgreSQL database."""
    database_url = os.getenv("DATABASE_URL")
    if not database_url:
        raise ValueError("DATABASE_URL environment variable is not set.")
    return psycopg2.connect(database_url)

def store_activities_in_db(activities, cursor):
    for activity in activities:
        cursor.execute(
            """
            INSERT INTO activities (id, name, distance, moving_time, elapsed_time, total_elevation_gain, type, start_date)
            VALUES (%s, %s, %s, %s, %s, %s, %s, %s)
            ON CONFLICT (id) DO NOTHING;
            """,
            (
                activity["id"],
                activity["name"],
                activity["distance"],
                activity["moving_time"],
                activity["elapsed_time"],
                activity["total_elevation_gain"],
                activity["type"],
                activity["start_date"],
            ),
        )

def fetch_and_store_activities(access_token):
    headers = {"Authorization": f"Bearer {access_token}"}
    page = 1
    per_page = 30

    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS activities (
            id BIGINT PRIMARY KEY,
            name TEXT,
            distance REAL,
            moving_time INTEGER,
            elapsed_time INTEGER,
            total_elevation_gain REAL,
            type TEXT,
            start_date TEXT
        );
    """)
    conn.commit()

    while True:
        response = requests.get(
            ACTIVITIES_URL, headers=headers, params={"page": page, "per_page": per_page}
        )
        response.raise_for_status()  # Raise an exception for bad status codes
        activities = response.json()

        if not activities:
            break

        store_activities_in_db(activities, cursor)
        conn.commit()
        page += 1

    cursor.close()
    conn.close()

def main():
    # For initial population, we'll need a way to get the access token.
    # This is a placeholder and will be replaced by the OAuth flow.
    # You can manually insert a valid token into your .env file for now.
    access_token = os.getenv("STRAVA_ACCESS_TOKEN")
    if not access_token:
        print("STRAVA_ACCESS_TOKEN not found in .env file. Please add it to populate the database.")
        return

    # We also need a way to create the tokens table for the first time.
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS tokens (
            id SERIAL PRIMARY KEY,
            access_token TEXT NOT NULL,
            refresh_token TEXT NOT NULL,
            created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
        );
    """)
    conn.commit()
    cursor.close()
    conn.close()

    print("Fetching and storing activities...")
    fetch_and_store_activities(access_token)
    print("Database population complete.")

if __name__ == "__main__":
    main()