#!/bin/bash

# Unified startup script for Guide application
# Runs all services together: Reverse Proxy, Streamlit, Payments Service, Adaptive Learning

echo "🚀 Starting Guide Application..."

# Start Payments Service in background
echo "💳 Starting Payments Service..."
node payments/server.js &
PAYMENTS_PID=$!

# Start Adaptive Learning Server in background
echo "📊 Starting Adaptive Learning Server..."
node adaptive/server.js &
ADAPTIVE_PID=$!

# Wait for services to start
sleep 2

# Start Streamlit in background
echo "🌱 Starting Guide AI Assistant (Streamlit)..."
streamlit run app.py --server.port 8080 &
STREAMLIT_PID=$!

# Wait for Streamlit to be ready
sleep 3

# Start Reverse Proxy (main entry point on port 5000)
echo "🔀 Starting Reverse Proxy..."
node proxy_server.js &
PROXY_PID=$!

echo "✅ All services started!"
echo "   - Reverse Proxy (port 5000 - exposed)"
echo "   - Streamlit (port 8080)"
echo "   - Payments Service (port 3001)"
echo "   - Adaptive Learning (port 3000)"

# Handle shutdown
cleanup() {
    echo "🛑 Shutting down services..."
    kill $PROXY_PID $STREAMLIT_PID $PAYMENTS_PID $ADAPTIVE_PID 2>/dev/null
    exit 0
}

trap cleanup SIGTERM SIGINT

# Wait for all background processes
wait
