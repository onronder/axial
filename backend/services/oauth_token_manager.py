"""
OAuth Token Manager

Centralized service for managing OAuth tokens across all connectors.
Handles automatic refresh, expiry detection, and database persistence.
"""

import logging
from datetime import datetime, timedelta, timezone
from functools import wraps
from typing import Any

import requests

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
    def is_token_expired(expires_at: str | None) -> bool:
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
        expires_at: str | None = None
    ) -> tuple[str, str]:
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
            from google.auth.transport.requests import Request
            from google.oauth2.credentials import Credentials

            from core.config import settings
            from core.db import get_supabase
            from core.security import decrypt_token, encrypt_token

            # Decrypt tokens
            decrypted_access = decrypt_token(access_token) if access_token else None
            decrypted_refresh = decrypt_token(refresh_token) if refresh_token else None

            if not decrypted_refresh:
                raise TokenRefreshError("No refresh token available")

            # Validate token after decryption (catch corruption/invalid tokens early)
            if len(decrypted_refresh) < 20:
                logger.warning(f"⚠️ [Google] Refresh token appears invalid (too short) for integration {integration_id}")
                raise TokenRefreshError("Invalid refresh token format")

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
            error_msg = str(e).lower()
            logger.error(f"❌ Failed to refresh Google token: {e}")

            # Handle invalid_grant specifically - token revoked or expired (7-day testing mode limit)
            if 'invalid_grant' in error_msg or 'token has been expired or revoked' in error_msg:
                logger.warning(f"🔒 [Google] Token revoked/expired for integration {integration_id}, marking as reconnection_required")
                try:
                    # Mark integration as requiring reconnection
                    supabase = get_supabase()
                    supabase.table("user_integrations").update({
                        "status": "reconnection_required",
                        "status_message": "Your Google Drive connection has expired. Please reconnect your account.",
                        "updated_at": datetime.now(timezone.utc).isoformat()
                    }).eq("id", integration_id).execute()
                except Exception as db_err:
                    logger.error(f"❌ Failed to update integration status: {db_err}")

                raise TokenRefreshError(
                    "Google Drive connection expired. Please reconnect your account in Settings > Integrations."
                ) from e

            raise TokenRefreshError(f"Token refresh failed: {e}") from e

    @staticmethod
    def refresh_notion_token(
        integration_id: str,
        access_token: str,
        refresh_token: str | None = None,
        expires_at: str | None = None
    ) -> tuple[str, str | None]:
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
        expires_at: str | None = None,
        provider: str = "onedrive",
    ) -> tuple[str, str, str | None]:
        """
        Refresh Microsoft Graph OAuth token for OneDrive/SharePoint.
        """
        try:
            from core.config import settings
            from core.db import get_supabase
            from core.security import decrypt_token, encrypt_token

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
                # Check for invalid_grant (token revoked/expired)
                try:
                    error_data = response.json()
                    error_code = error_data.get("error", "")
                    if error_code == "invalid_grant" or "AADSTS70008" in response.text:
                        # Mark integration as needing reconnection
                        supabase = get_supabase()
                        supabase.table("user_integrations").update({
                            "status": "reconnection_required",
                            "status_message": "Your Microsoft connection has expired. Please reconnect.",
                            "updated_at": datetime.now(timezone.utc).isoformat()
                        }).eq("id", integration_id).execute()
                        raise TokenRefreshError(
                            "Microsoft connection expired. Please reconnect your account in Settings > Integrations."
                        )
                except TokenRefreshError:
                    raise
                except Exception as e:
                    logger.warning(f"[OAuth] Failed to mark Microsoft integration as expired: {e}")
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
    def refresh_dropbox_token(
        integration_id: str,
        access_token: str,
        refresh_token: str,
        expires_at: str | None = None,
    ) -> tuple[str, str, str | None]:
        """
        Refresh Dropbox OAuth token.

        Dropbox tokens expire after ~4 hours and require refresh using
        the offline refresh token.

        Args:
            integration_id: Database ID of user_integration
            access_token: Current access token (encrypted or plain)
            refresh_token: Refresh token (encrypted or plain)
            expires_at: Current expiry timestamp

        Returns:
            Tuple of (new_access_token, new_refresh_token, new_expires_at)

        Raises:
            TokenRefreshError: If refresh fails
        """
        try:
            from core.config import settings
            from core.db import get_supabase
            from core.security import decrypt_token, encrypt_token

            decrypted_access = decrypt_token(access_token) if access_token else None
            decrypted_refresh = decrypt_token(refresh_token) if refresh_token else None

            if not decrypted_refresh:
                raise TokenRefreshError("No Dropbox refresh token available")

            # Check if refresh is needed
            if not OAuthTokenManager.is_token_expired(expires_at):
                logger.debug(f"Dropbox token for integration {integration_id} is still valid")
                return decrypted_access, decrypted_refresh, expires_at

            if not settings.DROPBOX_CLIENT_ID or not settings.DROPBOX_CLIENT_SECRET:
                raise TokenRefreshError("Dropbox client credentials not configured")

            logger.info(f"🔄 Refreshing Dropbox token for integration {integration_id}")

            # Dropbox token refresh endpoint
            token_url = "https://api.dropboxapi.com/oauth2/token"
            token_payload = {
                "grant_type": "refresh_token",
                "refresh_token": decrypted_refresh,
                "client_id": settings.DROPBOX_CLIENT_ID,
                "client_secret": settings.DROPBOX_CLIENT_SECRET,
            }

            response = requests.post(
                token_url,
                data=token_payload,
                timeout=30,
            )

            if response.status_code != 200:
                error_detail = response.text[:500] if response.text else "Unknown error"
                logger.error(f"❌ Dropbox token refresh failed: {error_detail}")

                # Check for invalid_grant (token revoked/expired)
                try:
                    error_data = response.json()
                    error_code = error_data.get("error", "")
                    if error_code == "invalid_grant" or "expired" in str(error_data).lower():
                        # Mark integration as needing reconnection
                        supabase = get_supabase()
                        supabase.table("user_integrations").update({
                            "status": "reconnection_required",
                            "status_message": "Your Dropbox connection has expired. Please reconnect.",
                            "updated_at": datetime.now(timezone.utc).isoformat()
                        }).eq("id", integration_id).execute()
                        raise TokenRefreshError(
                            "Dropbox connection expired. Please reconnect your account in Settings > Integrations."
                        )
                except TokenRefreshError:
                    raise
                except Exception as e:
                    logger.warning(f"[OAuth] Failed to mark Dropbox integration as expired: {e}")

                raise TokenRefreshError(f"Dropbox token refresh failed: {error_detail}")

            payload = response.json()
            new_access = payload.get("access_token")
            # Dropbox may not return a new refresh token; keep the old one
            new_refresh = payload.get("refresh_token") or decrypted_refresh
            expires_in = payload.get("expires_in")

            new_expires = None
            if expires_in:
                new_expires = (datetime.now(timezone.utc) + timedelta(seconds=int(expires_in))).isoformat()

            # Persist to database
            supabase = get_supabase()
            update_data = {
                "access_token": encrypt_token(new_access),
                "expires_at": new_expires,
                "updated_at": datetime.now(timezone.utc).isoformat(),
            }
            # Only update refresh_token if we got a new one
            if payload.get("refresh_token"):
                update_data["refresh_token"] = encrypt_token(new_refresh)

            supabase.table("user_integrations").update(update_data).eq("id", integration_id).execute()

            logger.info(f"✅ Dropbox token refreshed for integration {integration_id}")

            return new_access, new_refresh, new_expires

        except TokenRefreshError:
            raise
        except Exception as e:
            logger.error(f"❌ Failed to refresh Dropbox token: {e}")
            raise TokenRefreshError(f"Dropbox token refresh failed: {e}") from e

    @staticmethod
    def validate_github_token(
        integration_id: str,
        access_token: str,
    ) -> str:
        """
        Validate GitHub OAuth token.

        GitHub OAuth tokens do not expire by default, but they can be revoked.
        This method validates the token is still active by calling /user.

        Args:
            integration_id: Database ID of user_integration
            access_token: Current access token (encrypted or plain)

        Returns:
            Valid access token (decrypted)

        Raises:
            TokenRefreshError: If token is invalid/revoked
        """
        try:
            from core.security import decrypt_token

            decrypted_access = decrypt_token(access_token) if access_token else None

            if not decrypted_access:
                raise TokenRefreshError("No GitHub access token available")

            # Validate token by calling /user
            response = requests.get(
                "https://api.github.com/user",
                headers={
                    "Authorization": f"Bearer {decrypted_access}",
                    "Accept": "application/vnd.github.v3+json",
                    "X-GitHub-Api-Version": "2022-11-28",
                },
                timeout=10
            )

            if response.status_code == 401:
                # Mark integration as needing reconnection
                try:
                    from core.db import get_supabase
                    supabase = get_supabase()
                    supabase.table("user_integrations").update({
                        "status": "reconnection_required",
                        "status_message": "Your GitHub token has been revoked. Please reconnect.",
                        "updated_at": datetime.now(timezone.utc).isoformat()
                    }).eq("id", integration_id).execute()
                except Exception as e:
                    logger.warning(f"[OAuth] Failed to mark GitHub integration as revoked: {e}")
                raise TokenRefreshError("GitHub token has been revoked or is invalid")

            if response.status_code == 403:
                raise TokenRefreshError("GitHub token lacks required permissions")

            if response.status_code != 200:
                logger.warning(f"⚠️ [GitHub] Token validation returned {response.status_code}")
                # Non-401 errors might be transient, allow through

            logger.debug(f"✅ [GitHub] Token validated for integration {integration_id}")
            return decrypted_access

        except TokenRefreshError:
            raise
        except Exception as e:
            logger.error(f"❌ Failed to validate GitHub token: {e}")
            raise TokenRefreshError(f"GitHub token validation failed: {e}") from e

    @staticmethod
    def _acquire_refresh_lock(supabase, lock_key: str, locked_by: str, ttl_seconds: int = 30) -> bool:
        """
        Acquire a distributed lock for token refresh operations.

        Returns True if lock acquired, False if already locked by another process.
        """
        try:
            result = supabase.rpc(
                "acquire_lock",
                {
                    "p_lock_key": lock_key,
                    "p_locked_by": locked_by,
                    "p_ttl_seconds": ttl_seconds,
                }
            ).execute()
            return result.data if isinstance(result.data, bool) else False
        except Exception as exc:
            error_msg = str(exc)
            if "function" in error_msg.lower() and "does not exist" in error_msg.lower():
                # RPC doesn't exist yet (migration not applied), proceed without lock
                logger.warning("⚠️ [Lock] acquire_lock RPC not found, proceeding without lock")
                return True
            logger.error(f"❌ [Lock] Failed to acquire lock: {exc}")
            return True  # Fail open to avoid blocking operations

    @staticmethod
    def _release_refresh_lock(supabase, lock_key: str, locked_by: str) -> None:
        """Release a distributed lock."""
        try:
            supabase.rpc(
                "release_lock",
                {
                    "p_lock_key": lock_key,
                    "p_locked_by": locked_by,
                }
            ).execute()
        except Exception as exc:
            error_msg = str(exc)
            if "function" in error_msg.lower() and "does not exist" in error_msg.lower():
                return  # RPC doesn't exist yet
            logger.error(f"❌ [Lock] Failed to release lock: {exc}")

    @staticmethod
    def _get_fresh_integration_tokens(supabase, integration_id: str) -> dict[str, Any]:
        """
        Re-fetch integration tokens from database to get the freshest data.

        This is crucial for race condition handling - another process may have
        already refreshed the token while we were waiting for the lock.
        """
        try:
            result = supabase.table("user_integrations").select(
                "access_token, refresh_token, expires_at"
            ).eq("id", integration_id).maybe_single().execute()
            return result.data if result.data else {}
        except Exception as exc:
            logger.error(f"❌ [Box] Failed to re-fetch integration: {exc}")
            return {}

    @staticmethod
    def refresh_box_token(
        integration_id: str,
        access_token: str,
        refresh_token: str,
        expires_at: str | None = None,
    ) -> tuple[str, str, str | None]:
        """
        Refresh Box OAuth token with distributed locking.

        CRITICAL: Box refresh tokens are SINGLE-USE and rotate on each refresh.
        Each refresh returns a NEW refresh token that invalidates the previous one.
        We must atomically update BOTH access_token AND refresh_token.

        RACE CONDITION FIX: Uses distributed lock to prevent concurrent refresh
        attempts from invalidating each other's refresh tokens.

        Box Token Lifecycle:
        - Access tokens expire after 60 minutes
        - Refresh tokens expire after 60 days (but rotate on each use)

        Args:
            integration_id: Database ID of user_integration
            access_token: Current access token (encrypted or plain)
            refresh_token: Refresh token (encrypted or plain) - WILL BE ROTATED
            expires_at: Current expiry timestamp

        Returns:
            Tuple of (new_access_token, new_refresh_token, new_expires_at)

        Raises:
            TokenRefreshError: If refresh fails
        """
        import uuid

        try:
            from core.config import settings
            from core.db import get_supabase
            from core.security import decrypt_token, encrypt_token

            supabase = get_supabase()

            decrypted_access = decrypt_token(access_token) if access_token else None
            decrypted_refresh = decrypt_token(refresh_token) if refresh_token else None

            if not decrypted_refresh:
                raise TokenRefreshError("No Box refresh token available")

            # Check if refresh is needed BEFORE acquiring lock
            if not OAuthTokenManager.is_token_expired(expires_at):
                logger.debug(f"Box token for integration {integration_id} is still valid")
                return decrypted_access, decrypted_refresh, expires_at

            if not settings.BOX_CLIENT_ID or not settings.BOX_CLIENT_SECRET:
                raise TokenRefreshError("Box client credentials not configured")

            # RACE CONDITION FIX: Acquire distributed lock
            lock_key = f"box_token_refresh:{integration_id}"
            locked_by = str(uuid.uuid4())

            lock_acquired = OAuthTokenManager._acquire_refresh_lock(
                supabase, lock_key, locked_by, ttl_seconds=60
            )

            if not lock_acquired:
                # Another process is refreshing - wait and re-check
                logger.info(f"🔒 [Box] Token refresh locked for {integration_id}, waiting...")
                import time
                time.sleep(2)  # Wait for other process to finish

                # Re-fetch tokens from database - another process may have refreshed them
                fresh_tokens = OAuthTokenManager._get_fresh_integration_tokens(supabase, integration_id)
                if fresh_tokens:
                    fresh_expires = fresh_tokens.get("expires_at")
                    if not OAuthTokenManager.is_token_expired(fresh_expires):
                        # Token was refreshed by another process
                        logger.info(f"✅ [Box] Token already refreshed by another process for {integration_id}")
                        fresh_access = decrypt_token(fresh_tokens.get("access_token")) if fresh_tokens.get("access_token") else None
                        fresh_refresh = decrypt_token(fresh_tokens.get("refresh_token")) if fresh_tokens.get("refresh_token") else None
                        return fresh_access, fresh_refresh, fresh_expires

                # Still need to refresh - try to acquire lock again
                lock_acquired = OAuthTokenManager._acquire_refresh_lock(
                    supabase, lock_key, locked_by, ttl_seconds=60
                )
                if not lock_acquired:
                    raise TokenRefreshError("Could not acquire lock for Box token refresh")

            try:
                # Double-check token validity after acquiring lock
                # Another process may have refreshed while we were acquiring
                fresh_tokens = OAuthTokenManager._get_fresh_integration_tokens(supabase, integration_id)
                if fresh_tokens:
                    fresh_expires = fresh_tokens.get("expires_at")
                    if not OAuthTokenManager.is_token_expired(fresh_expires):
                        logger.info(f"✅ [Box] Token already refreshed (post-lock check) for {integration_id}")
                        fresh_access = decrypt_token(fresh_tokens.get("access_token")) if fresh_tokens.get("access_token") else None
                        fresh_refresh = decrypt_token(fresh_tokens.get("refresh_token")) if fresh_tokens.get("refresh_token") else None
                        return fresh_access, fresh_refresh, fresh_expires

                    # Use the fresh refresh token from database
                    decrypted_refresh = decrypt_token(fresh_tokens.get("refresh_token")) if fresh_tokens.get("refresh_token") else decrypted_refresh

                logger.info(f"🔄 Refreshing Box token for integration {integration_id}")

                # Box token refresh endpoint
                token_url = "https://api.box.com/oauth2/token"
                token_payload = {
                    "grant_type": "refresh_token",
                    "refresh_token": decrypted_refresh,
                    "client_id": settings.BOX_CLIENT_ID,
                    "client_secret": settings.BOX_CLIENT_SECRET,
                }

                response = requests.post(
                    token_url,
                    data=token_payload,
                    timeout=30,
                )

                if response.status_code != 200:
                    error_detail = response.text[:500] if response.text else "Unknown error"
                    logger.error(f"❌ Box token refresh failed: {error_detail}")

                    # Check for specific Box errors
                    try:
                        error_json = response.json()
                        error_code = error_json.get("error", "")
                        if error_code == "invalid_grant":
                            # Mark integration as needing reconnection
                            supabase.table("user_integrations").update({
                                "status": "reconnection_required",
                                "status_message": "Your Box connection has expired. Please reconnect.",
                                "updated_at": datetime.now(timezone.utc).isoformat()
                            }).eq("id", integration_id).execute()
                            raise TokenRefreshError(
                                "Box refresh token has expired or been revoked. Please reconnect your Box account."
                            )
                    except TokenRefreshError:
                        raise
                    except Exception as e:
                        logger.warning(f"[OAuth] Failed to mark Box integration as expired: {e}")

                    raise TokenRefreshError(f"Box token refresh failed: {error_detail}")

                payload = response.json()
                new_access = payload.get("access_token")
                # CRITICAL: Box ALWAYS returns a new refresh token - we MUST save it
                new_refresh = payload.get("refresh_token")

                if not new_refresh:
                    logger.warning("⚠️ [Box] No new refresh token returned - using existing")
                    new_refresh = decrypted_refresh

                expires_in = payload.get("expires_in")

                new_expires = None
                if expires_in:
                    new_expires = (datetime.now(timezone.utc) + timedelta(seconds=int(expires_in))).isoformat()

                # ATOMIC UPDATE: Must update both tokens together
                update_data = {
                    "access_token": encrypt_token(new_access),
                    "refresh_token": encrypt_token(new_refresh),  # ALWAYS update refresh token
                    "expires_at": new_expires,
                    "updated_at": datetime.now(timezone.utc).isoformat(),
                }

                supabase.table("user_integrations").update(update_data).eq("id", integration_id).execute()

                logger.info(f"✅ Box token refreshed for integration {integration_id}")

                return new_access, new_refresh, new_expires

            finally:
                # Always release the lock
                OAuthTokenManager._release_refresh_lock(supabase, lock_key, locked_by)

        except TokenRefreshError:
            raise
        except Exception as e:
            logger.error(f"❌ Failed to refresh Box token: {e}")
            raise TokenRefreshError(f"Box token refresh failed: {e}") from e

    @staticmethod
    def get_valid_credentials(
        integration: dict[str, Any],
        provider: str
    ) -> dict[str, Any]:
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

            elif provider == 'dropbox':
                new_access, new_refresh, new_expires = OAuthTokenManager.refresh_dropbox_token(
                    integration_id,
                    access_token,
                    refresh_token,
                    expires_at,
                )
                return {
                    'access_token': new_access,
                    'refresh_token': new_refresh,
                    'expires_at': new_expires,
                    'integration_id': integration_id
                }

            elif provider == 'github':
                # GitHub OAuth tokens don't expire by default
                # We just validate the token is still active
                new_access = OAuthTokenManager.validate_github_token(
                    integration_id,
                    access_token,
                )
                return {
                    'access_token': new_access,
                    'refresh_token': None,  # GitHub doesn't use refresh tokens
                    'expires_at': None,
                    'integration_id': integration_id
                }

            elif provider == 'box':
                # Box tokens expire after 60 minutes, refresh tokens rotate
                new_access, new_refresh, new_expires = OAuthTokenManager.refresh_box_token(
                    integration_id,
                    access_token,
                    refresh_token,
                    expires_at,
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
