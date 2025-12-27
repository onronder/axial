from pydantic_settings import BaseSettings
from typing import Optional

class Settings(BaseSettings):
    SUPABASE_URL: str
    SUPABASE_SECRET_KEY: str  # Replaces SUPABASE_KEY for backend/service_role
    SUPABASE_JWT_SECRET: str
    SUPABASE_PUBLISHABLE_KEY: Optional[str] = None # Optional, usually for client-side
    
    OPENAI_API_KEY: str
    API_KEY: str = "default-insecure-key"
    
    # Google OAuth
    GOOGLE_CLIENT_ID: Optional[str] = None
    GOOGLE_CLIENT_SECRET: Optional[str] = None
    GOOGLE_REDIRECT_URI: Optional[str] = None
    
    # Notion OAuth
    NOTION_CLIENT_ID: Optional[str] = None
    NOTION_CLIENT_SECRET: Optional[str] = None
    NOTION_REDIRECT_URI: Optional[str] = None
    
    # Redis (Celery broker/backend)
    REDIS_URL: str = "redis://localhost:6379/0"
    
    # Email (Resend)
    RESEND_API_KEY: Optional[str] = None
    EMAILS_FROM_EMAIL: str = "noreply@axiohub.io"
    APP_URL: str = "https://axiohub.io"
    
    # Error Tracking (Sentry)
    SENTRY_DSN: Optional[str] = None
    
    # =========================================================================
    # AI & Multi-Model Configuration
    # =========================================================================
    
    # Primary Model (High Intelligence - GPT-4o)
    # Used for: complex reasoning, summarization, final answers
    PRIMARY_MODEL_PROVIDER: str = "openai"
    PRIMARY_MODEL_NAME: str = "gpt-4o"
    
    # Secondary Model (High Speed/Low Cost - Llama 3.3 70B via Groq)
    # Used for: fast responses, bulk processing, cost optimization
    SECONDARY_MODEL_PROVIDER: str = "groq"
    SECONDARY_MODEL_NAME: str = "llama-3.3-70b-versatile"
    
    # Guardrail Model (Ultra Fast - Llama 3.1 8B via Groq)
    # Used for: input validation, classification, quick checks
    GUARDRAIL_MODEL_PROVIDER: str = "groq"
    GUARDRAIL_MODEL_NAME: str = "llama-3.1-8b-instant"
    
    # Groq API Key (for secondary/guardrail models)
    GROQ_API_KEY: Optional[str] = None

    class Config:
        env_file = [".env", "../.env"]
        extra = "ignore" # Ignore extra fields in .env

settings = Settings()
