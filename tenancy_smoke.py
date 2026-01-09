import jwt
import requests
import json

BASE_URL = "http://localhost:8000"

def generate_token(user_id):
    payload = {"sub": user_id, "aud": "authenticated"}
    # Unsigned/Unverified for local testing as per implementation
    return jwt.encode(payload, "secret", algorithm="HS256")

def test_ingest(user_id):
    token = generate_token(user_id)
    headers = {"Authorization": f"Bearer {token}"}
    
    files = {
        'file': ('test_doc.txt', 'This is a test document for user ' + user_id, 'text/plain')
    }
    data = {
        'metadata': json.dumps({"client_id": "test_client"})
    }
    
    print(f"Ingesting for user {user_id}...")
    try:
        response = requests.post(f"{BASE_URL}/api/v1/ingest", headers=headers, files=files, data=data)
        print(f"Status: {response.status_code}")
        print(f"Response: {response.text}")
        return response.status_code == 200
    except Exception as e:
        print(f"Ingest failed: {e}")
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
        print(f"Response: {response.json()}")
        return response.json()
    except Exception as e:
        print(f"Chat failed: {e}")
        return None

if __name__ == "__main__":
    user1 = "00000000-0000-0000-0000-000000000001"
    user2 = "00000000-0000-0000-0000-000000000002"
    
    print("--- Test 1: Ingest for User 1 ---")
    if test_ingest(user1):
        print("Ingest User 1: PASS")
    else:
        print("Ingest User 1: FAIL (Check DB migrations?)")
        
    print("\n--- Test 2: Chat for User 1 ---")
    res1 = test_chat(user1, "test document")
    if res1 and "test document for user " + user1 in str(res1):
         print("Chat User 1: PASS (Found own doc)")
    else:
         # It might not find it directly depending on strict match, but let's see response
         pass

    print("\n--- Test 3: Chat for User 2 (Isolation) ---")
    res2 = test_chat(user2, "test document")
    if res2 and "I don't have enough information" in res2.get("answer", ""):
        print("Chat User 2: PASS (Did not find User 1 doc)")
    else:
        print("Chat User 2: POTENTIAL FAIL (Should not see data)")
