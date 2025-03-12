import os
import requests
import json
from google.cloud import vision
from supabase import create_client
from datetime import datetime
import re

# Supabase setup - commented out to avoid initialization errors
# supabase = create_client(
#     "https://umuqydzeqqifiywqsxec.supabase.co",
#     "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJzdXBhYmFzZSIsInJlZiI6InVtdXF5ZHplcXFpZml5d3FzeGVjIiwicm9sZSI6InNlcnZpY2Vfcm9sZSIsImlhdCI6MTczODk4Mzk3MywiZXhwIjoyMDU0NTU5OTczfQ.Sf22jz_kuthKOJjpK9rfVs_s1X_ixGMKou3nL9_Aepw"
# )

def find_value_after_header(text, header, value_pattern=None, max_chars=100):
    """Find a value that appears after a specific header within a certain number of characters"""
    # Split text into lines and normalize spaces
    lines = [re.sub(r'\s+', ' ', line).strip() for line in text.split('\n')]
    header = re.sub(r'\s+', ' ', header).strip()
    
    # Find the line containing the header
    header_line = None
    for i, line in enumerate(lines):
        if header in line:
            header_line = line
            break
    
    if not header_line:
        print(f"Header '{header}' not found in text")
        return None
    
    # Look for the value in the text after the header on the same line
    header_pos = header_line.find(header)
    search_text = header_line[header_pos + len(header):].strip()
    
    # Print for debugging
    print(f"Found header line: '{header_line}'")
    print(f"Searching in: '{search_text}'")
    
    # Try different patterns if no specific pattern is provided
    patterns = [
        r'^\$\s*(\d+\.\d{2})',  # Matches $ 379.02 at start
        r'^-\$?\s*(\d+\.\d{2})',  # Matches -379.02 or -$ 379.02 at start
        r'^\s*\$\s*(\d+\.\d{2})',  # Matches with leading space
        r'^\s*-\s*(\d+\.\d{2})',  # Matches negative with leading space
        r'\$\s*(\d+\.\d{2})',  # Matches anywhere
        r'-\s*(\d+\.\d{2})'  # Matches negative anywhere
    ] if value_pattern is None else [value_pattern]
    
    for pattern in patterns:
        match = re.search(pattern, search_text)
        if match:
            value = match.group(1)
            print(f"Found match with pattern '{pattern}': {value}")
            # If the pattern starts with a negative sign or the text before the match contains a negative sign
            if pattern.startswith('^-') or pattern.startswith(r'^\s*-') or search_text[:match.start()].strip().endswith('-'):
                return str(-float(value.replace('$', '').replace(' ', '')))
            return value.replace('$', '').replace(' ', '')
    
    print("No matching patterns found")
    return None
    
    return None

def extract_bill_data(text):
    """Extract data from bill text using known section headers"""
    # Define known section headers and their expected values
    sections = {
        'previous_amount': {
            'header': 'Amount Due on Previous Statement',
            'pattern': None
        },
        'payments_received': {
            'header': 'Payment(s) Received Since Last Statement',
            'pattern': None
        },
        'unpaid_balance': {
            'header': 'Previous Unpaid Balance',
            'pattern': None
        },
        'total_amount': {
            'header': 'Total Amount Due',
            'pattern': None
        }
    }
    
    extracted_data = {}
    # Process each section
    for field, section_info in sections.items():
        print(f"\nSearching for {field} using header: {section_info['header']}")
        value = find_value_after_header(
            text,
            section_info['header'],
            section_info['pattern']
        )
        if value:
            extracted_data[field] = value
            print(f"Found value: {value}")
        else:
            extracted_data[field] = None
            print("No value found")
    
    return extracted_data

def ocr_space_file(filename, overlay=False, api_key='K86742198888957', language='eng'):
    """ OCR.space API request with local file.
        Python3.5 - not tested on 2.7
    :param filename: Your file path & name.
    :param overlay: Is OCR.space overlay required in your response.
                    Defaults to False.
    :param api_key: OCR.space API key.
                    Defaults to 'helloworld'. Get your own API key from https://ocr.space/
    :param language: Language code to be used in OCR.
                    Defaults to 'eng'.
    :return: Result in JSON format.
    """

    payload = {'isOverlayRequired': overlay,
               'apikey': api_key,
               'language': language,
               }
    with open(filename, 'rb') as f:
        r = requests.post('https://api.ocr.space/parse/image',
                          files={filename: f},
                          data=payload,
                          )
    return r.json()

def ocr_space_url(url, overlay=False, api_key='K86742198888957', language='eng'):
    """ OCR.space API request with remote file.
        Python3.5 - not tested on 2.7
    :param url: Image url.
    :param overlay: Is OCR.space overlay required in your response.
                    Defaults to False.
    :param api_key: OCR.space API key.
                    Defaults to 'helloworld'. Get your own API key from https://ocr.space/
    :param language: Language code to be used in OCR.
                    Defaults to 'eng'.
    :return: Result in JSON format.
    """

    payload = {'url': url,
               'isOverlayRequired': overlay,
               'apikey': api_key,
               'language': language,
               }
    r = requests.post('https://api.ocr.space/parse/image',
                      data=payload,
                      )
    return r.json()

def extract_text_from_ocr_space(ocr_result):
    """Extract text from OCR.space API result"""
    if ocr_result.get('IsErroredOnProcessing', False):
        print(f"Error: {ocr_result.get('ErrorMessage', 'Unknown error')}")
        return ""
    
    parsed_results = ocr_result.get('ParsedResults', [])
    if not parsed_results:
        return ""
    
    # Extract text from all parsed results
    all_text = []
    for result in parsed_results:
        text = result.get('ParsedText', '').strip()
        if text:
            all_text.append(text)
    
    return '\n'.join(all_text)

