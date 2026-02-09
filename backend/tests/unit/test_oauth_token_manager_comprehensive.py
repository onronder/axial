"""
Comprehensive Unit Tests for OAuth Token Manager

Tests all OAuth token management functionality:
- Token expiry detection
- Google token refresh
- Notion token handling (long-lived)
- Microsoft token refresh
- Dropbox token refresh
- GitHub token validation
- Box token refresh with locking
- Provider-agnostic get_valid_credentials
- Token refresh decorator
"""

import os
import sys
from datetime import datetime, timedelta, timezone
from unittest.mock import MagicMock, Mock, patch

import pytest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

from services.oauth_token_manager import (
    OAuthTokenManager,
    TokenRefreshError,
    with_token_refresh,
)


class TestIsTokenExpired:
    """Test token expiry detection."""

    def test_expired_token_returns_true(self):
        """Token in the past should be expired."""
        past = (datetime.now(timezone.utc) - timedelta(hours=1)).isoformat()
        assert OAuthTokenManager.is_token_expired(past) is True

    def test_token_expiring_soon_returns_true(self):
        """Token expiring within buffer should be treated as expired."""
        # Buffer is 300 seconds (5 minutes), test with 3 minutes left
        soon = (datetime.now(timezone.utc) + timedelta(minutes=3)).isoformat()
        assert OAuthTokenManager.is_token_expired(soon) is True

    def test_valid_token_returns_false(self):
        """Token with plenty of time left should not be expired."""
        future = (datetime.now(timezone.utc) + timedelta(hours=1)).isoformat()
        assert OAuthTokenManager.is_token_expired(future) is False

    def test_none_expiry_returns_true(self):
        """None expiry should be treated as expired (safe default)."""
        assert OAuthTokenManager.is_token_expired(None) is True

    def test_invalid_expiry_format_returns_true(self):
        """Invalid format should be treated as expired (safe default)."""
        assert OAuthTokenManager.is_token_expired("not-a-date") is True
        assert OAuthTokenManager.is_token_expired("") is True

    def test_z_suffix_handled(self):
        """ISO format with Z suffix should work."""
        future = (datetime.now(timezone.utc) + timedelta(hours=1)).strftime("%Y-%m-%dT%H:%M:%SZ")
        assert OAuthTokenManager.is_token_expired(future) is False


class TestRefreshGoogleToken:
    """Test Google OAuth token refresh."""

    def test_returns_existing_if_not_expired(self):
        """Should return existing token if still valid."""
        future = (datetime.now(timezone.utc) + timedelta(hours=1)).isoformat()

        with patch("core.security.decrypt_token", return_value="decrypted-token"):
            access, expires = OAuthTokenManager.refresh_google_token(
                integration_id="int-1",
                access_token="encrypted-access",
                refresh_token="encrypted-refresh",
                expires_at=future,
            )

        assert access == "decrypted-token"
        assert expires == future

    def test_no_refresh_token_raises(self):
        """Should raise if no refresh token available."""
        with patch("core.security.decrypt_token", return_value=None):
            with pytest.raises(TokenRefreshError) as exc:
                OAuthTokenManager.refresh_google_token(
                    integration_id="int-1",
                    access_token="access",
                    refresh_token="",
                    expires_at=None,
                )
            assert "No refresh token" in str(exc.value)

    def test_refresh_success(self):
        """Should refresh and persist token."""
        past = (datetime.now(timezone.utc) - timedelta(hours=1)).isoformat()

        mock_creds = Mock()
        mock_creds.token = "new-access-token"
        mock_creds.expiry = datetime.now(timezone.utc) + timedelta(hours=1)

        mock_supabase = MagicMock()

        with patch("core.security.decrypt_token", return_value="decrypted"), \
             patch("core.security.encrypt_token", return_value="encrypted"), \
             patch("core.db.get_supabase", return_value=mock_supabase), \
             patch("google.oauth2.credentials.Credentials", return_value=mock_creds), \
             patch("google.auth.transport.requests.Request"):
            access, expires = OAuthTokenManager.refresh_google_token(
                integration_id="int-1",
                access_token="old-access",
                refresh_token="refresh",
                expires_at=past,
            )

        assert access == "new-access-token"
        mock_supabase.table.return_value.update.return_value.eq.return_value.execute.assert_called()

    def test_refresh_failure_raises(self):
        """Should raise TokenRefreshError on failure."""
        past = (datetime.now(timezone.utc) - timedelta(hours=1)).isoformat()

        with patch("core.security.decrypt_token", return_value="decrypted"), \
             patch("google.oauth2.credentials.Credentials", side_effect=Exception("Auth failed")):
            with pytest.raises(TokenRefreshError) as exc:
                OAuthTokenManager.refresh_google_token(
                    integration_id="int-1",
                    access_token="access",
                    refresh_token="refresh",
                    expires_at=past,
                )
            assert "Token refresh failed" in str(exc.value)


