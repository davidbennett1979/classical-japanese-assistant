#!/bin/bash

# Activate virtual environment
source venv/bin/activate

# Apply Ollama optimizations for high-memory system
./optimize_ollama.sh

# Start the Gradio app
python app.py

