# Strava Webhook Integration Tests

This directory contains comprehensive integration tests for the Strava webhook functionality.

## Overview

The integration tests create real Strava activities, wait for webhook delivery via ngrok, and verify database operations. All test activities are automatically cleaned up.

## Test Files

- **`test_webhook_integration.py`** - Main integration test suite
- **`conftest.py`** - Test configuration and fixtures
- **`utils/activity_manager.py`** - Safe activity creation and cleanup
- **`utils/db_test_utils.py`** - Test database utilities

## Prerequisites

1. **ngrok tunnel running** with webhook handler active
2. **Valid Strava credentials** in `.env.test`
3. **Test environment configured**

## Setup

1. Copy environment template:
   ```bash
   cp .env.test.example .env.test  # If you have a template
   ```

2. Configure `.env.test` with your credentials:
   ```
   STRAVA_ACCESS_TOKEN=your_access_token
   CLIENT_ID=your_client_id  
   CLIENT_SECRET=your_client_secret
   ```

3. Install test dependencies:
   ```bash
   pip install -r requirements.txt
   ```

## Running Tests

### Quick Start
```bash
python run_integration_tests.py
```

### Manual pytest
```bash
pytest tests/test_webhook_integration.py -v -s
```

### Specific test
```bash
pytest tests/test_webhook_integration.py::TestWebhookIntegration::test_webhook_create_activity -v -s
```

## Test Scenarios

- **Create Event**: Creates activity → verifies webhook → checks database
- **Update Event**: Updates activity → verifies webhook → checks changes  
- **Delete Event**: Deletes activity → verifies webhook → checks removal
- **Multiple Activities**: Tests batch processing
- **Error Handling**: Validates error scenarios
- **Cleanup Safety**: Ensures proper activity cleanup

## Safety Features

- **Auto-cleanup**: All activities deleted automatically
- **Test prefixes**: Activities clearly marked as tests
- **Orphan cleanup**: Removes leftover activities from failed runs
- **Private activities**: Test activities are private and trainer-marked
- **Local database**: Tests use isolated test database

## Troubleshooting

### Tests fail to create activities
- Check your `STRAVA_ACCESS_TOKEN` in `.env.test`
- Verify token has `activity:write` scope

### Webhooks not received  
- Ensure ngrok tunnel is running
- Verify webhook handler (FastAPI) is active
- Check webhook subscription is active

### Database errors
- Verify test database path is writable
- Check no competing processes using test DB

## Test Activity Format

Test activities are created with:
- Name: `[TEST-WEBHOOK] {timestamp} - Auto-Delete {suffix}`
- Duration: 1 second (minimal)
- Type: Run or Ride
- Visibility: Private
- Trainer: Yes (indoor activity)

This makes them easy to identify and ensures they don't pollute your activity feed.