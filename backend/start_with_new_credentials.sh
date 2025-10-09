#!/bin/bash

echo "🚀 Starting OEE Co-Pilot with New Credentials"
echo "=============================================="

# Check if config.json exists
if [ ! -f "config.json" ]; then
    echo "❌ config.json not found!"
    echo "Please make sure the credentials file exists."
    exit 1
fi

echo "✅ Found config.json with credentials"

# Test credentials first
echo "🔍 Testing credentials..."
python3 test_credentials.py

if [ $? -eq 0 ]; then
    echo ""
    echo "🎉 All tests passed! Starting the application..."
    echo "📡 API will be available at: http://localhost:8000"
    echo "📚 API docs will be available at: http://localhost:8000/docs"
    echo ""
    echo "Press Ctrl+C to stop the server"
    echo ""
    
    # Start the FastAPI server
    python3 -m uvicorn main:app --host 0.0.0.0 --port 8000 --reload
else
    echo "❌ Credential tests failed. Please check your configuration."
    exit 1
fi
