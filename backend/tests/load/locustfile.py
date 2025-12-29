import os
import logging
from locust import HttpUser, task, between, events
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# Set up logging
logger = logging.getLogger(__name__)

SUPABASE_URL = os.getenv("SUPABASE_URL")
SUPABASE_KEY = os.getenv("SUPABASE_PUBLISHABLE_KEY") or os.getenv("SUPABASE_ANON_KEY")

if not SUPABASE_URL or not SUPABASE_KEY:
    logger.warning("SUPABASE_URL or SUPABASE_PUBLISHABLE_KEY not set. Auth might fail.")

# Global cache for token to avoid rate limiting
import time
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
        
        response = client.post(
            auth_url, 
            json={
                "email": "test@example.com",
                "password": "password"
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
    # Default host to prevent InvalidSchema if user forgets http://
    host = "http://localhost:8000"
    
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


