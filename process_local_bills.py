from google.cloud import vision
import os
from supabase import create_client
from datetime import datetime
import re

# Supabase setup
supabase = create_client(
    "https://umuqydzeqqifiywqsxec.supabase.co",
    "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJzdXBhYmFzZSIsInJlZiI6InVtdXF5ZHplcXFpZml5d3FzeGVjIiwicm9sZSI6InNlcnZpY2Vfcm9sZSIsImlhdCI6MTczODk4Mzk3MywiZXhwIjoyMDU0NTU5OTczfQ.Sf22jz_kuthKOJjpK9rfVs_s1X_ixGMKou3nL9_Aepw"
)

def extract_bill_data(text):
    """Extract data from OCR text using regex patterns"""
    patterns = {
        'account_number': r'Account Number:\s*(\d{10})',
        'service_address': r'Service For:\s*(.*?)(?=\n)',
        'billing_period': r'Billing period:\s*(\w+\s+\d{1,2},\s*\d{4})\s*to\s*(\w+\s+\d{1,2},\s*\d{4})',
        'billing_days': r'Number of days:\s*(\d+)',
        'total_kwh': r'Total\s+Usage:\s*([\d,]+)\s*kWh',
        'total_amount': r'Total\s+Amount\s+Due:\s*\$?([\d,]+\.?\d*)',
    }
    
    extracted_data = {}
    for field, pattern in patterns.items():
        match = re.search(pattern, text)
        if match:
            extracted_data[field] = match.group(1)
        else:
            extracted_data[field] = None
            
    return extracted_data

def process_local_bills():
    print("\nStarting bill processing...")
    
    # Initialize Vision client
    vision_client = vision.ImageAnnotatorClient()
    
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
            # Read PDF file
            with open(file_path, 'rb') as pdf_file:
                content = pdf_file.read()
                
            # Store PDF in Supabase
            storage_path = f"bills/{filename}"
            print("Uploading PDF to Supabase storage...")
            supabase.storage.from_('bills').upload(
                storage_path,
                content
            )
            
            # Process with Google Vision
            print("Processing with OCR...")
            image = vision.Image(content=content)
            response = vision_client.document_text_detection(image=image)
            
            if response.error.message:
                raise Exception(f"Error processing file: {response.error.message}")
                
            # Extract and store data
            print("Extracting bill data...")
            extracted_data = extract_bill_data(response.full_text_annotation.text)
            
            # Add metadata
            extracted_data.update({
                'storage_path': storage_path,
                'processed_at': datetime.utcnow().isoformat(),
                'source_filename': filename
            })
            
            # Store in Supabase
            print("Storing data in Supabase...")
            result = supabase.table('pge_bills').insert(extracted_data).execute()
            
            print(f"Successfully processed bill: {filename}")
            print(f"Account: {extracted_data.get('account_number')}")
            print(f"Amount: ${extracted_data.get('total_amount')}")
            print(f"Billing Period: {extracted_data.get('billing_period')}")
            
            # Move processed file to done folder
            done_dir = 'processed_bills'
            if not os.path.exists(done_dir):
                os.makedirs(done_dir)
            os.rename(file_path, os.path.join(done_dir, filename))
            
        except Exception as e:
            print(f"Error processing {filename}: {str(e)}")
            continue

if __name__ == '__main__':
    process_local_bills()
