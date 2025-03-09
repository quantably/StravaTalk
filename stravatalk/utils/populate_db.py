import requests
import sqlite3
import json


ACTIVITIES_URL = "https://www.strava.com/api/v3/athlete/activities"


def store_activities_in_db(activities, cursor):
    for activity in activities:
        cursor.execute(
            """
            INSERT OR REPLACE INTO activities (id, name, distance, moving_time, elapsed_time, total_elevation_gain, type, start_date)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?)
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


# Function to fetch and store activities
def fetch_and_store_activities(access_token):
    headers = {"Authorization": f"Bearer {access_token}"}
    page = 1
    per_page = 30

    conn = sqlite3.connect("strava_activities.db")
    c = conn.cursor()
    c.execute("""
        CREATE TABLE IF NOT EXISTS activities (
            id INTEGER PRIMARY KEY,
            name TEXT,
            distance REAL,
            moving_time INTEGER,
            elapsed_time INTEGER,
            total_elevation_gain REAL,
            type TEXT,
            start_date TEXT
        )
    """)

    while True:
        response = requests.get(
            ACTIVITIES_URL, headers=headers, params={"page": page, "per_page": per_page}
        )

        activities = response.json()

        if not activities:
            break  # Exit the loop if no more activities are returned

        store_activities_in_db(activities, c)
        conn.commit()  # Commit after each page
        page += 1  # Move to the next page

    conn.close()


def main():
    with open("strava_tokens.json", "r") as f:
        tokens = json.load(f)
    access_token = tokens["access_token"]
    fetch_and_store_activities(access_token)


if __name__ == "__main__":
    main()

    # # test a query to the db
    # conn = sqlite3.connect("strava_activities.db")
    # c = conn.cursor()
    # c.execute("SELECT count(*) FROM activities")
    # print(c.fetchall())
    # conn.close()
