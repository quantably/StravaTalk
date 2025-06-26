import sqlite3
import os
from datetime import datetime

class TestDatabaseManager:
    """Utility class for managing test database operations."""
    
    def __init__(self, db_path="test_strava.db"):
        self.db_path = db_path
    
    def get_connection(self):
        """Get database connection."""
        return sqlite3.connect(self.db_path)
    
    def insert_test_token(self, access_token="test_token", refresh_token="test_refresh"):
        """Insert a test token for webhook processing."""
        conn = self.get_connection()
        cursor = conn.cursor()
        
        cursor.execute(
            "INSERT INTO tokens (access_token, refresh_token) VALUES (?, ?)",
            (access_token, refresh_token)
        )
        
        conn.commit()
        token_id = cursor.lastrowid
        conn.close()
        return token_id
    
    def get_activity_by_id(self, activity_id):
        """Retrieve activity by ID."""
        conn = self.get_connection()
        cursor = conn.cursor()
        
        cursor.execute("SELECT * FROM activities WHERE id = ?", (activity_id,))
        result = cursor.fetchone()
        
        conn.close()
        
        if result:
            return {
                'id': result[0],
                'name': result[1],
                'distance': result[2],
                'moving_time': result[3],
                'elapsed_time': result[4],
                'total_elevation_gain': result[5],
                'type': result[6],
                'start_date': result[7]
            }
        return None
    
    def activity_exists(self, activity_id):
        """Check if activity exists in database."""
        return self.get_activity_by_id(activity_id) is not None
    
    def get_all_activities(self):
        """Get all activities from database."""
        conn = self.get_connection()
        cursor = conn.cursor()
        
        cursor.execute("SELECT * FROM activities")
        results = cursor.fetchall()
        
        conn.close()
        
        activities = []
        for result in results:
            activities.append({
                'id': result[0],
                'name': result[1],
                'distance': result[2],
                'moving_time': result[3],
                'elapsed_time': result[4],
                'total_elevation_gain': result[5],
                'type': result[6],
                'start_date': result[7]
            })
        
        return activities
    
    def count_activities(self):
        """Count total activities in database."""
        conn = self.get_connection()
        cursor = conn.cursor()
        
        cursor.execute("SELECT COUNT(*) FROM activities")
        count = cursor.fetchone()[0]
        
        conn.close()
        return count
    
    def clear_all_activities(self):
        """Clear all activities from test database."""
        conn = self.get_connection()
        cursor = conn.cursor()
        
        cursor.execute("DELETE FROM activities")
        conn.commit()
        
        conn.close()
    
    def verify_activity_update(self, activity_id, expected_name=None, expected_type=None):
        """Verify activity was updated with expected values."""
        activity = self.get_activity_by_id(activity_id)
        if not activity:
            return False
        
        if expected_name and activity['name'] != expected_name:
            return False
            
        if expected_type and activity['type'] != expected_type:
            return False
            
        return True