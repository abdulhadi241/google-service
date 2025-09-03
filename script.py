from google.oauth2 import service_account
import google.auth.transport.requests
import requests
import json
import os
from datetime import datetime, timezone

def validate_service_account_file(file_path):
    """Validate and fix service account JSON file."""
    if not os.path.exists(file_path):
        raise FileNotFoundError(f"Service account file not found: {file_path}")
    
    with open(file_path, 'r') as f:
        try:
            data = json.load(f)
        except json.JSONDecodeError as e:
            raise ValueError(f"Invalid JSON in service account file: {e}")
    
    # Check required fields
    required_fields = ['type', 'project_id', 'private_key_id', 'private_key', 'client_email', 'client_id', 'auth_uri', 'token_uri']
    missing_fields = [field for field in required_fields if field not in data]
    
    if missing_fields:
        raise ValueError(f"Missing required fields in service account file: {missing_fields}")
    
    # Fix private key format if needed
    private_key = data.get('private_key', '')
    if '\\n' in private_key:
        print("Fixing private key format...")
        data['private_key'] = private_key.replace('\\n', '\n')
        
        # Save the corrected file
        with open(file_path, 'w') as f:
            json.dump(data, f, indent=2)
        print("✓ Private key format fixed")
    
    return data

def get_google_indexing_token(service_account_file):
    """Get Google Indexing API access token with error handling."""
    try:
        # Validate service account file first
        service_account_info = validate_service_account_file(service_account_file)
        print(f"✓ Service account: {service_account_info['client_email']}")
        print(f"✓ Project ID: {service_account_info['project_id']}")
        print(f"✓ Current time: {datetime.now(timezone.utc)}")
        
        # Create credentials
        scopes = ['https://www.googleapis.com/auth/indexing']
        creds = service_account.Credentials.from_service_account_file(
            service_account_file, scopes=scopes)
        
        # Refresh credentials to get access token
        request = google.auth.transport.requests.Request()
        creds.refresh(request)
        
        print("✓ Access token obtained successfully")
        return creds.token
        
    except Exception as e:
        print(f"❌ Error getting access token: {e}")
        raise

def submit_url_to_google(url, url_type='URL_UPDATED', service_account_file='service-account.json'):
    """Submit URL to Google Indexing API."""
    try:
        # Get access token
        access_token = get_google_indexing_token(service_account_file)
        
        # Prepare request
        headers = {
            'Authorization': f'Bearer {access_token}',
            'Content-Type': 'application/json'
        }
        
        payload = {
            'url': url,
            'type': url_type
        }
        
        print(f"Submitting URL: {url}")
        print(f"Type: {url_type}")
        
        # Make API call
        response = requests.post(
            'https://indexing.googleapis.com/v3/urlNotifications:publish',
            headers=headers,
            json=payload,
            timeout=30
        )
        
        print(f"Response Status: {response.status_code}")
        print(f"Response Body: {response.text}")
        
        if response.status_code == 200:
            print("✅ URL submitted successfully!")
            return True
        else:
            print("❌ Failed to submit URL")
            return False
            
    except Exception as e:
        print(f"❌ Error submitting URL: {e}")
        return False

# Main execution
if __name__ == "__main__":
    SERVICE_ACCOUNT_FILE = 'service-account.json'
    TEST_URL = 'https://www.bodygoodstudio.com/blogs/news/creatine-monohydrate-for-women-benefits-research-safe-use'
    
    print("=== Google Indexing API Test ===")
    
    try:
        result = submit_url_to_google(TEST_URL, 'URL_UPDATED', SERVICE_ACCOUNT_FILE)
        if result:
            print("✅ Success!")
        else:
            print("❌ Failed!")
            
    except Exception as e:
        print(f"❌ Script failed: {e}")
        
        # Debugging information
        print("\n=== Debugging Information ===")
        print("1. Check if service-account.json exists and has correct permissions")
        print("2. Verify your system clock is synchronized")
        print("3. Ensure the service account has Indexing API permissions")
        print("4. Check if the URL is verified in Google Search Console")
        print("5. Verify your Google Cloud project has the Indexing API enabled")