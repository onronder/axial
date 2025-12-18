import requests
import json

url = "http://127.0.0.1:8000/api/v1/ingest"

# 1. Test with a MALFORMED token (not 3 parts)
print("--- Sending MALFORMED token ---")
headers = {"Authorization": "Bearer bad.token"}
try:
    # Minimal valid body for the endpoint
    # metadata is required as a string
    data = {"metadata": json.dumps({"client_id": "test"})}
    # We must send *some* form data for file/url or it fails validation? 
    # Actually ingest_document has optional file/url.
    files = {"file": ("test.txt", b"content")}
    
    resp = requests.post(url, headers=headers, data=data, files=files)
    print(f"Status: {resp.status_code}")
    print(f"Body: {resp.text}")
except Exception as e:
    print(f"Request failed: {e}")

# 2. Test with a VALID-LOOKING dummy token (3 parts, base64)
print("\n--- Sending DUMMY token (valid structure, invalid signature) ---")
# eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJzdWIiOiIxMjM0NTY3ODkwIiwibmFtZSI6IkpvaG4gRG9lIiwiaWF0IjoxNTE2MjM5MDIyfQ.scope
token = "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJzdWIiOiIxMjM0NTY3ODkwIiwibmFtZSI6IkpvaG4gRG9lIiwiaWF0IjoxNTE2MjM5MDIyfQ.SflKxwRJSMeKKF2QT4fwpMeJf36POk6yJV_adQssw5c"
headers = {"Authorization": f"Bearer {token}"}
try:
    resp = requests.post(url, headers=headers, data=data, files=files)
    print(f"Status: {resp.status_code}")
    print(f"Body: {resp.text}")
except Exception as e:
    print(f"Request failed: {e}")
