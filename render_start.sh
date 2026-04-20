#!/bin/bash
set -e

echo "Starting Guide Application on Render..."
echo "Render PORT=${PORT:-unset}"

ADAPTIVE_PORT="${ADAPTIVE_PORT:-3000}"

if [ -z "$PORT" ]; then
  PORT=8000
fi

if [ "$ADAPTIVE_PORT" = "$PORT" ]; then
  echo "ADAPTIVE_PORT collides with PORT ($PORT); switching adaptive to $((PORT + 1))"
  ADAPTIVE_PORT=$((PORT + 1))
fi
export ADAPTIVE_PORT

if [ ! -d "adaptive/node_modules" ]; then
  echo "Installing Adaptive Learning Server Node dependencies..."
  (cd adaptive && npm install --omit=dev)
fi

echo "Starting Adaptive Learning Server on port ${ADAPTIVE_PORT} (internal)..."
node adaptive/server.js &
ADAPTIVE_PID=$!

for i in $(seq 1 20); do
  if curl -sf "http://127.0.0.1:${ADAPTIVE_PORT}/health" > /dev/null 2>&1; then
    echo "Adaptive Learning Server is healthy on port ${ADAPTIVE_PORT}"
    break
  fi
  if ! kill -0 $ADAPTIVE_PID 2>/dev/null; then
    echo "ERROR: Adaptive Learning Server failed to start"
    exit 1
  fi
  sleep 1
done

cleanup() {
  echo "Shutting down services..."
  kill $ADAPTIVE_PID 2>/dev/null || true
  exit 0
}
trap cleanup SIGTERM SIGINT EXIT

echo "Starting Guide API Server (foreground) on port ${PORT}..."
exec uvicorn api.main:app --host 0.0.0.0 --port "${PORT}"
