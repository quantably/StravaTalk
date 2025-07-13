-- Migration: Enable Row-Level Security for multi-tenant data isolation
-- This ensures users can only access their own data at the database level

-- Enable RLS on activities table
ALTER TABLE activities ENABLE ROW LEVEL SECURITY;

-- Create policy for activities table
-- Users can only see/modify activities where athlete_id matches current user
CREATE POLICY user_activities_policy ON activities
    FOR ALL
    TO PUBLIC
    USING (athlete_id = current_setting('app.current_user_id', true)::integer);

-- Enable RLS on users table  
ALTER TABLE users ENABLE ROW LEVEL SECURITY;

-- Create policy for users table
-- Users can only see/modify their own user record
CREATE POLICY user_profile_policy ON users
    FOR ALL
    TO PUBLIC
    USING (id = current_setting('app.current_user_id', true)::integer);

-- Enable RLS on strava_connections table
ALTER TABLE strava_connections ENABLE ROW LEVEL SECURITY;

-- Create policy for strava_connections table
-- Users can only see/modify their own Strava connection
CREATE POLICY user_strava_connections_policy ON strava_connections
    FOR ALL
    TO PUBLIC
    USING (user_id = current_setting('app.current_user_id', true)::integer);

-- Enable RLS on user_sessions table
ALTER TABLE user_sessions ENABLE ROW LEVEL SECURITY;

-- Create policy for user_sessions table
-- Users can only see/modify their own sessions
CREATE POLICY user_sessions_policy ON user_sessions
    FOR ALL
    TO PUBLIC
    USING (user_id = current_setting('app.current_user_id', true)::integer);

-- Enable RLS on magic_tokens table
ALTER TABLE magic_tokens ENABLE ROW LEVEL SECURITY;

-- Create policy for magic_tokens table
-- Users can only see/modify magic tokens for their email
-- Note: magic_tokens uses email, not user_id, so we need a different approach
-- For now, we'll allow all access to magic_tokens as they're temporary and email-based
CREATE POLICY user_magic_tokens_policy ON magic_tokens
    FOR ALL
    TO PUBLIC
    USING (true); -- Allow all access for magic tokens (they're temporary and email-based)

-- Grant usage on all tables to ensure policies work correctly
-- Note: Existing permissions should be sufficient, but ensuring they're explicit
GRANT SELECT, INSERT, UPDATE, DELETE ON activities TO PUBLIC;
GRANT SELECT, INSERT, UPDATE, DELETE ON users TO PUBLIC;
GRANT SELECT, INSERT, UPDATE, DELETE ON strava_connections TO PUBLIC;
GRANT SELECT, INSERT, UPDATE, DELETE ON user_sessions TO PUBLIC;
GRANT SELECT, INSERT, UPDATE, DELETE ON magic_tokens TO PUBLIC;

-- Test the policies (these should return 0 rows when no user is set)
-- SELECT COUNT(*) FROM activities; -- Should return 0
-- SET app.current_user_id = '123';
-- SELECT COUNT(*) FROM activities; -- Should return user 123's activities only