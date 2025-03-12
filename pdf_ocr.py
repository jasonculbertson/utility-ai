import os
from google.cloud import vision
from pdf2image import convert_from_path
from PIL import Image
import io
import json
from typing import List, Dict, Any
from dotenv import load_dotenv

class PDFOCRProcessor:
    def __init__(self):
        """Initialize the Google Cloud Vision client"""
        load_dotenv()
        credentials_path = os.getenv('GOOGLE_APPLICATION_CREDENTIALS')
        if not credentials_path:
            raise ValueError("GOOGLE_APPLICATION_CREDENTIALS environment variable is not set")
        if not os.path.exists(credentials_path):
            raise FileNotFoundError(f"Credentials file not found at: {credentials_path}")
        self.client = vision.ImageAnnotatorClient()

    def convert_pdf_to_images(self, pdf_path: str) -> List[Image.Image]:
        """Convert PDF pages to images
        
        Args:
            pdf_path: Path to the PDF file
            
        Returns:
            List of PIL Image objects, one per page
        """
        try:
            # Convert PDF to images
            images = convert_from_path(pdf_path)
            print(f"Successfully converted PDF to {len(images)} images")
            return images
        except Exception as e:
            print(f"Error converting PDF to images: {str(e)}")
            return []

    def process_image(self, image: Image.Image) -> Dict[str, Any]:
        """Process a single image with Google Cloud Vision API
        
        Args:
            image: PIL Image object
            
        Returns:
            Dictionary containing OCR results
        """
        try:
            # Convert PIL image to bytes
            img_byte_arr = io.BytesIO()
            image.save(img_byte_arr, format='PNG')
            img_byte_arr = img_byte_arr.getvalue()

            # Create image object
            image = vision.Image(content=img_byte_arr)

            # Perform OCR
            response = self.client.document_text_detection(image=image)
            
            if response.error.message:
                raise Exception(
                    '{}\nFor more info on error messages, check: '
                    'https://cloud.google.com/apis/design/errors'.format(
                        response.error.message))

            return {
                'full_text': response.full_text_annotation.text,
                'pages': [{
                    'blocks': [{
                        'text': block.text,
                        'confidence': block.confidence,
                        'bounding_box': [[vertex.x, vertex.y] for vertex in block.bounding_box.vertices]
                    } for block in page.blocks]
                } for page in response.pages]
            }

        except Exception as e:
            print(f"Error processing image with Vision API: {str(e)}")
            return {}

    def process_pdf(self, pdf_path: str, output_path: str = None) -> List[Dict[str, Any]]:
        """Process entire PDF and extract text using OCR
        
        Args:
            pdf_path: Path to the PDF file
            output_path: Optional path to save JSON results
            
        Returns:
            List of dictionaries containing OCR results for each page
        """
        # Convert PDF to images
        images = self.convert_pdf_to_images(pdf_path)
        if not images:
            return []

        # Process each image
        results = []
        for i, image in enumerate(images):
            print(f"Processing page {i+1}/{len(images)}")
            page_result = self.process_image(image)
            if page_result:
                results.append(page_result)

        # Save results if output path provided
        if output_path and results:
            with open(output_path, 'w') as f:
                json.dump(results, f, indent=2)
            print(f"Results saved to {output_path}")

        return results

    def extract_data_by_pattern(self, results: List[Dict[str, Any]], patterns: Dict[str, str]) -> Dict[str, str]:
        """Extract specific data using regex patterns
        
        Args:
            results: List of OCR results from process_pdf
            patterns: Dictionary of field names and their regex patterns
            
        Returns:
            Dictionary of extracted fields and their values
        """
        import re
        
        extracted_data = {}
        
        # Combine all text from all pages
        full_text = "\n".join(result['full_text'] for result in results)
        
        # Extract data using patterns
        for field_name, pattern in patterns.items():
            match = re.search(pattern, full_text)
            if match:
                extracted_data[field_name] = match.group(1)
            else:
                extracted_data[field_name] = None
                
        return extracted_data

def main():
    # Example usage
    processor = PDFOCRProcessor()
    
    # Replace with your PDF path
    pdf_path = "example.pdf"
    
    # Process the PDF
    results = processor.process_pdf(pdf_path, "ocr_results.json")
    
    # Example patterns to extract specific data
    patterns = {
        'invoice_number': r'Invoice\s*#?\s*:\s*([A-Z0-9-]+)',
        'date': r'Date\s*:\s*(\d{1,2}[-/]\d{1,2}[-/]\d{2,4})',
        'total_amount': r'Total\s*:\s*\$?\s*([\d,]+\.?\d*)',
    }
    
    # Extract specific data
    extracted_data = processor.extract_data_by_pattern(results, patterns)
    print("\nExtracted Data:")
    print(json.dumps(extracted_data, indent=2))

if __name__ == "__main__":
    main()
