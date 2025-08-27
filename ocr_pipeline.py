import cv2
import pytesseract
import numpy as np
from pdf2image import convert_from_path
from PIL import Image
import os
import json

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
            # No text pixels found, skip deskewing
            return denoised
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
        
        # Use both Japanese and English OCR
        custom_config = r'--oem 3 --psm 6 -l jpn+eng'
        
        # Get detailed OCR data
        data = pytesseract.image_to_data(processed, config=custom_config, 
                                        output_type=pytesseract.Output.DICT)
        
        # Structure the text with metadata
        structured_text = []
        current_paragraph = []
        last_y = 0
        
        for i in range(len(data['text'])):
            if data['text'][i].strip():
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
                
                current_paragraph.append(data['text'][i])
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
        """Convert PDF to images and extract text"""
        print(f"Processing PDF: {pdf_path}")
        
        # Convert PDF to images
        images = convert_from_path(pdf_path, 300, first_page=start_page, 
                                  last_page=end_page)
        
        all_text_data = []
        
        for i, image in enumerate(images):
            page_num = (start_page or 1) + i
            image_path = os.path.join(self.output_dir, f"page_{page_num:04d}.png")
            image.save(image_path, 'PNG')
            
            print(f"Processing page {page_num}...")
            text_data = self.extract_text_with_coordinates(image_path)
            
            for item in text_data:
                item['source_pdf'] = os.path.basename(pdf_path)
                item['page_number'] = page_num
            
            all_text_data.extend(text_data)
        
        # Save structured data
        output_json = os.path.join(self.output_dir, 
                                  f"{os.path.basename(pdf_path)}.json")
        with open(output_json, 'w', encoding='utf-8') as f:
            json.dump(all_text_data, f, ensure_ascii=False, indent=2)
        
        print(f"Saved structured text to {output_json}")
        return all_text_data

# Usage
# ocr = JapaneseOCR()
# # For scanned PDFs
# text_data = ocr.process_pdf("your_textbook.pdf")
# # For individual images
# text_data = ocr.extract_text_with_coordinates("page_scan.jpg")

