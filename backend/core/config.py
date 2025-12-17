from pydantic_settings import BaseSettings
from typing import Optional

class Settings(BaseSettings):
    SUPABASE_URL: str
    SUPABASE_SECRET_KEY: str  # Replaces SUPABASE_KEY for backend/service_role
    SUPABASE_PUBLISHABLE_KEY: Optional[str] = None # Optional, usually for client-side
    
    OPENAI_API_KEY: str
    API_KEY: str = "default-insecure-key"

    class Config:
        env_file = [".env", "../.env"]
        extra = "ignore" # Ignore extra fields in .env

settings = Settings()
