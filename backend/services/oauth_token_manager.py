"""
OAuth Token Manager

Centralized service for managing OAuth tokens across all connectors.
Handles automatic refresh, expiry detection, and database persistence.
"""

import logging
import requests
from datetime import datetime, timezone, timedelta
from typing import Dict, Any, Optional, Tuple
from functools import wraps

logger = logging.getLogger(__name__)


class TokenRefreshError(Exception):
    """Raised when token refresh fails."""
    pass


class OAuthTokenManager:
    """
    Manages OAuth tokens for all connectors.
    
    Features:
    - Automatic token refresh before expiry
    - Retry on 401/invalid_grant errors
    - Database persistence
    - Provider-agnostic interface
    """
    
    # Token refresh buffer: refresh 5 minutes before expiry
    REFRESH_BUFFER_SECONDS = 300
    
    @staticmethod
    def is_token_expired(expires_at: Optional[str]) -> bool:
        """
        Check if token is expired or will expire soon.
        
        Args:
            expires_at: ISO timestamp of token expiry
            
        Returns:
            True if token is expired or will expire within buffer time
        """
        if not expires_at:
            # No expiry info = assume expired (safe default)
            return True
        
        try:
            expiry = datetime.fromisoformat(expires_at.replace('Z', '+00:00'))
            now = datetime.now(timezone.utc)
            buffer = timedelta(seconds=OAuthTokenManager.REFRESH_BUFFER_SECONDS)
            
            # Refresh if expired or will expire soon
            return (expiry - now) < buffer
        except Exception as e:
            logger.warning(f"Failed to parse expires_at '{expires_at}': {e}")
            return True  # Safe default
    
    @staticmethod
    def refresh_google_token(
        integration_id: str,
        access_token: str,
        refresh_token: str,
        expires_at: Optional[str] = None
    ) -> Tuple[str, str]:
        """
        Refresh Google OAuth token.
        
        Args:
            integration_id: Database ID of user_integration
            access_token: Current access token (encrypted or plain)
            refresh_token: Refresh token (encrypted or plain)
            expires_at: Current expiry timestamp
            
        Returns:
            Tuple of (new_access_token, new_expires_at)
            
        Raises:
            TokenRefreshError: If refresh fails
        """
        try:
            from google.oauth2.credentials import Credentials
            from google.auth.transport.requests import Request
            from core.db import get_supabase
            from core.security import encrypt_token, decrypt_token
            from core.config import settings
            
            # Decrypt tokens
            decrypted_access = decrypt_token(access_token) if access_token else None
            decrypted_refresh = decrypt_token(refresh_token) if refresh_token else None
            
            if not decrypted_refresh:
                raise TokenRefreshError("No refresh token available")
            
            # Check if refresh needed
            if not OAuthTokenManager.is_token_expired(expires_at):
                logger.debug(f"Token for integration {integration_id} is still valid")
                return decrypted_access, expires_at
            
            logger.info(f"🔄 Refreshing Google token for integration {integration_id}")
            
            # Build Google credentials
            creds = Credentials(
                token=decrypted_access,
                refresh_token=decrypted_refresh,
                token_uri="https://oauth2.googleapis.com/token",
                client_id=settings.GOOGLE_CLIENT_ID,
                client_secret=settings.GOOGLE_CLIENT_SECRET,
                scopes=['https://www.googleapis.com/auth/drive.readonly']
            )
            
            # Refresh
            creds.refresh(Request())
            
            # Get new values
            new_access_token = creds.token
            new_expires_at = creds.expiry.isoformat() if creds.expiry else None
            
            # Persist to database
            supabase = get_supabase()
            supabase.table("user_integrations").update({
                "access_token": encrypt_token(new_access_token),
                "expires_at": new_expires_at,
                "updated_at": datetime.now(timezone.utc).isoformat()
            }).eq("id", integration_id).execute()
            
            logger.info(f"✅ Google token refreshed for integration {integration_id}")
            
            return new_access_token, new_expires_at
            
        except Exception as e:
            logger.error(f"❌ Failed to refresh Google token: {e}")
            raise TokenRefreshError(f"Token refresh failed: {e}") from e
    
    @staticmethod
    def refresh_notion_token(
        integration_id: str,
        access_token: str,
        refresh_token: Optional[str] = None,
        expires_at: Optional[str] = None
    ) -> Tuple[str, Optional[str]]:
        """
        Refresh Notion OAuth token.
        
        Note: Notion tokens don't expire by default (long-lived).
        This is a placeholder for future Notion token refresh if needed.
        
        Args:
            integration_id: Database ID of user_integration
            access_token: Current access token
            refresh_token: Refresh token (if available)
            expires_at: Current expiry timestamp
            
        Returns:
            Tuple of (access_token, expires_at)
        """
        from core.security import decrypt_token
        
        # Notion tokens are long-lived and don't typically need refresh
        # If Notion implements token expiry in future, add refresh logic here
        logger.debug(f"Notion token for integration {integration_id} (long-lived)")
        
        decrypted_access = decrypt_token(access_token) if access_token else None
        return decrypted_access, expires_at

    @staticmethod
    def refresh_microsoft_token(
        integration_id: str,
        access_token: str,
        refresh_token: str,
        expires_at: Optional[str] = None,
        provider: str = "onedrive",
    ) -> tuple[str, str, Optional[str]]:
        """
        Refresh Microsoft Graph OAuth token for OneDrive/SharePoint.
        """
        try:
            from core.security import decrypt_token, encrypt_token
            from core.db import get_supabase
            from core.config import settings

            decrypted_access = decrypt_token(access_token) if access_token else None
            decrypted_refresh = decrypt_token(refresh_token) if refresh_token else None

            if not decrypted_refresh:
                raise TokenRefreshError("No refresh token available")

            if not OAuthTokenManager.is_token_expired(expires_at):
                return decrypted_access, decrypted_refresh, expires_at

            if not settings.MICROSOFT_CLIENT_ID:
                raise TokenRefreshError("Microsoft client ID not configured")

            scopes = settings.MICROSOFT_SCOPES_SHAREPOINT if provider == "sharepoint" else settings.MICROSOFT_SCOPES_ONEDRIVE
            tenant = settings.MICROSOFT_TENANT_ID or "common"
            token_url = f"https://login.microsoftonline.com/{tenant}/oauth2/v2.0/token"

            token_payload = {
                "client_id": settings.MICROSOFT_CLIENT_ID,
                "grant_type": "refresh_token",
                "refresh_token": decrypted_refresh,
                "scope": scopes,
            }
            if settings.MICROSOFT_CLIENT_SECRET:
                token_payload["client_secret"] = settings.MICROSOFT_CLIENT_SECRET

            response = requests.post(
                token_url,
                data=token_payload,
                timeout=30,
            )
            if (
                response.status_code != 200
                and token_payload.get("client_secret")
                and "AADSTS700025" in response.text
            ):
                logger.warning(
                    "Microsoft refresh rejected client_secret; retrying as public client."
                )
                token_payload.pop("client_secret", None)
                response = requests.post(
                    token_url,
                    data=token_payload,
                    timeout=30,
                )
            if response.status_code != 200:
                raise TokenRefreshError(f"Token refresh failed: {response.text}")

            payload = response.json()
            new_access = payload.get("access_token")
            new_refresh = payload.get("refresh_token") or decrypted_refresh
            expires_in = payload.get("expires_in")
            new_expires = None
            if expires_in:
                new_expires = (datetime.now(timezone.utc) + timedelta(seconds=int(expires_in))).isoformat()

            supabase = get_supabase()
            supabase.table("user_integrations").update({
                "access_token": encrypt_token(new_access),
                "refresh_token": encrypt_token(new_refresh),
                "expires_at": new_expires,
                "updated_at": datetime.now(timezone.utc).isoformat(),
            }).eq("id", integration_id).execute()

            return new_access, new_refresh, new_expires
        except TokenRefreshError:
            raise
        except Exception as e:
            logger.error(f"❌ Failed to refresh Microsoft token: {e}")
            raise TokenRefreshError(f"Token refresh failed: {e}") from e
    
    @staticmethod
    def get_valid_credentials(
        integration: Dict[str, Any],
        provider: str
    ) -> Dict[str, Any]:
        """
        Get valid credentials for an integration, refreshing if needed.
        
        This is the main entry point for connectors.
        
        Args:
            integration: Integration record from database
            provider: Provider type ('google_drive', 'notion', etc.)
            
        Returns:
            Dict with valid credentials:
            {
                'access_token': str,
                'refresh_token': str (optional),
                'expires_at': str (optional),
                'integration_id': str
            }
            
        Raises:
            TokenRefreshError: If refresh fails
        """
        integration_id = integration['id']
        access_token = integration.get('access_token')
        refresh_token = integration.get('refresh_token')
        expires_at = integration.get('expires_at')
        
        try:
            if provider == 'google_drive':
                # Refresh Google token if needed
                new_access, new_expires = OAuthTokenManager.refresh_google_token(
                    integration_id,
                    access_token,
                    refresh_token,
                    expires_at
                )
                
                from core.security import decrypt_token
                return {
                    'access_token': new_access,
                    'refresh_token': decrypt_token(refresh_token) if refresh_token else None,
                    'expires_at': new_expires,
                    'integration_id': integration_id
                }
            
            elif provider == 'notion':
                # Notion tokens are long-lived
                new_access, new_expires = OAuthTokenManager.refresh_notion_token(
                    integration_id,
                    access_token,
                    refresh_token,
                    expires_at
                )
                
                from core.security import decrypt_token
                return {
                    'access_token': new_access,
                    'refresh_token': decrypt_token(refresh_token) if refresh_token else None,
                    'expires_at': new_expires,
                    'integration_id': integration_id
                }

            elif provider in {'onedrive', 'sharepoint'}:
                new_access, new_refresh, new_expires = OAuthTokenManager.refresh_microsoft_token(
                    integration_id,
                    access_token,
                    refresh_token,
                    expires_at,
                    provider=provider,
                )
                return {
                    'access_token': new_access,
                    'refresh_token': new_refresh,
                    'expires_at': new_expires,
                    'integration_id': integration_id
                }
            
            else:
                # Future connectors: add refresh logic here
                logger.warning(f"No refresh logic for provider '{provider}', using token as-is")
                
                from core.security import decrypt_token
                return {
                    'access_token': decrypt_token(access_token) if access_token else None,
                    'refresh_token': decrypt_token(refresh_token) if refresh_token else None,
                    'expires_at': expires_at,
                    'integration_id': integration_id
                }
        
        except TokenRefreshError:
            raise
        except Exception as e:
            logger.error(f"Failed to get valid credentials for {provider}: {e}")
            raise TokenRefreshError(f"Credential validation failed: {e}") from e


