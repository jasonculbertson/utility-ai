import os
import tempfile
import requests
from urllib.parse import urlparse, parse_qs

def download_from_drive(url: str) -> str:
    """Download a file from Google Drive and save it locally.
    
    Args:
        url: Google Drive sharing URL
        
    Returns:
        Path to downloaded file
    """
    print(f"Processing URL: {url}")
    
    # Extract file ID from URL
    parsed = urlparse(url)
    print(f"Parsed URL: {parsed}")
    
    if 'drive.google.com' not in parsed.netloc:
        raise ValueError("Not a Google Drive URL")
    
    file_id = None
    if '/file/d/' in url:
        # Handle direct file links
        file_id = url.split('/file/d/')[1].split('/')[0]
        print(f"Extracted file ID from direct link: {file_id}")
    else:
        # Handle sharing links
        query_params = parse_qs(parsed.query)
        file_id = query_params.get('id', [None])[0]
        print(f"Extracted file ID from query params: {file_id}")
    
    if not file_id:
        raise ValueError("Could not extract file ID from URL")
    
    # Create download URL
    download_url = f"https://drive.google.com/uc?export=download&id={file_id}"
    print(f"Download URL: {download_url}")
    
    # Download file with session to handle cookies
    session = requests.Session()
    print("Initiating download...")
    
    response = session.get(download_url, stream=True)
    if response.status_code != 200:
        raise Exception(f"Failed to download file: {response.status_code}")
    
    # Check if we need to handle the confirmation page
    if 'Content-Disposition' not in response.headers:
        print("Large file detected, handling confirmation page...")
        # Extract confirmation code
        for form in response.text.split('form'):
            if 'confirm' in form:
                confirm_token = form.split('confirm=')[1].split('"')[0]
                print(f"Found confirmation token: {confirm_token}")
                download_url = f"{download_url}&confirm={confirm_token}"
                response = session.get(download_url, stream=True)
                break
    
    # Save to temporary file
    temp_dir = tempfile.gettempdir()
    temp_path = os.path.join(temp_dir, f"pge_bill_{file_id}.pdf")
    print(f"Saving to: {temp_path}")
    
    with open(temp_path, 'wb') as f:
        for chunk in response.iter_content(chunk_size=8192):
            if chunk:
                f.write(chunk)
    
    file_size = os.path.getsize(temp_path)
    print(f"Downloaded file size: {file_size} bytes")
    
    if file_size == 0:
        raise Exception("Downloaded file is empty")
    
    return temp_path
