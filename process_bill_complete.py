import os
import json
import requests
import base64
import fitz  # PyMuPDF
import openai
from dotenv import load_dotenv
from datetime import datetime

# Import rate plan analyzer
try:
    import rate_plan_analyzer
    RATE_ANALYSIS_AVAILABLE = True
except ImportError:
    print("Warning: rate_plan_analyzer module not found. Rate plan analysis will be skipped.")
    RATE_ANALYSIS_AVAILABLE = False

# Load environment variables from .env file
load_dotenv()

# Set up API keys
ocr_space_api_key = os.getenv("OCR_SPACE_API_KEY", "K86742198888957")  # Default key or from env
openai.api_key = os.getenv("OPENAI_API_KEY")

def extract_ocr_text(pdf_file):
    """Extract text from a PDF file using OCR.space API"""
    print(f"Processing PDF file: {pdf_file}")
    
    # Generate output filenames based on input PDF name
    base_name = os.path.splitext(os.path.basename(pdf_file))[0]
    text_output = os.path.join('ocr_output', f"{base_name}_ocr_text.txt")
    json_output = os.path.join('ocr_output', f"{base_name}_ocr_combined.json")
    
    # Check if PDF exists
    if not os.path.exists(pdf_file):
        print(f"Error: PDF file {pdf_file} not found.")
        return None, None
    
    # Open the PDF
    pdf_document = fitz.open(pdf_file)
    page_count = pdf_document.page_count
    
    print(f"PDF has {page_count} pages. Processing...")
    
    all_text = ""
    all_results = []
    
    # Process each page
    for page_num in range(page_count):
        page = pdf_document[page_num]
        
        # Convert page to image
        pix = page.get_pixmap(matrix=fitz.Matrix(300/72, 300/72))  # 300 DPI
        img_data = pix.tobytes("png")
        
        # Encode image to base64
        base64_img = base64.b64encode(img_data).decode('ascii')
        
        # Call OCR.space API
        payload = {
            'apikey': ocr_space_api_key,
            'base64Image': f'data:image/png;base64,{base64_img}',
            'language': 'eng',
            'scale': 'true',
            'isTable': 'true',
            'OCREngine': '2'
        }
        
        try:
            response = requests.post('https://api.ocr.space/parse/image', 
                                   data=payload,
                                   timeout=60)
            result = response.json()
            
            if result.get('OCRExitCode') == 1:  # Success
                page_text = result['ParsedResults'][0]['ParsedText']
                all_text += f"\n--- PAGE {page_num + 1} ---\n{page_text}\n"
                all_results.append(result)
                print(f"Page {page_num + 1}/{page_count} processed successfully")
            else:
                error_msg = result.get('ErrorMessage', 'Unknown error')
                print(f"Error processing page {page_num + 1}: {error_msg}")
        except Exception as e:
            print(f"Exception processing page {page_num + 1}: {str(e)}")
    
    # Close the PDF
    pdf_document.close()
    
    # Save the combined text to a file
    with open(text_output, 'w', encoding='utf-8') as f:
        f.write(all_text)
    
    # Save the combined JSON results
    with open(json_output, 'w', encoding='utf-8') as f:
        json.dump(all_results, f, indent=4)
    
    print(f"OCR processing complete. Text saved to {text_output}")
    return text_output, json_output

