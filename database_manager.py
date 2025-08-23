#!/usr/bin/env python3
"""
Database management utilities for Classical Japanese Assistant
"""

from vector_store import JapaneseVectorStore
from collections import Counter
import json

class DatabaseManager:
    def __init__(self):
        self.vector_store = JapaneseVectorStore()
    
    def get_textbook_stats(self):
        """Get statistics about textbooks in the database"""
        try:
            all_docs = self.vector_store.collection.get(include=['metadatas', 'documents'])
            metadatas = all_docs['metadatas']
            documents = all_docs['documents']
            
            # Count by source
            sources = [meta.get('source', 'unknown') for meta in metadatas]
            source_counts = Counter(sources)
            
            # Find REAL duplicates - identical text content that's likely from processing errors
            # Not just repeated words/particles which are normal in language
            real_duplicates = 0
            text_counts = Counter(doc.strip() for doc in documents if doc.strip())
            
            # Only count as duplicates if:
            # 1. Text is substantial (>10 characters)
            # 2. Appears more than 2 times (very likely processing error)
            # 3. Isn't common single words/particles
            for text, count in text_counts.items():
                if (len(text) > 10 and  # Substantial text
                    count > 2 and       # Appears many times
                    not self._is_common_element(text)):  # Not a common element
                    real_duplicates += (count - 1)  # Count extras only
            
            return {
                'total_documents': len(metadatas),
                'textbooks': dict(source_counts),
                'duplicates': real_duplicates,
                'duplicate_examples': {}  # Don't show examples of legitimate repeated text
            }
        except Exception as e:
            return {'error': str(e)}
    
    def _is_common_element(self, text):
        """Check if text is a common element that naturally repeats"""
        text = text.strip().lower()
        
        # Common particles, short words, page numbers, etc.
        common_elements = {
            'は', 'が', 'を', 'に', 'の', 'と', 'で', 'から', 'まで', 'へ',
            'である', 'です', 'だ', 'である。', 'です。', 'だ。',
            'page', 'chapter', '章', '節', '項'
        }
        
        # Single characters or very short text
        if len(text) <= 3:
            return True
            
        # Numbers (page numbers, etc.)
        if text.isdigit():
            return True
            
        # Common elements
        if text in common_elements:
            return True
            
        # Mostly punctuation
        if len([c for c in text if c.isalnum()]) < len(text) * 0.5:
            return True
            
        return False
    
    def delete_textbook(self, source_name):
        """Delete all documents from a specific textbook"""
        try:
            # Count documents before deletion
            before_stats = self.get_textbook_stats()
            before_count = before_stats['textbooks'].get(source_name, 0)
            
            if before_count == 0:
                return {'success': False, 'message': f'No documents found for source: {source_name}'}
            
            # Delete documents by source
            self.vector_store.collection.delete(where={"source": source_name})
            
            # Verify deletion
            after_stats = self.get_textbook_stats()
            after_count = after_stats['textbooks'].get(source_name, 0)
            
            return {
                'success': True,
                'message': f'Deleted {before_count - after_count} documents from {source_name}',
                'deleted_count': before_count - after_count
            }
        except Exception as e:
            return {'success': False, 'message': f'Error deleting textbook: {str(e)}'}
    
    def clean_duplicates(self, source_name=None):
        """Remove REAL duplicate content (processing errors), preserve natural language repetition"""
        try:
            # Get all documents with full content
            if source_name:
                all_docs = self.vector_store.collection.get(
                    where={"source": source_name},
                    include=['metadatas', 'documents']
                )
            else:
                all_docs = self.vector_store.collection.get(include=['metadatas', 'documents'])
            
            metadatas = all_docs['metadatas']
            documents = all_docs['documents']
            ids = all_docs['ids']  # ids are always included by default
            
            # Track substantial duplicate content only
            text_to_ids = {}
            duplicate_ids = []
            
            for i, (doc_text, meta) in enumerate(zip(documents, metadatas)):
                text = doc_text.strip()
                
                # Only process substantial text that could be a real duplicate
                if (len(text) > 10 and  # Substantial text
                    not self._is_common_element(text)):  # Not a common element
                    
                    if text in text_to_ids:
                        # This is a duplicate of substantial content
                        duplicate_ids.append(ids[i])
                    else:
                        # First occurrence - keep it
                        text_to_ids[text] = ids[i]
            
            if duplicate_ids:
                # Delete only REAL duplicates
                self.vector_store.collection.delete(ids=duplicate_ids)
                return {
                    'success': True,
                    'message': f'Removed {len(duplicate_ids)} processing duplicates (preserved natural repetition)',
                    'removed_count': len(duplicate_ids)
                }
            else:
                return {'success': True, 'message': 'No processing duplicates found - database is clean!'}
                
        except Exception as e:
            return {'success': False, 'message': f'Error cleaning duplicates: {str(e)}'}
    
    def get_png_stats(self):
        """Get statistics about PNG files in processed_docs directory"""
        try:
            import glob
            import os
            
            png_dir = "./processed_docs"
            # Get ALL PNG files, not just page_*.png
            png_files = glob.glob(os.path.join(png_dir, "*.png"))
            
            if not png_files:
                return {
                    'count': 0,
                    'size_gb': 0,
                    'size_mb': 0,
                    'message': 'No PNG files found'
                }
            
            # Calculate total size
            total_size_bytes = sum(os.path.getsize(f) for f in png_files)
            size_mb = total_size_bytes / (1024 * 1024)
            size_gb = total_size_bytes / (1024 * 1024 * 1024)
            
            return {
                'count': len(png_files),
                'size_gb': round(size_gb, 2),
                'size_mb': round(size_mb, 1),
                'message': f'Found {len(png_files)} PNG files',
                'files': png_files  # In case we need the list
            }
        except Exception as e:
            return {
                'count': 0,
                'size_gb': 0,
                'size_mb': 0,
                'message': f'Error getting PNG stats: {str(e)}'
            }
    
    def delete_png_files(self):
        """Delete all PNG files from processed_docs, preserving JSON files"""
        try:
            import glob
            import os
            
            png_dir = "./processed_docs"
            # Delete ALL PNG files, not just page_*.png
            png_files = glob.glob(os.path.join(png_dir, "*.png"))
            
            if not png_files:
                return {
                    'success': False,
                    'message': 'No PNG files to delete',
                    'deleted_count': 0
                }
            
            # Count and size before deletion
            count_before = len(png_files)
            size_before = sum(os.path.getsize(f) for f in png_files) / (1024 * 1024)  # MB
            
            # Delete each PNG file
            deleted_count = 0
            failed_files = []
            
            for png_file in png_files:
                try:
                    os.remove(png_file)
                    deleted_count += 1
                except Exception as e:
                    failed_files.append(png_file)
            
            if failed_files:
                return {
                    'success': False,
                    'message': f'Deleted {deleted_count}/{count_before} PNG files. Failed to delete {len(failed_files)} files.',
                    'deleted_count': deleted_count,
                    'failed_files': failed_files
                }
            else:
                return {
                    'success': True,
                    'message': f'Successfully deleted {deleted_count} PNG files ({size_before:.1f} MB freed)',
                    'deleted_count': deleted_count,
                    'size_freed_mb': size_before
                }
                
        except Exception as e:
            return {
                'success': False,
                'message': f'Error deleting PNG files: {str(e)}',
                'deleted_count': 0
            }

if __name__ == "__main__":
    db_mgr = DatabaseManager()
    stats = db_mgr.get_textbook_stats()
    
    print("=== Database Statistics ===")
    print(f"Total documents: {stats.get('total_documents', 'unknown')}")
    print(f"Duplicates found: {stats.get('duplicates', 'unknown')}")
    print("\nTextbooks:")
    for source, count in stats.get('textbooks', {}).items():
        print(f"  📚 {source}: {count:,} chunks")