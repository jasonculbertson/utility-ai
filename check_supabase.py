from supabase import create_client
import os
from datetime import datetime, timedelta

# Initialize Supabase client
supabase = create_client(
    os.environ.get('SUPABASE_URL'),
    os.environ.get('SUPABASE_SERVICE_KEY')
)

# Get records from the last 15 minutes
now = datetime.utcnow()
fifteen_mins_ago = now - timedelta(minutes=15)

try:
    # Query recent records
    response = supabase.table('pge_bills').select('*').gte('processed_at', fifteen_mins_ago.isoformat()).execute()
    
    print("\nChecking for recently processed bills...")
    if response.data:
        print(f"Found {len(response.data)} recently processed bills:")
        for record in response.data:
            print(f"\nBill Details:")
            print(f"- File: {record.get('source_filename')}")
            print(f"- Account Number: {record.get('account_number')}")
            print(f"- Service Address: {record.get('service_address')}")
            print(f"- Billing Period: {record.get('billing_period')}")
            print(f"- Total Amount: ${record.get('total_amount')}")
            print(f"- Processed At: {record.get('processed_at')}")
    else:
        print("No bills have been processed in the last 15 minutes.")
        
except Exception as e:
    print(f"Error checking Supabase: {str(e)}")
