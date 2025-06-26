# StravaTalk: Live Application Deployment Plan

This plan outlines the steps to take StravaTalk from a local application to a live, shareable web application.

## Phase 1: Migrate to a Remote Database

The goal of this phase is to replace the local SQLite database with a cloud-hosted PostgreSQL database.

- [x] **Set up Remote Database:** Choose a provider (e.g., Neon, Supabase) and set up a free-tier PostgreSQL database.
- [x] **Create `requirements.txt`:** Add `psycopg2-binary`, `python-dotenv`, and other necessary packages.
- [x] **Isolate Environments:**
    - [x] Create a `.env.example` file to show what environment variables are needed.
    - [x] Update `.gitignore` to ensure `.env` is not committed to version control.
    - [x] Implement logic to load a `DATABASE_URL` from environment variables. This will allow local development to use a local DB (or a separate dev DB) while production uses the production DB.
- [x] **Update Database Utilities:** Modify `utils/db_utils.py` to connect to the PostgreSQL database using the `DATABASE_URL`.
- [x] **Update Population Script:** Adapt `utils/populate_db.py` to work with the new PostgreSQL database.
- [x] **Test Locally:** Verify that the application runs correctly with the new database connection.

## Phase 2: Dynamic Data with Strava Webhooks ✅ COMPLETE

This phase replaced the manual data population script with a dynamic, event-driven system using Strava Webhooks.

- [x] **Create Webhook Handler:** Build a new FastAPI service to listen for incoming webhook events from Strava.
- [x] **Implement Strava Webhook Subscription:** Add automatic subscription verification logic during OAuth.
- [x] **Process Webhook Events:**
    - [x] Handle `create` events for new activities.
    - [x] Handle `update` events for changed activities.
    - [x] Handle `delete` events for removed activities.
- [x] **Implement Strava OAuth Flow:**
    - [x] Create a user-facing page to initiate the OAuth flow with scope selection.
    - [x] Add a callback endpoint to handle the OAuth redirect from Strava.
    - [x] Securely store user access and refresh tokens in the database.
- [x] **Additional Features Implemented:**
    - [x] **User Data Segregation:** Multi-user support with athlete_id filtering
    - [x] **Automatic Token Refresh:** Seamless token renewal without user intervention
    - [x] **Manual Activity Sync:** Backup sync capability for comprehensive data
    - [x] **Real-time Updates:** Webhook-driven activity synchronization
    - [x] **User Authentication:** Complete OAuth integration with user sessions

## Phase 3: Deployment 🚀 IN PROGRESS

This phase packages the application and deploys it to Render with the existing Neon PostgreSQL database.

**Architecture:** 
- **Database:** Neon PostgreSQL (already deployed)
- **App Services:** Render (containerized deployment)
- **Services:** Streamlit App + FastAPI (OAuth + Webhook)

- [ ] **Containerize the Application:**
    - [ ] Create a `Dockerfile` for the Streamlit application.
    - [ ] Create a `Dockerfile` for the FastAPI services (OAuth + Webhook combined).
    - [ ] Create `docker-compose.yml` for local development/testing.
    - [ ] Add `.dockerignore` for optimized builds.
- [ ] **Production Configuration:**
    - [ ] Configure production environment variables for Render.
    - [ ] Update OAuth redirect URLs for production domains.
    - [ ] Update webhook subscription URLs (replace ngrok).
- [ ] **Deploy to Render:**
    - [ ] Deploy the Streamlit service as a web service.
    - [ ] Deploy the FastAPI service as a web service.
    - [ ] Configure custom domains and environment variables.
- [ ] **Production Testing & Documentation:**
    - [ ] Test end-to-end OAuth flow in production.
    - [ ] Verify webhook events with real Strava activities.
    - [ ] Update README with deployment instructions and production URLs.
