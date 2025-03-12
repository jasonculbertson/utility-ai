import os
from dotenv import load_dotenv
from supabase import create_client, Client

def setup_supabase():
    """Set up Supabase database and storage for PG&E bill analysis"""
    load_dotenv()
    
    # Initialize Supabase with service role key for admin operations
    supabase_url = "https://umuqydzeqqifiywqsxec.supabase.co"
    supabase_service_key = os.getenv("SUPABASE_SERVICE_KEY")
    
    if not supabase_url or not supabase_service_key:
        raise ValueError("Supabase credentials not found in environment variables")
    
    supabase: Client = create_client(supabase_url, supabase_service_key)
    
    try:
        # Create the pge_bills table
        print("Creating pge_bills table...")
        
        # Enable extensions and create SQL execution function
        enable_sql = """
        create extension if not exists pgcrypto;
        
        drop table if exists pge_bills;
        
        create table pge_bills (
            id bigint primary key generated always as identity,
            account_number varchar,
            statement_date date,
            total_amount decimal(10,2),
            due_date date,
            service_address text,
            electric_charges decimal(10,2),
            gas_charges decimal(10,2),
            total_usage_kwh decimal(10,2),
            total_usage_therms decimal(10,2),
            storage_path text,
            processed_at timestamp with time zone,
            created_at timestamp with time zone default now()
        );
        """
        
        # Execute SQL directly
        response = supabase.postgrest.schema('public').execute(enable_sql)
        print("Table created successfully")
        
        # Create storage bucket
        print("\nCreating storage bucket...")
        try:
            supabase.storage.create_bucket(
                "bills",
                {"public": False}  # Make it private by default
            )
            print("Storage bucket 'bills' created successfully")
        except Exception as e:
            if "Duplicate" in str(e):
                print("Storage bucket 'bills' already exists")
            else:
                raise
        
        print("\nSetup completed successfully!")
        
    except Exception as e:
        print(f"Error during setup: {str(e)}")
        raise

if __name__ == "__main__":
    setup_supabase()
