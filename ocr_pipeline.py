import cv2
import pytesseract
import numpy as np
from pdf2image import convert_from_path
from PIL import Image
import os
import json
import logging
from config import settings

class JapaneseOCR:
    def __init__(self, output_dir="./processed_docs"):
        self.output_dir = output_dir
        os.makedirs(output_dir, exist_ok=True)
        
    def preprocess_image(self, image):
        """Enhance image for better OCR accuracy"""
        # Convert to grayscale
        gray = cv2.cvtColor(np.array(image), cv2.COLOR_RGB2GRAY)
        
        # Apply threshold to get binary image
        _, binary = cv2.threshold(gray, 0, 255, cv2.THRESH_BINARY + cv2.THRESH_OTSU)
        
        # Denoise
        denoised = cv2.medianBlur(binary, 3)
        
        # Deskew - guard against empty coords
        coords = np.column_stack(np.where(denoised > 0))
        if coords.size == 0:
            # No text pixels found, skip deskewing but return PIL Image for consistency
            return Image.fromarray(denoised)
        angle = cv2.minAreaRect(coords)[-1]
        if angle < -45:
            angle = 90 + angle
        (h, w) = denoised.shape[:2]
        center = (w // 2, h // 2)
        M = cv2.getRotationMatrix2D(center, angle, 1.0)
        rotated = cv2.warpAffine(denoised, M, (w, h), flags=cv2.INTER_CUBIC, 
                                 borderMode=cv2.BORDER_REPLICATE)
        
        return Image.fromarray(rotated)
    
    def extract_text_with_coordinates(self, image_path):
        """Extract text with position data for citation purposes"""
        image = Image.open(image_path)
        processed = self.preprocess_image(image)
        
        # Use languages and PSM from settings
        custom_config = rf"--oem 3 --psm {settings.ocr_psm} -l {settings.ocr_langs}"
        
        # Get detailed OCR data
        data = pytesseract.image_to_data(processed, config=custom_config, 
                                        output_type=pytesseract.Output.DICT)
        
        # Structure the text with metadata
        structured_text = []
        current_paragraph = []
        last_y = 0
        
        min_conf = int(settings.ocr_min_conf)
        token_buffer = []
        for i in range(len(data['text'])):
            token = data['text'][i]
            if token and token.strip():
                try:
                    conf_val = int(float(data.get('conf', ['-1'])[i]))
                except Exception:
                    conf_val = -1
                if conf_val >= min_conf:
                    token_buffer.append(token.strip())
                x, y, w, h = data['left'][i], data['top'][i], data['width'][i], data['height'][i]
                
                # Detect paragraph breaks
                if last_y > 0 and abs(y - last_y) > 50:
                    if current_paragraph:
                        structured_text.append({
                            'type': 'paragraph',
                            'text': ' '.join(current_paragraph),
                            'page': os.path.basename(image_path),
                            'coordinates': {'x': x, 'y': y}
                        })
                        current_paragraph = []
                
                if token_buffer:
                    current_paragraph.append(' '.join(token_buffer))
                    token_buffer = []
                last_y = y
        
        # Add last paragraph
        if current_paragraph:
            structured_text.append({
                'type': 'paragraph',
                'text': ' '.join(current_paragraph),
                'page': os.path.basename(image_path)
            })
        
        return structured_text
    
    def process_pdf(self, pdf_path, start_page=None, end_page=None):
        """Convert PDF to images and extract text - yields progress updates"""
        logging.getLogger(__name__).info(f"Processing PDF: {pdf_path}, start={start_page}, end={end_page}")
        
        # Convert PDF to images - handle None values properly
        if start_page is not None or end_page is not None:
            yield f"Converting PDF pages {start_page or 'first'} to {end_page or 'last'}..."
            images = convert_from_path(pdf_path, 300, first_page=start_page, 
                                      last_page=end_page)
        else:
            # Process all pages when no range specified
            yield f"Converting entire PDF document..."
            images = convert_from_path(pdf_path, 300)
        
        total_pages = len(images)
        yield f"Starting OCR processing for {total_pages} pages..."
        
        all_text_data = []
        
        for i, image in enumerate(images):
            page_num = (start_page or 1) + i
            image_path = os.path.join(self.output_dir, f"page_{page_num:04d}.png")
            image.save(image_path, 'PNG')
            
            yield f"Processing page {page_num}/{page_num + total_pages - i - 1}..."
            logging.getLogger(__name__).info(f"Processing page {page_num}...")
            text_data = self.extract_text_with_coordinates(image_path)
            
            for item in text_data:
                item['source_pdf'] = os.path.basename(pdf_path)
                item['page_number'] = page_num
            
            all_text_data.extend(text_data)
            # Yield the page data so app can collect it
            yield text_data
        
        # Save structured data
        output_json = os.path.join(self.output_dir, 
                                  f"{os.path.basename(pdf_path)}.json")
        with open(output_json, 'w', encoding='utf-8') as f:
            json.dump(all_text_data, f, ensure_ascii=False, indent=2)
        
        logging.getLogger(__name__).info(f"Saved structured text to {output_json}")
        # Final yield to signal completion
        yield f"Completed processing {total_pages} pages"

# Usage
# ocr = JapaneseOCR()
# # For scanned PDFs
# text_data = ocr.process_pdf("your_textbook.pdf")
# # For individual images
# text_data = ocr.extract_text_with_coordinates("page_scan.jpg")
