#!/bin/bash
set -e

echo "Starting Guide Application on Render..."

ADAPTIVE_PORT="${ADAPTIVE_PORT:-3000}"

if [ ! -d "adaptive/node_modules" ]; then
  echo "Installing Adaptive Learning Server Node dependencies..."
  (cd adaptive && npm install --omit=dev)
fi

echo "Starting Adaptive Learning Server on port ${ADAPTIVE_PORT}..."
node adaptive/server.js &
ADAPTIVE_PID=$!

for i in $(seq 1 15); do
  if curl -sf "http://127.0.0.1:${ADAPTIVE_PORT}/health" > /dev/null 2>&1; then
    echo "Adaptive Learning Server is healthy"
    break
  fi
  if ! kill -0 $ADAPTIVE_PID 2>/dev/null; then
    echo "ERROR: Adaptive Learning Server failed to start"
    exit 1
  fi
  sleep 1
done

if ! curl -sf "http://127.0.0.1:${ADAPTIVE_PORT}/health" > /dev/null 2>&1; then
  echo "ERROR: Adaptive Learning Server did not become healthy in time"
  kill $ADAPTIVE_PID 2>/dev/null
  exit 1
fi

echo "Starting Guide API Server on port ${PORT:-8000}..."
uvicorn api.main:app --host 0.0.0.0 --port "${PORT:-8000}" &
API_PID=$!

echo "All services started!"
echo "   - Guide API (port ${PORT:-8000})"
echo "   - Adaptive Learning (port ${ADAPTIVE_PORT})"

cleanup() {
    echo "Shutting down services..."
    kill $API_PID $ADAPTIVE_PID 2>/dev/null
    exit 0
}

trap cleanup SIGTERM SIGINT

while true; do
  if ! kill -0 $ADAPTIVE_PID 2>/dev/null; then
    echo "ERROR: Adaptive Learning Server crashed, shutting down"
    kill $API_PID 2>/dev/null
    exit 1
  fi
  if ! kill -0 $API_PID 2>/dev/null; then
    echo "ERROR: Guide API Server crashed, shutting down"
    kill $ADAPTIVE_PID 2>/dev/null
    exit 1
  fi
  sleep 5
done
