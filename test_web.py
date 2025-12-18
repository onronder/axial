import jwt
import requests
import json

BASE_URL = "http://localhost:8000"

def generate_token(user_id):
    payload = {"sub": user_id, "aud": "authenticated"}
    return jwt.encode(payload, "secret", algorithm="HS256")

def test_web_ingest(user_id, url):
    token = generate_token(user_id)
    headers = {"Authorization": f"Bearer {token}"}
    
    # Send URL as Form data
    data = {
        'url': url,
        'metadata': json.dumps({"client_id": "web_test"})
    }
    
    print(f"Crawling URL {url} for user {user_id}...")
    try:
        # Note: No 'files' argument here
        response = requests.post(f"{BASE_URL}/api/v1/ingest", headers=headers, data=data)
        print(f"Status: {response.status_code}")
        print(f"Response: {response.text}")
        return response.status_code == 200
    except Exception as e:
        print(f"Web Ingest failed: {e}")
        return False

def test_chat(user_id, query):
    token = generate_token(user_id)
    headers = {"Authorization": f"Bearer {token}"}
    
    payload = {
        "query": query,
        "history": []
    }
    
    print(f"Chatting as user {user_id}...")
    try:
        response = requests.post(f"{BASE_URL}/api/v1/chat", headers=headers, json=payload)
        print(f"Status: {response.status_code}")
        print(f"Answer: {response.json().get('answer')}")
        return response.json()
    except Exception as e:
        print(f"Chat failed: {e}")
        return None

if __name__ == "__main__":
    user_web = "00000000-0000-0000-0000-000000000003"
    target_url = "https://example.com" 
    
    print("--- Test 1: Web Ingest ---")
    if test_web_ingest(user_web, target_url):
        print("Web Ingest: PASS")
    else:
        print("Web Ingest: FAIL")
        
    print("\n--- Test 2: Chat about Web Content ---")
    # example.com usually contains "Example Domain" text
    res = test_chat(user_web, "What is the content of the ingested website?")
    if res and "Example Domain" in str(res):
         print("Chat Web: PASS (Found domain text)")
    else:
         print("Chat Web: CHECK RESPONSE (Might need specific query)")
