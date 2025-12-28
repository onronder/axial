from locust import HttpUser, task, between, events
import random
import string
import logging

# Set up logging
logger = logging.getLogger(__name__)

class AxioUser(HttpUser):
    # Aggressive testing - wait 1 second between tasks
    wait_time = lambda self: 1.0

    def on_start(self):
        """
        Register a random user and log in to get the access token.
        """
        self.email = f"loadtest_{''.join(random.choices(string.ascii_lowercase + string.digits, k=8))}@example.com"
        self.password = "LoadTest123!"
        self.first_name = "Load"
        self.last_name = "Tester"

        # Register
        logger.info(f"Registering user: {self.email}")
        with self.client.post("/auth/register", json={
            "email": self.email,
            "password": self.password,
            "first_name": self.first_name,
            "last_name": self.last_name,
            "terms_accepted": True
        }, catch_response=True) as response:
            if response.status_code != 200:
                # If registration fails (e.g., email taken), try logging in
                if response.status_code == 400 and "Email already registered" in response.text:
                    logger.info("User already exists, proceeding to login.")
                else:
                    response.failure(f"Registration failed: {response.text}")
                    return

        # Login to get valid token
        logger.info(f"Logging in user: {self.email}")
        with self.client.post("/auth/jwt/login", data={
            "username": self.email,
            "password": self.password
        }, catch_response=True) as response:
            if response.status_code == 200:
                data = response.json()
                self.token = data.get("access_token")
                self.headers = {"Authorization": f"Bearer {self.token}"}
                logger.info(f"Login successful for {self.email}")
            else:
                response.failure(f"Login failed: {response.text}")
                self.token = None

    @task(3)
    def chat(self):
        """
        Simulate sending a chat message. Weighted higher (3x) than document listing.
        """
        if not hasattr(self, 'token') or not self.token:
            return

        payload = {
            "message": "Hello, this is a load test message.",
            "stream": False # Disable streaming for simpler load testing verification
        }
        
        # Determine endpoint - verify if /api/v1/chat exists or needs specific router
        # Assuming /api/v1/chat based on task description
        with self.client.post("/api/v1/chat", json=payload, headers=self.headers, catch_response=True) as response:
            if response.status_code == 200:
                # Basic check for response structure
                if "response" not in response.json() and "content" not in response.json():
                     response.failure("Invalid chat response structure")
            else:
                response.failure(f"Chat failed: {response.status_code} - {response.text}")

    @task(1)
    def list_documents(self):
        """
        Simulate listing documents (DB read).
        """
        if not hasattr(self, 'token') or not self.token:
            return

        with self.client.get("/api/v1/documents", headers=self.headers, catch_response=True) as response:
            if response.status_code != 200:
                 response.failure(f"List documents failed: {response.status_code} - {response.text}")
