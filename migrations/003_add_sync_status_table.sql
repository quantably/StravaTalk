-- Migration: Add user sync status tracking table
-- This tracks whether users have synced their historical Strava activities

CREATE TABLE IF NOT EXISTS user_sync_status (
    user_id INTEGER PRIMARY KEY REFERENCES users(id) ON DELETE CASCADE,
    sync_started TIMESTAMP,
    sync_completed BOOLEAN DEFAULT FALSE,
    last_sync_date TIMESTAMP,
    total_activities_synced INTEGER DEFAULT 0,
    created_at TIMESTAMP DEFAULT NOW(),
    updated_at TIMESTAMP DEFAULT NOW()
);

-- Create index for faster lookups
CREATE INDEX IF NOT EXISTS idx_user_sync_status_user_id ON user_sync_status(user_id);
CREATE INDEX IF NOT EXISTS idx_user_sync_status_completed ON user_sync_status(sync_completed);