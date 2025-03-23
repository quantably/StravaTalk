# StravaTalk

StravaTalk is an intelligent conversational interface for analyzing your Strava activities using natural language queries. It leverages AI agents to understand your questions about your Strava data and provides insightful responses.

## Features

- 🗣️ Natural Language Processing: Ask questions about your Strava activities in plain English
- 📊 SQL Query Generation: Automatically converts natural language to optimized SQL queries
- 🤖 Intelligent Classification: Determines if queries can be answered using available Strava data
- 📈 Smart Response Generation: Provides formatted, easy-to-understand responses with proper units
- 🔄 Conversation Memory: Maintains context throughout your interaction

## Architecture

The project consists of three main AI agents:

1. **Classification Agent**: Determines if a query can be answered using the Strava database
2. **SQL Agent**: Converts natural language queries into SQL
3. **Response Agent**: Generates human-friendly responses from query results

Example queries:
- "What was my longest run last month?"
- "Show me my average speed on bike rides this year"
- "How many activities did I do in 2023?"
- "What was my average heart rate during my last 5 runs?"
