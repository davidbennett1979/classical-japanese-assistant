#!/bin/bash

# Ollama optimizations for macOS (launchctl). Safe no-op on other OS.

if [[ "$(uname)" != "Darwin" ]]; then
  echo "optimize_ollama.sh: Skipping (requires macOS)."
  exit 0
fi

echo "Setting Ollama optimizations for high-memory system (macOS)..."

# Keep models loaded in memory longer (30 minutes instead of default 5)
launchctl setenv OLLAMA_KEEP_ALIVE "30m"

# Allow multiple parallel requests (good for batch processing)
launchctl setenv OLLAMA_NUM_PARALLEL "4"

# Allow multiple models loaded simultaneously
launchctl setenv OLLAMA_MAX_LOADED_MODELS "2"

# Set reasonable context window (reduce for faster inference)
launchctl setenv OLLAMA_NUM_CTX "4096"

# Use actual GPU cores (e.g., M2 Ultra has 76 GPU cores)
launchctl setenv OLLAMA_NUM_GPU "76"

echo "Environment variables set. Restart Ollama for settings to take effect."
echo "(This script no longer restarts Ollama automatically.)"

echo "Current suggested settings:"
echo "- OLLAMA_KEEP_ALIVE: 30m (keeps model in memory)"
echo "- OLLAMA_NUM_PARALLEL: 4 (parallel requests)"
echo "- OLLAMA_MAX_LOADED_MODELS: 2"
echo "- OLLAMA_NUM_CTX: 4096 (optimized for speed)"
echo "- OLLAMA_NUM_GPU: 76 (GPU cores)"
