from google.cloud import vision
from google.oauth2 import service_account
from googleapiclient.discovery import build
from googleapiclient.http import MediaIoBaseDownload
import io
import os
from supabase import create_client
from datetime import datetime
import re

# Google Drive folder ID
DRIVE_FOLDER_ID = '1UxvmDE9IxiGE0r0RQFg8VhsDWl6n5Qa2'

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

def process_bills():
    print("\nStarting bill processing...")
    
    # Initialize services
    credentials = service_account.Credentials.from_service_account_file(
        'service_account.json',
        scopes=['https://www.googleapis.com/auth/drive.readonly']
    )
    
    drive_service = build('drive', 'v3', credentials=credentials)
    vision_client = vision.ImageAnnotatorClient(credentials=credentials)
    
    # Get list of processed files
    processed_files = supabase.table('pge_bills').select('source_file_id').execute()
    processed_ids = {record['source_file_id'] for record in processed_files.data}
    
    # List files in Drive folder
    print("Checking Google Drive folder for new bills...")
    results = drive_service.files().list(
        q=f"'{DRIVE_FOLDER_ID}' in parents and mimeType='application/pdf' and trashed=false",
        fields="files(id, name)"
    ).execute()
    
    files = results.get('files', [])
    if not files:
        print("No files found in the Drive folder.")
        return
        
    print(f"Found {len(files)} files in Drive folder")
    
    for file in files:
        file_id = file['id']
        if file_id in processed_ids:
            print(f"\nSkipping already processed file: {file['name']}")
            continue
            
        print(f"\nProcessing new file: {file['name']}")
        
        try:
            # Download PDF from Drive
            request = drive_service.files().get_media(fileId=file_id)
            file_content = io.BytesIO()
            downloader = MediaIoBaseDownload(file_content, request)
            done = False
            while done is False:
                _, done = downloader.next_chunk()
                
            # Store PDF in Supabase
            storage_path = f"bills/{file['name']}"
            print("Uploading PDF to Supabase storage...")
            supabase.storage.from_('bills').upload(
                storage_path,
                file_content.getvalue()
            )
            
            # Process with Google Vision
            print("Processing with OCR...")
            image = vision.Image(content=file_content.getvalue())
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
                'source_file_id': file_id,
                'source_filename': file['name']
            })
            
            # Store in Supabase
            print("Storing data in Supabase...")
            result = supabase.table('pge_bills').insert(extracted_data).execute()
            
            print(f"Successfully processed bill: {file['name']}")
            print(f"Account: {extracted_data.get('account_number')}")
            print(f"Amount: ${extracted_data.get('total_amount')}")
            print(f"Billing Period: {extracted_data.get('billing_period')}")
            
        except Exception as e:
            print(f"Error processing {file['name']}: {str(e)}")
            continue

if __name__ == '__main__':
    process_bills()
