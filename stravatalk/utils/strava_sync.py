"""
Strava historical activities sync service.
"""

import os
import requests
import time
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Callable
from .db_utils import get_db_connection
from .auth_utils import get_user_strava_connection
import psycopg2.extras

class StravaSyncService:
    """Service for syncing historical Strava activities."""
    
    def __init__(self):
        self.base_url = "https://www.strava.com/api/v3"
        
    def check_sync_status(self, user_id: int) -> Dict:
        """Check if user has synced activities and their sync status."""
        conn = get_db_connection()
        if not conn:
            return {"synced": False, "activity_count": 0, "error": "Database connection failed"}
            
        try:
            cursor = conn.cursor(cursor_factory=psycopg2.extras.DictCursor)
            
            # Count current activities for this user's athlete
            strava_connection = get_user_strava_connection(user_id)
            if not strava_connection:
                return {"synced": False, "activity_count": 0, "error": "No Strava connection"}
                
            athlete_id = strava_connection["athlete_id"]
            cursor.execute("SELECT COUNT(*) as count FROM activities WHERE athlete_id = %s", (athlete_id,))
            activity_count = cursor.fetchone()["count"]
            
            # Check if sync status table exists
            cursor.execute("""
                SELECT EXISTS (
                    SELECT FROM information_schema.tables 
                    WHERE table_schema = 'public' 
                    AND table_name = 'user_sync_status'
                );
            """)
            
            table_exists = cursor.fetchone()[0]
            
            if not table_exists:
                # Table doesn't exist, assume sync needed if few activities
                return {
                    "synced": activity_count > 50,  # Assume synced if many activities
                    "activity_count": activity_count,
                    "needs_sync": activity_count <= 50
                }
            
            # Check if user has a sync record
            cursor.execute("""
                SELECT last_sync_date, total_activities_synced, sync_completed 
                FROM user_sync_status 
                WHERE user_id = %s
            """, (user_id,))
            
            sync_record = cursor.fetchone()
            
            if sync_record and sync_record["sync_completed"]:
                return {
                    "synced": True,
                    "activity_count": activity_count,
                    "last_sync": sync_record["last_sync_date"],
                    "total_synced": sync_record["total_activities_synced"]
                }
            else:
                return {
                    "synced": False,
                    "activity_count": activity_count,
                    "needs_sync": True
                }
                
        except Exception as e:
            return {"synced": False, "activity_count": 0, "error": str(e)}
        finally:
            cursor.close()
            conn.close()
    
    def sync_historical_activities(self, user_id: int, progress_callback: Optional[Callable] = None) -> Dict:
        """Sync historical activities from Strava with progress updates."""
        
        # Get user's Strava connection
        strava_connection = get_user_strava_connection(user_id)
        if not strava_connection:
            return {"success": False, "error": "No Strava connection found"}
            
        access_token = strava_connection["access_token"]
        athlete_id = strava_connection["athlete_id"]
        
        try:
            # Initialize sync status
            self._init_sync_status(user_id)
            
            activities_synced = 0
            page = 1
            per_page = 30  # Strava API limit
            
            if progress_callback:
                progress_callback(0, "Starting sync...")
                
            while True:
                # Fetch activities page
                activities = self._fetch_activities_page(access_token, page, per_page)
                
                if not activities:
                    break  # No more activities
                    
                # Process this batch
                for activity in activities:
                    success = self._store_activity(activity, athlete_id)
                    if success:
                        activities_synced += 1
                        
                if progress_callback:
                    progress_callback(
                        activities_synced, 
                        f"Synced {activities_synced} activities..."
                    )
                
                # Respect Strava API rate limits (100 requests per 15 minutes)
                time.sleep(0.2)  # Small delay between requests
                
                if len(activities) < per_page:
                    break  # Last page
                    
                page += 1
                
            # Mark sync as completed
            self._complete_sync_status(user_id, activities_synced)
            
            if progress_callback:
                progress_callback(activities_synced, f"Sync completed! {activities_synced} activities synced.")
                
            return {
                "success": True, 
                "activities_synced": activities_synced,
                "message": f"Successfully synced {activities_synced} activities"
            }
            
        except Exception as e:
            return {"success": False, "error": str(e)}
    
    def _fetch_activities_page(self, access_token: str, page: int, per_page: int) -> List[Dict]:
        """Fetch a page of activities from Strava API."""
        headers = {"Authorization": f"Bearer {access_token}"}
        
        params = {
            "page": page,
            "per_page": per_page
        }
        
        response = requests.get(
            f"{self.base_url}/athlete/activities",
            headers=headers,
            params=params,
            timeout=30
        )
        
        if response.status_code == 200:
            return response.json()
        elif response.status_code == 401:
            raise Exception("Strava access token expired or invalid")
        else:
            raise Exception(f"Strava API error: {response.status_code}")
    
    def _store_activity(self, activity: Dict, athlete_id: int) -> bool:
        """Store a single activity in the database."""
        conn = get_db_connection()
        if not conn:
            return False
            
        try:
            cursor = conn.cursor()
            
            # Check if activity already exists
            cursor.execute("SELECT id FROM activities WHERE id = %s", (activity["id"],))
            if cursor.fetchone():
                return True  # Already exists, skip
                
            # Insert activity
            cursor.execute("""
                INSERT INTO activities (
                    id, name, distance, moving_time, elapsed_time, 
                    total_elevation_gain, type, start_date, athlete_id
                ) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s)
                ON CONFLICT (id) DO NOTHING
            """, (
                activity["id"],
                activity.get("name", ""),
                activity.get("distance", 0),
                activity.get("moving_time", 0),
                activity.get("elapsed_time", 0),
                activity.get("total_elevation_gain", 0),
                activity.get("type", ""),
                activity.get("start_date"),
                athlete_id
            ))
            
            conn.commit()
            return True
            
        except Exception as e:
            print(f"Error storing activity {activity.get('id', 'unknown')}: {e}")
            conn.rollback()
            return False
        finally:
            cursor.close()
            conn.close()
    
    def _init_sync_status(self, user_id: int):
        """Initialize sync status for user."""
        conn = get_db_connection()
        if not conn:
            return
            
        try:
            cursor = conn.cursor()
            
            # Check if table exists first
            cursor.execute("""
                SELECT EXISTS (
                    SELECT FROM information_schema.tables 
                    WHERE table_schema = 'public' 
                    AND table_name = 'user_sync_status'
                );
            """)
            
            if cursor.fetchone()[0]:
                cursor.execute("""
                    INSERT INTO user_sync_status (user_id, sync_started, sync_completed)
                    VALUES (%s, NOW(), false)
                    ON CONFLICT (user_id) 
                    DO UPDATE SET sync_started = NOW(), sync_completed = false
                """, (user_id,))
                conn.commit()
            else:
                print("user_sync_status table does not exist, skipping status tracking")
                
        except Exception as e:
            print(f"Error initializing sync status: {e}")
            conn.rollback()
        finally:
            cursor.close()
            conn.close()
    
    def _complete_sync_status(self, user_id: int, activities_count: int):
        """Mark sync as completed."""
        conn = get_db_connection()
        if not conn:
            return
            
        try:
            cursor = conn.cursor()
            
            # Check if table exists first
            cursor.execute("""
                SELECT EXISTS (
                    SELECT FROM information_schema.tables 
                    WHERE table_schema = 'public' 
                    AND table_name = 'user_sync_status'
                );
            """)
            
            if cursor.fetchone()[0]:
                cursor.execute("""
                    UPDATE user_sync_status 
                    SET sync_completed = true, 
                        last_sync_date = NOW(),
                        total_activities_synced = %s
                    WHERE user_id = %s
                """, (activities_count, user_id))
                conn.commit()
            else:
                print("user_sync_status table does not exist, skipping status tracking")
                
        except Exception as e:
            print(f"Error completing sync status: {e}")
            conn.rollback()
        finally:
            cursor.close()
            conn.close()