import functions_framework
from google.cloud import vision
from google.cloud import storage
import io
import os
from supabase import create_client, Client
from datetime import datetime
import re
import json
import logging

# Configure logging
logging.basicConfig(level=logging.INFO)

def initialize_drive_service():
    """Initialize Google Drive service"""
    credentials = service_account.Credentials.from_service_account_file(
        'google_credentials.json',
        scopes=['https://www.googleapis.com/auth/drive.readonly']
    )
    return build('drive', 'v3', credentials=credentials)

def download_file(service, file_id):
    """Download a file from Google Drive"""
    request = service.files().get_media(fileId=file_id)
    file = io.BytesIO()
    downloader = MediaIoBaseDownload(file, request)
    done = False
    while done is False:
        _, done = downloader.next_chunk()
    return file.getvalue()

def extract_bill_data(text):
    """Extract data from OCR text using regex patterns"""
    patterns = {
        # Basic Info
        'account_number': r'Account Number:\s*(\d{10})',
        'service_address': r'Service For:\s*(.*?)(?=\n)',
        'billing_period': r'Billing period:\s*(\w+\s+\d{1,2},\s*\d{4})\s*to\s*(\w+\s+\d{1,2},\s*\d{4})',
        'billing_days': r'Number of days:\s*(\d+)',
        
        # Usage Data
        'total_kwh': r'Total\s+Usage:\s*([\d,]+)\s*kWh',
        'peak_kwh': r'Peak:\s*([\d,]+)\s*kWh',
        'off_peak_kwh': r'Off-Peak:\s*([\d,]+)\s*kWh',
        'tier1_kwh': r'Tier\s*1\s*Usage:\s*([\d,]+)\s*kWh',
        'tier2_kwh': r'Tier\s*2\s*Usage:\s*([\d,]+)\s*kWh',
        'tier3_kwh': r'Tier\s*3\s*Usage:\s*([\d,]+)\s*kWh',
        
        # Rate Plan Info
        'rate_plan': r'Rate Schedule:\s*([\w-]+)',
        'peak_rate': r'Peak\s*Rate:\s*\$?([\d.]+)',
        'off_peak_rate': r'Off-Peak\s*Rate:\s*\$?([\d.]+)',
        'tier1_rate': r'Tier\s*1\s*Rate:\s*\$?([\d.]+)',
        'tier2_rate': r'Tier\s*2\s*Rate:\s*\$?([\d.]+)',
        'tier3_rate': r'Tier\s*3\s*Rate:\s*\$?([\d.]+)',
        
        # Charges and Adjustments
        'base_electric_charges': r'Electric\s+Delivery\s+Charges:\s*\$?([\d,]+\.?\d*)',
        'generation_credits': r'Generation\s+Credit:\s*-?\$?([\d,]+\.?\d*)',
        'dcare_discount': r'CARE\s+Discount:\s*-?\$?([\d,]+\.?\d*)',
        'taxes_and_surcharges': r'Taxes\s+and\s+Surcharges:\s*\$?([\d,]+\.?\d*)',
        'minimum_charges': r'Minimum\s+Charge:\s*\$?([\d,]+\.?\d*)',
        'total_amount': r'Total\s+Amount\s+Due:\s*\$?([\d,]+\.?\d*)',
    }
    
    extracted_data = {}
    for field, pattern in patterns.items():
        match = re.search(pattern, text)
        if match:
            extracted_data[field] = match.group(1).strip()
        else:
            extracted_data[field] = None
            
    return extracted_data

@functions_framework.cloud_event
def process_storage_file(cloud_event):
    """Process a new file when it's uploaded to Cloud Storage"""
    try:
        logging.info('Starting file processing')
        logging.info(f'Event: {cloud_event.data}')
        
        data = cloud_event.data
        bucket_name = data['bucket']
        file_name = data['name']
        
        # Only process PDF files
        if not file_name.lower().endswith('.pdf'):
            logging.info(f"Skipping non-PDF file: {file_name}")
            return
            
        logging.info(f'Processing file {file_name} from bucket {bucket_name}')
    
        # Initialize services
        logging.info('Initializing services...')
        drive_service = initialize_drive_service()
        vision_client = vision.ImageAnnotatorClient()
        
        # Initialize Supabase
        supabase_url = os.environ.get('SUPABASE_URL')
        supabase_key = os.environ.get('SUPABASE_SERVICE_KEY')
        
        if not supabase_url or not supabase_key:
            raise ValueError('Supabase credentials not found in environment variables')
            
        logging.info('Initializing Supabase client...')
        supabase = create_client(supabase_url, supabase_key)
        logging.info('Supabase client initialized')
        
        # Get the file from Cloud Storage
        logging.info('Getting file from Cloud Storage...')
        storage_client = storage.Client()
        bucket = storage_client.bucket(bucket_name)
        blob = bucket.blob(file_name)
        file_content = blob.download_as_bytes()
        logging.info('File downloaded from Cloud Storage')
        
        # Store in Supabase storage
        logging.info('Uploading to Supabase storage...')
        storage_path = f"bills/{file_name}"
        
        supabase.storage.from_('bills').upload(
            storage_path,
            file_content
        )
        logging.info('File uploaded to Supabase storage')
        
        # Process with Google Vision
        logging.info('Processing with Google Vision OCR...')
        vision_client = vision.ImageAnnotatorClient()
        image = vision.Image(content=file_content)
        response = vision_client.document_text_detection(image=image)
        
        if response.error.message:
            raise Exception(f"Error processing file: {response.error.message}")
            
        logging.info('OCR processing complete')
            
        # Extract bill data
        logging.info('Extracting bill data...')
        extracted_data = extract_bill_data(response.full_text_annotation.text)
        
        # Add metadata
        extracted_data.update({
            'storage_path': storage_path,
            'processed_at': datetime.utcnow().isoformat(),
            'source_filename': file_name,
            'source_bucket': bucket_name
        })
        logging.info('Data extraction complete')
        
        # Store in Supabase
        logging.info('Storing data in Supabase...')
        result = supabase.table('pge_bills').insert(extracted_data).execute()
        
        logging.info(f"Successfully processed bill. Record ID: {result.data[0]['id']}")
        return result.data[0]
        
    except Exception as e:
        logging.error(f"Error processing file {file_name}: {str(e)}")
        raise
