"""
Security Module - Authentication & Application-Level Encryption

This module provides:
1. JWT authentication for API requests
2. OAuth token encryption (ENCRYPTION_KEY)
3. Ghost Protocol content encryption (CHUNK_ENCRYPTION_KEY) for zero-retention

Ghost Protocol ensures:
- Content is encrypted at rest using AES-256 (Fernet)
- Production requires encryption key (fail-secure)
- Strict mode rejects unencrypted content retrieval
"""

import logging
import os

import jwt
from fastapi import HTTPException, Security, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer

from core.config import settings

# =============================================================================
# FERNET ENCRYPTION SETUP
# =============================================================================

try:
    from cryptography.fernet import Fernet, InvalidToken
    _CRYPTO_AVAILABLE = True
except ImportError:
    _CRYPTO_AVAILABLE = False
    # Create a dummy InvalidToken for type checking when crypto is unavailable
    InvalidToken = Exception  # type: ignore

# -----------------------------------------------------------------------------
# OAuth Token Encryption (existing functionality)
# -----------------------------------------------------------------------------
ENCRYPTION_KEY = os.getenv("ENCRYPTION_KEY")
ENCRYPTION_KEYS = [
    key.strip()
    for key in (ENCRYPTION_KEY or "").split(",")
    if key.strip()
]
ENVIRONMENT = os.getenv("ENVIRONMENT", "development")

# SECURITY: Mandatory encryption in production
if ENVIRONMENT == "production" and not ENCRYPTION_KEYS:
    raise RuntimeError(
        "FATAL: ENCRYPTION_KEY is required in production. "
        "Generate with: python -c 'from cryptography.fernet import Fernet; print(Fernet.generate_key().decode())'"
    )

if ENCRYPTION_KEYS and _CRYPTO_AVAILABLE:
    try:
        cipher_suite = Fernet(ENCRYPTION_KEYS[0].encode())
        cipher_suites = [cipher_suite]
        for key in ENCRYPTION_KEYS[1:]:
            cipher_suites.append(Fernet(key.encode()))
        HAS_ENCRYPTION = True
    except (ValueError, Exception) as e:
        raise RuntimeError(
            f"FATAL: Invalid ENCRYPTION_KEY format. "
            f"Keys must be 32 url-safe base64-encoded bytes. "
            f"Generate with: python -c 'from cryptography.fernet import Fernet; print(Fernet.generate_key().decode())' "
            f"Error: {e}"
        ) from e
else:
    cipher_suite = None
    cipher_suites = None
    HAS_ENCRYPTION = False

# -----------------------------------------------------------------------------
# Ghost Protocol: Chunk Content Encryption with Key Rotation Support
# -----------------------------------------------------------------------------
# Supports comma-separated keys for rotation:
# CHUNK_ENCRYPTION_KEY="new_key,old_key,older_key"
# - First key is used for encryption
# - All keys are tried for decryption (in order)
# This allows seamless key rotation without data migration

_CHUNK_ENCRYPTION_KEYS_RAW = os.getenv("CHUNK_ENCRYPTION_KEY", "")
_CHUNK_ENCRYPTION_KEYS = [
    key.strip()
    for key in _CHUNK_ENCRYPTION_KEYS_RAW.split(",")
    if key.strip()
]

# CRITICAL: Fail-secure in production - app cannot ingest without encryption
if ENVIRONMENT == "production" and not _CHUNK_ENCRYPTION_KEYS:
    raise RuntimeError(
        "FATAL: CHUNK_ENCRYPTION_KEY is required in production for Ghost Protocol. "
        "Generate with: python -c 'from cryptography.fernet import Fernet; print(Fernet.generate_key().decode())'"
    )

# Initialize cipher suites for key rotation support
if _CHUNK_ENCRYPTION_KEYS and _CRYPTO_AVAILABLE:
    try:
        _chunk_cipher = Fernet(_CHUNK_ENCRYPTION_KEYS[0].encode())  # Primary for encryption
        _chunk_ciphers = [Fernet(key.encode()) for key in _CHUNK_ENCRYPTION_KEYS]  # All for decryption
        HAS_CHUNK_ENCRYPTION = True
    except (ValueError, Exception) as e:
        raise RuntimeError(
            f"FATAL: Invalid CHUNK_ENCRYPTION_KEY format. "
            f"Keys must be 32 url-safe base64-encoded bytes. "
            f"Generate with: python -c 'from cryptography.fernet import Fernet; print(Fernet.generate_key().decode())' "
            f"Error: {e}"
        ) from e
else:
    _chunk_cipher = None
    _chunk_ciphers = []
    HAS_CHUNK_ENCRYPTION = False

