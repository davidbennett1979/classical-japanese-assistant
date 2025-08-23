import chromadb
from chromadb.config import Settings
from sentence_transformers import SentenceTransformer
import json
import os
from typing import List, Dict
import hashlib

class JapaneseVectorStore:
    def __init__(self, persist_directory="./chroma_db"):
        # Initialize embedding model - excellent for Japanese
        self.embedder = SentenceTransformer('intfloat/multilingual-e5-large')
        
        # Initialize ChromaDB with persistence
        self.client = chromadb.PersistentClient(
            path=persist_directory,
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
            text = item['text']
            
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
                sentences = text.replace('。', '。|').split('|')
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
    
    def add_documents(self, documents: List[Dict]):
        """Add documents to vector store"""
        if not documents:
            return
        
        texts = [doc['text'] for doc in documents]
        metadatas = [doc['metadata'] for doc in documents]
        
        # Generate unique IDs using text content + metadata for uniqueness
        ids = []
        for i, (text, metadata) in enumerate(zip(texts, metadatas)):
            # Include metadata info to ensure uniqueness
            unique_string = f"{text}_{metadata.get('page', '')}_{metadata.get('source', '')}_{i}"
            ids.append(hashlib.md5(unique_string.encode()).hexdigest())
        
        # Generate embeddings
        embeddings = self.embedder.encode(texts).tolist()
        
        # Add to ChromaDB
        self.collection.add(
            documents=texts,
            embeddings=embeddings,
            metadatas=metadatas,
            ids=ids
        )
        
        print(f"Added {len(documents)} documents to vector store")
    
    def search(self, query: str, n_results: int = 5):
        """Search for relevant passages"""
        query_embedding = self.embedder.encode([query]).tolist()
        
        results = self.collection.query(
            query_embeddings=query_embedding,
            n_results=n_results,
            include=['documents', 'metadatas', 'distances']
        )
        
        return results
    
    def add_note(self, note_text: str, related_topic: str = None):
        """Add personal notes to the vector store"""
        note_doc = {
            'text': note_text,
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