class TestRefreshNotionToken:
    """Test Notion token handling (long-lived tokens)."""

    def test_returns_decrypted_token(self):
        """Notion tokens are long-lived, just decrypt and return."""
        with patch("core.security.decrypt_token", return_value="notion-token"):
            access, expires = OAuthTokenManager.refresh_notion_token(
                integration_id="int-1",
                access_token="encrypted",
                refresh_token=None,
                expires_at=None,
            )

        assert access == "notion-token"
        assert expires is None


class TestRefreshMicrosoftToken:
    """Test Microsoft OAuth token refresh."""

    def test_returns_existing_if_not_expired(self):
        """Should return existing if still valid."""
        future = (datetime.now(timezone.utc) + timedelta(hours=1)).isoformat()

        with patch("core.security.decrypt_token", return_value="decrypted"):
            access, refresh, expires = OAuthTokenManager.refresh_microsoft_token(
                integration_id="int-1",
                access_token="access",
                refresh_token="refresh",
                expires_at=future,
            )

        assert access == "decrypted"
        assert expires == future

    def test_no_refresh_token_raises(self):
        """Should raise if no refresh token."""
        with patch("core.security.decrypt_token", return_value=None):
            with pytest.raises(TokenRefreshError):
                OAuthTokenManager.refresh_microsoft_token(
                    integration_id="int-1",
                    access_token="access",
                    refresh_token="",
                    expires_at=None,
                )

    def test_refresh_success(self):
        """Should refresh Microsoft token."""
        past = (datetime.now(timezone.utc) - timedelta(hours=1)).isoformat()

        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            "access_token": "new-access",
            "refresh_token": "new-refresh",
            "expires_in": 3600,
        }

        mock_supabase = MagicMock()
        mock_settings = Mock()
        mock_settings.MICROSOFT_CLIENT_ID = "client-id"
        mock_settings.MICROSOFT_CLIENT_SECRET = "secret"
        mock_settings.MICROSOFT_TENANT_ID = "common"
        mock_settings.MICROSOFT_SCOPES_ONEDRIVE = "scope"
        mock_settings.MICROSOFT_SCOPES_SHAREPOINT = "scope"

        with patch("core.security.decrypt_token", return_value="decrypted"), \
             patch("core.security.encrypt_token", return_value="encrypted"), \
             patch("core.db.get_supabase", return_value=mock_supabase), \
             patch("requests.post", return_value=mock_response), \
             patch("core.config.settings", mock_settings):
            access, refresh, expires = OAuthTokenManager.refresh_microsoft_token(
                integration_id="int-1",
                access_token="old",
                refresh_token="refresh",
                expires_at=past,
            )

        assert access == "new-access"
        assert refresh == "new-refresh"

    def test_refresh_retries_without_client_secret(self):
        """Should retry as public client if AADSTS700025 error."""
        past = (datetime.now(timezone.utc) - timedelta(hours=1)).isoformat()

        mock_response_fail = Mock()
        mock_response_fail.status_code = 400
        mock_response_fail.text = "AADSTS700025: Client is public"

        mock_response_success = Mock()
        mock_response_success.status_code = 200
        mock_response_success.json.return_value = {
            "access_token": "new-access",
            "expires_in": 3600,
        }

        mock_supabase = MagicMock()
        mock_settings = Mock()
        mock_settings.MICROSOFT_CLIENT_ID = "client-id"
        mock_settings.MICROSOFT_CLIENT_SECRET = "secret"
        mock_settings.MICROSOFT_TENANT_ID = "common"
        mock_settings.MICROSOFT_SCOPES_ONEDRIVE = "scope"
        mock_settings.MICROSOFT_SCOPES_SHAREPOINT = "scope"

        with patch("core.security.decrypt_token", return_value="decrypted"), \
             patch("core.security.encrypt_token", return_value="encrypted"), \
             patch("core.db.get_supabase", return_value=mock_supabase), \
             patch("requests.post", side_effect=[mock_response_fail, mock_response_success]), \
             patch("core.config.settings", mock_settings):
            access, _, _ = OAuthTokenManager.refresh_microsoft_token(
                integration_id="int-1",
                access_token="old",
                refresh_token="refresh",
                expires_at=past,
            )

        assert access == "new-access"


