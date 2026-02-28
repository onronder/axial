import os
import sys

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    SUPABASE_URL: str
    SUPABASE_SECRET_KEY: str  # Replaces SUPABASE_KEY for backend/service_role
    SUPABASE_JWT_SECRET: str
    SUPABASE_PUBLISHABLE_KEY: str | None = None

    OPENAI_API_KEY: str
    API_KEY: str = ""

    # Google OAuth
    GOOGLE_CLIENT_ID: str | None = None
    GOOGLE_CLIENT_SECRET: str | None = None
    GOOGLE_REDIRECT_URI: str | None = None

    # Notion OAuth
    NOTION_CLIENT_ID: str | None = None
    NOTION_CLIENT_SECRET: str | None = None
    NOTION_REDIRECT_URI: str | None = None

    # Microsoft OAuth (OneDrive / SharePoint)
    MICROSOFT_CLIENT_ID: str | None = None
    MICROSOFT_CLIENT_SECRET: str | None = None
    MICROSOFT_REDIRECT_URI: str | None = None
    MICROSOFT_TENANT_ID: str = "common"
    MICROSOFT_SCOPES_ONEDRIVE: str = "offline_access User.Read Files.Read.All"
    MICROSOFT_SCOPES_SHAREPOINT: str = "offline_access User.Read Files.Read.All Sites.Read.All"

    # Dropbox OAuth (Supports Personal & Business/Team accounts)
    DROPBOX_CLIENT_ID: str | None = None
    DROPBOX_CLIENT_SECRET: str | None = None
    DROPBOX_REDIRECT_URI: str | None = None

    # GitHub OAuth (Code repository integration)
    GITHUB_CLIENT_ID: str | None = None
    GITHUB_CLIENT_SECRET: str | None = None
    GITHUB_REDIRECT_URI: str | None = None

    # Box OAuth (Enterprise cloud storage)
    BOX_CLIENT_ID: str | None = None
    BOX_CLIENT_SECRET: str | None = None
    BOX_REDIRECT_URI: str | None = None

    # Redis
    REDIS_URL: str = "redis://localhost:6379/0"
    REDIS_JOB_COUNTER_TTL_SECONDS: int = 86400  # 24 hours
    REDIS_JOB_FINALIZE_TTL_SECONDS: int = 3600  # 1 hour
    REDIS_JOB_PROGRESS_UPDATE_BATCH: int = 10
    REDIS_JOB_PROGRESS_UPDATE_INTERVAL: int = 30

    # Dedicated DB URL for least-privilege ingestion role (optional)
    INGESTION_DATABASE_URL: str | None = None

    # Email
    RESEND_API_KEY: str | None = None
    EMAILS_FROM_EMAIL: str = "noreply@axiohub.io"
    APP_URL: str = "https://app.axiohub.io"

    # Branding
    LOGO_URL: str = "https://raw.githubusercontent.com/onronder/axial/main/frontend-new/public/assets/axio-hub-full-light.png"

    # CORS (Critical for Production)
    ALLOWED_ORIGINS: str = ""

    # Error Tracking
    SENTRY_DSN: str | None = None
    ENVIRONMENT: str = "development"

    # Rate Limiting
    RATE_LIMIT_DEFAULT: str = "50/minute"

    # Celery time limits (seconds)
    CELERY_TASK_SOFT_TIME_LIMIT: int = 900
    CELERY_TASK_TIME_LIMIT: int = 1200

    # =========================================================================
    # Celery Worker Memory Management (Enterprise 8-Core/32GB)
    # =========================================================================
    # Self-healing workers with prefork pool for CPU-bound file processing.
    #
    # Memory Budget (32GB Node):
    #   Total RAM:       32 GB
    #   System Reserve:  -4 GB (OS, Redis, API, buffers)
    #   Worker Pool:     28 GB
    #   Concurrency:     8 workers (1 per CPU core)
    #   Per Worker:      28GB ÷ 8 = 3.5 GB
    #   Safety Margin:   -0.5 GB
    #   Final Limit:     3.0 GB (3,000,000 KB)
    #
    # Peak Usage: 8 × 3GB = 24GB << 28GB available ✅
    #
    # CRITICAL: Requires --pool=prefork (gevent does NOT support memory limits)

    CELERY_WORKER_MAX_MEMORY_PER_CHILD: int = 3000000  # 3GB in KB
    CELERY_WORKER_MAX_TASKS_PER_CHILD: int = 1000      # High for enterprise RAM
    CELERY_WORKER_CONCURRENCY: int = 8                 # Match CPU cores

    # =========================================================================
    # AI & Multi-Model Configuration
    # =========================================================================

    PRIMARY_MODEL_PROVIDER: str = "openai"
    PRIMARY_MODEL_NAME: str = "gpt-4o"

    SECONDARY_MODEL_PROVIDER: str = "openai"
    SECONDARY_MODEL_NAME: str = "gpt-4o-mini"

    GUARDRAIL_MODEL_PROVIDER: str = "groq"
    GUARDRAIL_MODEL_NAME: str = "llama-3.1-8b-instant"

    # Groq API Key
    GROQ_API_KEY: str | None = None

    # Grok (xAI) OpenAI-compatible API
    GROK_API_KEY: str | None = None
    GROK_BASE_URL: str = "https://api.x.ai/v1"
    GROK_MODEL_NAME: str | None = None
    GROQ_CHAT_MODEL_NAME: str = "llama-3.3-70b-versatile"

    RAG_SIMILARITY_THRESHOLD: float = 0.35  # Lowered from 0.50 for better recall on conversational content

    # Cohere (Reranking)
    COHERE_API_KEY: str | None = None
    COHERE_RERANK_MODEL: str = "rerank-v3.5"

    # Semantic Cache (H7)
    SEMANTIC_CACHE_ENABLED: bool = False  # Disabled by default until Redis is verified in production
    SEMANTIC_CACHE_TTL: int = 3600  # 1 hour

    # =========================================================================
    # Guardrails Pre-Flight Search Configuration
    # =========================================================================
    # These settings control the document-context aware guardrails feature.
    # Pre-flight search checks if documents match a query before trusting
    # the LLM's intent classification.

    GUARDRAIL_PREFLIGHT_ENABLED: bool = True  # Enable/disable pre-flight document check
    GUARDRAIL_PREFLIGHT_THRESHOLD: float = 0.35  # Lower than RAG threshold for existence check
    GUARDRAIL_PREFLIGHT_MATCH_COUNT: int = 3  # Max documents to check
    GUARDRAIL_PREFLIGHT_MIN_MATCHES: int = 1  # Minimum matches to trigger override

    # =========================================================================
    # Advanced Document Parsing (LlamaParse OCR)
    # =========================================================================
    LLAMA_CLOUD_API_KEY: str | None = None

    # =========================================================================
    # Vision LLM Configuration
    # =========================================================================
    # Enable Vision LLM for semantic image/diagram understanding
    # When enabled, images are analyzed by Vision LLMs for meaning extraction
    VISION_LLM_ENABLED: bool = False  # Opt-in due to cost considerations
    VISION_LLM_PROVIDER: str = "openai"  # "openai" | "gemini"
    VISION_LLM_MAX_IMAGE_SIZE: int = 20 * 1024 * 1024  # 20MB max image size

    # =========================================================================
    # Resource Limits & Memory Management
    # =========================================================================
    MAX_FILE_SIZE: int = 100 * 1024 * 1024  # 100MB per file
    MAX_STRUCTURED_FILE_SIZE: int = 50 * 1024 * 1024  # 50MB for CSV/XLSX parsing
    MALWARE_SCAN_MAX_BYTES: int = 1024 * 1024 * 1024  # Skip malware scan above 1GB
    MALWARE_SCAN_FAIL_CLOSED: bool = os.getenv("ENVIRONMENT", "development") == "production"  # Reject uploads when scanner unavailable (production only)
    MAX_CHUNK_BATCH_SIZE: int = 100  # Process 100 chunks at a time
    MEMORY_WARNING_THRESHOLD: float = 0.85  # Warn at 85% memory
    MEMORY_CRITICAL_THRESHOLD: float = 0.95  # Stop at 95% memory
    EMBEDDING_BATCH_SIZE: int = 200  # M9: Increased from 10 for throughput (1000 safety cap in service)
    EMBEDDING_MAX_TOKENS_PER_REQUEST: int = 250000  # Safety cap below OpenAI 300k limit
    EMBEDDING_SLEEP_INTERVAL: float = 0.1  # M9: Reduced from 0.5 for throughput
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
    # GHOST PROTOCOL: Zero-Retention Security Configuration
    # =========================================================================
    # These settings control the "Zero-Retention" privacy architecture.
    # Content is encrypted at rest, files are securely wiped after processing.

    # Encryption key for document chunk content at rest (AES-256 via Fernet)
    # CRITICAL: Must be set in production - app will refuse to ingest without it
    # Generate with: python -c 'from cryptography.fernet import Fernet; print(Fernet.generate_key().decode())'
    CHUNK_ENCRYPTION_KEY: str | None = None

    # Memory processing threshold for SmartBuffer
    # Files below this use RAM (BytesIO), above use SecureTempFile (disk)
    # Default: 10MB - balances speed vs OOM risk
    MAX_RAM_PROCESS_LIMIT: int = 10 * 1024 * 1024

    # Secure wipe passes for forensic-grade file deletion
    # 1 = fast (single overwrite), 3 = DoD 5220.22-M compliant (3 passes)
    SECURE_WIPE_PASSES: int = 3  # Default to DoD 3-pass for enterprise compliance

    # Secure wipe pattern: "dod_5220_22_m" or "random"
    # dod_5220_22_m: 0x00 → 0xFF → Random (DoD compliant)
    # random: All passes use random data (faster, still secure)
    SECURE_WIPE_PATTERN: str = "dod_5220_22_m"

    # Enable verify read after secure wipe
    # Samples file content to ensure random pass completed successfully
    SECURE_WIPE_VERIFY: bool = True

    # Strict encryption mode: crash on unencrypted content retrieval
    # For greenfield deployments (no legacy data), this should ALWAYS be True
    # Set to False only for migration periods with legacy plaintext data
    STRICT_ENCRYPTION_MODE: bool = True

    # =========================================================================
    # Connector Concurrency Limits
    # =========================================================================
    CONNECTOR_CONCURRENCY_DEFAULT: int = 2
    CONNECTOR_CONCURRENCY_GOOGLE_DRIVE: int = 2
    CONNECTOR_CONCURRENCY_NOTION: int = 1
    CONNECTOR_CONCURRENCY_WEB: int = 2
    CONNECTOR_CONCURRENCY_ONEDRIVE: int = 2
    CONNECTOR_CONCURRENCY_SHAREPOINT: int = 2
    CONNECTOR_CONCURRENCY_DROPBOX: int = 2
    CONNECTOR_CONCURRENCY_GITHUB: int = 2
    CONNECTOR_CONCURRENCY_BOX: int = 2
    CONNECTOR_CONCURRENCY_S3: int = 4  # S3 has high rate limits
    CONNECTOR_CONCURRENCY_SFTP: int = 2  # SSH connection limits

    # =========================================================================
    # YouTube / Bright Data Unlocker API Configuration
    # =========================================================================
    # Required for YouTube transcript fetching from cloud infrastructure.
    # YouTube blocks most cloud provider IPs (AWS, GCP, Azure, Railway, etc.)
    #
    # Bright Data Unlocker API setup:
    #   1. Create an "Unlocker API" zone in Bright Data dashboard
    #   2. Get your API token from Bright Data settings
    #   3. Set BRIGHTDATA_API_KEY and BRIGHTDATA_UNLOCKER_ZONE
    #
    # API endpoint: https://api.brightdata.com/request
    # Docs: https://docs.brightdata.com/scraping-automation/web-unlocker/web-unlocker-api
    #
    BRIGHTDATA_API_KEY: str | None = None  # Bearer token for Bright Data API
    BRIGHTDATA_UNLOCKER_ZONE: str = "axio_unlocker"  # Zone name for Unlocker API
    BRIGHTDATA_TIMEOUT: int = 60  # Request timeout in seconds (YouTube can be slow)
    BRIGHTDATA_RETRY_COUNT: int = 3  # Retry attempts on failure
    BRIGHTDATA_RETRY_DELAY: float = 2.0  # Base delay between retries (exponential backoff)

    # Legacy proxy settings (kept for backwards compatibility)
    YOUTUBE_PROXY_URL: str | None = None
    YOUTUBE_PROXY_ENABLED: bool = False  # Disabled - use Unlocker API instead
    YOUTUBE_PROXY_TIMEOUT: int = 30
    YOUTUBE_PROXY_RETRY_COUNT: int = 3
    YOUTUBE_PROXY_RETRY_DELAY: float = 1.0
    YOUTUBE_DIRECT_FALLBACK: bool = True  # Try direct connection if Unlocker API fails


    # =========================================================================
    # COMMERCIALIZATION & TIER LIMITS
    # =========================================================================

    MODEL_ALIAS_FAST: str = "fast"
    MODEL_ALIAS_SMART: str = "smart"

    LIMITS_STARTER_FILES: int = 50
    LIMITS_PRO_FILES: int = 2000
    LIMITS_STARTER_SCOPES: int = 5
    LIMITS_PRO_SCOPES: int = 100
    LIMITS_ENTERPRISE_SCOPES: int = 1000

    LIMITS_STARTER_MB: int = 100
    LIMITS_PRO_MB: int = 10240
    LIMITS_STARTER_LLM_TOKENS: int = 1000000
    LIMITS_PRO_LLM_TOKENS: int = 10000000
    LIMITS_ENTERPRISE_LLM_TOKENS: int = 100000000

    MSG_UPSELL_SMART: str = "⚡ This answer used 'Axio Fast'. Upgrade to Pro for 'Axio Pro' intelligence."
    MSG_UPSELL_FILES: str = "🔒 You have reached your file limit. Upgrade to Pro for 10GB storage."

    # Optional load balancing across LLM providers
    LLM_LOAD_BALANCE: bool = False

    # =========================================================================
    # LLM Call Safety & Performance Settings
    # =========================================================================
    # Timeouts prevent hung requests from consuming resources indefinitely
    LLM_REQUEST_TIMEOUT: int = 120  # Base timeout for LLM HTTP calls (seconds)
    LLM_STREAM_TIMEOUT: int = 60  # Timeout for streaming responses (seconds)
    LLM_MAX_CONCURRENT_REQUESTS: int = 20  # Global semaphore limit for LLM calls
    LLM_MAX_TOKENS_PER_REQUEST: int = 50000  # Max input tokens per single request
    LLM_HEARTBEAT_INTERVAL: float = 10.0  # SSE heartbeat interval (seconds)

    # =========================================================================
    # Payment Integration (Polar.sh)
    # =========================================================================

    POLAR_ACCESS_TOKEN: str | None = None
    POLAR_ORGANIZATION_ID: str | None = None
    POLAR_WEBHOOK_SECRET: str | None = None

    POLAR_PRODUCT_ID_STARTER_MONTHLY: str | None = None
    POLAR_PRODUCT_ID_PRO_MONTHLY: str | None = None
    POLAR_PRODUCT_ID_ENTERPRISE: str | None = None

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
        import logging as py_logging  # Import BEFORE using logging.INFO/ERROR

        import sentry_sdk
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
