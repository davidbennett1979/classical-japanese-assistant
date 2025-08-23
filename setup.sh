#!/bin/bash

echo "🚀 Classical Japanese Learning Assistant Setup"
echo "============================================"

# Check Python version
python_version=$(python3 --version 2>&1 | grep -oE '[0-9]+\.[0-9]+')
echo "✓ Python version: $python_version"

# Create virtual environment
echo "Creating virtual environment..."
python3 -m venv venv
source venv/bin/activate

# Install Python dependencies
echo "Installing Python dependencies..."
pip install --upgrade pip
pip install -r requirements.txt

# Check Tesseract
if command -v tesseract &> /dev/null; then
    echo "✓ Tesseract installed"
    if tesseract --list-langs 2>&1 | grep -q "jpn"; then
        echo "✓ Japanese language pack installed"
    else
        echo "⚠️  Japanese language pack not found. Please install:"
        echo "   macOS: brew install tesseract-lang"
        echo "   Linux: sudo apt-get install tesseract-ocr-jpn"
    fi
else
    echo "❌ Tesseract not found. Please install:"
    echo "   macOS: brew install tesseract"
    echo "   Linux: sudo apt-get install tesseract-ocr"
fi

# Check Poppler
if command -v pdfinfo &> /dev/null; then
    echo "✓ Poppler installed"
else
    echo "⚠️  Poppler not found. Please install:"
    echo "   macOS: brew install poppler"
    echo "   Linux: sudo apt-get install poppler-utils"
fi

# Check Ollama
if command -v ollama &> /dev/null; then
    echo "✓ Ollama installed"
    echo ""
    echo "Available models:"
    ollama list
    echo ""
    echo "To pull recommended model, run:"
    echo "  ollama pull qwen2.5:72b"
else
    echo "⚠️  Ollama not found. Please install from https://ollama.ai"
fi

# Create necessary directories
echo ""
echo "Creating application directories..."
mkdir -p chroma_db
mkdir -p processed_docs

echo ""
echo "✅ Setup complete!"
echo ""
echo "To start the application:"
echo "  1. Activate virtual environment: source venv/bin/activate"
echo "  2. Start Ollama: ollama serve"
echo "  3. Run application: python app.py"
echo "  4. Open browser to: http://localhost:7860"