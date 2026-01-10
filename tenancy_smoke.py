import jwt
import requests

BASE_URL = "http://localhost:8000"

def generate_token(user_id):
    payload = {"sub": user_id, "aud": "authenticated"}
    # Unsigned/Unverified for local testing as per implementation
    return jwt.encode(payload, "secret", algorithm="HS256")

def test_ingest(user_id):
    token = generate_token(user_id)
    headers = {"Authorization": f"Bearer {token}"}
    
    print(f"Ingesting for user {user_id}...")
    try:
        content = f"This is a test document for user {user_id}".encode("utf-8")
        filename = "test_doc.txt"

        upload_payload = {
            "filename": filename,
            "file_type": "text/plain",
            "file_size": len(content),
        }
        upload_res = requests.post(
            f"{BASE_URL}/api/v1/uploads/upload-url",
            headers=headers,
            json=upload_payload,
            timeout=30,
        )
        upload_res.raise_for_status()
        upload_data = upload_res.json()

        signed_url = upload_data["upload_url"]
        storage_path = upload_data["storage_path"]

        put_headers = {"Content-Type": "text/plain"}
        put_res = requests.put(signed_url, data=content, headers=put_headers, timeout=60)
        put_res.raise_for_status()

        reference_payload = {
            "storage_path": storage_path,
            "filename": filename,
            "file_size": len(content),
            "metadata": {"client_id": "test_client"},
        }
        response = requests.post(
            f"{BASE_URL}/api/v1/uploads/file/reference",
            headers=headers,
            json=reference_payload,
            timeout=30,
        )
        print(f"Status: {response.status_code}")
        print(f"Response: {response.text}")
        return response.status_code in (200, 202)
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
