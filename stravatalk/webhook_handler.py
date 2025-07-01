from fastapi import FastAPI, Request, HTTPException
import os
from dotenv import load_dotenv

load_dotenv()

app = FastAPI()

STRAVA_WEBHOOK_VERIFY_TOKEN = os.getenv("STRAVA_WEBHOOK_VERIFY_TOKEN")

@app.get("/webhook")
async def verify_webhook(request: Request):
    # Strava sends parameters with dots, access them from query params
    hub_mode = request.query_params.get("hub.mode")
    hub_challenge = request.query_params.get("hub.challenge")
    hub_verify_token = request.query_params.get("hub.verify_token")
    
    if hub_mode == "subscribe" and hub_verify_token == STRAVA_WEBHOOK_VERIFY_TOKEN:
        return {"hub.challenge": hub_challenge}
    raise HTTPException(status_code=403, detail="Verification failed")

@app.post("/webhook")
async def handle_webhook_event(request: Request):
    event_data = await request.json()
    print(f"Received webhook event: {event_data}")
    
    try:
        await process_webhook_event(event_data)
        return {"message": "Event processed successfully"}
    except Exception as e:
        print(f"Error processing webhook event: {e}")
        import traceback
        traceback.print_exc()
        raise HTTPException(status_code=500, detail="Event received but processing failed")

async def process_webhook_event(event_data):
    """Process incoming Strava webhook events"""
    object_type = event_data.get("object_type")
    aspect_type = event_data.get("aspect_type")
    object_id = event_data.get("object_id")
    owner_id = event_data.get("owner_id")
    updates = event_data.get("updates", {})
    
    if object_type == "activity":
        if aspect_type == "create":
            await handle_activity_create(object_id, owner_id)
        elif aspect_type == "update":
            await handle_activity_update(object_id, owner_id, updates)
        elif aspect_type == "delete":
            await handle_activity_delete(object_id, owner_id)
    elif object_type == "athlete":
        if aspect_type == "update" and updates.get("authorized") == "false":
            await handle_athlete_deauthorize(owner_id)
    
    print(f"Processed {aspect_type} event for {object_type} {object_id}")

async def handle_activity_create(activity_id, owner_id):
    """Handle new activity creation by fetching and storing activity data"""
    from .utils.db_utils import get_db_connection
    import requests
    
    # Get access token for this user (we'll need OAuth implementation later)
    access_token = await get_user_access_token(owner_id)
    if not access_token:
        print(f"No access token found for user {owner_id}")
        return
    
    # Fetch activity details from Strava API
    headers = {"Authorization": f"Bearer {access_token}"}
    response = requests.get(f"https://www.strava.com/api/v3/activities/{activity_id}", headers=headers)
    
    if response.status_code != 200:
        print(f"Failed to fetch activity {activity_id}: {response.status_code}")
        return
    
    activity = response.json()
    
    # Store activity in database with athlete_id
    conn = get_db_connection()
    cursor = conn.cursor()
    
    cursor.execute(
        """
        INSERT INTO activities (id, athlete_id, name, distance, moving_time, elapsed_time, total_elevation_gain, type, start_date)
        VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s)
        ON CONFLICT (id) DO UPDATE SET
            athlete_id = EXCLUDED.athlete_id,
            name = EXCLUDED.name,
            distance = EXCLUDED.distance,
            moving_time = EXCLUDED.moving_time,
            elapsed_time = EXCLUDED.elapsed_time,
            total_elevation_gain = EXCLUDED.total_elevation_gain,
            type = EXCLUDED.type,
            start_date = EXCLUDED.start_date;
        """,
        (
            activity["id"],
            owner_id,  # Store the athlete_id from webhook
            activity["name"],
            activity["distance"],
            activity["moving_time"],
            activity["elapsed_time"],
            activity["total_elevation_gain"],
            activity["type"],
            activity["start_date"],
        ),
    )
    
    conn.commit()
    cursor.close()
    conn.close()
    print(f"Stored new activity: {activity['name']} ({activity_id})")

async def handle_activity_update(activity_id, owner_id, updates):
    """Handle activity updates (name, type, privacy changes)"""
    from .utils.db_utils import get_db_connection
    
    if not updates:
        return
    
    conn = get_db_connection()
    cursor = conn.cursor()
    
    # Build dynamic UPDATE query based on what changed
    update_fields = []
    update_values = []
    
    if "title" in updates:
        update_fields.append("name = %s")
        update_values.append(updates["title"])
    
    if "type" in updates:
        update_fields.append("type = %s")
        update_values.append(updates["type"])
    
    if update_fields:
        update_values.extend([activity_id, owner_id])  # For WHERE clause
        query = f"UPDATE activities SET {', '.join(update_fields)} WHERE id = %s AND athlete_id = %s"
        cursor.execute(query, update_values)
        conn.commit()
        print(f"Updated activity {activity_id} for athlete {owner_id}: {updates}")
    
    cursor.close()
    conn.close()

async def handle_activity_delete(activity_id, owner_id):
    """Handle activity deletion"""
    from .utils.db_utils import get_db_connection
    
    conn = get_db_connection()
        
    cursor = conn.cursor()
    cursor.execute("DELETE FROM activities WHERE id = %s AND athlete_id = %s", (activity_id, owner_id))
    
    conn.commit()
    cursor.close()
    conn.close()
    print(f"Deleted activity {activity_id} for athlete {owner_id}")

async def handle_athlete_deauthorize(owner_id):
    """Handle athlete deauthorization by removing their tokens"""
    from .utils.db_utils import get_db_connection
    
    conn = get_db_connection()
    cursor = conn.cursor()
    
    # Remove user's tokens (we'll need to add athlete_id to tokens table later)
    cursor.execute("DELETE FROM tokens WHERE id = %s", (owner_id,))
    conn.commit()
    
    cursor.close()
    conn.close()
    print(f"Removed tokens for deauthorized athlete {owner_id}")

async def get_user_access_token(owner_id):
    """Get access token for a specific user by athlete_id, with automatic refresh"""
    from .utils.db_utils import get_valid_access_token
    
    return get_valid_access_token(owner_id)

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