def extract_bill_data_with_openai(ocr_text_file, output_folder='extracted_data'):
    """Extract specific bill data using OpenAI API"""
    print(f"Analyzing OCR text with OpenAI: {ocr_text_file}")
    
    # Read the OCR text file
    with open(ocr_text_file, 'r', encoding='utf-8') as f:
        ocr_text = f.read()
    
    # Create a prompt for OpenAI
    prompt = f"""
    Extract the following information from this PG&E bill OCR text. Return the results as a JSON object with these fields:
    1. Name (the customer name)
    2. Address (full service address including city, state, zip)
    3. RateSchedule (the rate schedule code and description)
    4. ElectricUsageThisPeriod (total kWh used in the billing period)
    5. BillingDays (number of days in the billing period)
    6. PeakUsage (peak usage in kWh)
    7. PeakRate (the rate charged for peak usage, e.g. $0.49378/kWh)
    8. PeakTotal (total amount charged for peak usage, e.g. $85.82)
    9. OffPeakUsage (off-peak usage in kWh)
    10. OffPeakRate (the rate charged for off-peak usage, e.g. $0.46378/kWh)
    11. OffPeakTotal (total amount charged for off-peak usage, e.g. $224.97)
    12. BillingPeriod (the billing period dates, e.g. "01/01/2025 - 01/31/2025")
    13. TotalAmountDue (the total amount due on the bill)
    
    Look for the 'Energy Charges' section of the bill, which typically contains the peak and off-peak usage information.
    If any field cannot be found, return null for that field.
    
    OCR Text:
    {ocr_text}
    """
    
    # Call OpenAI API
    response = openai.chat.completions.create(
        model="gpt-3.5-turbo",  # Using gpt-3.5-turbo which is more widely available
        messages=[
            {"role": "system", "content": "You are a utility bill data extraction assistant. Extract the requested information accurately from the OCR text of a PG&E bill. Return your response as a valid JSON object."},
            {"role": "user", "content": prompt}
        ],
        temperature=0.0  # Use low temperature for more deterministic results
    )
    
    # Extract and parse the response
    result = response.choices[0].message.content
    
    # Print raw response for debugging
    print("\nRaw OpenAI API Response:")
    print(result)
    
    # Clean the response - remove markdown code block markers if present
    cleaned_result = result
    if result.startswith("```json") and result.endswith("```"):
        cleaned_result = result[7:-3].strip()  # Remove ```json and ``` markers
    elif result.startswith("```") and result.endswith("```"):
        cleaned_result = result[3:-3].strip()  # Remove ``` markers
    
    # Parse JSON response
    try:
        parsed_result = json.loads(cleaned_result)
        return parsed_result
    except json.JSONDecodeError as e:
        print(f"Error parsing JSON response: {e}")
        print(f"Cleaned result: {cleaned_result}")
        return {"error": "Failed to parse API response"}

def ensure_folders_exist():
    """Ensure all required folders exist"""
    folders = ['bills_to_process', 'processed_bills', 'ocr_output', 'extracted_data']
    for folder in folders:
        if not os.path.exists(folder):
            os.makedirs(folder)
            print(f"Created folder: {folder}")
            
def get_processed_bill_list():
    """Get a list of already processed bill filenames"""
    if not os.path.exists('processed_bills'):
        return []
    return [os.path.basename(f) for f in os.listdir('processed_bills') if f.endswith('.pdf')]

def is_bill_already_processed(pdf_filename):
    """Check if a bill has already been processed"""
    processed_bills = get_processed_bill_list()
    return os.path.basename(pdf_filename) in processed_bills