class TestRefreshDropboxToken:
    """Test Dropbox OAuth token refresh."""

    def test_returns_existing_if_not_expired(self):
        """Should return existing if still valid."""
        future = (datetime.now(timezone.utc) + timedelta(hours=1)).isoformat()

        with patch("core.security.decrypt_token", return_value="decrypted"):
            access, refresh, expires = OAuthTokenManager.refresh_dropbox_token(
                integration_id="int-1",
                access_token="access",
                refresh_token="refresh",
                expires_at=future,
            )

        assert access == "decrypted"
        assert expires == future

    def test_refresh_success(self):
        """Should refresh Dropbox token."""
        past = (datetime.now(timezone.utc) - timedelta(hours=1)).isoformat()

        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            "access_token": "new-access",
            "expires_in": 14400,
        }

        mock_supabase = MagicMock()
        mock_settings = Mock()
        mock_settings.DROPBOX_CLIENT_ID = "client-id"
        mock_settings.DROPBOX_CLIENT_SECRET = "secret"

        with patch("core.security.decrypt_token", return_value="decrypted"), \
             patch("core.security.encrypt_token", return_value="encrypted"), \
             patch("core.db.get_supabase", return_value=mock_supabase), \
             patch("requests.post", return_value=mock_response), \
             patch("core.config.settings", mock_settings):
            access, refresh, expires = OAuthTokenManager.refresh_dropbox_token(
                integration_id="int-1",
                access_token="old",
                refresh_token="refresh",
                expires_at=past,
            )

        assert access == "new-access"

    def test_no_credentials_raises(self):
        """Should raise if no Dropbox credentials configured."""
        past = (datetime.now(timezone.utc) - timedelta(hours=1)).isoformat()

        mock_settings = Mock()
        mock_settings.DROPBOX_CLIENT_ID = None
        mock_settings.DROPBOX_CLIENT_SECRET = None

        with patch("core.security.decrypt_token", return_value="decrypted"), \
             patch("core.config.settings", mock_settings):
            with pytest.raises(TokenRefreshError) as exc:
                OAuthTokenManager.refresh_dropbox_token(
                    integration_id="int-1",
                    access_token="old",
                    refresh_token="refresh",
                    expires_at=past,
                )
            assert "not configured" in str(exc.value)


class TestValidateGitHubToken:
    """Test GitHub token validation."""

    def test_valid_token_returns(self):
        """Valid token should return decrypted access."""
        mock_response = Mock()
        mock_response.status_code = 200

        with patch("core.security.decrypt_token", return_value="github-token"), \
             patch("requests.get", return_value=mock_response):
            access = OAuthTokenManager.validate_github_token(
                integration_id="int-1",
                access_token="encrypted",
            )

        assert access == "github-token"

    def test_no_token_raises(self):
        """No token should raise."""
        with patch("core.security.decrypt_token", return_value=None):
            with pytest.raises(TokenRefreshError) as exc:
                OAuthTokenManager.validate_github_token(
                    integration_id="int-1",
                    access_token="",
                )
            assert "No GitHub access token" in str(exc.value)

    def test_revoked_token_raises(self):
        """401 response should indicate revoked token."""
        mock_response = Mock()
        mock_response.status_code = 401

        with patch("core.security.decrypt_token", return_value="token"), \
             patch("requests.get", return_value=mock_response):
            with pytest.raises(TokenRefreshError) as exc:
                OAuthTokenManager.validate_github_token(
                    integration_id="int-1",
                    access_token="token",
                )
            assert "revoked" in str(exc.value)

    def test_insufficient_permissions_raises(self):
        """403 response should indicate permission issue."""
        mock_response = Mock()
        mock_response.status_code = 403

        with patch("core.security.decrypt_token", return_value="token"), \
             patch("requests.get", return_value=mock_response):
            with pytest.raises(TokenRefreshError) as exc:
                OAuthTokenManager.validate_github_token(
                    integration_id="int-1",
                    access_token="token",
                )
            assert "permissions" in str(exc.value)