logger = logging.getLogger(__name__)
security = HTTPBearer()

# =============================================================================
# METRICS INTEGRATION
# =============================================================================
try:
    from core.metrics import METRICS_ENABLED, encryption_operations
except ImportError:
    METRICS_ENABLED = False
    class _DummyMetric:
        def labels(self, *args, **kwargs): return self
        def inc(self, *args, **kwargs): pass
    encryption_operations = _DummyMetric()


# =============================================================================
# GHOST PROTOCOL EXCEPTIONS
# =============================================================================

class EncryptionError(Exception):
    """Raised when content encryption/decryption fails."""
    pass


class UnencryptedContentError(Exception):
    """
    Raised when attempting to decrypt plaintext in strict mode.

    This indicates a policy violation - all content should be encrypted
    in Ghost Protocol deployments.
    """
    pass


def encrypt_token(token: str) -> str:
    """
    Encrypt a token using Fernet symmetric encryption.

    Args:
        token: Plain text token to encrypt

    Returns:
        Encrypted token string, or original token if encryption unavailable
    """
    if not token:
        return token

    if not HAS_ENCRYPTION or not cipher_suite:
        if settings.ENVIRONMENT not in ("test", "development"):
            logger.error("[Security] ENCRYPTION_KEY not set in non-dev environment — token stored in plain text!")
        else:
            logger.warning("[Security] ENCRYPTION_KEY not set, storing token in plain text (dev mode)")
        return token

    try:
        encrypted = cipher_suite.encrypt(token.encode()).decode()
        logger.debug("[Security] Token encrypted successfully")
        return encrypted
    except Exception as e:
        logger.error(f"[Security] Encryption failed: {e}")
        return token


def decrypt_token(token: str) -> str:
    """
    Decrypt a token using Fernet symmetric encryption.

    Args:
        token: Encrypted or plain text token

    Returns:
        Decrypted token string
    """
    if not token:
        return token

    suites = cipher_suites or ([cipher_suite] if cipher_suite else [])
    if not HAS_ENCRYPTION or not suites:
        # No encryption configured, return as-is
        return token

    try:
        # Attempt decryption with all configured keys
        for suite in suites:
            try:
                decrypted = suite.decrypt(token.encode()).decode()
                logger.debug("[Security] Token decrypted successfully")
                return decrypted
            except InvalidToken:
                continue
        raise ValueError("Token is not encrypted or uses an unknown key")
    except Exception as e:
        logger.warning(f"[Security] Decryption failed: {e}")
        raise


# =============================================================================
# GHOST PROTOCOL: CHUNK CONTENT ENCRYPTION API
# =============================================================================

def encrypt_text(data: str) -> str:
    """
    Encrypt text content using Fernet (AES-256) for Ghost Protocol.

    This function encrypts document chunk content before storage in the database.
    In production, encryption is mandatory - storing plaintext is blocked.

    Args:
        data: Plaintext string to encrypt

    Returns:
        Base64-encoded encrypted string (Fernet token format)

    Raises:
        EncryptionError: If encryption key is not configured in production

    Example:
        >>> encrypted = encrypt_text("sensitive document content")
        >>> encrypted.startswith("gAAAAA")  # Fernet token prefix
        True
    """
    if not data:
        return data

    if not HAS_CHUNK_ENCRYPTION or not _chunk_cipher:
        if ENVIRONMENT == "production":
            raise EncryptionError(
                "CHUNK_ENCRYPTION_KEY not configured. "
                "Cannot store plaintext content in production."
            )
        logger.warning(
            "[Security] ⚠️ CHUNK_ENCRYPTION_KEY not set - "
            "storing PLAINTEXT (dev/test only)"
        )
        return data

    try:
        encrypted = _chunk_cipher.encrypt(data.encode("utf-8")).decode("utf-8")
        encryption_operations.labels(operation="encrypt", result="success").inc()
        return encrypted
    except Exception as e:
        # NEVER log the actual content - only the error type
        encryption_operations.labels(operation="encrypt", result="failure").inc()
        logger.error(f"[Security] Content encryption failed: {type(e).__name__}")
        raise EncryptionError(f"Content encryption failed: {type(e).__name__}") from e


