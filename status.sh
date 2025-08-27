#!/bin/bash

# Check if the classical-japanese-assistant app is running
PID=$(pgrep -f "app.py")

if [ -n "$PID" ]; then
    echo "Classical Japanese Assistant is running (PID: $PID)"
    echo "Listening on port (if Gradio default): http://127.0.0.1:7860"
    exit 0
else
    echo "Classical Japanese Assistant is not running"
    exit 1
fi