class TestRefreshBoxToken:
    """Test Box OAuth token refresh with locking."""

    def test_returns_existing_if_not_expired(self):
        """Should return existing if still valid."""
        future = (datetime.now(timezone.utc) + timedelta(minutes=30)).isoformat()

        with patch("core.security.decrypt_token", return_value="decrypted"):
            access, refresh, expires = OAuthTokenManager.refresh_box_token(
                integration_id="int-1",
                access_token="access",
                refresh_token="refresh",
                expires_at=future,
            )

        assert access == "decrypted"
        assert expires == future

    def test_refresh_success_with_lock(self):
        """Should acquire lock, refresh, and release."""
        past = (datetime.now(timezone.utc) - timedelta(hours=1)).isoformat()

        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            "access_token": "new-access",
            "refresh_token": "new-refresh",
            "expires_in": 3600,
        }

        mock_supabase = MagicMock()
        # Lock acquisition succeeds
        mock_supabase.rpc.return_value.execute.return_value.data = True
        # Fresh tokens return None (triggers refresh)
        mock_supabase.table.return_value.select.return_value.eq.return_value.single.return_value.execute.return_value.data = None

        mock_settings = Mock()
        mock_settings.BOX_CLIENT_ID = "client-id"
        mock_settings.BOX_CLIENT_SECRET = "secret"

        with patch("core.security.decrypt_token", return_value="decrypted"), \
             patch("core.security.encrypt_token", return_value="encrypted"), \
             patch("core.db.get_supabase", return_value=mock_supabase), \
             patch("requests.post", return_value=mock_response), \
             patch("core.config.settings", mock_settings):
            access, refresh, expires = OAuthTokenManager.refresh_box_token(
                integration_id="int-1",
                access_token="old",
                refresh_token="refresh",
                expires_at=past,
            )

        assert access == "new-access"
        assert refresh == "new-refresh"

    def test_waits_if_locked_then_uses_refreshed(self):
        """Should wait if locked and use freshly refreshed token."""
        future = (datetime.now(timezone.utc) + timedelta(minutes=30)).isoformat()

        # This test verifies that when lock acquisition fails, the code re-checks
        # for freshly refreshed tokens. We mock _get_fresh_integration_tokens directly.

        mock_supabase = MagicMock()
        # First call: lock fails
        mock_supabase.rpc.return_value.execute.return_value.data = False

        mock_settings = Mock()
        mock_settings.BOX_CLIENT_ID = "client-id"
        mock_settings.BOX_CLIENT_SECRET = "secret"

        # Create a function that returns fresh tokens
        def mock_get_fresh(*args, **kwargs):
            return {
                "access_token": "fresh-encrypted-access",
                "refresh_token": "fresh-encrypted-refresh",
                "expires_at": future,
            }

        with patch("core.security.decrypt_token", return_value="fresh-token"), \
             patch("core.db.get_supabase", return_value=mock_supabase), \
             patch("core.config.settings", mock_settings), \
             patch.object(OAuthTokenManager, "_get_fresh_integration_tokens", mock_get_fresh), \
             patch.object(OAuthTokenManager, "is_token_expired", side_effect=[True, False]), \
             patch("time.sleep"):
            access, refresh, expires = OAuthTokenManager.refresh_box_token(
                integration_id="int-1",
                access_token="old",
                refresh_token="old-refresh",
                expires_at=None,  # Expired
            )

        assert access == "fresh-token"
        assert expires == future


class TestAcquireReleaseLock:
    """Test distributed lock helpers."""

    def test_acquire_lock_success(self):
        """Should return True on successful lock acquisition."""
        mock_supabase = MagicMock()
        mock_supabase.rpc.return_value.execute.return_value.data = True

        result = OAuthTokenManager._acquire_refresh_lock(
            mock_supabase, "lock-key", "worker-1", 30
        )

        assert result is True

    def test_acquire_lock_failure(self):
        """Should return False if lock already held."""
        mock_supabase = MagicMock()
        mock_supabase.rpc.return_value.execute.return_value.data = False

        result = OAuthTokenManager._acquire_refresh_lock(
            mock_supabase, "lock-key", "worker-1", 30
        )

        assert result is False

    def test_acquire_lock_rpc_not_found(self):
        """Should return True (proceed) if RPC doesn't exist."""
        mock_supabase = MagicMock()
        mock_supabase.rpc.side_effect = Exception("function acquire_lock does not exist")

        result = OAuthTokenManager._acquire_refresh_lock(
            mock_supabase, "lock-key", "worker-1", 30
        )

        assert result is True

    def test_release_lock_success(self):
        """Should release lock without error."""
        mock_supabase = MagicMock()

        # Should not raise
        OAuthTokenManager._release_refresh_lock(
            mock_supabase, "lock-key", "worker-1"
        )

        mock_supabase.rpc.assert_called()


