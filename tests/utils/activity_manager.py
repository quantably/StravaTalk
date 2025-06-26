import requests
import time
import os
from datetime import datetime, timezone
from typing import List, Dict, Optional

class SafeActivityManager:
    """Manages test activity creation and cleanup for webhook testing."""
    
    def __init__(self, access_token: str):
        self.access_token = access_token
        self.created_activities: List[int] = []
        self.base_url = "https://www.strava.com/api/v3"
        self.headers = {"Authorization": f"Bearer {access_token}"}
        self.test_prefix = os.getenv("TEST_ACTIVITY_PREFIX", "[TEST-WEBHOOK]")
    
    def create_test_activity(self, 
                           name_suffix: str = "",
                           sport_type: str = "Run",
                           duration_seconds: int = 1) -> Optional[int]:
        """
        Create a minimal test activity that's easy to identify and clean up.
        
        Args:
            name_suffix: Additional text for activity name
            sport_type: Type of activity (Run, Ride, etc.)
            duration_seconds: Duration in seconds (default: 1 second)
            
        Returns:
            Activity ID if successful, None if failed
        """
        timestamp = datetime.now().strftime("%Y%m%d-%H%M%S")
        activity_name = f"{self.test_prefix} {timestamp} - Auto-Delete {name_suffix}".strip()
        
        # Create minimal activity data
        activity_data = {
            "name": activity_name,
            "sport_type": sport_type,
            "start_date_local": datetime.now(timezone.utc).isoformat(),
            "elapsed_time": duration_seconds,
            "description": "Automated test activity - will be deleted",
            "trainer": 1,  # Mark as indoor/trainer activity
            "private": 1   # Keep private
        }
        
        try:
            response = requests.post(
                f"{self.base_url}/activities",
                headers=self.headers,
                json=activity_data
            )
            
            if response.status_code == 201:
                activity = response.json()
                activity_id = activity["id"]
                self.created_activities.append(activity_id)
                print(f"Created test activity: {activity_name} (ID: {activity_id})")
                return activity_id
            else:
                print(f"Failed to create activity: {response.status_code} - {response.text}")
                return None
                
        except Exception as e:
            print(f"Error creating test activity: {e}")
            return None
    
    def update_test_activity(self, activity_id: int, new_name: str = None, new_type: str = None) -> bool:
        """
        Update a test activity's name or type.
        
        Args:
            activity_id: ID of activity to update
            new_name: New activity name (optional)
            new_type: New activity type (optional)
            
        Returns:
            True if successful, False otherwise
        """
        update_data = {}
        
        if new_name:
            update_data["name"] = new_name
        
        if new_type:
            update_data["sport_type"] = new_type
        
        if not update_data:
            return True  # Nothing to update
        
        try:
            response = requests.put(
                f"{self.base_url}/activities/{activity_id}",
                headers=self.headers,
                json=update_data
            )
            
            if response.status_code == 200:
                print(f"Updated activity {activity_id}: {update_data}")
                return True
            else:
                print(f"Failed to update activity {activity_id}: {response.status_code} - {response.text}")
                return False
                
        except Exception as e:
            print(f"Error updating activity {activity_id}: {e}")
            return False
    
    def delete_activity(self, activity_id: int) -> bool:
        """
        Delete a specific activity.
        
        Args:
            activity_id: ID of activity to delete
            
        Returns:
            True if successful, False otherwise
        """
        try:
            response = requests.delete(
                f"{self.base_url}/activities/{activity_id}",
                headers=self.headers
            )
            
            if response.status_code == 204:
                print(f"Deleted activity {activity_id}")
                if activity_id in self.created_activities:
                    self.created_activities.remove(activity_id)
                return True
            else:
                print(f"Failed to delete activity {activity_id}: {response.status_code} - {response.text}")
                return False
                
        except Exception as e:
            print(f"Error deleting activity {activity_id}: {e}")
            return False
    
    def cleanup_all_created_activities(self) -> Dict[str, int]:
        """
        Clean up all activities created during testing.
        
        Returns:
            Dictionary with cleanup statistics
        """
        stats = {"deleted": 0, "failed": 0, "total": len(self.created_activities)}
        
        for activity_id in self.created_activities.copy():
            if self.delete_activity(activity_id):
                stats["deleted"] += 1
            else:
                stats["failed"] += 1
        
        return stats
    
    def cleanup_orphaned_test_activities(self) -> Dict[str, int]:
        """
        Find and clean up any orphaned test activities from previous runs.
        
        Returns:
            Dictionary with cleanup statistics
        """
        stats = {"found": 0, "deleted": 0, "failed": 0}
        
        try:
            # Get recent activities
            response = requests.get(
                f"{self.base_url}/athlete/activities",
                headers=self.headers,
                params={"per_page": 50}  # Check last 50 activities
            )
            
            if response.status_code != 200:
                print(f"Failed to fetch activities for cleanup: {response.status_code}")
                return stats
            
            activities = response.json()
            
            # Find test activities
            test_activities = [
                activity for activity in activities 
                if activity["name"].startswith(self.test_prefix)
            ]
            
            stats["found"] = len(test_activities)
            
            # Delete test activities
            for activity in test_activities:
                activity_id = activity["id"]
                if self.delete_activity(activity_id):
                    stats["deleted"] += 1
                else:
                    stats["failed"] += 1
            
            return stats
            
        except Exception as e:
            print(f"Error during orphaned activity cleanup: {e}")
            return stats
    
    def wait_for_webhook_processing(self, timeout_seconds: int = 10) -> None:
        """
        Wait for webhook processing to complete.
        
        Args:
            timeout_seconds: Maximum time to wait
        """
        print(f"Waiting {timeout_seconds} seconds for webhook processing...")
        time.sleep(timeout_seconds)
    
    def __enter__(self):
        """Context manager entry."""
        return self
    
    def __exit__(self, exc_type, exc_val, exc_tb):
        """Context manager exit - ensures cleanup."""
        print("Cleaning up test activities...")
        stats = self.cleanup_all_created_activities()
        print(f"Cleanup complete: {stats}")
        
        if stats["failed"] > 0:
            print(f"Warning: {stats['failed']} activities failed to delete")
        
        return False  # Don't suppress exceptions