from pydantic_settings import BaseSettings, SettingsConfigDict
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

    # Rate Limiting
    RATE_LIMIT_DEFAULT: str = "50/minute"
    
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
    # Groq API Key (for secondary/guardrail models)
    # RAG Settings
    RAG_SIMILARITY_THRESHOLD: float = 0.70  # Minimum cosine similarity for context injection

    # =========================================================================
    # COMMERCIALIZATION & TIER LIMITS (Phase 6)
    # =========================================================================
    
    # Model Abstraction (Internal Mapping)
    # Frontend sends "fast" -> Maps to SECONDARY_MODEL_NAME (e.g. Llama/Mini)
    # Frontend sends "smart" -> Maps to PRIMARY_MODEL_NAME (e.g. GPT-4o)
    MODEL_ALIAS_FAST: str = "fast"
    MODEL_ALIAS_SMART: str = "smart"
    
    # Storage Limits (File Counts)
    LIMITS_STARTER_FILES: int = 50
    LIMITS_PRO_FILES: int = 2000
    
    # Storage Limits (Total Size in MB) - Enforcement logic needs bytes (MB * 1024 * 1024)
    LIMITS_STARTER_MB: int = 100
    LIMITS_PRO_MB: int = 10240  # 10 GB
    
    # Marketing & Upsell Messages
    MSG_UPSELL_SMART: str = "⚡ This answer used 'Axio Fast'. Upgrade to Pro for 'Axio Pro' intelligence."
    MSG_UPSELL_FILES: str = "🔒 You have reached your file limit. Upgrade to Pro for 10GB storage."
    
    # =========================================================================
    # Payment Integration (Polar.sh)
    # =========================================================================
    
    # Webhook secret for signature verification
    POLAR_WEBHOOK_SECRET: Optional[str] = None
    
    # Product ID mappings (Polar Product UUID -> Internal Plan Name)
    # These are placeholders - replace with real Polar product IDs in .env
    POLAR_STARTER_PRODUCT_ID: Optional[str] = None
    POLAR_PRO_PRODUCT_ID: Optional[str] = None
    POLAR_ENTERPRISE_PRODUCT_ID: Optional[str] = None

    # Pydantic V2 settings configuration
    model_config = SettingsConfigDict(
        env_file=[".env", "../.env"],
        extra="ignore"
    )


# Product mapping helper - maps Polar product IDs to internal plan names
def get_polar_product_mapping() -> dict:
    """
    Returns mapping of Polar Product IDs to internal plan names.
    Only includes products that are configured (not None).
    """
    mapping = {}
    if settings.POLAR_STARTER_PRODUCT_ID:
        mapping[settings.POLAR_STARTER_PRODUCT_ID] = "starter"
    if settings.POLAR_PRO_PRODUCT_ID:
        mapping[settings.POLAR_PRO_PRODUCT_ID] = "pro"
    if settings.POLAR_ENTERPRISE_PRODUCT_ID:
        mapping[settings.POLAR_ENTERPRISE_PRODUCT_ID] = "enterprise"
    return mapping


settings = Settings()

