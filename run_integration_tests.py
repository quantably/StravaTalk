#!/usr/bin/env python3
"""
Integration test runner for Strava webhook functionality.

This script runs comprehensive integration tests that:
1. Create real activities via Strava API
2. Wait for webhooks to be delivered via ngrok
3. Verify database operations completed correctly
4. Clean up all test activities

Prerequisites:
- ngrok tunnel running and webhook handler active
- Valid Strava access token in .env.test
- Test environment configured

Usage:
    python run_integration_tests.py
"""

import os
import sys
import subprocess
from dotenv import load_dotenv

def check_prerequisites():
    """Check that all prerequisites are met."""
    print("🔍 Checking prerequisites...")
    
    # Load test environment
    if not os.path.exists('.env.test'):
        print("❌ .env.test file not found. Please create it with test configuration.")
        return False
    
    load_dotenv('.env.test')
    
    # Check for required environment variables
    required_vars = ['STRAVA_ACCESS_TOKEN', 'CLIENT_ID', 'CLIENT_SECRET']
    missing_vars = []
    
    for var in required_vars:
        if not os.getenv(var):
            missing_vars.append(var)
    
    if missing_vars:
        print(f"❌ Missing required environment variables: {', '.join(missing_vars)}")
        print("Please add them to .env.test file.")
        return False
    
    print("✅ Prerequisites check passed")
    return True

def run_tests():
    """Run the integration tests."""
    print("\n🚀 Running Strava webhook integration tests...")
    print("=" * 60)
    
    # Run pytest with verbose output
    cmd = [
        sys.executable, '-m', 'pytest',
        'tests/test_webhook_integration.py',
        '-v',           # Verbose output
        '-s',           # Don't capture output
        '--tb=short',   # Short traceback format
        '--color=yes'   # Colored output
    ]
    
    try:
        result = subprocess.run(cmd, check=False)
        return result.returncode == 0
    except Exception as e:
        print(f"❌ Error running tests: {e}")
        return False

def main():
    """Main test runner."""
    print("🧪 Strava Webhook Integration Test Runner")
    print("=" * 50)
    
    if not check_prerequisites():
        sys.exit(1)
    
    print("\n⚠️  IMPORTANT REMINDERS:")
    print("1. Make sure your ngrok tunnel is running")
    print("2. Make sure your webhook handler (FastAPI) is running")
    print("3. Test activities will be created and deleted automatically")
    print("4. Tests use real Strava API calls")
    
    response = input("\n➡️  Ready to proceed? (y/n): ").lower().strip()
    if response != 'y':
        print("❌ Test run cancelled.")
        sys.exit(0)
    
    success = run_tests()
    
    if success:
        print("\n🎉 All integration tests passed!")
        print("Your webhook integration is working correctly.")
    else:
        print("\n❌ Some tests failed.")
        print("Check the output above for details.")
        sys.exit(1)

if __name__ == "__main__":
    main()