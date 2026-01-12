import os
import uuid
import logging
import time
from locust import HttpUser, task, between
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# Set up logging
logger = logging.getLogger(__name__)

SUPABASE_URL = os.getenv("SUPABASE_URL")
SUPABASE_KEY = os.getenv("SUPABASE_PUBLISHABLE_KEY") or os.getenv("SUPABASE_ANON_KEY")
LOAD_TEST_EMAIL = os.getenv("LOAD_TEST_EMAIL")
LOAD_TEST_PASSWORD = os.getenv("LOAD_TEST_PASSWORD")

if not SUPABASE_URL or not SUPABASE_KEY:
    logger.warning("SUPABASE_URL or SUPABASE_PUBLISHABLE_KEY not set. Auth might fail.")
if not LOAD_TEST_EMAIL or not LOAD_TEST_PASSWORD:
    logger.warning("LOAD_TEST_EMAIL or LOAD_TEST_PASSWORD not set. Login will fail.")

# Global cache for token to avoid rate limiting
_CACHED_TOKEN = None
_TOKEN_LAST_REFRESH = 0

def get_auth_token(client):
    """
    Get auth token, reusing validation from previous calls if successful.
    This prevents hitting Supabase Rate Limits when spawning thousands of users.
    Refreshes token if it's older than 50 minutes (3000 seconds).
    """
    global _CACHED_TOKEN, _TOKEN_LAST_REFRESH
    
    current_time = time.time()
    
    # Check if token exists and is fresh (< 50 mins)
    if _CACHED_TOKEN and (current_time - _TOKEN_LAST_REFRESH < 3000):
        return _CACHED_TOKEN

    if not SUPABASE_URL or not SUPABASE_KEY:
        logger.error("Skipping login due to missing Supabase config")
        return None

    logger.info("Performing global login via Supabase...")
    auth_url = f"{SUPABASE_URL}/auth/v1/token?grant_type=password"
    
    try:
        # We use a separate request here to not mess with the user session analytics yet,
        # or we just use the 'client' passed in.
        # Since we want to cache it, we only really need to do this once.
        # Race condition: Multiple users might enter here at start.
        # It's acceptable for a few to race, better than 250.
        
        if not LOAD_TEST_EMAIL or not LOAD_TEST_PASSWORD:
            logger.error("Skipping login due to missing load test credentials")
            return None

        response = client.post(
            auth_url, 
            json={
                "email": LOAD_TEST_EMAIL,
                "password": LOAD_TEST_PASSWORD
            },
            headers={
                "apikey": SUPABASE_KEY,
                "Content-Type": "application/json"
            },
            name="/auth/v1/token"
        )
        
        if response.status_code == 200:
            data = response.json()
            token = data.get("access_token")
            if token:
                _CACHED_TOKEN = token
                _TOKEN_LAST_REFRESH = current_time
                logger.info("Global login successful. Token cached.")
                return token
        else:
            logger.error(f"Login failed: {response.status_code} - {response.text}")
            
    except Exception as e:
        logger.error(f"Login exception: {e}")
    
    return None

