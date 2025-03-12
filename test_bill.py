from pge_bill_analyzer import PGEBillAnalyzer
from drive_downloader import download_from_drive
import asyncio
import json
import os
import sys
import traceback

async def test_bill(bill_source: str):
    analyzer = PGEBillAnalyzer()
    pdf_path = None
    
    try:
        # If it's a Google Drive URL, download it first
        if bill_source.startswith('http'):
            print("Downloading bill from Google Drive...")
            try:
                pdf_path = download_from_drive(bill_source)
                print(f"Downloaded to: {pdf_path}")
                if not os.path.exists(pdf_path):
                    raise Exception(f"Downloaded file not found at {pdf_path}")
                print(f"File size: {os.path.getsize(pdf_path)} bytes")
            except Exception as e:
                print(f"Error downloading file: {str(e)}")
                traceback.print_exc()
                return
        else:
            pdf_path = bill_source
            if not os.path.exists(pdf_path):
                print(f"Error: File not found at {pdf_path}")
                return
        
        # Process the bill
        print("Processing bill...")
        try:
            result = await analyzer.process_bill(pdf_path)
            print("\nExtracted Bill Data:")
            print(json.dumps(result, indent=2))
            return result
        except Exception as e:
            print(f"Error processing bill: {str(e)}")
            traceback.print_exc()
    finally:
        # Clean up temporary file if we downloaded it
        if pdf_path and bill_source.startswith('http') and os.path.exists(pdf_path):
            try:
                os.remove(pdf_path)
                print(f"Cleaned up temporary file: {pdf_path}")
            except Exception as e:
                print(f"Error cleaning up file: {str(e)}")

if __name__ == "__main__":
    # You can use either a local path or a Google Drive URL
    if len(sys.argv) > 1:
        bill_source = sys.argv[1]
    else:
        bill_source = "https://drive.google.com/file/d/1cOp4VrdYvyudZFTecPJLLITo1vPjP1RN/view?usp=sharing"
    
    print(f"Processing bill from: {bill_source}")
    asyncio.run(test_bill(bill_source))
