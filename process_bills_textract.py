import os
import textract
from supabase import create_client
from datetime import datetime
import re

# Supabase setup
supabase = create_client(
    "https://umuqydzeqqifiywqsxec.supabase.co",
    "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJzdXBhYmFzZSIsInJlZiI6InVtdXF5ZHplcXFpZml5d3FzeGVjIiwicm9sZSI6InNlcnZpY2Vfcm9sZSIsImlhdCI6MTczODk4Mzk3MywiZXhwIjoyMDU0NTU5OTczfQ.Sf22jz_kuthKOJjpK9rfVs_s1X_ixGMKou3nL9_Aepw"
)

def extract_bill_data(text):
    """Extract data from PDF text using regex patterns"""
    patterns = {
        'previous_amount': r'Previous Amount[^$]*\$(\d+\.\d{2})',
        'payments_received': r'Payment\(s\) Received[^$]*\$(\d+\.\d{2})',
        'unpaid_balance': r'Previous Unpaid Balance[^$]*\$(\d+\.\d{2})',
        'electric_delivery': r'Electric Delivery[^$]*\$(\d+\.\d{2})',
        'electric_generation': r'Electric Generation[^$]*\$(\d+\.\d{2})',
        'gas_charges': r'Gas Charges[^$]*\$(\d+\.\d{2})',
        'total_amount': r'Total Amount[^$]*\$(\d+\.\d{2})',
        'due_date': r'Due Date:\s*(\d{2}/\d{2}/\d{4})',
    }
    
    extracted_data = {}
    for field, pattern in patterns.items():
        print(f"\nSearching for {field} using pattern: {pattern}")
        match = re.search(pattern, text)
        if match:
            extracted_data[field] = match.group(1)
            print(f"Found match: {match.group(0)}")
        else:
            extracted_data[field] = None
            print("No match found")
            
    return extracted_data

def process_bills():
    print("\nStarting bill processing...")
    
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
            # Extract text from PDF
            print("Extracting text from PDF...")
            text = textract.process(file_path, method='pdfminer').decode('utf-8')
            
            # Clean up text
            text = re.sub(r'[^a-zA-Z0-9$.,/ ]', ' ', text)  # Remove special chars except those needed
            text = re.sub(r'\s+', ' ', text)  # Normalize whitespace
            text = text.strip()
            
            print("\nExtracted text:")
            print(text)
            print("\n---End of extracted text---\n")
            
            # Store PDF in Supabase
            with open(file_path, 'rb') as pdf_file:
                content = pdf_file.read()
                storage_path = f"bills/{filename}"
                print("Uploading PDF to Supabase storage...")
                try:
                    supabase.storage.from_('bills').upload(
                        storage_path,
                        content
                    )
                except Exception as e:
                    if 'Duplicate' in str(e):
                        print("File already exists in storage, continuing...")
                    else:
                        raise e
            
            # Extract and store data
            print("Extracting bill data...")
            extracted_data = extract_bill_data(text)
            
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
            print(f"Previous Amount: ${extracted_data.get('previous_amount')}")
            print(f"Payments Received: ${extracted_data.get('payments_received')}")
            print(f"Electric Delivery: ${extracted_data.get('electric_delivery')}")
            print(f"Electric Generation: ${extracted_data.get('electric_generation')}")
            print(f"Gas Charges: ${extracted_data.get('gas_charges')}")
            print(f"Total Amount: ${extracted_data.get('total_amount')}")
            print(f"Due Date: {extracted_data.get('due_date')}")
            
            # Move processed file to done folder
            done_dir = 'processed_bills'
            if not os.path.exists(done_dir):
                os.makedirs(done_dir)
            os.rename(file_path, os.path.join(done_dir, filename))
            
        except Exception as e:
            print(f"Error processing {filename}: {str(e)}")
            continue

if __name__ == '__main__':
    process_bills()
