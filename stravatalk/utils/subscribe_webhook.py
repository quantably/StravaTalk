import requests
import os
from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv()

CLIENT_ID = os.getenv("CLIENT_ID")
CLIENT_SECRET = os.getenv("CLIENT_SECRET")
STRAVA_WEBHOOK_VERIFY_TOKEN = os.getenv("STRAVA_WEBHOOK_VERIFY_TOKEN")

# Replace with your public URL (e.g., ngrok URL)
CALLBACK_URL = (
    "https://828b-2a0a-ef40-9bc-3601-75dd-37be-6c0b-162f.ngrok-free.app/webhook"
)
SUBSCRIPTION_URL = "https://www.strava.com/api/v3/push_subscriptions"


def subscribe_to_webhook():
    if (
        not CLIENT_ID
        or not CLIENT_SECRET
        or not STRAVA_WEBHOOK_VERIFY_TOKEN
        or CALLBACK_URL == "YOUR_PUBLIC_URL_HERE"
    ):
        print(
            "Please ensure CLIENT_ID, CLIENT_SECRET, STRAVA_WEBHOOK_VERIFY_TOKEN are set in your .env file and CALLBACK_URL is updated in this script."
        )
        return

    data = {
        "client_id": CLIENT_ID,
        "client_secret": CLIENT_SECRET,
        "callback_url": CALLBACK_URL,
        "verify_token": STRAVA_WEBHOOK_VERIFY_TOKEN,
    }

    response = requests.post(SUBSCRIPTION_URL, json=data)

    if response.status_code == 201:
        print("Webhook subscription successful!")
        print(response.json())
    else:
        print("Webhook subscription failed.")
        print(f"Status Code: {response.status_code}")
        print(f"Response: {response.json()}")


if __name__ == "__main__":
    subscribe_to_webhook()
