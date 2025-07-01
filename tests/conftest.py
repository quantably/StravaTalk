import pytest
import os
import asyncio
from dotenv import load_dotenv

# Load test environment
load_dotenv('.env.test')

@pytest.fixture(scope="session")
def event_loop():
    """Create an instance of the default event loop for the test session."""
    loop = asyncio.get_event_loop_policy().new_event_loop()
    yield loop
    loop.close()

# Note: PostgreSQL test database setup should be handled externally
# or through a proper test database configuration

@pytest.fixture
def strava_credentials():
    """Provide Strava API credentials for testing."""
    return {
        'access_token': os.getenv('STRAVA_ACCESS_TOKEN'),
        'client_id': os.getenv('CLIENT_ID'),
        'client_secret': os.getenv('CLIENT_SECRET')
    }

@pytest.fixture
def activity_registry():
    """Track created activities for cleanup."""
    created_activities = []
    yield created_activities
    # Cleanup is handled by the activity_manager fixture