def process_bill(pdf_file):
    """Process a bill from PDF to structured data in one go"""
    # Ensure all required folders exist
    ensure_folders_exist()
    
    print(f"\n{'=' * 50}")
    print(f"Starting complete bill processing for: {pdf_file}")
    print(f"{'=' * 50}\n")
    
    # Step 1: Extract OCR text from PDF
    ocr_text_file, ocr_json_file = extract_ocr_text(pdf_file)
    if not ocr_text_file:
        print("OCR text extraction failed. Cannot proceed.")
        return None
    
    # Step 2: Analyze OCR text with OpenAI
    extracted_data = extract_bill_data_with_openai(ocr_text_file)
    
    # Step 3: Move the processed PDF to the processed_bills folder
    processed_pdf_path = os.path.join('processed_bills', os.path.basename(pdf_file))
    try:
        import shutil
        shutil.move(pdf_file, processed_pdf_path)
        print(f"Moved PDF to processed_bills: {processed_pdf_path}")
    except Exception as e:
        print(f"Warning: Could not move PDF file: {e}")
    
    # Generate output filename based on input PDF name
    base_name = os.path.splitext(os.path.basename(pdf_file))[0]
    output_file = os.path.join('extracted_data', f"{base_name}_extracted_data.json")
    
    # Save results to a JSON file
    with open(output_file, 'w') as f:
        json.dump(extracted_data, f, indent=4)
    
    # Print formatted results
    print("\nExtracted Information:")
    print("=======================")
    print(f"Name: {extracted_data.get('Name', 'Not found')}")
    print(f"Address: {extracted_data.get('Address', 'Not found')}")
    print(f"Rate Schedule: {extracted_data.get('RateSchedule', 'Not found')}")
    print(f"Billing Period: {extracted_data.get('BillingPeriod', 'Not found')}")
    print(f"Electric Usage This Period: {extracted_data.get('ElectricUsageThisPeriod', 'Not found')} kWh")
    print(f"Billing Days: {extracted_data.get('BillingDays', 'Not found')}")
    
    print("\nEnergy Usage Details:")
    print("=======================")
    print(f"Peak Usage: {extracted_data.get('PeakUsage', 'Not found')} kWh")
    print(f"Peak Rate: {extracted_data.get('PeakRate', 'Not found')}")
    print(f"Peak Total: {extracted_data.get('PeakTotal', 'Not found')}")
    print(f"Off-Peak Usage: {extracted_data.get('OffPeakUsage', 'Not found')} kWh")
    print(f"Off-Peak Rate: {extracted_data.get('OffPeakRate', 'Not found')}")
    print(f"Off-Peak Total: {extracted_data.get('OffPeakTotal', 'Not found')}")
    print(f"\nTotal Amount Due: {extracted_data.get('TotalAmountDue', 'Not found')}")
    
    print(f"\nProcessing complete! Results saved to {output_file}")
    
    # Perform rate plan analysis if available
    if RATE_ANALYSIS_AVAILABLE:
        try:
            print("\nAnalyzing rate plans...")
            analysis = rate_plan_analyzer.analyze_bill_with_openai(extracted_data)
            
            # Save the analysis results
            analysis_file = os.path.join('extracted_data', f"{base_name}_rate_analysis.json")
            with open(analysis_file, 'w') as f:
                json.dump(analysis, f, indent=4)
            
            print("\nRate Plan Analysis:")
            print("====================")
            print(f"Current Plan: {analysis['currentPlan']} - {analysis['currentPlanDescription']}")
            print(f"Current Cost: ${analysis['currentCost']}")
            print(f"Best Plan: {analysis['bestPlan']} - {analysis['bestPlanDescription']}")
            print(f"Best Cost: ${analysis['bestCost']}")
            print(f"Estimated Monthly Savings: ${analysis['monthlySavings']}")
            print(f"Estimated Yearly Savings: ${analysis['yearlySavings']}")
            print("\nRecommendation:")
            print(analysis['recommendation'])
            
            print(f"\nAnalysis saved to: {analysis_file}")
        except Exception as e:
            print(f"Error during rate plan analysis: {e}")
    
    return extracted_data

def main():
    # Ensure all required folders exist
    ensure_folders_exist()
    
    # Check for PDF files only in the bills_to_process folder
    bills_folder = 'bills_to_process'
    pdf_files = [os.path.join(bills_folder, f) for f in os.listdir(bills_folder) if f.endswith('.pdf')]
    
    if not pdf_files:
        print(f"No PDF files found in the {bills_folder} directory.")
        return
    
    # Get list of already processed bills
    processed_bills = get_processed_bill_list()
    
    # Filter out already processed bills
    new_bills = []
    for pdf_file in pdf_files:
        if os.path.basename(pdf_file) in processed_bills:
            print(f"Skipping already processed bill: {pdf_file}")
        else:
            new_bills.append(pdf_file)
    
    if not new_bills:
        print("No new bills to process.")
        return
    
    print(f"Found {len(new_bills)} new bills to process.")
    for pdf_file in new_bills:
        process_bill(pdf_file)

if __name__ == "__main__":
    main()