def decrypt_text(token: str) -> str:
    """
    Decrypt text content using Fernet (AES-256) for Ghost Protocol.

    This function decrypts document chunk content retrieved from the database.

    KEY ROTATION SUPPORT:
    - Tries all configured keys (CHUNK_ENCRYPTION_KEY can be comma-separated)
    - Allows seamless key rotation without data re-encryption
    - Example: CHUNK_ENCRYPTION_KEY="new_key,old_key,older_key"

    STRICT MODE (default for greenfield):
    - Raises UnencryptedContentError if content appears to be plaintext
    - This prevents accidentally serving unencrypted data from misconfigured systems
    - Controlled by settings.STRICT_ENCRYPTION_MODE

    Args:
        token: Encrypted Fernet token or plaintext string

    Returns:
        Decrypted plaintext string

    Raises:
        UnencryptedContentError: If content is plaintext and strict mode is enabled
        EncryptionError: If decryption fails for other reasons

    Example:
        >>> encrypted = encrypt_text("hello world")
        >>> decrypt_text(encrypted)
        'hello world'
    """
    if not token:
        return token

    if not HAS_CHUNK_ENCRYPTION or not _chunk_ciphers:
        if ENVIRONMENT == "production":
            raise EncryptionError(
                "CHUNK_ENCRYPTION_KEY not configured. "
                "Cannot decrypt content in production."
            )
        # In dev/test without encryption, return as-is
        return token

    # Try all configured keys for decryption (key rotation support)
    last_error = None
    for cipher in _chunk_ciphers:
        try:
            decrypted = cipher.decrypt(token.encode("utf-8")).decode("utf-8")
            encryption_operations.labels(operation="decrypt", result="success").inc()
            return decrypted
        except InvalidToken:
            last_error = InvalidToken
            continue  # Try next key
        except Exception as e:
            # Other errors should be raised immediately
            encryption_operations.labels(operation="decrypt", result="failure").inc()
            logger.error(f"[Security] Content decryption failed: {type(e).__name__}")
            raise EncryptionError(f"Content decryption failed: {type(e).__name__}") from e

    # All keys failed - content is NOT encrypted (or uses unknown key)
    # This is a policy violation in strict mode
    strict_mode = getattr(settings, 'STRICT_ENCRYPTION_MODE', True)
    if strict_mode:
        encryption_operations.labels(operation="decrypt", result="unencrypted_strict").inc()
        raise UnencryptedContentError(
            "Attempted to retrieve unencrypted content. "
            "Ghost Protocol requires all content to be encrypted. "
            "Set STRICT_ENCRYPTION_MODE=false for legacy data migration."
        )

    # Legacy mode: return plaintext with warning
    encryption_operations.labels(operation="decrypt", result="unencrypted_legacy").inc()
    logger.warning(
        "[Security] ⚠️ Serving unencrypted content (legacy mode). "
        "Enable STRICT_ENCRYPTION_MODE after migration."
    )
    return token


# =============================================================================
# AUTHENTICATION
# =============================================================================

async def get_current_user(credentials: HTTPAuthorizationCredentials = Security(security)):
    token = credentials.credentials
    try:
        # Verify signature using SUPABASE_JWT_SECRET
        # Algorithms should be explicitly set to HS256 for Supabase default
        payload = jwt.decode(
            token,
            settings.SUPABASE_JWT_SECRET,
            algorithms=["HS256"],
            audience="authenticated"
        )
        user_id = payload.get("sub")

        if not user_id:
            raise HTTPException(status_code=401, detail="Invalid token payload")

        return user_id
    except Exception as e:
        logger.warning(f"Auth error: {type(e).__name__}")  # Don't log token details
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid authentication credentials",
            headers={"WWW-Authenticate": "Bearer"},
        )


# =============================================================================
# KEY ROTATION UTILITIES
# =============================================================================

def get_encryption_key_count() -> int:
    """
    Get the number of configured chunk encryption keys.

    Useful for monitoring key rotation status.

    Returns:
        Number of keys configured (0 = no encryption)
    """
    return len(_chunk_ciphers)


def generate_new_encryption_key() -> str:
    """
    Generate a new Fernet encryption key for key rotation.

    Usage:
        1. Generate new key: new_key = generate_new_encryption_key()
        2. Update env: CHUNK_ENCRYPTION_KEY="new_key,old_key"
        3. Deploy and verify
        4. (Optional) Re-encrypt old data with new key
        5. Remove old key after migration

    Returns:
        Base64-encoded Fernet key (32 bytes)
    """
    if not _CRYPTO_AVAILABLE:
        raise RuntimeError("cryptography package not installed")
    return Fernet.generate_key().decode()


def re_encrypt_content(encrypted_content: str) -> str:
    """
    Re-encrypt content with the current primary key.

    Use this during key rotation to migrate old data encrypted
    with deprecated keys to the new primary key.

    Args:
        encrypted_content: Content encrypted with any configured key

    Returns:
        Content re-encrypted with the primary (first) key

    Raises:
        EncryptionError: If decryption or re-encryption fails
    """
    # Decrypt with any key
    plaintext = decrypt_text(encrypted_content)
    # Re-encrypt with primary key
    return encrypt_text(plaintext)
