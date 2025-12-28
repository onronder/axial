from locust import HttpUser, task, between, events
import logging

# Set up logging
logger = logging.getLogger(__name__)

class AxioUser(HttpUser):
    # Realistic wait time between tasks (1-5 seconds)
    wait_time = between(1, 5)

    def on_start(self):
        """
        Log in a user ONCE when the simulation starts.
        Uses dummy credentials as requested.
        """
        self.email = "test@example.com"
        self.password = "password"
        self.token = None
        self.headers = {}

        # Login to get valid token
        logger.info(f"Logging in user: {self.email}")
        # Note: Using standard /auth/jwt/login endpoint. 
        # If your API uses /api/v1/auth/login, update the path below.
        with self.client.post("/auth/jwt/login", data={
            "username": self.email,
            "password": self.password
        }, catch_response=True) as response:
            if response.status_code == 200:
                try:
                    data = response.json()
                    self.token = data.get("access_token")
                    if self.token:
                        self.headers = {"Authorization": f"Bearer {self.token}"}
                        logger.info(f"Login successful for {self.email}")
                    else:
                        response.failure("No access token in response")
                        self.stop()
                except Exception as e:
                    response.failure(f"Failed to parse login response: {e}")
                    self.stop()
            else:
                # Fail gracefully as requested
                logger.error(f"Login failed: {response.status_code} - {response.text}")
                response.failure(f"Login failed with status {response.status_code}")
                self.stop() # Stop this user from running further tasks

    @task(3)
    def chat_interaction(self):
        """
        Task A: Simulate sending a chat message. High weight (3).
        """
        if not self.token:
            return

        payload = {
            "messages": [
                {"role": "user", "content": "Hello, this is a load test message."}
            ],
            "stream": False,
            "use_search": False
        }
        
        with self.client.post("/api/v1/chat", json=payload, headers=self.headers, catch_response=True) as response:
            if response.status_code == 200:
                pass # Success
            else:
                response.failure(f"Chat failed: {response.status_code} - {response.text}")

    @task(1)
    def view_profile(self):
        """
        Task B: View user profile. Low weight (1).
        URL: /api/v1/settings/profile (mapped from /api/v1/users/me requirement)
        """
        if not self.token:
            return

        with self.client.get("/api/v1/settings/profile", headers=self.headers, catch_response=True) as response:
            if response.status_code != 200:
                 response.failure(f"Profile fetch failed: {response.status_code} - {response.text}")
