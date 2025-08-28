#!/bin/bash

# Activate virtual environment
source venv/bin/activate

# Apply Ollama optimizations on macOS only (safe no-op on others)
./optimize_ollama.sh || true

# Start the Gradio app
python app.py