class TestGetValidCredentials:
    """Test main entry point for getting credentials."""

    def test_google_drive_provider(self):
        """Should call Google refresh for google_drive."""
        integration = {
            "id": "int-1",
            "access_token": "access",
            "refresh_token": "refresh",
            "expires_at": None,
        }

        with patch.object(OAuthTokenManager, "refresh_google_token", return_value=("new-access", "new-expires")) as mock_refresh, \
             patch("core.security.decrypt_token", return_value="decrypted"):
            result = OAuthTokenManager.get_valid_credentials(integration, "google_drive")

        mock_refresh.assert_called_once()
        assert result["access_token"] == "new-access"

    def test_notion_provider(self):
        """Should call Notion refresh for notion."""
        integration = {
            "id": "int-1",
            "access_token": "access",
            "refresh_token": None,
            "expires_at": None,
        }

        with patch.object(OAuthTokenManager, "refresh_notion_token", return_value=("notion-token", None)) as mock_refresh, \
             patch("core.security.decrypt_token", return_value="decrypted"):
            result = OAuthTokenManager.get_valid_credentials(integration, "notion")

        mock_refresh.assert_called_once()
        assert result["access_token"] == "notion-token"

    def test_github_provider(self):
        """Should validate GitHub token."""
        integration = {
            "id": "int-1",
            "access_token": "access",
            "refresh_token": None,
            "expires_at": None,
        }

        with patch.object(OAuthTokenManager, "validate_github_token", return_value="github-token"):
            result = OAuthTokenManager.get_valid_credentials(integration, "github")

        assert result["access_token"] == "github-token"
        assert result["refresh_token"] is None

    def test_unknown_provider_returns_decrypted(self):
        """Unknown provider should just decrypt tokens."""
        integration = {
            "id": "int-1",
            "access_token": "access",
            "refresh_token": "refresh",
            "expires_at": "2024-01-01T00:00:00Z",
        }

        with patch("core.security.decrypt_token", return_value="decrypted"):
            result = OAuthTokenManager.get_valid_credentials(integration, "unknown")

        assert result["access_token"] == "decrypted"


class TestWithTokenRefreshDecorator:
    """Test automatic token refresh decorator."""

    def test_successful_call_returns_result(self):
        """Should pass through successful calls."""
        @with_token_refresh("google_drive")
        def my_func():
            return "success"

        assert my_func() == "success"

    def test_non_token_error_propagates(self):
        """Non-token errors should propagate."""
        @with_token_refresh("google_drive")
        def my_func():
            raise ValueError("not a token error")

        with pytest.raises(ValueError):
            my_func()

    def test_token_error_triggers_refresh(self):
        """Token errors should trigger refresh and retry."""
        call_count = 0

        @with_token_refresh("google_drive")
        def my_func(integration):
            nonlocal call_count
            call_count += 1
            if call_count == 1:
                raise Exception("401 Unauthorized")
            return "success after retry"

        integration = {
            "id": "int-1",
            "access_token": "old",
            "refresh_token": "refresh",
        }

        with patch.object(OAuthTokenManager, "get_valid_credentials", return_value={"access_token": "new"}):
            result = my_func(integration=integration)

        assert result == "success after retry"
        assert call_count == 2

    def test_refresh_failure_raises_reconnect_error(self):
        """Refresh failure should raise reconnection error."""
        @with_token_refresh("google_drive")
        def my_func(integration):
            raise Exception("invalid_grant: token expired")

        integration = {
            "id": "int-1",
            "access_token": "old",
            "refresh_token": "refresh",
        }

        with patch.object(OAuthTokenManager, "get_valid_credentials", side_effect=TokenRefreshError("Failed")):
            with pytest.raises(Exception) as exc:
                my_func(integration=integration)
            assert "requires reconnection" in str(exc.value)


class TestTokenRefreshErrorException:
    """Test TokenRefreshError class."""

    def test_exception_message(self):
        """Exception should carry message."""
        exc = TokenRefreshError("Token expired")
        assert "Token expired" in str(exc)

    def test_exception_is_catchable(self):
        """Exception should be catchable."""
        with pytest.raises(TokenRefreshError):
            raise TokenRefreshError("test")
