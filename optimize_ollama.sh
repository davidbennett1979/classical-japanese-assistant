#!/bin/bash

# Ollama optimizations for Mac Studio with 192GB RAM

echo "Setting Ollama optimizations for high-memory system..."

# Keep models loaded in memory longer (30 minutes instead of default 5)
launchctl setenv OLLAMA_KEEP_ALIVE "30m"

# Allow multiple parallel requests (good for batch processing)
launchctl setenv OLLAMA_NUM_PARALLEL "4"

# Allow multiple models loaded simultaneously
launchctl setenv OLLAMA_MAX_LOADED_MODELS "2"

# Set reasonable context window (reduce for faster inference)
launchctl setenv OLLAMA_NUM_CTX "4096"

# Use actual GPU cores (M2 Ultra has 76 GPU cores)
launchctl setenv OLLAMA_NUM_GPU "76"

echo "Environment variables set. Restarting Ollama..."

# Restart Ollama to apply settings
killall ollama 2>/dev/null || true
sleep 2
ollama serve > /dev/null 2>&1 &
sleep 3

echo "Ollama optimized for your system!"
echo ""
echo "Current settings:"
echo "- OLLAMA_KEEP_ALIVE: 30m (keeps model in memory)"
echo "- OLLAMA_NUM_PARALLEL: 4 (parallel requests)"
echo "- OLLAMA_MAX_LOADED_MODELS: 2"
echo "- OLLAMA_NUM_CTX: 4096 (optimized for speed)"
echo "- OLLAMA_NUM_GPU: 76 (M2 Ultra GPU cores)"
echo ""
echo "With 192GB RAM, you could also run:"
echo "- llama3.1:70b (40GB)"
echo "- mixtral:8x7b (26GB)"
echo "- deepseek-coder:33b (19GB)"
echo ""
echo "Run multiple models simultaneously without issues!"