#!/usr/bin/env python3
"""
Test script to verify user data segregation is working correctly.
"""

import os
from dotenv import load_dotenv
from stravatalk.utils.db_utils import get_user_activities, get_user_activity_count, execute_user_query, get_user_from_token

load_dotenv()

def test_user_segregation():
    """Test that user data segregation is working."""
    print("🧪 Testing User Data Segregation")
    print("=" * 50)
    
    # Test 1: Get current user from tokens
    print("📍 Test 1: Get current user from tokens")
    current_user = get_user_from_token()
    if current_user:
        print(f"✅ Found current user: {current_user}")
    else:
        print("❌ No user found - run OAuth flow first")
        return
    
    # Test 2: Get user's activity count
    print(f"\n📊 Test 2: Get activities for user {current_user}")
    activity_count = get_user_activity_count(current_user)
    print(f"✅ User has {activity_count} activities")
    
    # Test 3: Get recent activities
    print(f"\n📝 Test 3: Get recent activities for user {current_user}")
    recent_activities = get_user_activities(current_user, limit=5)
    if recent_activities:
        print(f"✅ Retrieved {len(recent_activities)} recent activities:")
        for activity in recent_activities:
            print(f"   - {activity['name']} (ID: {activity['id']}, Athlete: {activity['athlete_id']})")
    else:
        print("⚠️  No activities found for this user")
    
    # Test 4: Test user-scoped query
    print(f"\n🔍 Test 4: Test user-scoped query")
    query_result = execute_user_query(
        "SELECT COUNT(*) as total_runs FROM activities WHERE type = 'Run'", 
        current_user
    )
    
    if query_result["success"]:
        total_runs = query_result["rows"][0]["total_runs"]
        print(f"✅ User {current_user} has {total_runs} runs")
    else:
        print(f"❌ Query failed: {query_result['error_message']}")
    
    # Test 5: Test that user filtering is applied
    print(f"\n🔐 Test 5: Verify user filtering is applied")
    
    # This should only return activities for current_user
    all_activities_query = execute_user_query(
        "SELECT athlete_id, COUNT(*) as count FROM activities GROUP BY athlete_id",
        current_user
    )
    
    if all_activities_query["success"]:
        athlete_counts = all_activities_query["rows"]
        print(f"✅ Query returned data for {len(athlete_counts)} athlete(s):")
        for row in athlete_counts:
            athlete_id = row["athlete_id"]
            count = row["count"]
            is_current_user = "👤 (current user)" if athlete_id == current_user else "❌ (OTHER USER - THIS IS A PROBLEM!)"
            print(f"   Athlete {athlete_id}: {count} activities {is_current_user}")
            
            if athlete_id != current_user:
                print(f"🚨 WARNING: Data leakage detected! Query returned data for athlete {athlete_id}")
                return False
    else:
        print(f"❌ Query failed: {all_activities_query['error_message']}")
        return False
    
    print(f"\n🎉 User data segregation test PASSED!")
    print(f"✅ All queries properly filtered to user {current_user}")
    return True

def test_multi_user_scenario():
    """Test multi-user scenario if multiple users exist."""
    print("\n👥 Testing Multi-User Scenario")
    print("=" * 30)
    
    from stravatalk.utils.db_utils import get_db_connection
    import psycopg2.extras
    
    conn = get_db_connection()
    if not conn:
        print("❌ Database connection failed")
        return
    
    cursor = conn.cursor(cursor_factory=psycopg2.extras.DictCursor)
    
    try:
        # Get all users
        cursor.execute("SELECT athlete_id FROM user_tokens ORDER BY athlete_id")
        users = [row[0] for row in cursor.fetchall()]
        
        print(f"📊 Found {len(users)} users: {users}")
        
        if len(users) < 2:
            print("⚠️  Only one user found - create another OAuth connection to test multi-user")
            return
        
        # Test each user's data isolation
        for user_id in users:
            user_count = get_user_activity_count(user_id)
            print(f"   User {user_id}: {user_count} activities")
            
            # Test cross-user query isolation
            other_users = [u for u in users if u != user_id]
            for other_user in other_users:
                cross_query = execute_user_query(
                    f"SELECT COUNT(*) as count FROM activities WHERE athlete_id = {other_user}",
                    user_id  # This should filter to user_id, so should return 0
                )
                
                if cross_query["success"]:
                    cross_count = cross_query["rows"][0]["count"]
                    if cross_count > 0:
                        print(f"🚨 Data leakage: User {user_id} can see {cross_count} activities from user {other_user}")
                        return False
                    else:
                        print(f"✅ User {user_id} correctly cannot see user {other_user}'s activities")
        
        print("🎉 Multi-user segregation test PASSED!")
        
    except Exception as e:
        print(f"❌ Multi-user test failed: {e}")
        return False
    finally:
        cursor.close()
        conn.close()
    
    return True

if __name__ == "__main__":
    success = test_user_segregation()
    if success:
        test_multi_user_scenario()
    else:
        print("\n💥 User segregation test FAILED - fix issues before proceeding")