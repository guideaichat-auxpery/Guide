#!/bin/bash

echo "Starting Guide Application..."

if [ ! -d "frontend/dist" ]; then
  echo "Building frontend..."
  cd frontend && npm run build 2>&1
  cd ..
fi

echo "Starting Adaptive Learning Server..."
node adaptive/server.js &
ADAPTIVE_PID=$!

sleep 2

echo "Starting Guide API Server..."
uvicorn api.main:app --host 0.0.0.0 --port 5000 &
API_PID=$!

echo "All services started!"
echo "   - Guide API + Static Frontend (port 5000)"
echo "   - Adaptive Learning (port 3000)"

cleanup() {
    echo "Shutting down services..."
    kill $API_PID $ADAPTIVE_PID 2>/dev/null
    exit 0
}

trap cleanup SIGTERM SIGINT

wait
