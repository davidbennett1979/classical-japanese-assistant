# Classical Japanese Learning Assistant

A RAG (Retrieval-Augmented Generation) powered application for studying Classical Japanese using your own textbooks and notes. The system uses OCR to extract text from PDFs/images, stores them in a vector database, and provides an AI assistant that can answer questions based on your specific study materials.

## Features

- 📚 **PDF/Image OCR**: Automatically extract Japanese text from scanned textbooks
- 🔍 **Semantic Search**: Find relevant information from your textbooks using natural language queries
- 💬 **AI Chat Interface**: Ask questions about grammar, vocabulary, and get explanations with citations
- ⚡ **Real-time Streaming**: Watch responses generate in real-time with token-by-token streaming
- 🧠 **Thinking Mode Support**: For reasoning models (qwen3, deepseek-r1), see the AI's thought process in a collapsible accordion while the answer streams separately
- 📝 **Personal Notes**: Add and search through your own study notes
- 🎯 **Grammar Search**: Dedicated interface for exploring specific grammar points
- 📖 **Source Citations**: All answers include page references from your materials
- 🔄 **Model Switching**: Seamlessly switch between different Ollama models from the settings tab
- 🛡️ **Production Ready**: Robust error handling, session isolation, and performance optimizations

## Architecture Overview

### Components

1. **`app.py`** - Main Gradio web interface
   - Provides tabs for chat, notes, grammar search, and document upload
   - Handles user interactions and coordinates between components

2. **`ocr_pipeline.py`** - Japanese OCR processing
   - Uses Tesseract OCR with Japanese language support
   - Processes PDFs by converting to images
   - Extracts text while preserving layout information

3. **`vector_store.py`** - Vector database management
   - Uses ChromaDB for semantic search
   - Chunks text into manageable segments
   - Stores document metadata (source, page numbers)

4. **`rag_assistant.py`** - AI assistant logic
   - Interfaces with Ollama for LLM inference with streaming support
   - Creates prompts with retrieved context
   - Implements tag-aware parsing for thinking models (`<think>` tags)
   - Formats responses with citations
   - Automatically detects and handles reasoning/thinking models

5. **`optimize.py`** - Mac-specific optimizations
   - Configures Metal acceleration
   - Optimizes Ollama settings for Apple Silicon

## Prerequisites

### System Requirements
- Python 3.8+
- macOS (optimized for Apple Silicon) or Linux
- At least 16GB RAM (32GB+ recommended for larger models)
- 100GB+ free disk space for models

### Required Software

1. **Tesseract OCR**
   ```bash
   # macOS
   brew install tesseract
   brew install tesseract-lang  # for Japanese support
   
   # Ubuntu/Debian
   sudo apt-get install tesseract-ocr
   sudo apt-get install tesseract-ocr-jpn
   ```

2. **Poppler** (for PDF processing)
   ```bash
   # macOS
   brew install poppler
   
   # Ubuntu/Debian
   sudo apt-get install poppler-utils
   ```

3. **Ollama** (for local LLM)
   ```bash
   # Download from https://ollama.ai
   # Then pull a model:
   ollama pull qwen2.5:72b  # or llama3.1:70b for smaller systems
   ```

### Python Dependencies

```bash
pip install -r requirements.txt
```

Create `requirements.txt`:
```
gradio>=4.0.0
chromadb>=0.4.0
sentence-transformers>=2.2.0
pytesseract>=0.3.10
pdf2image>=1.16.0
Pillow>=10.0.0
requests>=2.31.0
numpy>=1.24.0
```

## Installation

1. Clone the repository:
   ```bash
   git clone https://github.com/yourusername/classical-japanese-assistant.git
   cd classical-japanese-assistant
   ```

2. Create a virtual environment:
   ```bash
   python -m venv venv
   source venv/bin/activate  # On Windows: venv\Scripts\activate
   ```

3. Install Python dependencies:
   ```bash
   pip install -r requirements.txt
   ```

4. Verify Tesseract installation:
   ```bash
   tesseract --version
   tesseract --list-langs | grep jpn  # Should show 'jpn'
   ```

5. Start Ollama:
   ```bash
   ollama serve  # Run in a separate terminal
   ```

6. Run the application:
   ```bash
   python app.py
   ```

7. Open your browser to `http://localhost:7860`

## Usage

### First Time Setup
1. Launch the application
2. Go to the "Add Documents" tab
3. Upload your Classical Japanese textbook PDF
4. Wait for OCR processing (this may take several minutes)
5. Once processed, go to the "Chat" tab to start asking questions

### Adding Documents
- Supported formats: PDF, JPG, PNG
- PDFs are automatically split into pages and OCR'd
- Text is chunked and indexed for semantic search
- Metadata (source filename, page number) is preserved

### Asking Questions
- Use natural language queries in the Chat tab
- Example: "Explain the べし auxiliary verb"
- The assistant will search your textbooks and provide answers with page citations

### Adding Personal Notes
- Use the "Add Notes" tab to save study notes
- Tag notes with topics for better organization
- Notes are searchable alongside textbook content

## Preparing for GitHub

### 1. Create `.gitignore`
```
# Python
__pycache__/
*.py[cod]
*$py.class
*.so
.Python
venv/
env/
ENV/

# IDE
.vscode/
.idea/
*.swp
*.swo
.DS_Store

# Application specific
chroma_db/
processed_docs/
*.db
*.sqlite
*.json

# Models (too large for git)
models/
*.gguf
*.bin

# Logs
*.log
logs/

# Temporary files
tmp/
temp/
```

### 2. Create `requirements.txt` (as shown above)

### 3. Remove sensitive data
- Check for any API keys or credentials
- Remove test data from the code
- Ensure no copyrighted textbook content is included

### 4. Initialize Git repository
```bash
git init
git add .
git commit -m "Initial commit: Classical Japanese Learning Assistant"
```

### 5. Create GitHub repository and push
```bash
git remote add origin https://github.com/yourusername/classical-japanese-assistant.git
git branch -M main
git push -u origin main
```

## Configuration

### Changing the LLM Model
Edit `app.py` line 99-100 to change available models:
```python
choices=["qwen2.5:72b", "llama3.1:70b", "your-model-here"]
```

### Adjusting Chunk Size
Edit `vector_store.py` line 51-52:
```python
chunk_size=500  # Characters per chunk
chunk_overlap=50  # Overlap between chunks
```

### Optimizing for Your System
Run the optimization script for Mac:
```bash
python optimize.py
```

## Troubleshooting

### "Model not found" error
- Ensure Ollama is running: `ollama serve`
- Pull the required model: `ollama pull qwen2.5:72b`

### OCR produces garbled text
- Verify Japanese language pack: `tesseract --list-langs`
- Install if missing: `brew install tesseract-lang`

### Out of memory errors
- Use a smaller model (e.g., `llama3.1:7b`)
- Reduce chunk size in `vector_store.py`
- Close other applications

### Slow performance
- Ensure Ollama is using GPU/Metal acceleration
- Run `optimize.py` for Mac optimizations
- Consider using a smaller model

## Contributing

Contributions are welcome! Please feel free to submit a Pull Request.

## License

MIT License - feel free to use this for your own learning!

## Acknowledgments

- Built with Gradio, ChromaDB, and Ollama
- Designed for Classical Japanese learners
- Optimized for Apple Silicon Macs

## Support

For issues or questions, please open an issue on GitHub.