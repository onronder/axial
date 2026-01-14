from pydantic_settings import BaseSettings, SettingsConfigDict
from typing import Optional
import os
import sys

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

    # Microsoft OAuth (OneDrive / SharePoint)
    MICROSOFT_CLIENT_ID: Optional[str] = None
    MICROSOFT_CLIENT_SECRET: Optional[str] = None
    MICROSOFT_REDIRECT_URI: Optional[str] = None
    MICROSOFT_TENANT_ID: str = "common"
    MICROSOFT_SCOPES_ONEDRIVE: str = "offline_access User.Read Files.Read.All"
    MICROSOFT_SCOPES_SHAREPOINT: str = "offline_access User.Read Files.Read.All Sites.Read.All"
    
    # Redis
    REDIS_URL: str = "redis://localhost:6379/0"
    REDIS_JOB_COUNTER_TTL_SECONDS: int = 86400  # 24 hours
    REDIS_JOB_FINALIZE_TTL_SECONDS: int = 3600  # 1 hour
    REDIS_JOB_PROGRESS_UPDATE_BATCH: int = 10
    REDIS_JOB_PROGRESS_UPDATE_INTERVAL: int = 30

    # Dedicated DB URL for least-privilege ingestion role (optional)
    INGESTION_DATABASE_URL: Optional[str] = None
    
    # Email
    RESEND_API_KEY: Optional[str] = None
    EMAILS_FROM_EMAIL: str = "noreply@axiohub.io"
    APP_URL: str = "https://app.axiohub.io"
    
    # Branding
    LOGO_URL: str = "https://raw.githubusercontent.com/onronder/axial/main/frontend-new/public/assets/axio-hub-full-light.png"
    
    # CORS (Critical for Production)
    ALLOWED_ORIGINS: str = ""
    
    # Error Tracking
    SENTRY_DSN: Optional[str] = None
    ENVIRONMENT: str = "development"

    # Rate Limiting
    RATE_LIMIT_DEFAULT: str = "50/minute"

    # Celery time limits (seconds)
    CELERY_TASK_SOFT_TIME_LIMIT: int = 900
    CELERY_TASK_TIME_LIMIT: int = 1200
    
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
    
    RAG_SIMILARITY_THRESHOLD: float = 0.50 
    
    # =========================================================================
    # Advanced Document Parsing (LlamaParse OCR)
    # =========================================================================
    LLAMA_CLOUD_API_KEY: Optional[str] = None 
    
    # =========================================================================
    # Resource Limits & Memory Management
    # =========================================================================
    MAX_FILE_SIZE: int = 100 * 1024 * 1024  # 100MB per file
    MAX_STRUCTURED_FILE_SIZE: int = 50 * 1024 * 1024  # 50MB for CSV/XLSX parsing
    MALWARE_SCAN_MAX_BYTES: int = 1024 * 1024 * 1024  # Skip malware scan above 1GB
    MAX_CHUNK_BATCH_SIZE: int = 100  # Process 100 chunks at a time
    MEMORY_WARNING_THRESHOLD: float = 0.85  # Warn at 85% memory
    MEMORY_CRITICAL_THRESHOLD: float = 0.95  # Stop at 95% memory
    EMBEDDING_BATCH_SIZE: int = 10  # Safe default for OpenAI embeddings
    EMBEDDING_MAX_TOKENS_PER_REQUEST: int = 250000  # Safety cap below OpenAI 300k limit
    EMBEDDING_SLEEP_INTERVAL: float = 0.5  # Seconds between embedding batches
    EMBEDDING_MAX_CONCURRENCY: int = 3  # Max concurrent embedding requests (async path)
    CHUNK_INSERT_BATCH_SIZE: int = 100  # Batch size for PostgREST chunk inserts
    EMBEDDING_ADAPTIVE_LATENCY_FACTOR: float = 0.05  # Extra sleep = batch_duration * factor
    EMBEDDING_ADAPTIVE_MAX_SLEEP: float = 2.0  # Max extra sleep per batch
    EMBEDDING_RATE_LIMIT_BACKOFF_STEP: float = 0.5  # Incremental backoff on rate-limit hits
    EMBEDDING_RATE_LIMIT_BACKOFF_MAX: float = 5.0  # Cap for rate-limit backoff
    EMBEDDING_RATE_LIMIT_DECAY: float = 0.25  # Backoff decay after successful batch

    # Parser timeouts (soft thresholds, seconds)
    TEXT_PARSE_TIMEOUT: int = 60
    PDF_PARSE_TIMEOUT: int = 300
    PDF_PARSE_TIMEOUT_OCR: int = 600

    # =========================================================================
    # Connector Concurrency Limits
    # =========================================================================
    CONNECTOR_CONCURRENCY_DEFAULT: int = 2
    CONNECTOR_CONCURRENCY_GOOGLE_DRIVE: int = 2
    CONNECTOR_CONCURRENCY_NOTION: int = 1
    CONNECTOR_CONCURRENCY_WEB: int = 2
    CONNECTOR_CONCURRENCY_ONEDRIVE: int = 2
    CONNECTOR_CONCURRENCY_SHAREPOINT: int = 2
 

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
    PLAN_ENTERPRISE_SMALL: str = "enterprise_small"
    PLAN_ENTERPRISE_MEDIUM: str = "enterprise_medium"
    PLAN_ENTERPRISE_LARGE: str = "enterprise_large"
    
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

