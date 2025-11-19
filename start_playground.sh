#!/bin/bash

# Nummary ChatKit Playground Launcher
# This script starts the backend server and opens the playground in your browser

echo "════════════════════════════════════════════════"
echo "    Nummary ChatKit Playground Launcher"
echo "════════════════════════════════════════════════"
echo ""

# Check if Python is installed
if ! command -v python3 &> /dev/null; then
    echo "❌ Python 3 is not installed. Please install Python 3.7 or higher."
    exit 1
fi

# Check if required packages are installed
echo "📦 Checking dependencies..."
python3 -c "import flask" 2>/dev/null
if [ $? -ne 0 ]; then
    echo "Installing Flask..."
    pip3 install flask flask-cors requests
fi

# Kill any existing server on port 5000
echo "🔍 Checking for existing server..."
lsof -ti:5000 | xargs kill -9 2>/dev/null

# Start the backend server in the background
echo "🚀 Starting backend server..."
python3 playground_server.py &
SERVER_PID=$!

# Wait for server to start
echo "⏳ Waiting for server to initialize..."
sleep 2

# Check if server is running
if ! kill -0 $SERVER_PID 2>/dev/null; then
    echo "❌ Failed to start the backend server"
    exit 1
fi

# Get the full path to the HTML file
PLAYGROUND_PATH="$(pwd)/nummary_playground.html"

# Open the playground in the default browser
echo "🌐 Opening playground in browser..."
if [[ "$OSTYPE" == "darwin"* ]]; then
    # macOS
    open "$PLAYGROUND_PATH"
elif [[ "$OSTYPE" == "linux-gnu"* ]]; then
    # Linux
    xdg-open "$PLAYGROUND_PATH"
elif [[ "$OSTYPE" == "msys" ]] || [[ "$OSTYPE" == "win32" ]]; then
    # Windows
    start "$PLAYGROUND_PATH"
else
    echo "⚠️  Could not automatically open browser. Please open manually:"
    echo "   $PLAYGROUND_PATH"
fi

echo ""
echo "✅ Playground is ready!"
echo ""
echo "📌 Server running at: http://localhost:5000"
echo "📌 Playground at: $PLAYGROUND_PATH"
echo ""
echo "Press Ctrl+C to stop the server and exit"
echo ""

# Keep the script running and handle Ctrl+C
trap "echo ''; echo '🛑 Shutting down server...'; kill $SERVER_PID 2>/dev/null; exit 0" INT

# Wait for the server process
wait $SERVER_PID
