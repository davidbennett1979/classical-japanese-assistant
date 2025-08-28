import os
from dataclasses import dataclass
from dotenv import load_dotenv
import logging

# Load environment variables from a .env file if present
load_dotenv()


@dataclass
class Settings:
    # Server
    gradio_host: str = os.getenv("GRADIO_HOST", "127.0.0.1")
    gradio_port: int = int(os.getenv("GRADIO_PORT", "7860"))

    # Ollama / LLM
    ollama_url: str = os.getenv("OLLAMA_URL", "http://localhost:11434/api/generate")

    # Vector store / embeddings
    chroma_dir: str = os.getenv("CHROMA_DIR", "./chroma_db")
    embedding_model: str = os.getenv("EMBEDDING_MODEL", "intfloat/multilingual-e5-large")
    embed_batch_size: int = int(os.getenv("EMBED_BATCH_SIZE", "512"))

    # OCR
    ocr_langs: str = os.getenv("OCR_LANGS", "jpn+eng")
    ocr_psm: str = os.getenv("OCR_PSM", "6")  # Page segmentation mode

    # Logging
    log_level: str = os.getenv("LOG_LEVEL", "INFO")


settings = Settings()


def configure_logging():
    level = getattr(logging, settings.log_level.upper(), logging.INFO)
    logging.basicConfig(
        level=level,
        format="%(asctime)s %(levelname)s %(name)s: %(message)s",
    )


# Configure logging on import
configure_logging()

