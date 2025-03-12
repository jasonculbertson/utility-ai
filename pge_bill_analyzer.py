import os
from google.cloud import vision
# Google Vision can handle PDFs directly
from PIL import Image
import io
import json
from typing import List, Dict, Any
from dotenv import load_dotenv
from supabase import create_client, Client
import base64
from datetime import datetime
import re

class PGEBillAnalyzer:
    def __init__(self):
        """Initialize the Google Cloud Vision client and Supabase client"""
        load_dotenv()
        
        # Initialize Google Vision
        self.vision_client = vision.ImageAnnotatorClient()
        
        # Initialize Supabase with service role key for admin access
        supabase_url = os.getenv("SUPABASE_URL")
        supabase_key = os.getenv("SUPABASE_SERVICE_KEY")
        if not supabase_url or not supabase_key:
            raise ValueError("Supabase credentials not found in environment variables")
        self.supabase: Client = create_client(supabase_url, supabase_key)

    async def store_bill_in_supabase(self, pdf_path: str) -> str:
        """Store PDF bill in Supabase storage
        
        Args:
            pdf_path: Path to the PDF file
            
        Returns:
            storage_path: Path where the file is stored in Supabase
        """
        try:
            # Read PDF file
            with open(pdf_path, 'rb') as f:
                file_contents = f.read()
            
            # Generate a unique filename
            filename = f"pge_bill_{datetime.now().strftime('%Y%m%d_%H%M%S')}.pdf"
            storage_path = f"bills/{filename}"
            
            # Upload to Supabase storage
            response = self.supabase.storage.from_('bills').upload(
                storage_path,
                file_contents
            )
            
            print(f"Bill stored in Supabase: {storage_path}")
            return storage_path
            
        except Exception as e:
            print(f"Error storing bill in Supabase: {str(e)}")
            raise

    def extract_bill_data(self, ocr_results: Dict[str, Any]) -> Dict[str, Any]:
        """Extract relevant data from OCR results
        
        Args:
            ocr_results: OCR results from Google Vision API
            
        Returns:
            Dictionary containing extracted bill data
        """
        full_text = ocr_results['full_text']
        
        # Define regex patterns for PG&E bill data
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
        
        # Extract data using patterns
        for field, pattern in patterns.items():
            match = re.search(pattern, full_text)
            if match:
                extracted_data[field] = match.group(1).strip()
            else:
                extracted_data[field] = None
                
        return extracted_data

    async def store_bill_data(self, bill_data: Dict[str, Any], storage_path: str) -> int:
        """Store extracted bill data in Supabase database
        
        Args:
            bill_data: Extracted bill data
            storage_path: Path to PDF in Supabase storage
            
        Returns:
            record_id: ID of the created database record
        """
        try:
            # Add storage path and processing timestamp to bill data
            bill_data['storage_path'] = storage_path
            bill_data['processed_at'] = datetime.now().isoformat()
            
            # Insert into Supabase
            response = self.supabase.table('pge_bills').insert(bill_data).execute()
            
            record_id = response.data[0]['id']
            print(f"Bill data stored in database with ID: {record_id}")
            return record_id
            
        except Exception as e:
            print(f"Error storing bill data in database: {str(e)}")
            raise

    async def process_bill(self, pdf_path: str) -> Dict[str, Any]:
        """Process a PG&E bill: store PDF, extract data, and save to database
        
        Args:
            pdf_path: Path to the PDF file
            
        Returns:
            Dictionary containing processing results
        """
        try:
            # Store PDF in Supabase
            storage_path = await self.store_bill_in_supabase(pdf_path)
            
            # Read the PDF file
            with open(pdf_path, 'rb') as pdf_file:
                content = pdf_file.read()
            
            # Create image object directly from PDF
            image = vision.Image(content=content)

            # Perform OCR
            response = self.vision_client.document_text_detection(image=image)
            
            if response.error.message:
                raise Exception(
                    '{}\nFor more info on error messages, check: '
                    'https://cloud.google.com/apis/design/errors'.format(
                        response.error.message))

            # Extract bill data
            ocr_results = {
                'full_text': response.full_text_annotation.text,
                'pages': [{
                    'blocks': [{
                        'text': block.text,
                        'confidence': block.confidence,
                        'bounding_box': [[vertex.x, vertex.y] for vertex in block.bounding_box.vertices]
                    } for block in page.blocks]
                } for page in response.pages]
            }
            
            bill_data = self.extract_bill_data(ocr_results)
            
            # Store in database
            record_id = await self.store_bill_data(bill_data, storage_path)
            
            return {
                'success': True,
                'storage_path': storage_path,
                'record_id': record_id,
                'extracted_data': bill_data
            }
            
        except Exception as e:
            return {
                'success': False,
                'error': str(e)
            }

def main():
    # Example usage
    analyzer = PGEBillAnalyzer()
    
    # Replace with your PDF path
    pdf_path = "example_pge_bill.pdf"
    
    import asyncio
    result = asyncio.run(analyzer.process_bill(pdf_path))
    
    print("\nProcessing Result:")
    print(json.dumps(result, indent=2))

if __name__ == "__main__":
    main()
