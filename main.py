from fastapi import FastAPI, HTTPException
from pydantic import BaseModel, HttpUrl
from google.oauth2 import service_account
import google.auth.transport.requests
import requests
import json
from typing import Optional
import os

app = FastAPI(title="Google Indexing API", description="Submit URLs to Google for indexing")

# Configuration
SERVICE_ACCOUNT_FILE = 'service-account.json'
SCOPES = ['https://www.googleapis.com/auth/indexing']

class URLRequest(BaseModel):
    url: HttpUrl
    type: Optional[str] = "URL_UPDATED"  # URL_UPDATED or URL_DELETED

class URLResponse(BaseModel):
    success: bool
    status_code: int
    message: str
    url: str
    type: str

def get_access_token():
    """Get Google API access token using service account."""
    try:
        if not os.path.exists(SERVICE_ACCOUNT_FILE):
            raise FileNotFoundError(f"Service account file '{SERVICE_ACCOUNT_FILE}' not found")
        
        creds = service_account.Credentials.from_service_account_file(
            SERVICE_ACCOUNT_FILE, scopes=SCOPES)
        
        # Refresh to obtain access_token
        request = google.auth.transport.requests.Request()
        creds.refresh(request)
        return creds.token
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to get access token: {str(e)}")

@app.post("/submit-url", response_model=URLResponse)
async def submit_url(request: URLRequest):
    """Submit a URL to Google Indexing API."""
    try:
        # Get access token
        access_token = get_access_token()
        
        # Prepare the request
        headers = {
            'Authorization': f'Bearer {access_token}',
            'Content-Type': 'application/json'
        }
        
        payload = {
            'url': str(request.url),
            'type': request.type
        }
        
        # Make the API call
        response = requests.post(
            'https://indexing.googleapis.com/v3/urlNotifications:publish',
            headers=headers,
            json=payload
        )
        
        # Parse response
        success = response.status_code == 200
        
        return URLResponse(
            success=success,
            status_code=response.status_code,
            message=response.text if not success else "URL submitted successfully",
            url=str(request.url),
            type=request.type
        )
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to submit URL: {str(e)}")

@app.post("/submit-urls", response_model=list[URLResponse])
async def submit_multiple_urls(requests_list: list[URLRequest]):
    """Submit multiple URLs to Google Indexing API."""
    results = []
    
    try:
        # Get access token once for all requests
        access_token = get_access_token()
        
        headers = {
            'Authorization': f'Bearer {access_token}',
            'Content-Type': 'application/json'
        }
        
        for url_request in requests_list:
            try:
                payload = {
                    'url': str(url_request.url),
                    'type': url_request.type
                }
                
                response = requests.post(
                    'https://indexing.googleapis.com/v3/urlNotifications:publish',
                    headers=headers,
                    json=payload
                )
                
                success = response.status_code == 200
                
                results.append(URLResponse(
                    success=success,
                    status_code=response.status_code,
                    message=response.text if not success else "URL submitted successfully",
                    url=str(url_request.url),
                    type=url_request.type
                ))
                
            except Exception as e:
                results.append(URLResponse(
                    success=False,
                    status_code=500,
                    message=f"Error: {str(e)}",
                    url=str(url_request.url),
                    type=url_request.type
                ))
        
        return results
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to process URLs: {str(e)}")

@app.get("/health")
async def health_check():
    """Health check endpoint."""
    return {"status": "healthy", "service": "google-indexing-api"}

@app.get("/")
async def root():
    """Root endpoint with API information."""
    return {
        "message": "Google Indexing API Service",
        "endpoints": {
            "submit_single": "/submit-url",
            "submit_multiple": "/submit-urls",
            "health": "/health",
            "docs": "/docs"
        }
    }

# Example usage information
@app.get("/example")
async def example_usage():
    """Show example usage."""
    return {
        "single_url_example": {
            "url": "https://example.com/page",
            "type": "URL_UPDATED"
        },
        "multiple_urls_example": [
            {
                "url": "https://example.com/page1",
                "type": "URL_UPDATED"
            },
            {
                "url": "https://example.com/page2", 
                "type": "URL_DELETED"
            }
        ],
        "curl_example": 'curl -X POST "http://localhost:8000/submit-url" -H "Content-Type: application/json" -d \'{"url": "https://example.com", "type": "URL_UPDATED"}\''
    }

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)