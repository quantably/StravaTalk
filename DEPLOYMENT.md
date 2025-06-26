# StravaTalk Deployment Guide

This guide walks through deploying StravaTalk to Render with the existing Neon PostgreSQL database.

## Architecture

- **Database**: Neon PostgreSQL (already deployed)
- **Frontend**: Streamlit app (containerized on Render)
- **Backend**: FastAPI services for OAuth + Webhooks (containerized on Render)

## Prerequisites

1. **Neon Database**: Already set up ✅
2. **Render Account**: Sign up at [render.com](https://render.com)
3. **GitHub Repository**: Code should be pushed to GitHub
4. **Strava App**: Registered at [developers.strava.com](https://developers.strava.com)

## Deployment Steps

### 1. Deploy FastAPI Service (OAuth + Webhook)

1. **Create Web Service on Render**:
   - Connect your GitHub repository
   - Select "Docker" as build method
   - Set **Dockerfile Path**: `Dockerfile.fastapi`
   - Set **Service Name**: `stravatalk-api`

2. **Configure Environment Variables**:
   ```bash
   DATABASE_URL=your-neon-postgresql-url
   OPENAI_API_KEY=your-openai-api-key
   CLIENT_ID=your-strava-client-id
   CLIENT_SECRET=your-strava-client-secret
   STRAVA_WEBHOOK_VERIFY_TOKEN=your-webhook-verify-token
   OAUTH_REDIRECT_URI=https://stravatalk-api.onrender.com/oauth/callback
   WEBHOOK_CALLBACK_URL=https://stravatalk-api.onrender.com/webhook
   ```

3. **Deploy and Get URL**: Note the service URL (e.g., `https://stravatalk-api.onrender.com`)

### 2. Deploy Streamlit App

1. **Create Web Service on Render**:
   - Connect your GitHub repository
   - Select "Docker" as build method  
   - Set **Dockerfile Path**: `Dockerfile.streamlit`
   - Set **Service Name**: `stravatalk-app`

2. **Configure Environment Variables**:
   ```bash
   DATABASE_URL=your-neon-postgresql-url
   OPENAI_API_KEY=your-openai-api-key
   ```

3. **Deploy and Get URL**: Note the app URL (e.g., `https://stravatalk-app.onrender.com`)

### 3. Update Strava App Settings

1. **Go to Strava Developers Console**
2. **Update OAuth Settings**:
   - Authorization Callback Domain: `stravatalk-api.onrender.com`
   - Authorization Callback URL: `https://stravatalk-api.onrender.com/oauth/callback`

### 4. Test Production Deployment

1. **Visit FastAPI Service**: `https://stravatalk-api.onrender.com`
   - Should show OAuth login page
   - Test OAuth flow end-to-end

2. **Visit Streamlit App**: `https://stravatalk-app.onrender.com`  
   - Should prompt for authentication
   - Complete OAuth flow
   - Test activity queries

3. **Test Webhooks**: Upload a new Strava activity
   - Should appear in database automatically
   - Check Render logs for webhook events

## Production URLs

After deployment, you'll have:

- **Main App**: `https://stravatalk-app.onrender.com` (Streamlit interface)
- **API/OAuth**: `https://stravatalk-api.onrender.com` (Authentication & webhooks)
- **Database**: Neon PostgreSQL (existing)

## Monitoring

- **Render Dashboard**: Monitor service health and logs
- **Database**: Use Neon dashboard for database monitoring
- **Webhooks**: Check Render logs for webhook event processing

## Environment Variables Reference

Copy the values from `.env.production` to your Render service environment variables.

## Troubleshooting

- **Service Won't Start**: Check Render build logs
- **Database Connection**: Verify DATABASE_URL is correct
- **OAuth Issues**: Ensure Strava app settings match production URLs
- **Webhooks Not Working**: Check webhook subscription and verify tokens