# main.py - Simple Single URL Google Indexing API
from fastapi import FastAPI, HTTPException
from pydantic import BaseModel, HttpUrl
from google.oauth2 import service_account
import google.auth.transport.requests
import requests
import json
import os
from typing import Optional, Dict, Any
import base64
import time

app = FastAPI(
    title="Google Indexing API - Single URL",
    description="Submit single URL to Google for indexing",
    version="1.0.0"
)

# Configuration
DEFAULT_SCOPES = ['https://www.googleapis.com/auth/indexing']
TIMEOUT = 30
API_ENDPOINT = 'https://indexing.googleapis.com/v3/urlNotifications:publish'
MAX_RETRIES = 3

class ServiceAccountModel(BaseModel):
    type: str
    project_id: str
    private_key_id: str
    private_key: str
    client_email: str
    client_id: str
    auth_uri: str
    token_uri: str
    auth_provider_x509_cert_url: Optional[str] = None
    client_x509_cert_url: Optional[str] = None

class URLRequest(BaseModel):
    url: HttpUrl
    type: Optional[str] = "URL_UPDATED"
    service_account: Optional[ServiceAccountModel] = None
    project_id: Optional[str] = None
    scopes: Optional[list[str]] = None

class URLResponse(BaseModel):
    success: bool
    status_code: int
    message: str
    url: str
    type: str

def fix_private_key_format(private_key: str) -> str:
    """Fix private key format issues."""
    if not private_key:
        return private_key
    
    if '\\n' in private_key and '\n' not in private_key:
        return private_key.replace('\\n', '\n')
    
    return private_key

def get_service_account_info(service_account_data: Optional[ServiceAccountModel] = None):
    """Get service account info."""
    try:
        # Use provided service account
        if service_account_data:
            data = service_account_data.dict()
            if 'private_key' in data:
                data['private_key'] = fix_private_key_format(data['private_key'])
            return data
        
        # Environment variable
        env_service_account_base64 = os.getenv('GOOGLE_SERVICE_ACCOUNT_BASE64')
        if env_service_account_base64:
            service_account_json = base64.b64decode(env_service_account_base64).decode('utf-8')
            data = json.loads(service_account_json)
            
            if 'private_key' in data:
                data['private_key'] = fix_private_key_format(data['private_key'])
            
            return data
        
        # File
        service_account_file = os.getenv('SERVICE_ACCOUNT_FILE', 'service-account.json')
        if os.path.exists(service_account_file):
            with open(service_account_file, 'r', encoding='utf-8') as f:
                data = json.load(f)
                
                if 'private_key' in data:
                    data['private_key'] = fix_private_key_format(data['private_key'])
                
                return data
        
        raise FileNotFoundError("Service account credentials not found")
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to load service account: {str(e)}")

@app.post("/submit-url", response_model=URLResponse)
async def submit_url(request: URLRequest):
    """Submit a single URL to Google Indexing API."""
    try:
        # Get service account
        service_account_info = get_service_account_info(request.service_account)
        
        # Use provided scopes or default
        token_scopes = request.scopes if request.scopes else DEFAULT_SCOPES
        
        # Validate required fields
        required_fields = ['type', 'project_id', 'private_key_id', 'private_key', 'client_email']
        missing_fields = [field for field in required_fields if field not in service_account_info]
        
        if missing_fields:
            raise ValueError(f"Missing required fields: {missing_fields}")
        
        # Get access token with retry
        access_token = None
        for attempt in range(MAX_RETRIES):
            try:
                creds = service_account.Credentials.from_service_account_info(
                    service_account_info, scopes=token_scopes)
                
                if attempt > 0:
                    time.sleep(1)
                
                auth_request = google.auth.transport.requests.Request()
                creds.refresh(auth_request)
                access_token = creds.token
                break
                
            except Exception as e:
                if "Invalid JWT Signature" in str(e) and attempt < MAX_RETRIES - 1:
                    continue
                else:
                    raise e
        
        # Prepare request
        project_id = request.project_id or service_account_info.get('project_id')
        
        headers = {
            'Authorization': f'Bearer {access_token}',
            'Content-Type': 'application/json'
        }
        
        if project_id:
            headers['X-Goog-User-Project'] = project_id
        
        payload = {
            'url': str(request.url),
            'type': request.type
        }
        
        # Submit to Google
        response = requests.post(
            API_ENDPOINT,
            headers=headers,
            json=payload,
            timeout=TIMEOUT
        )
        
        success = response.status_code == 200
        
        return URLResponse(
            success=success,
            status_code=response.status_code,
            message=response.text if not success else "URL submitted successfully",
            url=str(request.url),
            type=request.type
        )
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to submit URL: {str(e)}")

if __name__ == "__main__":
    import uvicorn
    port = int(os.environ.get("PORT", 8000))
    uvicorn.run(app, host="0.0.0.0", port=port)