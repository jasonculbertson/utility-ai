from google.cloud import storage
import os

def main():
    # Initialize the client
    storage_client = storage.Client.from_service_account_json('service_account.json')
    
    # Get the bucket
    bucket_name = os.environ['BUCKET_NAME']
    print(f"\nChecking bucket: {bucket_name}")
    bucket = storage_client.bucket(bucket_name)
    
    # List all blobs
    blobs = bucket.list_blobs()
    
    print("\nFiles in bucket:")
    for blob in blobs:
        print(f"- {blob.name} (uploaded: {blob.time_created})")

if __name__ == '__main__':
    main()
