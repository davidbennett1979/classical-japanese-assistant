#!/usr/bin/env python3
"""Debug script for PDF import issues"""

import sys
import os
import traceback
from ocr_pipeline import JapaneseOCR
from vector_store import JapaneseVectorStore

def test_pdf_import(pdf_path):
    """Test PDF import process step by step"""
    print(f"🔍 Testing PDF import for: {pdf_path}")
    
    if not os.path.exists(pdf_path):
        print(f"❌ PDF file not found: {pdf_path}")
        return False
    
    print(f"✅ PDF file exists: {os.path.getsize(pdf_path)} bytes")
    
    try:
        # Initialize OCR
        print("📝 Initializing OCR...")
        ocr = JapaneseOCR()
        print("✅ OCR initialized")
        
        # Test PDF processing
        print("🔄 Processing PDF...")
        ocr_data = []
        for page_data in ocr.process_pdf(pdf_path):
            if isinstance(page_data, str) and "Processing" in page_data:
                print(f"  📖 {page_data}")
            else:
                ocr_data.append(page_data)
                print(f"  📄 Page processed: {len(ocr_data)} pages total")
        
        print(f"✅ OCR completed: {len(ocr_data)} pages processed")
        
        if not ocr_data:
            print("❌ No OCR data extracted!")
            return False
        
        # Test chunking
        print("📝 Testing text chunking...")
        vector_store = JapaneseVectorStore()
        chunks = vector_store.chunk_text(ocr_data)
        print(f"✅ Chunking completed: {len(chunks)} chunks created")
        
        if not chunks:
            print("❌ No chunks created!")
            return False
        
        # Test vector store addition
        print("💾 Testing vector store addition...")
        initial_count = vector_store.collection.count()
        print(f"📊 Initial vector store count: {initial_count}")
        
        vector_store.add_documents(chunks[:5])  # Just test with first 5 chunks
        final_count = vector_store.collection.count()
        print(f"📊 Final vector store count: {final_count}")
        print(f"✅ Successfully added {final_count - initial_count} test chunks")
        
        return True
        
    except Exception as e:
        print(f"❌ Error during testing: {str(e)}")
        print("📍 Full traceback:")
        traceback.print_exc()
        return False

if __name__ == "__main__":
    if len(sys.argv) != 2:
        print("Usage: python debug_import.py <path_to_pdf>")
        print("Example: python debug_import.py '/path/to/grammar.pdf'")
        sys.exit(1)
    
    pdf_path = sys.argv[1]
    success = test_pdf_import(pdf_path)
    
    if success:
        print("🎉 Test completed successfully!")
    else:
        print("💥 Test failed!")
    
    sys.exit(0 if success else 1)