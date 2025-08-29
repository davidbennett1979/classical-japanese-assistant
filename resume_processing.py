#!/usr/bin/env python3
"""
Resume PDF processing from where it left off.
This script will continue from page 537 onwards.
"""

import os
import glob
from pdf2image import convert_from_path
from vector_store import JapaneseVectorStore
from ocr_pipeline import JapaneseOCR
import logging

# Setup logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(message)s')
logger = logging.getLogger(__name__)

def resume_processing(pdf_path):
    """Resume processing from where we left off"""
    
    # Initialize components
    logger.info("Initializing components...")
    vector_store = JapaneseVectorStore()
    ocr = JapaneseOCR()
    
    # Find existing PNG files to determine where we left off
    existing_pngs = sorted(glob.glob("processed_docs/page_*.png"))
    last_page_processed = len(existing_pngs)  # 536 files means we processed up to page 536
    
    logger.info(f"Found {last_page_processed} existing PNG files")
    logger.info(f"Last processed page: {last_page_processed}")
    
    # Convert remaining PDF pages to images
    logger.info(f"Loading PDF: {pdf_path}")
    logger.info("This may take a moment for large PDFs...")
    
    try:
        # Get total page count first
        images = convert_from_path(pdf_path, 300, first_page=1, last_page=1)
        
        # Now get all pages to check total count
        all_images = convert_from_path(pdf_path, 300)
        total_pages = len(all_images)
        logger.info(f"PDF has {total_pages} total pages")
        
        if last_page_processed >= total_pages:
            logger.info("All pages already converted to PNG!")
            process_existing = input("Process existing PNG files for OCR? (y/n): ")
            if process_existing.lower() != 'y':
                return
        else:
            # Convert remaining pages
            start_page = last_page_processed + 1
            logger.info(f"Converting pages {start_page} to {total_pages}...")
            
            remaining_images = convert_from_path(
                pdf_path, 
                300, 
                first_page=start_page,
                last_page=total_pages
            )
            
            # Save remaining pages as PNG
            for i, image in enumerate(remaining_images, start=start_page):
                page_path = f"processed_docs/page_{i:04d}.png"
                logger.info(f"Saving page {i}/{total_pages}...")
                image.save(page_path, 'PNG')
    
    except Exception as e:
        logger.error(f"Error loading PDF: {e}")
        process_existing = input("Continue with existing PNG files? (y/n): ")
        if process_existing.lower() != 'y':
            return
    
    # Now process PNG files with OCR starting from where the database left off
    # The error occurred at page 532, so let's start from there
    start_ocr_page = 532  # Or ask the user
    
    response = input(f"\nStart OCR from page {start_ocr_page}? Enter page number or press Enter to use {start_ocr_page}: ")
    if response.strip():
        start_ocr_page = int(response)
    
    # Get list of PNG files to process
    all_pngs = sorted(glob.glob("processed_docs/page_*.png"))
    pngs_to_process = [p for p in all_pngs if int(p.split('_')[1].split('.')[0]) >= start_ocr_page]
    
    logger.info(f"Processing {len(pngs_to_process)} pages with OCR...")
    
    # Process with OCR
    processed_chunks = []
    failed_pages = []
    batch_size = 500  # Add to vector store every 500 chunks
    
    for png_path in pngs_to_process:
        page_num = int(png_path.split('_')[1].split('.')[0])
        logger.info(f"OCR processing page {page_num}...")
        
        try:
            # Process the image
            text_data = ocr.process_image(png_path)
            
            # Add metadata
            for item in text_data:
                item['source_pdf'] = os.path.basename(pdf_path)
                item['page_number'] = page_num
            
            processed_chunks.extend(text_data)
            
            # Add to vector store in batches
            if len(processed_chunks) >= batch_size:
                logger.info(f"Adding {len(processed_chunks)} chunks to vector store...")
                chunks = vector_store.chunk_text(processed_chunks)
                vector_store.add_documents(chunks)
                processed_chunks = []  # Clear the buffer
                
        except KeyboardInterrupt:
            logger.info("\nInterrupted by user. Saving progress...")
            if processed_chunks:
                chunks = vector_store.chunk_text(processed_chunks)
                vector_store.add_documents(chunks)
            break
            
        except Exception as e:
            logger.error(f"Failed to process page {page_num}: {e}")
            failed_pages.append(page_num)
            continue
    
    # Add any remaining chunks
    if processed_chunks:
        logger.info(f"Adding final {len(processed_chunks)} chunks to vector store...")
        chunks = vector_store.chunk_text(processed_chunks)
        vector_store.add_documents(chunks)
    
    # Report results
    logger.info("=" * 50)
    logger.info("Processing complete!")
    if failed_pages:
        logger.warning(f"Failed pages: {failed_pages}")
    logger.info(f"Successfully processed from page {start_ocr_page} onwards")
    
    # Optional: Clean up PNG files
    response = input("\nDelete PNG files? (y/n): ")
    if response.lower() == 'y':
        logger.info("Cleaning up PNG files...")
        for png_file in all_pngs:
            try:
                os.remove(png_file)
            except:
                pass
        logger.info("PNG files removed")

if __name__ == "__main__":
    print("=" * 50)
    print("PDF PROCESSING RESUME SCRIPT")
    print("=" * 50)
    
    import sys
    if len(sys.argv) < 2:
        print("\nUsage: python resume_processing.py <pdf_path>")
        print("Example: python resume_processing.py 'my_textbook.pdf'")
        
        # Try to find PDF files
        pdfs = glob.glob("*.pdf")
        if pdfs:
            print(f"\nFound PDFs in current directory:")
            for i, pdf in enumerate(pdfs, 1):
                print(f"  {i}. {pdf}")
        sys.exit(1)
    
    pdf_path = sys.argv[1]
    
    if not os.path.exists(pdf_path):
        print(f"Error: PDF file not found: {pdf_path}")
        sys.exit(1)
    
    print(f"\nPDF to process: {pdf_path}")
    print(f"Existing PNG files: {len(glob.glob('processed_docs/page_*.png'))}")
    print("\nThis script will:")
    print("1. Convert any remaining PDF pages to PNG")
    print("2. Run OCR on pages starting from where the error occurred")
    print("3. Add the text to the vector database")
    print("=" * 50)
    
    proceed = input("\nProceed? (y/n): ")
    if proceed.lower() == 'y':
        resume_processing(pdf_path)
    else:
        print("Aborted.")