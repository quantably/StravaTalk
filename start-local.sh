#!/bin/bash

# StravaTalk Local Development Startup Script

echo "🚀 Starting StravaTalk Local Development Environment"
echo "=================================================="

# Check if .env file exists
if [ ! -f .env ]; then
    echo "❌ .env file not found. Please copy .env.example to .env and configure it."
    exit 1
fi

# Start services with docker-compose
echo "📦 Starting services with Docker Compose..."
docker compose up --build -d

echo ""
echo "✅ StravaTalk is starting up!"
echo ""
echo "🌐 Services will be available at:"
echo "   • Streamlit App:    http://localhost:8504"
echo "   • FastAPI Services: http://localhost:8000"
echo "   • OAuth Flow:       http://localhost:8000/"
echo "   • API Health:       http://localhost:8000/health"
echo ""
echo "📋 To view logs:"
echo "   docker compose logs -f"
echo ""
echo "🛑 To stop services:"
echo "   docker compose down"
echo ""
echo "⏳ Services are starting... This may take a few moments."

# Wait for services to be healthy
echo "🔍 Waiting for services to be ready..."
sleep 10

# Check if services are responding
if curl -s http://localhost:8000/health > /dev/null; then
    echo "✅ FastAPI service is healthy"
else
    echo "⚠️  FastAPI service not responding yet"
fi

if curl -s http://localhost:8504/_stcore/health > /dev/null; then
    echo "✅ Streamlit service is healthy"
else
    echo "⚠️  Streamlit service not responding yet (may still be starting)"
fi

echo ""
echo "🎉 StravaTalk development environment is ready!"
echo "   Visit http://localhost:8504 to access the application"