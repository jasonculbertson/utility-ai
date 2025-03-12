from google.cloud import storage
from google.oauth2 import service_account
from googleapiclient.discovery import build
from googleapiclient.http import MediaIoBaseDownload
import io
import os

DRIVE_FOLDER_ID = '1UxvmDE9IxiGE0r0RQFg8VhsDWl6n5Qa2'

def initialize_drive_service():
    """Initialize Google Drive service"""
    credentials = service_account.Credentials.from_service_account_file(
        'service_account.json',
        scopes=['https://www.googleapis.com/auth/drive.readonly']
    )
    return build('drive', 'v3', credentials=credentials)

def initialize_storage_client():
    """Initialize Google Cloud Storage client"""
    credentials = service_account.Credentials.from_service_account_file(
        'service_account.json'
    )
    return storage.Client(credentials=credentials)

def main():
    print("Starting upload process...")
    
    # Initialize services
    print("Initializing Drive service...")
    drive_service = initialize_drive_service()
    print("Initializing Storage client...")
    storage_client = initialize_storage_client()
    
    # Get bucket
    bucket_name = os.environ['BUCKET_NAME']
    print(f"Getting bucket: {bucket_name}")
    bucket = storage_client.bucket(bucket_name)
    
    # List files in Drive folder
    print(f"Listing files in Drive folder {DRIVE_FOLDER_ID}...")
    results = drive_service.files().list(
        q=f"'{DRIVE_FOLDER_ID}' in parents and mimeType='application/pdf' and trashed=false",
        fields="files(id, name, modifiedTime)"
    ).execute()
    
    files = results.get('files', [])
    print(f"Found {len(files)} PDF files in Drive folder")
    
    for file in files:
        print(f"\nProcessing file: {file['name']} (ID: {file['id']})")
        print(f"Last modified: {file['modifiedTime']}")
        
        # Download from Drive
        print(f"Downloading {file['name']} from Drive...")
        request = drive_service.files().get_media(fileId=file['id'])
        fh = io.BytesIO()
        downloader = MediaIoBaseDownload(fh, request)
        done = False
        while done is False:
            status, done = downloader.next_chunk()
            if status:
                print(f"Download {int(status.progress() * 100)}% complete")
            
        # Upload to Cloud Storage
        print(f"Uploading {file['name']} to Cloud Storage...")
        blob = bucket.blob(file['name'])
        blob.upload_from_string(
            fh.getvalue(),
            content_type='application/pdf'
        )
        print(f"Successfully uploaded {file['name']} to Cloud Storage bucket {bucket_name}")

if __name__ == '__main__':
    main()
