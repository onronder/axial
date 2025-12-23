from fastapi import Security, HTTPException, status, Depends
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
import jwt
import os
import logging
from core.config import settings

# Fernet encryption for OAuth tokens
try:
    from cryptography.fernet import Fernet, InvalidToken
    ENCRYPTION_KEY = os.getenv("ENCRYPTION_KEY")
    if ENCRYPTION_KEY:
        cipher_suite = Fernet(ENCRYPTION_KEY.encode())
        HAS_ENCRYPTION = True
    else:
        cipher_suite = None
        HAS_ENCRYPTION = False
except ImportError:
    cipher_suite = None
    HAS_ENCRYPTION = False

logger = logging.getLogger(__name__)
security = HTTPBearer()


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
        logger.warning("[Security] ENCRYPTION_KEY not set, storing token in plain text")
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
    
    CRITICAL: Has fallback for legacy plain-text tokens.
    If decryption fails, returns the original token as-is.
    This ensures backward compatibility with existing unencrypted data.
    
    Args:
        token: Encrypted or plain text token
        
    Returns:
        Decrypted token string
    """
    if not token:
        return token
    
    if not HAS_ENCRYPTION or not cipher_suite:
        # No encryption configured, return as-is
        return token
    
    try:
        # Attempt decryption
        decrypted = cipher_suite.decrypt(token.encode()).decode()
        logger.debug("[Security] Token decrypted successfully")
        return decrypted
    except InvalidToken:
        # Token is not encrypted (legacy plain-text data)
        logger.debug("[Security] Token appears to be plain text (legacy), using as-is")
        return token
    except Exception as e:
        # Any other error, return original to avoid breaking existing users
        logger.warning(f"[Security] Decryption failed, using original token: {e}")
        return token


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

