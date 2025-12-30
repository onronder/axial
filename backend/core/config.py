from pydantic_settings import BaseSettings, SettingsConfigDict
from typing import Dict, Any, Optional


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
    
    # AI & Multi-Model
    PRIMARY_MODEL_PROVIDER: str = "openai"
    PRIMARY_MODEL_NAME: str = "gpt-4o"
    SECONDARY_MODEL_PROVIDER: str = "groq"
    SECONDARY_MODEL_NAME: str = "llama-3.3-70b-versatile"
    GUARDRAIL_MODEL_PROVIDER: str = "groq"
    GUARDRAIL_MODEL_NAME: str = "llama-3.1-8b-instant"
    RAG_SIMILARITY_THRESHOLD: float = 0.70

    # COMMERCIALIZATION
    MODEL_ALIAS_FAST: str = "fast"
    MODEL_ALIAS_SMART: str = "smart"
    LIMITS_STARTER_FILES: int = 50
    LIMITS_PRO_FILES: int = 2000
    LIMITS_STARTER_MB: int = 100
    LIMITS_PRO_MB: int = 10240
    MSG_UPSELL_SMART: str = "⚡ Upgrade to Pro."
    MSG_UPSELL_FILES: str = "🔒 Upgrade to Pro."

    # POLAR.SH CONFIGURATION
    POLAR_ACCESS_TOKEN: str = ""
    POLAR_WEBHOOK_SECRET: str = ""
    POLAR_ORGANIZATION_ID: str = ""
    POLAR_PRODUCT_ID_STARTER_MONTHLY: str = ""
    POLAR_PRODUCT_ID_PRO_MONTHLY: str = ""
    POLAR_PRODUCT_ID_ENTERPRISE: str = ""
    
    # Deprecated fields but kept for compat just in case
    PLAN_STARTER: str = "starter"
    PLAN_PRO: str = "pro"
    PLAN_ENTERPRISE: str = "enterprise"

    @property
    def POLAR_PRODUCT_MAPPING(self) -> Dict[str, str]:
        return {
            self.POLAR_PRODUCT_ID_STARTER_MONTHLY: "starter",
            self.POLAR_PRODUCT_ID_PRO_MONTHLY: "pro",
            self.POLAR_PRODUCT_ID_ENTERPRISE: "enterprise",
        }

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
    if settings.POLAR_PRODUCT_ID_STARTER_MONTHLY:
        mapping[settings.POLAR_PRODUCT_ID_STARTER_MONTHLY] = settings.PLAN_STARTER
    if settings.POLAR_PRODUCT_ID_PRO_MONTHLY:
        mapping[settings.POLAR_PRODUCT_ID_PRO_MONTHLY] = settings.PLAN_PRO
    if settings.POLAR_PRODUCT_ID_ENTERPRISE:
        mapping[settings.POLAR_PRODUCT_ID_ENTERPRISE] = settings.PLAN_ENTERPRISE
    return mapping


settings = Settings()