def with_token_refresh(provider: str):
    """
    Decorator to automatically refresh tokens on 401/invalid_grant errors.
    
    Usage:
        @with_token_refresh('google_drive')
        def my_api_call(integration, ...):
            # ... make API call ...
    """
    def decorator(func):
        @wraps(func)
        def wrapper(*args, **kwargs):
            try:
                # First attempt
                return func(*args, **kwargs)
            except Exception as e:
                error_msg = str(e).lower()
                
                # Check if it's a token error
                if any(err in error_msg for err in ['invalid_grant', 'token has been expired', '401', 'unauthorized']):
                    logger.warning(f"🔄 Token error detected, attempting refresh: {e}")
                    
                    # Extract integration from args/kwargs
                    integration = None
                    if 'integration' in kwargs:
                        integration = kwargs['integration']
                    elif len(args) > 0 and isinstance(args[0], dict) and 'id' in args[0]:
                        integration = args[0]
                    
                    if integration:
                        try:
                            # Refresh token
                            new_creds = OAuthTokenManager.get_valid_credentials(
                                integration,
                                provider
                            )
                            
                            # Update integration in args/kwargs
                            if 'integration' in kwargs:
                                kwargs['integration'].update(new_creds)
                            elif len(args) > 0:
                                args[0].update(new_creds)
                            
                            # Retry with new token
                            logger.info("🔄 Retrying with refreshed token")
                            return func(*args, **kwargs)
                        
                        except TokenRefreshError as refresh_err:
                            logger.error(f"❌ Token refresh failed: {refresh_err}")
                            raise Exception(
                                "Integration requires reconnection (Token Expired/Revoked)"
                            ) from refresh_err
                
                # Not a token error, re-raise
                raise
        
        return wrapper
    return decorator
