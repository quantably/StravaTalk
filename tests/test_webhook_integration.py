import pytest
import asyncio
import os
from datetime import datetime

from tests.utils.activity_manager import SafeActivityManager
from tests.utils.db_test_utils import TestDatabaseManager


class TestWebhookIntegration:
    """Integration tests for Strava webhook processing."""
    
    @pytest.fixture(autouse=True)
    def setup(self, test_db, strava_credentials):
        """Set up test environment for each test."""
        self.db_manager = TestDatabaseManager(test_db)
        self.access_token = strava_credentials['access_token']
        
        # Skip tests if no access token provided
        if not self.access_token:
            pytest.skip("STRAVA_ACCESS_TOKEN not provided in test environment")
        
        # Insert test token for webhook processing
        self.db_manager.insert_test_token(self.access_token)
        
        # Pre-test cleanup of any orphaned activities
        with SafeActivityManager(self.access_token) as activity_manager:
            orphan_stats = activity_manager.cleanup_orphaned_test_activities()
            if orphan_stats["found"] > 0:
                print(f"Cleaned up {orphan_stats['deleted']} orphaned test activities")
    
    @pytest.mark.asyncio
    async def test_webhook_create_activity(self, test_db, strava_credentials):
        """Test webhook processing for activity creation."""
        with SafeActivityManager(self.access_token) as activity_manager:
            # Create test activity
            activity_id = activity_manager.create_test_activity(
                name_suffix="Create Test",
                sport_type="Run"
            )
            
            assert activity_id is not None, "Failed to create test activity"
            
            # Wait for webhook processing
            activity_manager.wait_for_webhook_processing(timeout_seconds=15)
            
            # Verify activity was stored in database via webhook
            assert self.db_manager.activity_exists(activity_id), \
                f"Activity {activity_id} not found in database after webhook processing"
            
            # Verify activity details
            stored_activity = self.db_manager.get_activity_by_id(activity_id)
            assert stored_activity is not None
            assert "[TEST-WEBHOOK]" in stored_activity['name']
            assert stored_activity['type'] == "Run"
            
            print(f"✅ Create webhook test passed for activity {activity_id}")
    
    @pytest.mark.asyncio
    async def test_webhook_update_activity(self, test_db, strava_credentials):
        """Test webhook processing for activity updates."""
        with SafeActivityManager(self.access_token) as activity_manager:
            # Create test activity
            activity_id = activity_manager.create_test_activity(
                name_suffix="Update Test",
                sport_type="Run"
            )
            
            assert activity_id is not None, "Failed to create test activity"
            
            # Wait for initial webhook processing
            activity_manager.wait_for_webhook_processing(timeout_seconds=10)
            
            # Verify initial creation
            assert self.db_manager.activity_exists(activity_id)
            
            # Update activity name
            updated_name = f"[TEST-WEBHOOK] Updated - {datetime.now().strftime('%H%M%S')}"
            success = activity_manager.update_test_activity(
                activity_id=activity_id,
                new_name=updated_name
            )
            
            assert success, "Failed to update test activity"
            
            # Wait for update webhook processing
            activity_manager.wait_for_webhook_processing(timeout_seconds=10)
            
            # Verify update was processed
            assert self.db_manager.verify_activity_update(
                activity_id=activity_id,
                expected_name=updated_name
            ), "Activity update not reflected in database"
            
            print(f"✅ Update webhook test passed for activity {activity_id}")
    
    @pytest.mark.asyncio
    async def test_webhook_delete_activity(self, test_db, strava_credentials):
        """Test webhook processing for activity deletion."""
        with SafeActivityManager(self.access_token) as activity_manager:
            # Create test activity
            activity_id = activity_manager.create_test_activity(
                name_suffix="Delete Test",
                sport_type="Run"
            )
            
            assert activity_id is not None, "Failed to create test activity"
            
            # Wait for initial webhook processing
            activity_manager.wait_for_webhook_processing(timeout_seconds=10)
            
            # Verify initial creation
            assert self.db_manager.activity_exists(activity_id)
            initial_count = self.db_manager.count_activities()
            
            # Delete activity (this will trigger delete webhook)
            success = activity_manager.delete_activity(activity_id)
            assert success, "Failed to delete test activity"
            
            # Wait for delete webhook processing
            activity_manager.wait_for_webhook_processing(timeout_seconds=10)
            
            # Verify deletion was processed
            assert not self.db_manager.activity_exists(activity_id), \
                f"Activity {activity_id} still exists in database after delete webhook"
            
            final_count = self.db_manager.count_activities()
            assert final_count == initial_count - 1, \
                "Activity count did not decrease after delete webhook"
            
            print(f"✅ Delete webhook test passed for activity {activity_id}")
    
    @pytest.mark.asyncio
    async def test_webhook_multiple_activities(self, test_db, strava_credentials):
        """Test webhook processing for multiple activities."""
        with SafeActivityManager(self.access_token) as activity_manager:
            initial_count = self.db_manager.count_activities()
            created_ids = []
            
            # Create multiple test activities
            for i in range(3):
                activity_id = activity_manager.create_test_activity(
                    name_suffix=f"Multi Test {i+1}",
                    sport_type="Run" if i % 2 == 0 else "Ride"
                )
                assert activity_id is not None
                created_ids.append(activity_id)
            
            # Wait for all webhook processing
            activity_manager.wait_for_webhook_processing(timeout_seconds=20)
            
            # Verify all activities were stored
            final_count = self.db_manager.count_activities()
            assert final_count == initial_count + 3, \
                f"Expected {initial_count + 3} activities, found {final_count}"
            
            # Verify each activity exists
            for activity_id in created_ids:
                assert self.db_manager.activity_exists(activity_id), \
                    f"Activity {activity_id} not found in database"
            
            print(f"✅ Multiple webhook test passed for activities {created_ids}")
    
    @pytest.mark.asyncio
    async def test_webhook_error_handling(self, test_db, strava_credentials):
        """Test webhook error handling and recovery."""
        with SafeActivityManager(self.access_token) as activity_manager:
            # Create activity with normal flow
            activity_id = activity_manager.create_test_activity(
                name_suffix="Error Test",
                sport_type="Run"
            )
            
            assert activity_id is not None
            
            # Wait for processing
            activity_manager.wait_for_webhook_processing(timeout_seconds=10)
            
            # Verify normal processing worked
            assert self.db_manager.activity_exists(activity_id)
            
            # Test that invalid activity ID doesn't break system
            invalid_id = 999999999
            assert not self.db_manager.activity_exists(invalid_id)
            
            print(f"✅ Error handling test passed")
    
    def test_cleanup_safety(self, strava_credentials):
        """Test that cleanup mechanisms work properly."""
        with SafeActivityManager(self.access_token) as activity_manager:
            # Create an activity
            activity_id = activity_manager.create_test_activity(
                name_suffix="Cleanup Test"
            )
            
            assert activity_id is not None
            assert activity_id in activity_manager.created_activities
            
            # Manual cleanup test
            success = activity_manager.delete_activity(activity_id)
            assert success
            assert activity_id not in activity_manager.created_activities
            
            print("✅ Cleanup safety test passed")
    
    def test_orphaned_activity_cleanup(self, strava_credentials):
        """Test cleanup of orphaned test activities."""
        with SafeActivityManager(self.access_token) as activity_manager:
            # Check for orphaned activities
            stats = activity_manager.cleanup_orphaned_test_activities()
            
            # Should be able to run without errors
            assert isinstance(stats, dict)
            assert "found" in stats
            assert "deleted" in stats
            assert "failed" in stats
            
            print(f"✅ Orphaned cleanup test passed: {stats}")


if __name__ == "__main__":
    # Run tests with verbose output
    pytest.main([__file__, "-v", "-s"])