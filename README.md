# StravaTalk

StravaTalk is an intelligent conversational interface for analyzing your Strava activities using natural language queries. It leverages AI agents to understand your questions about your Strava data and provides insightful responses.

## Features

- 🗣️ **Natural Language Processing**: Ask questions about your Strava activities in plain English
- 📊 **SQL Query Generation**: Automatically converts natural language to optimized SQL queries
- 🤖 **Intelligent Classification**: Determines if queries can be answered using available Strava data
- 📈 **Smart Response Generation**: Provides formatted, easy-to-understand responses with proper units
- 🔄 **Conversation Memory**: Maintains context throughout your interaction
- 🔐 **User Authentication**: Secure OAuth integration with Strava
- 🏃‍♂️ **Multi-User Support**: User data segregation and authentication
- ⚡ **Real-time Sync**: Automatic activity updates via Strava webhooks
- 🔄 **Token Management**: Automatic token refresh for uninterrupted service
- 🎨 **Interactive Visualizations**: Charts and graphs for activity data

## Architecture

The project consists of three main AI agents:

1. **Classification Agent**: Determines if a query can be answered using the Strava database
2. **SQL Agent**: Converts natural language queries into SQL
3. **Response Agent**: Generates human-friendly responses from query results

## Services Architecture

StravaTalk consists of three main services:

1. **Streamlit App**: Interactive web interface for querying activities
2. **FastAPI OAuth Service**: Handles Strava authentication and user management  
3. **FastAPI Webhook Service**: Processes real-time activity updates from Strava
4. **PostgreSQL Database**: Stores user activities and authentication tokens (Neon)

Example queries:
- "What was my longest run last month?"
- "Show me my average speed on bike rides this year" 
- "How many activities did I do in 2023?"
- "Create a chart of my distance over time"

## Quick Start

### Local Development

1. **Clone the repository**:
   ```bash
   git clone <repository-url>
   cd StravaTalk
   ```

2. **Set up environment**:
   ```bash
   cp .env.example .env
   # Edit .env with your configuration
   ```

3. **Start with Docker**:
   ```bash
   ./start-local.sh
   ```

4. **Access the application**:
   - Main App: http://localhost:8504
   - OAuth/API: http://localhost:8000

### Production Deployment

See [DEPLOYMENT.md](DEPLOYMENT.md) for detailed deployment instructions to Render.

## Configuration

Required environment variables:
- `DATABASE_URL`: PostgreSQL connection string (Neon)
- `OPENAI_API_KEY`: OpenAI API key for AI agents
- `CLIENT_ID`: Strava application client ID
- `CLIENT_SECRET`: Strava application client secret
- `STRAVA_WEBHOOK_VERIFY_TOKEN`: Webhook verification token
- `OAUTH_REDIRECT_URI`: OAuth callback URL
- `WEBHOOK_CALLBACK_URL`: Webhook endpoint URL
