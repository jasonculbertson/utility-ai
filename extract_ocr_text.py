import os
import json
import fitz
import io
from PIL import Image
from process_bills_vision import ocr_space_file, extract_text_from_ocr_space

def extract_ocr_text(pdf_file, output_file=None, ocr_space_api_key='K86742198888957'):
    """Extract text from a PDF file using OCR.space API and save it to a text file."""
    print(f"Processing: {pdf_file}")
    
    # Set default output file name if not provided
    if output_file is None:
        output_file = os.path.splitext(os.path.basename(pdf_file))[0] + '_ocr_text.txt'
    
    # Convert PDF to images and extract text
    print("Converting PDF to images...")
    pdf_document = fitz.open(pdf_file)
    all_text = []
    
    print("Extracting text using OCR.space API...")
    for page_num in range(pdf_document.page_count):
        page = pdf_document[page_num]
        pix = page.get_pixmap(matrix=fitz.Matrix(2, 2))  # Increase resolution
        
        # Convert to PIL Image
        img = Image.frombytes("RGB", [pix.width, pix.height], pix.samples)
        
        # Save the image to a temporary file
        temp_img_path = f"temp_page_{page_num}.png"
        img.save(temp_img_path, format='PNG')
        
        # Use OCR.space API
        ocr_result = ocr_space_file(temp_img_path, api_key=ocr_space_api_key)
        page_text = extract_text_from_ocr_space(ocr_result)
        all_text.append(page_text)
        
        # Clean up temporary file
        try:
            os.remove(temp_img_path)
        except:
            pass
        
        print(f"Processed page {page_num + 1} of {pdf_document.page_count}")
    
    pdf_document.close()
    
    # Combine all text
    combined_text = '\n\n'.join(all_text)
    
    # Save to text file
    with open(output_file, 'w') as f:
        f.write(combined_text)
    
    print(f"OCR text saved to {output_file}")
    
    # Also save chunk files for compatibility with format_ocr_results.py
    chunk1_text = all_text[0] if len(all_text) > 0 else ""
    chunk2_text = all_text[1] if len(all_text) > 1 else ""
    
    # Save chunk 1 JSON
    chunk1_json = {
        "ParsedResults": [
            {"ParsedText": chunk1_text}
        ],
        "OCRExitCode": 1,
        "IsErroredOnProcessing": False
    }
    chunk1_file = os.path.splitext(os.path.basename(pdf_file))[0] + '_ocr_chunk1.json'
    with open(chunk1_file, 'w') as f:
        json.dump(chunk1_json, f, indent=4)
    
    # Save chunk 2 JSON
    chunk2_json = {
        "ParsedResults": [
            {"ParsedText": chunk2_text}
        ],
        "OCRExitCode": 1,
        "IsErroredOnProcessing": False
    }
    chunk2_file = os.path.splitext(os.path.basename(pdf_file))[0] + '_ocr_chunk2.json'
    with open(chunk2_file, 'w') as f:
        json.dump(chunk2_json, f, indent=4)
    
    # Save combined JSON
    combined_json = {
        "ParsedResults": [
            {"ParsedText": combined_text}
        ],
        "OCRExitCode": 1,
        "IsErroredOnProcessing": False
    }
    combined_file = os.path.splitext(os.path.basename(pdf_file))[0] + '_ocr_combined.json'
    with open(combined_file, 'w') as f:
        json.dump(combined_json, f, indent=4)
    
    print(f"OCR JSON files saved: {chunk1_file}, {chunk2_file}, {combined_file}")
    
    return output_file

def main():
    # Process the 3307custbill01022025.pdf file
    pdf_file = '/Users/jasonculbertson/Documents/GitHub/utilityAI/processed_bills/3307custbill01022025.pdf'
    extract_ocr_text(pdf_file)

if __name__ == '__main__':
    main()
