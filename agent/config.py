import os

class Config:
    BACKEND_URL = "http://localhost:8000/api/v1/ingest"
    API_KEY = "default-insecure-key"
    WATCHED_FOLDER = os.path.abspath("watched_folder")
    CLIENT_ID = "desktop-agent-01"
