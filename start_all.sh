#!/bin/bash

echo "Starting Guide Application..."

echo "Starting Adaptive Learning Server..."
node adaptive/server.js &
ADAPTIVE_PID=$!

sleep 2

echo "Starting Guide API Server..."
uvicorn api.main:app --host 0.0.0.0 --port 8000 &
API_PID=$!

echo "All services started!"
echo "   - Guide API (port 8000)"
echo "   - Adaptive Learning (port 3000)"

cleanup() {
    echo "Shutting down services..."
    kill $API_PID $ADAPTIVE_PID 2>/dev/null
    exit 0
}

trap cleanup SIGTERM SIGINT

wait
