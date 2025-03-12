import os
import json
import requests
import fitz  # PyMuPDF

def ocr_space_file(filename, overlay=False, api_key='K86742198888957', language='eng'):
    """ OCR.space API request with local file.
    :param filename: Your file path & name.
    :param overlay: Is OCR.space overlay required in your response.
                    Defaults to False.
    :param api_key: OCR.space API key.
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

def split_pdf(input_path, output_dir='split_pdfs', chunk_size=3):
    """Split a PDF into chunks of specified size"""
    # Create output directory if it doesn't exist
    if not os.path.exists(output_dir):
        os.makedirs(output_dir)
    
    # Get base filename without extension
    base_name = os.path.splitext(os.path.basename(input_path))[0]
    
    # Open the PDF
    doc = fitz.open(input_path)
    total_pages = len(doc)
    print(f"PDF has {total_pages} pages. Splitting into chunks of {chunk_size} pages.")
    
    # Calculate number of chunks
    num_chunks = (total_pages + chunk_size - 1) // chunk_size
    chunk_files = []
    
    # Split into chunks
    for i in range(num_chunks):
        start_page = i * chunk_size
        end_page = min((i + 1) * chunk_size - 1, total_pages - 1)
        
        # Create a new PDF for this chunk
        new_doc = fitz.open()
        for page_num in range(start_page, end_page + 1):
            new_doc.insert_pdf(doc, from_page=page_num, to_page=page_num)
        
        # Save the chunk
        output_path = os.path.join(output_dir, f"{base_name}_chunk{i+1}.pdf")
        new_doc.save(output_path)
        new_doc.close()
        
        chunk_files.append(output_path)
        print(f"Created chunk {i+1}: pages {start_page+1}-{end_page+1} -> {output_path}")
    
    doc.close()
    return chunk_files

def process_pdf_with_ocr_space(input_path, api_key='K86742198888957'):
    """Process a PDF with OCR.space, splitting if necessary"""
    # Get base filename without extension for unique output files
    base_name = os.path.splitext(os.path.basename(input_path))[0]
    
    # Split the PDF into chunks
    chunk_files = split_pdf(input_path)
    
    # Process each chunk
    all_results = []
    all_text = []
    
    for i, chunk_file in enumerate(chunk_files):
        print(f"\nProcessing chunk {i+1}/{len(chunk_files)}: {chunk_file}")
        ocr_result = ocr_space_file(chunk_file, api_key=api_key)
        
        # Save individual chunk results with unique filenames
        chunk_output_file = f"{base_name}_ocr_chunk{i+1}.json"
        with open(chunk_output_file, 'w') as f:
            json.dump(ocr_result, f, indent=4)
        print(f"Saved chunk result to {chunk_output_file}")
        
        # Extract text from this chunk
        chunk_text = ""
        if not ocr_result.get('IsErroredOnProcessing', True):
            for result in ocr_result.get('ParsedResults', []):
                chunk_text += result.get('ParsedText', '')
        
        all_results.append(ocr_result)
        all_text.append(chunk_text)
    
    # Combine all results
    combined_result = {
        "ChunkResults": all_results,
        "CombinedText": "\n\n".join(all_text)
    }
    
    # Save combined results with unique filenames
    combined_output_file = f"{base_name}_ocr_combined.json"
    with open(combined_output_file, 'w') as f:
        json.dump(combined_result, f, indent=4)
    print(f"\nSaved combined results to {combined_output_file}")
    
    # Save just the combined text
    text_output_file = f"{base_name}_ocr_text.txt"
    with open(text_output_file, 'w') as f:
        f.write(combined_result["CombinedText"])
    print(f"Saved extracted text to {text_output_file}")
    
    return combined_result, combined_output_file

def main():
    import sys
    
    # Check if a file was provided as a command-line argument
    if len(sys.argv) > 1:
        input_file = sys.argv[1]
    else:
        # Default file if none provided
        input_file = 'bills_to_process/2035custbill12112024.pdf'
    
    if not os.path.exists(input_file):
        print(f"Could not find {input_file}")
        return
    
    # Process the PDF and get the combined output file path
    result, combined_output_file = process_pdf_with_ocr_space(input_file)
    
    print("\nProcessing complete!")
    print("\nExtracted text preview:")
    # Print first 500 characters of the combined text
    print(result["CombinedText"][:500] + "...")
    
    # Run the formatting script on the combined output
    print("\nFormatting OCR results...")
    os.system(f"python format_ocr_results.py {combined_output_file}")

if __name__ == "__main__":
    main()
