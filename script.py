from google.oauth2 import service_account
import google.auth.transport.requests
import requests
import json

SERVICE_ACCOUNT_FILE = 'service-account.json'
SCOPES = ['https://www.googleapis.com/auth/indexing']

creds = service_account.Credentials.from_service_account_file(
    SERVICE_ACCOUNT_FILE, scopes=SCOPES)

# refresh to obtain access_token
request = google.auth.transport.requests.Request()
creds.refresh(request)
access_token = creds.token
print("access_token:", access_token)

resp = requests.post(
    'https://indexing.googleapis.com/v3/urlNotifications:publish',
    headers={'Authorization': f'Bearer {access_token}', 'Content-Type': 'application/json'},
    json={'url': 'https://www.bodygoodstudio.com/blogs/news/creatine-monohydrate-for-women-benefits-research-safe-use', 'type': 'URL_UPDATED'}
)
print(resp.status_code, resp.text)
