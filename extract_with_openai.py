import os
import json
import openai
from dotenv import load_dotenv

# Load environment variables from .env file (for API key)
load_dotenv()

# Set up OpenAI API key
openai.api_key = os.getenv("OPENAI_API_KEY")

def extract_bill_data_with_openai(ocr_text_file):
    """Extract specific bill data using OpenAI API"""
    # Read the OCR text file
    with open(ocr_text_file, 'r') as f:
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

def main():
    # Path to OCR text file
    ocr_text_file = '3307custbill01022025_ocr_text.txt'
    
    # Check if file exists
    if not os.path.exists(ocr_text_file):
        print(f"Error: File {ocr_text_file} not found.")
        return
    
    print(f"Extracting data from {ocr_text_file} using OpenAI API...")
    
    # Extract data using OpenAI
    extracted_data = extract_bill_data_with_openai(ocr_text_file)
    
    # Print formatted results
    print("\nExtracted Information:")
    print("=======================")
    print(f"Name: {extracted_data.get('Name', 'Not found')}")
    print(f"Address: {extracted_data.get('Address', 'Not found')}")
    print(f"Rate Schedule: {extracted_data.get('RateSchedule', 'Not found')}")
    print(f"Electric Usage This Period: {extracted_data.get('ElectricUsageThisPeriod', 'Not found')}")
    print(f"Billing Days: {extracted_data.get('BillingDays', 'Not found')}")
    
    print("\nEnergy Usage Details:")
    print("=======================")
    print(f"Peak Usage: {extracted_data.get('PeakUsage', 'Not found')} kWh")
    print(f"Peak Rate: {extracted_data.get('PeakRate', 'Not found')}")
    print(f"Peak Total: {extracted_data.get('PeakTotal', 'Not found')}")
    print(f"Off-Peak Usage: {extracted_data.get('OffPeakUsage', 'Not found')} kWh")
    print(f"Off-Peak Rate: {extracted_data.get('OffPeakRate', 'Not found')}")
    print(f"Off-Peak Total: {extracted_data.get('OffPeakTotal', 'Not found')}")
    
    # Save results to a JSON file
    output_file = 'openai_extracted_data.json'
    with open(output_file, 'w') as f:
        json.dump(extracted_data, f, indent=4)
    
    print(f"\nResults saved to {output_file}")

if __name__ == "__main__":
    main()
