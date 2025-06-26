import requests
import os
import sys
from dotenv import load_dotenv

# Add the project root to the python path to allow imports from stravatalk
# Assumes the script is in StravaTalk/stravatalk/utils/auth
project_root = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..', '..'))
sys.path.insert(0, project_root)

from ..db_utils import get_db_connection

# Load .env from the project root
load_dotenv(dotenv_path=os.path.join(project_root, '.env'))

CLIENT_ID = os.getenv("CLIENT_ID")
CLIENT_SECRET = os.getenv("CLIENT_SECRET")

# The redirect_uri must match the one you have in your Strava API application settings.
REDIRECT_URI = "http://localhost/exchange_token"
AUTHORIZATION_URL = f"https://www.strava.com/oauth/authorize?client_id={CLIENT_ID}&response_type=code&redirect_uri={REDIRECT_URI}&approval_prompt=force&scope=activity:read_all"
TOKEN_URL = "https://www.strava.com/oauth/token"


def get_authorization_code():
    """Guides the user to get an authorization code from Strava."""
    print(f"Please visit this URL to authorize the application: {AUTHORIZATION_URL}")
    print(f"\nAfter authorizing, Strava will redirect you to a URL like:")
    print(f"{REDIRECT_URI}?state=&code=YOUR_CODE_HERE&scope=read,activity:read_all")
    authorization_code = input("\nPlease paste the 'code' from the redirect URL here: ")
    return authorization_code.strip()


def get_tokens(authorization_code):
    """Exchanges an authorization code for access and refresh tokens."""
    response = requests.post(
        TOKEN_URL,
        data={
            "client_id": CLIENT_ID,
            "client_secret": CLIENT_SECRET,
            "code": authorization_code,
            "grant_type": "authorization_code",
        },
    )
    response.raise_for_status()
    token_data = response.json()
    return token_data["access_token"], token_data["refresh_token"]


def store_tokens_in_db(access_token, refresh_token):
    """Stores the access and refresh tokens in the PostgreSQL database."""
    conn = get_db_connection()
    if conn is None:
        print("Could not connect to the database. Please check your DATABASE_URL environment variable.")
        return
        
    cursor = conn.cursor()

    # This table should be created by populate_db.py, but we ensure it's there.
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS tokens (
            id SERIAL PRIMARY KEY,
            access_token TEXT NOT NULL,
            refresh_token TEXT NOT NULL,
            created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
        );
    """)

    # Insert new tokens.
    cursor.execute(
        """
        INSERT INTO tokens (access_token, refresh_token)
        VALUES (%s, %s)
        """,
        (access_token, refresh_token),
    )

    conn.commit()
    cursor.close()
    conn.close()
    print("Tokens stored successfully in the database.")


def update_env_file(access_token):
    """Updates the STRAVA_ACCESS_TOKEN in the .env file."""
    env_path = os.path.join(project_root, '.env')

    try:
        with open(env_path, 'r') as f:
            lines = f.readlines()
    except FileNotFoundError:
        lines = []

    token_found = False
    with open(env_path, 'w') as f:
        for line in lines:
            if line.strip().startswith("STRAVA_ACCESS_TOKEN="):
                f.write(f"STRAVA_ACCESS_TOKEN={access_token}\n")
                token_found = True
            else:
                f.write(line)
        if not token_found:
            f.write(f"STRAVA_ACCESS_TOKEN={access_token}\n")

    print(f"Updated STRAVA_ACCESS_TOKEN in {env_path}.")


if __name__ == "__main__":
    try:
        authorization_code = get_authorization_code()
        access_token, refresh_token = get_tokens(authorization_code)
        store_tokens_in_db(access_token, refresh_token)
        update_env_file(access_token)
        print("\nNew access token is ready. You can now run the database population script.")
    except requests.exceptions.HTTPError as e:
        print(f"An error occurred while communicating with Strava: {e.response.text}")
    except Exception as e:
        print(f"An unexpected error occurred: {e}")