def process_bills(use_ocr_space=False, ocr_space_api_key='K86742198888957'):
    print("\nStarting bill processing...")
    
    # Initialize Vision client (only if using Google Cloud Vision)
    client = None
    if not use_ocr_space:
        client = vision.ImageAnnotatorClient()
    
    # Process files in bills_to_process directory
    bills_dir = 'bills_to_process'
    if not os.path.exists(bills_dir):
        os.makedirs(bills_dir)
        print(f"\nCreated {bills_dir} directory. Please put your PDF bills in this folder.")
        return
        
    files = [f for f in os.listdir(bills_dir) if f.endswith('.pdf')]
    if not files:
        print(f"\nNo PDF files found in {bills_dir}. Please add your bills there.")
        return
        
    print(f"\nFound {len(files)} files to process")
    
    for filename in files:
        print(f"\nProcessing: {filename}")
        file_path = os.path.join(bills_dir, filename)
        
        try:
            # Convert PDF to images and extract text
            print("Converting PDF to images...")
            import fitz
            import io
            from PIL import Image
            
            pdf_document = fitz.open(file_path)
            all_text = []
            
            if use_ocr_space:
                print("Extracting text using OCR.space API...")
            else:
                print("Extracting text using Google Cloud Vision...")
            for page_num in range(pdf_document.page_count):
                page = pdf_document[page_num]
                pix = page.get_pixmap(matrix=fitz.Matrix(2, 2))  # Increase resolution
                
                # Convert to PIL Image
                img = Image.frombytes("RGB", [pix.width, pix.height], pix.samples)
                
                # Save the image to a temporary file if using OCR.space
                if use_ocr_space:
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
                else:
                    # Convert to bytes for Google Cloud Vision
                    img_byte_arr = io.BytesIO()
                    img.save(img_byte_arr, format='PNG')
                    img_byte_arr = img_byte_arr.getvalue()
                    
                    # Create vision image and detect text with layout analysis
                    vision_image = vision.Image(content=img_byte_arr)
                    response = client.document_text_detection(image=vision_image)
                    
                    if response.error.message:
                        raise Exception(response.error.message)
                    
                    # Extract text with layout information
                    page_text = []
                    for page in response.full_text_annotation.pages:
                        for block in page.blocks:
                            for paragraph in block.paragraphs:
                                para_text = ''
                                para_bounds = paragraph.bounding_box
                                # Get the vertical position (y-coordinate) of the paragraph
                                y_pos = sum(vertex.y for vertex in para_bounds.vertices) / 4
                                
                                for word in paragraph.words:
                                    word_text = ''.join([symbol.text for symbol in word.symbols])
                                    para_text += word_text + ' '
                                
                                # Store text with its position
                                page_text.append((para_text.strip(), y_pos))
                    
                    # Sort by vertical position and join
                    page_text.sort(key=lambda x: x[1])
                    all_text.append('\n'.join(text for text, _ in page_text))
                print(f"Processed page {page_num + 1} of {pdf_document.page_count}")
            
            pdf_document.close()
            
            # Only use the first page for account summary values
            first_page_text = all_text[0] if all_text else ''
            print("\nFirst page text:")
            print(first_page_text)
            print("\n---End of first page text---\n")
            
            # Use first page text for extraction
            text = first_page_text
            
            # Store PDF in Supabase - commented out to avoid errors
            storage_path = f"bills/{filename}"
            print("Skipping Supabase storage upload for testing...")
            # try:
            #     with open(file_path, 'rb') as pdf_file:
            #         content = pdf_file.read()
            #         supabase.storage.from_('bills').upload(
            #             storage_path,
            #             content
            #         )
            # except Exception as e:
            #     if 'Duplicate' in str(e):
            #         print("File already exists in storage, continuing...")
            #     else:
            #         raise e
            
            # Extract and store data
            print("Extracting bill data...")
            extracted_data = extract_bill_data(text)
            
            # Add metadata
            extracted_data.update({
                'storage_path': storage_path,
                'processed_at': datetime.utcnow().isoformat(),
                'source_filename': filename
            })
            
            # Store in Supabase - commented out to avoid errors
            print("Skipping Supabase database storage for testing...")
            # result = supabase.table('pge_bills').insert(extracted_data).execute()
            
            print(f"Successfully processed bill: {filename}")
            print(f"Previous Amount: ${extracted_data.get('previous_amount')}")
            print(f"Payments Received: ${extracted_data.get('payments_received')}")
            print(f"Unpaid Balance: ${extracted_data.get('unpaid_balance')}")
            print(f"Total Amount: ${extracted_data.get('total_amount')}")
            
            # Save the extracted data to a JSON file instead of using Supabase
            output_dir = 'extracted_data'
            if not os.path.exists(output_dir):
                os.makedirs(output_dir)
                
            # Save extracted data to JSON file
            output_file = os.path.join(output_dir, f"{os.path.splitext(filename)[0]}.json")
            with open(output_file, 'w') as f:
                json.dump(extracted_data, f, indent=4)
            print(f"Saved extracted data to {output_file}")
            
            # Move processed file to done folder
            done_dir = 'processed_bills'
            if not os.path.exists(done_dir):
                os.makedirs(done_dir)
            os.rename(file_path, os.path.join(done_dir, filename))
            
        except Exception as e:
            print(f"Error processing {filename}: {str(e)}")
            continue

if __name__ == '__main__':
    # Set to True to use OCR.space API, False to use Google Cloud Vision
    use_ocr_space = True
    
    # Using the provided OCR.space API key
    ocr_space_api_key = 'K86742198888957'
    
    process_bills(use_ocr_space=use_ocr_space, ocr_space_api_key=ocr_space_api_key)
