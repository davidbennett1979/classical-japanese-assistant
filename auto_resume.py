#!/usr/bin/env python3
"""
Auto-resume PDF processing (no user prompts)
"""

import os
import glob
from pdf2image import convert_from_path
from vector_store import JapaneseVectorStore
from ocr_pipeline import JapaneseOCR
import logging
import sys

# Setup logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(message)s')
logger = logging.getLogger(__name__)

def auto_resume_processing(pdf_path):
    """Auto-resume processing without user prompts"""
    
    # Initialize components
    logger.info("Initializing components...")
    vector_store = JapaneseVectorStore()
    ocr = JapaneseOCR()
    
    # Find existing PNG files
    existing_pngs = sorted(glob.glob("processed_docs/page_*.png"))
    last_page_processed = len(existing_pngs)
    
    logger.info(f"Found {last_page_processed} existing PNG files")
    logger.info(f"Last processed page: {last_page_processed}")
    
    # Check if we need more PNG files
    try:
        logger.info(f"Checking PDF: {pdf_path}")
        test_images = convert_from_path(pdf_path, 300, first_page=1, last_page=1)
        all_images = convert_from_path(pdf_path, 300)
        total_pages = len(all_images)
        logger.info(f"PDF has {total_pages} total pages")
        
        if last_page_processed < total_pages:
            start_page = last_page_processed + 1
            logger.info(f"Converting pages {start_page} to {total_pages}...")
            
            remaining_images = convert_from_path(
                pdf_path, 
                300, 
                first_page=start_page,
                last_page=total_pages
            )
            
            for i, image in enumerate(remaining_images, start=start_page):
                page_path = f"processed_docs/page_{i:04d}.png"
                logger.info(f"Saving page {i}/{total_pages}...")
                image.save(page_path, 'PNG')
        else:
            logger.info("All pages already converted to PNG!")
            
    except Exception as e:
        logger.error(f"Error with PDF conversion: {e}")
        logger.info("Continuing with existing PNG files...")
    
    # Process with OCR starting from page 1 (database is empty)
    start_ocr_page = 1
    logger.info(f"Starting OCR from page {start_ocr_page} (database is empty)")
    
    all_pngs = sorted(glob.glob("processed_docs/page_*.png"))
    pngs_to_process = [p for p in all_pngs if int(os.path.basename(p).split('_')[1].split('.')[0]) >= start_ocr_page]
    
    logger.info(f"Processing {len(pngs_to_process)} pages with OCR...")
    
    processed_chunks = []
    failed_pages = []
    batch_size = 500
    
    for png_path in pngs_to_process:
        page_num = int(os.path.basename(png_path).split('_')[1].split('.')[0])
        logger.info(f"OCR processing page {page_num}...")
        
        try:
            text_data = ocr.extract_text_with_coordinates(png_path)
            
            for item in text_data:
                item['source_pdf'] = os.path.basename(pdf_path)
                item['page_number'] = page_num
            
            processed_chunks.extend(text_data)
            
            if len(processed_chunks) >= batch_size:
                logger.info(f"Adding {len(processed_chunks)} chunks to vector store...")
                chunks = vector_store.chunk_text(processed_chunks)
                vector_store.add_documents(chunks)
                processed_chunks = []
                
        except KeyboardInterrupt:
            logger.info("Interrupted by user. Saving progress...")
            if processed_chunks:
                chunks = vector_store.chunk_text(processed_chunks)
                vector_store.add_documents(chunks)
            return
            
        except Exception as e:
            logger.error(f"Failed to process page {page_num}: {e}")
            failed_pages.append(page_num)
            continue
    
    # Add remaining chunks
    if processed_chunks:
        logger.info(f"Adding final {len(processed_chunks)} chunks to vector store...")
        chunks = vector_store.chunk_text(processed_chunks)
        vector_store.add_documents(chunks)
    
    logger.info("=" * 50)
    logger.info("Processing complete!")
    if failed_pages:
        logger.warning(f"Failed pages: {failed_pages}")
    logger.info(f"Successfully processed from page {start_ocr_page} onwards")

if __name__ == "__main__":
    pdf_path = "/Users/davidbennett/Downloads/Classical Japanese - A Grammar by Haruo Shirane.pdf"
    logger.info("Starting auto-resume processing...")
    logger.info(f"PDF: {pdf_path}")
    logger.info(f"Existing PNGs: {len(glob.glob('processed_docs/page_*.png'))}")
    
    auto_resume_processing(pdf_path)