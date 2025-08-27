#!/bin/bash

# Stop the classical-japanese-assistant app gracefully
PID=$(pgrep -f "python app.py")

if [ -n "$PID" ]; then
    echo "Stopping Classical Japanese Assistant (PID: $PID)..."
    kill -TERM $PID
    
    # Wait up to 10 seconds for graceful shutdown
    for i in {1..10}; do
        if ! kill -0 $PID 2>/dev/null; then
            echo "Classical Japanese Assistant stopped successfully"
            exit 0
        fi
        sleep 1
    done
    
    # Force kill if still running
    echo "Process didn't stop gracefully, forcing shutdown..."
    kill -KILL $PID 2>/dev/null
    echo "Classical Japanese Assistant force stopped"
    exit 0
else
    echo "Classical Japanese Assistant is not running"
    exit 1
fi