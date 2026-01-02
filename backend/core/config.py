from pydantic_settings import BaseSettings, SettingsConfigDict
from typing import Optional

class Settings(BaseSettings):
    SUPABASE_URL: str
    SUPABASE_SECRET_KEY: str  # Replaces SUPABASE_KEY for backend/service_role
    SUPABASE_JWT_SECRET: str
    SUPABASE_PUBLISHABLE_KEY: Optional[str] = None 
    
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
    
    # Redis
    REDIS_URL: str = "redis://localhost:6379/0"
    
    # Email
    RESEND_API_KEY: Optional[str] = None
    EMAILS_FROM_EMAIL: str = "noreply@axiohub.io"
    APP_URL: str = "https://axiohub.io"
    
    # Branding
    LOGO_URL: str = "https://raw.githubusercontent.com/onronder/axial/main/frontend-new/public/assets/axio-hub-full-light.png"
    
    # CORS (Critical for Production)
    ALLOWED_ORIGINS: str = ""
    
    # Error Tracking
    SENTRY_DSN: Optional[str] = None

    # Rate Limiting
    RATE_LIMIT_DEFAULT: str = "50/minute"
    
    # =========================================================================
    # AI & Multi-Model Configuration
    # =========================================================================
    
    PRIMARY_MODEL_PROVIDER: str = "openai"
    PRIMARY_MODEL_NAME: str = "gpt-4o"
    
    SECONDARY_MODEL_PROVIDER: str = "groq"
    SECONDARY_MODEL_NAME: str = "llama-3.3-70b-versatile"
    
    GUARDRAIL_MODEL_PROVIDER: str = "groq"
    GUARDRAIL_MODEL_NAME: str = "llama-3.1-8b-instant"
    
    # Groq API Key
    GROQ_API_KEY: Optional[str] = None
    
    RAG_SIMILARITY_THRESHOLD: float = 0.70 

    # =========================================================================
    # COMMERCIALIZATION & TIER LIMITS
    # =========================================================================
    
    MODEL_ALIAS_FAST: str = "fast"
    MODEL_ALIAS_SMART: str = "smart"
    
    LIMITS_STARTER_FILES: int = 50
    LIMITS_PRO_FILES: int = 2000
    
    LIMITS_STARTER_MB: int = 100
    LIMITS_PRO_MB: int = 10240 
    
    MSG_UPSELL_SMART: str = "⚡ This answer used 'Axio Fast'. Upgrade to Pro for 'Axio Pro' intelligence."
    MSG_UPSELL_FILES: str = "🔒 You have reached your file limit. Upgrade to Pro for 10GB storage."
    
    # =========================================================================
    # Payment Integration (Polar.sh)
    # =========================================================================
    
    POLAR_ACCESS_TOKEN: Optional[str] = None
    POLAR_ORGANIZATION_ID: Optional[str] = None
    POLAR_WEBHOOK_SECRET: Optional[str] = None
    
    POLAR_PRODUCT_ID_STARTER_MONTHLY: Optional[str] = None
    POLAR_PRODUCT_ID_PRO_MONTHLY: Optional[str] = None
    POLAR_PRODUCT_ID_ENTERPRISE: Optional[str] = None
    
    PLAN_STARTER: str = "starter"
    PLAN_PRO: str = "pro"
    PLAN_ENTERPRISE: str = "enterprise"
    
    @property
    def POLAR_PRODUCT_MAPPING(self) -> dict:
        mapping = {}
        if self.POLAR_PRODUCT_ID_STARTER_MONTHLY:
            mapping[self.POLAR_PRODUCT_ID_STARTER_MONTHLY] = self.PLAN_STARTER
        if self.POLAR_PRODUCT_ID_PRO_MONTHLY:
            mapping[self.POLAR_PRODUCT_ID_PRO_MONTHLY] = self.PLAN_PRO
        if self.POLAR_PRODUCT_ID_ENTERPRISE:
            mapping[self.POLAR_PRODUCT_ID_ENTERPRISE] = self.PLAN_ENTERPRISE
        return mapping

    model_config = SettingsConfigDict(
        env_file=[".env", "../.env"],
        extra="ignore"
    )

def get_polar_product_mapping() -> dict:
    mapping = {}
    if settings.POLAR_PRODUCT_ID_STARTER_MONTHLY:
        mapping[settings.POLAR_PRODUCT_ID_STARTER_MONTHLY] = settings.PLAN_STARTER
    if settings.POLAR_PRODUCT_ID_PRO_MONTHLY:
        mapping[settings.POLAR_PRODUCT_ID_PRO_MONTHLY] = settings.PLAN_PRO
    if settings.POLAR_PRODUCT_ID_ENTERPRISE:
        mapping[settings.POLAR_PRODUCT_ID_ENTERPRISE] = settings.PLAN_ENTERPRISE
    return mapping

settings = Settings()
