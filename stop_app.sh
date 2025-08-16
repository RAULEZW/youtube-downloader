#!/bin/bash

echo "🛑 Stopping Flask (port 5050)..."
lsof -ti :5050 | xargs kill -9 2>/dev/null

echo "🛑 Stopping all ngrok sessions..."
pkill -f "ngrok" 2>/dev/null

echo "✅ All processes stopped."
