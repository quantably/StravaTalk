import pytest
import os
import sqlite3
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

@pytest.fixture(scope="function")
def test_db():
    """Create a fresh test database for each test function."""
    db_path = "test_strava.db"
    
    # Remove existing test DB
    if os.path.exists(db_path):
        os.remove(db_path)
    
    # Create fresh test database with schema
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
    
    # Create activities table
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS activities (
            id BIGINT PRIMARY KEY,
            name TEXT,
            distance REAL,
            moving_time INTEGER,
            elapsed_time INTEGER,
            total_elevation_gain REAL,
            type TEXT,
            start_date TEXT
        );
    """)
    
    # Create tokens table
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS tokens (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            access_token TEXT NOT NULL,
            refresh_token TEXT NOT NULL,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        );
    """)
    
    conn.commit()
    conn.close()
    
    yield db_path
    
    # Cleanup after test
    if os.path.exists(db_path):
        os.remove(db_path)

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