class AxioUser(HttpUser):
    # Allow overriding host via environment to target staging/prod
    host = os.getenv("LOAD_TEST_HOST", "http://localhost:8000")
    
    # Realistic wait time between tasks (1-5 seconds)
    wait_time = between(1, 5)

    def on_start(self):
        """
        Log in a user. Uses global cache to prevent 429s.
        """
        self.headers = {}
        
        # Use simple requests to get token if needed, or use self.client
        # We use self.client to track it, but we check cache first
        token = get_auth_token(self.client)
        
        if token:
            self.token = token
            self.headers = {
                "Authorization": f"Bearer {self.token}",
                # "apikey": SUPABASE_KEY 
            }
        else:
            self.token = None
            logger.error("Failed to obtain auth token. User will be inactive.")
            self.stop()

    def refresh_token(self):
        """Force refresh global token."""
        global _CACHED_TOKEN, _TOKEN_LAST_REFRESH
        _TOKEN_LAST_REFRESH = 0 # Force expiration check to fail
        _CACHED_TOKEN = None
        
        token = get_auth_token(self.client)
        if token:
             self.token = token
             self.headers["Authorization"] = f"Bearer {token}"
             return True
        return False

    # ---------------------------------------------------------------------
    # Helpers for upload/dedup/throughput scenarios
    # ---------------------------------------------------------------------
    def _generate_presigned_upload(self, filename: str, content: bytes, mime: str = "text/plain"):
        """
        Step 1: Request signed URL
        """
        payload = {
            "filename": filename,
            "file_type": mime,
            "file_size": len(content),
        }
        return self.client.post(
            "/api/v1/uploads/upload-url",
            json=payload,
            headers=self.headers,
            name="/uploads/upload-url",
        )

    def _upload_to_signed_url(self, upload_url: str, content: bytes, mime: str = "text/plain"):
        """
        Step 2: PUT the file to Supabase storage using the signed URL.
        """
        return self.client.put(
            upload_url,
            data=content,
            headers={"Content-Type": mime},
            name="/uploads/upload-url:put",
        )

    def _ingest_file_reference(self, storage_path: str, filename: str, content: bytes, metadata=None):
        """
        Step 3: Notify backend of uploaded file to trigger ingestion.
        """
        payload = {
            "storage_path": storage_path,
            "filename": filename,
            "file_size": len(content),
            "metadata": metadata or {},
        }
        return self.client.post(
            "/api/v1/uploads/file/reference",
            json=payload,
            headers=self.headers,
            name="/uploads/file/reference",
        )

    def _upload_once(self, label: str, content: bytes):
        """
        End-to-end upload flow: signed URL -> PUT -> ingest reference.
        Returns ingestion job response.
        """
        if not self.token and not self.refresh_token():
            return None

        presigned = self._generate_presigned_upload(f"{label}.txt", content)
        if presigned.status_code != 200:
            presigned.failure(f"presign failed {presigned.status_code}: {presigned.text}")
            return None

        data = presigned.json()
        upload_url = data.get("upload_url")
        storage_path = data.get("storage_path")
        if not upload_url or not storage_path:
            presigned.failure("presign missing upload_url or storage_path")
            return None

        upload = self._upload_to_signed_url(upload_url, content)
        if upload.status_code >= 300:
            upload.failure(f"upload failed {upload.status_code}: {upload.text}")
            return None

        ingest = self._ingest_file_reference(storage_path, f"{label}.txt", content)
        if ingest.status_code not in (200, 202):
            ingest.failure(f"ingest failed {ingest.status_code}: {ingest.text}")
            return None

        return ingest

    @task(3)
    def chat_interaction(self):
        """
        Task A: Simulate sending a chat message. High weight (3).
        """
        if not self.token:
             # Try getting token if missing
             if not self.refresh_token():
                 return

        # Correct payload matching ChatRequest schema in backend/api/v1/chat.py
        payload = {
            "query": "Hello, this is a load test message.",
            "stream": False,
            "model": "gpt-4o",
            # Optional: "conversation_id": "..."
            # Optional: "history": []
        }
        
        with self.client.post("/api/v1/chat", json=payload, headers=self.headers, catch_response=True) as response:
            if response.status_code == 200:
                pass 
            elif response.status_code == 401:
                # Token might be expired, try refreshing and retrying once
                logger.info("401 encountered, refreshing token...")
                if self.refresh_token():
                     with self.client.post("/api/v1/chat", json=payload, headers=self.headers, catch_response=True) as retry_response:
                        if retry_response.status_code != 200:
                             retry_response.failure(f"Chat retry failed: {retry_response.status_code}")
                else:
                     response.failure("Chat failed: 401 and refresh failed")
            else:
                try:
                    error_detail = response.json()
                except:
                    error_detail = response.text
                response.failure(f"Chat failed: {response.status_code} - {error_detail}")

    @task(1)
    def view_profile(self):
        """
        Task B: View user profile. Low weight (1).
        URL: /api/v1/settings/profile
        """
        if not self.token:
             if not self.refresh_token():
                 return

        with self.client.get("/api/v1/settings/profile", headers=self.headers, catch_response=True) as response:
            if response.status_code == 200:
                pass
            elif response.status_code == 401:
                 # Token might be expired, try refreshing
                 logger.info("401 encountered on profile, refreshing token...")
                 if self.refresh_token():
                     with self.client.get("/api/v1/settings/profile", headers=self.headers, catch_response=True) as retry_response:
                         if retry_response.status_code != 200:
                              retry_response.failure(f"Profile retry failed: {retry_response.status_code}")
                 else:
                     response.failure("Profile failed: 401 and refresh failed")
            else:
                 response.failure(f"Profile fetch failed: {response.status_code} - {response.text}")

    @task(2)
    def the_sprinter(self):
        """
        Task C: Upload distinct small files quickly to validate throughput and queue split.
        """
        content = b"sprinter-" + uuid.uuid4().hex.encode()
        label = f"sprinter-{uuid.uuid4().hex[:8]}"
        self._upload_once(label, content)

    @task(1)
    def the_repeater(self):
        """
        Task D: Upload the same file twice to validate deduplication path.
        Expect the second ingest to be near-instant (duplicate skip).
        """
        content = b"repeater-sample-content"
        label = "repeater"

        first = self._upload_once(f"{label}-{uuid.uuid4().hex[:6]}", content)
        time.sleep(2)
        second = self._upload_once(f"{label}-{uuid.uuid4().hex[:6]}", content)

        # Optional sanity check: mark success if second call returns quickly
        if second and second.elapsed.total_seconds() < 1:
            second.success()
