import chromadb
from chromadb.config import Settings
from sentence_transformers import SentenceTransformer
import json
import os
from typing import List, Dict
import hashlib
import logging
from config import settings
import unicodedata
import re

class JapaneseVectorStore:
    def __init__(self, persist_directory: str | None = None):
        # Initialize embedding model - excellent for Japanese
        model_name = settings.embedding_model
        self.embedder = SentenceTransformer(model_name)
        logging.getLogger(__name__).info(f"Loaded embedding model: {model_name}")

        # Initialize ChromaDB with persistence
        db_path = persist_directory or settings.chroma_dir
        self.client = chromadb.PersistentClient(
            path=db_path,
            settings=Settings(
                anonymized_telemetry=False,
                allow_reset=True
            )
        )
        
        # Create or get collection
        self.collection = self.client.get_or_create_collection(
            name="classical_japanese",
            metadata={"description": "Classical Japanese textbook and notes"}
        )
    
    def chunk_text(self, text_data: List[Dict], chunk_size: int = 500):
        """Intelligent chunking that preserves context"""
        chunks = []
        
        for item in text_data:
            text = self._normalize_text(item['text'])
            
            # For short texts, keep as single chunk
            if len(text) <= chunk_size:
                chunks.append({
                    'text': text,
                    'metadata': {
                        'source': item.get('source_pdf', 'unknown'),
                        'page': item.get('page_number', 0),
                        'type': item.get('type', 'text'),
                        'coordinates': item.get('coordinates', {})
                    }
                })
            else:
                # Split longer texts at sentence boundaries
                sentences = text.replace('。', '。|').replace('\n', '|').split('|')
                current_chunk = ""
                
                for sentence in sentences:
                    if len(current_chunk + sentence) <= chunk_size:
                        current_chunk += sentence
                    else:
                        if current_chunk:
                            chunks.append({
                                'text': current_chunk,
                                'metadata': {
                                    'source': item.get('source_pdf', 'unknown'),
                                    'page': item.get('page_number', 0),
                                    'type': 'chunk',
                                    'parent_type': item.get('type', 'text')
                                }
                            })
                        current_chunk = sentence
                
                # Add remaining chunk
                if current_chunk:
                    chunks.append({
                        'text': current_chunk,
                        'metadata': {
                            'source': item.get('source_pdf', 'unknown'),
                            'page': item.get('page_number', 0),
                            'type': 'chunk'
                        }
                    })
        
        return chunks

    def _normalize_text(self, text: str) -> str:
        """Apply Unicode normalization and whitespace cleanup for Japanese text."""
        if not isinstance(text, str):
            text = str(text)
        # NFKC normalization
        text = unicodedata.normalize('NFKC', text)
        # Normalize whitespace (collapse multiple spaces) but keep Japanese punctuation
        text = re.sub(r"[ \t\u3000]+", " ", text)
        # Strip outer whitespace
        return text.strip()
    
    def sanitize_metadata(self, metadata: Dict) -> Dict:
        """Ensure metadata only contains simple types that ChromaDB accepts"""
        clean_metadata = {}
        for key, value in metadata.items():
            if value is None or isinstance(value, (str, int, float, bool)):
                clean_metadata[key] = value
            elif isinstance(value, dict):
                # Flatten dictionary values (e.g., position {'x': 1017, 'y': 979})
                if 'x' in value and 'y' in value:
                    clean_metadata[f"{key}_x"] = value.get('x')
                    clean_metadata[f"{key}_y"] = value.get('y')
                else:
                    # Convert other dicts to string representation
                    clean_metadata[key] = str(value)
            elif isinstance(value, (list, tuple)):
                # Convert lists/tuples to comma-separated strings
                clean_metadata[key] = ', '.join(str(v) for v in value)
            else:
                # Convert any other type to string
                clean_metadata[key] = str(value)
        return clean_metadata
    
    def add_documents(self, documents: List[Dict]):
        """Add documents to vector store"""
        if not documents:
            return
        
        texts = [self._normalize_text(doc['text']) for doc in documents]
        # Sanitize metadata to ensure ChromaDB compatibility
        metadatas = [self.sanitize_metadata(doc['metadata']) for doc in documents]

        # Generate stable IDs using content + key metadata
        ids: list[str] = []
        seen: dict[str, int] = {}
        for text, metadata in zip(texts, metadatas):
            base = f"{text}_{metadata.get('page', '')}_{metadata.get('source', '')}"
            base_hash = hashlib.md5(base.encode()).hexdigest()
            if base_hash in seen:
                seen[base_hash] += 1
                uid = f"{base_hash}-{seen[base_hash]}"
            else:
                seen[base_hash] = 0
                uid = base_hash
            ids.append(uid)

        # Batch embeddings to reduce memory pressure
        batch_size = max(1, int(settings.embed_batch_size))
        logger = logging.getLogger(__name__)
        total = len(texts)
        for start in range(0, total, batch_size):
            end = min(start + batch_size, total)
            batch_texts = texts[start:end]
            batch_metas = metadatas[start:end]
            batch_ids = ids[start:end]
            try:
                embeddings = self.embedder.encode(batch_texts).tolist()
                self.collection.add(
                    documents=batch_texts,
                    embeddings=embeddings,
                    metadatas=batch_metas,
                    ids=batch_ids,
                )
            except Exception as e:
                logger.error(f"Failed to add batch {start}-{end}: {e}")
                raise
        logging.getLogger(__name__).info(f"Added {len(documents)} documents to vector store")
    
    def search(self, query: str, n_results: int = 5):
        """Search for relevant passages"""
        normalized_query = self._normalize_text(query)
        query_embedding = self.embedder.encode([normalized_query]).tolist()
        
        results = self.collection.query(
            query_embeddings=query_embedding,
            n_results=n_results,
            include=['documents', 'metadatas', 'distances']
        )
        
        return results
    
    def add_note(self, note_text: str, related_topic: str = None):
        """Add personal notes to the vector store"""
        note_doc = {
            'text': self._normalize_text(note_text),
            'metadata': {
                'source': 'personal_notes',
                'type': 'note',
                'topic': related_topic or 'general'
            }
        }
        self.add_documents([note_doc])

# Usage
# Test code - commented out
# vector_store = JapaneseVectorStore()
# 
# # Load and process OCR data
# with open('./processed_docs/your_textbook.pdf.json', 'r', encoding='utf-8') as f:
#     ocr_data = json.load(f)
# 
# # Chunk and add to vector store
# chunks = vector_store.chunk_text(ocr_data)
# vector_store.add_documents(chunks)
# 
# # Add a personal note
# vector_store.add_note(
#     "The particle ぞ is emphatic and often appears in classical poetry",
#     related_topic="particles"
# )