# =============================================================================
# High-Perception Quota Limits (Generous Concurrency, TPM safety valve)
# =============================================================================
# NOTE: These values are intentionally generous on concurrency to maximize
# perceived speed, while TPM caps act as the cost-control governor.
QUOTA_LIMITS = {
    # "Generous" Self-Serve Tiers
    "starter":           {"concurrent": 5,   "storage_mb": 100,     "daily_jobs": 10,    "max_tpm": 20000},
    "pro":               {"concurrent": 10,  "storage_mb": 2000,    "daily_jobs": 100,   "max_tpm": 50000},

    # Enterprise Tiers (High Performance)
    "enterprise_small":  {"concurrent": 15,  "storage_mb": 50000,   "daily_jobs": 1000,  "max_tpm": 100000},
    "enterprise_medium": {"concurrent": 25,  "storage_mb": 200000,  "daily_jobs": 5000,  "max_tpm": 250000},
    "enterprise_large":  {"concurrent": 50,  "storage_mb": 1000000, "daily_jobs": 10000, "max_tpm": 500000},
}

# Initialize settings
settings = Settings()

# =============================================================================
# Sentry Integration for Error Tracking
# =============================================================================

def _is_test_runtime() -> bool:
    return (
        settings.ENVIRONMENT == "test"
        or "PYTEST_CURRENT_TEST" in os.environ
        or "pytest" in sys.modules
    )

if settings.SENTRY_DSN and not _is_test_runtime():
    try:
        import sentry_sdk
        import logging as py_logging  # Import BEFORE using logging.INFO/ERROR
        from sentry_sdk.integrations.celery import CeleryIntegration
        from sentry_sdk.integrations.logging import LoggingIntegration
        
        sentry_sdk.init(
            dsn=settings.SENTRY_DSN,
            environment=settings.ENVIRONMENT,
            integrations=[
                CeleryIntegration(),
                LoggingIntegration(
                    level=py_logging.INFO,
                    event_level=py_logging.ERROR
                )
            ],
            traces_sample_rate=0.1,  # 10% of transactions
            profiles_sample_rate=0.1,  # 10% of transactions
            send_default_pii=False,  # Don't send PII
        )
        
        py_logging.getLogger(__name__).info("✅ Sentry initialized for error tracking")
    except ImportError:
        import logging
        logging.getLogger(__name__).warning("⚠️ Sentry SDK not installed, error tracking disabled")
    except Exception as e:
        import logging
        logging.getLogger(__name__).error(f"❌ Failed to initialize Sentry: {e}")
