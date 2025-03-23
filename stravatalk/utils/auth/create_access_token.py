import requests
import os
from dotenv import load_dotenv
import sqlite3

load_dotenv()

CLIENT_ID = os.getenv("CLIENT_ID")
CLIENT_SECRET = os.getenv("CLIENT_SECRET")

AUTHORIZATION_URL = f"https://www.strava.com/oauth/authorize?client_id={CLIENT_ID}&response_type=code&redirect_uri=https://google.com&approval_prompt=force&scope=activity:read"
TOKEN_URL = "https://www.strava.com/oauth/token"

# Add this constant near the top with other constants
STRAVA_DB_PATH = os.getenv("STRAVA_DB_PATH")


def get_authorization_code():
    # Redirect to Strava authorization page
    print(f"Please visit this URL to authorize the application: {AUTHORIZATION_URL}")
    authorization_code = input("Enter the authorization code: ")
    return authorization_code


# Function to get access token
def get_tokens(authorization_code):
    response = requests.post(
        TOKEN_URL,
        data={
            "client_id": CLIENT_ID,
            "client_secret": CLIENT_SECRET,
            "code": authorization_code,
            "grant_type": "authorization_code",
        },
    )
    access_token_data = response.json()
    return access_token_data["access_token"], access_token_data["refresh_token"]


def store_tokens_in_db(access_token, refresh_token):
    conn = sqlite3.connect(STRAVA_DB_PATH)
    cursor = conn.cursor()

    # Create table if it doesn't exist
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS tokens (
            id INTEGER PRIMARY KEY,
            access_token TEXT NOT NULL,
            refresh_token TEXT NOT NULL,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    """)

    # Insert or update tokens
    cursor.execute(
        """
        INSERT OR REPLACE INTO tokens (id, access_token, refresh_token)
        VALUES (1, ?, ?)
    """,
        (access_token, refresh_token),
    )

    conn.commit()
    conn.close()


if __name__ == "__main__":
    authorization_code = get_authorization_code()
    access_token, refresh_token = get_tokens(authorization_code)
    store_tokens_in_db(access_token, refresh_token)
