#!/bin/bash

# Activate virtual environment
source venv/bin/activate

# Apply Mac optimizations
python optimize.py

# Ensure Ollama is running
ollama serve &

# Wait for Ollama to start
sleep 5

# Start the Gradio app
python app.py

