from datetime import datetime, timedelta, timezone
from unittest.mock import MagicMock, patch

import pytest

from services.oauth_token_manager import OAuthTokenManager, TokenRefreshError, with_token_refresh
from core.config import settings


def test_is_token_expired_returns_true_on_missing():
    assert OAuthTokenManager.is_token_expired(None) is True


def test_is_token_expired_future_returns_false():
    expires_at = (datetime.now(timezone.utc) + timedelta(hours=1)).isoformat()
    assert OAuthTokenManager.is_token_expired(expires_at) is False


def test_is_token_expired_invalid_format_returns_true():
    assert OAuthTokenManager.is_token_expired("not-a-timestamp") is True


def test_refresh_google_token_skips_refresh_when_valid(monkeypatch):
    monkeypatch.setattr(settings, "GOOGLE_CLIENT_ID", "client-id")
    monkeypatch.setattr(settings, "GOOGLE_CLIENT_SECRET", "client-secret")

    with patch("core.security.decrypt_token", side_effect=["access", "refresh"]), \
         patch.object(OAuthTokenManager, "is_token_expired", return_value=False):
        access, expires_at = OAuthTokenManager.refresh_google_token(
            integration_id="int-1",
            access_token="enc-access",
            refresh_token="enc-refresh",
            expires_at="2030-01-01T00:00:00+00:00",
        )

    assert access == "access"
    assert expires_at == "2030-01-01T00:00:00+00:00"


def test_refresh_google_token_updates_db_on_refresh(monkeypatch):
    monkeypatch.setattr(settings, "GOOGLE_CLIENT_ID", "client-id")
    monkeypatch.setattr(settings, "GOOGLE_CLIENT_SECRET", "client-secret")

    supabase = MagicMock()
    supabase.table.return_value.update.return_value.eq.return_value.execute.return_value = MagicMock(data=[{"id": "int-1"}])

    class FakeCreds:
        def __init__(self, **kwargs):
            self.token = "new-token"
            self.expiry = datetime(2035, 1, 1, tzinfo=timezone.utc)

        def refresh(self, request):
            self.token = "new-token"
            self.expiry = datetime(2035, 1, 1, tzinfo=timezone.utc)

    with patch("core.security.decrypt_token", side_effect=["access", "refresh"]), \
         patch("core.security.encrypt_token", return_value="enc-new"), \
         patch("core.db.get_supabase", return_value=supabase), \
         patch("google.oauth2.credentials.Credentials", FakeCreds), \
         patch("google.auth.transport.requests.Request", return_value=object()), \
         patch.object(OAuthTokenManager, "is_token_expired", return_value=True):
        access, expires_at = OAuthTokenManager.refresh_google_token(
            integration_id="int-1",
            access_token="enc-access",
            refresh_token="enc-refresh",
            expires_at="2020-01-01T00:00:00+00:00",
        )

    assert access == "new-token"
    assert expires_at.startswith("2035-01-01")
    supabase.table.assert_called_with("user_integrations")


def test_refresh_google_token_raises_without_refresh_token():
    with patch("core.security.decrypt_token", return_value=None):
        with pytest.raises(TokenRefreshError):
            OAuthTokenManager.refresh_google_token(
                integration_id="int-1",
                access_token="enc-access",
                refresh_token=None,
                expires_at=None,
            )


def test_refresh_microsoft_token_skips_refresh_when_valid(monkeypatch):
    monkeypatch.setattr(settings, "MICROSOFT_CLIENT_ID", "client-id")
    monkeypatch.setattr(settings, "MICROSOFT_CLIENT_SECRET", "client-secret")

    with patch("core.security.decrypt_token", side_effect=["access", "refresh"]), \
         patch.object(OAuthTokenManager, "is_token_expired", return_value=False):
        access, refresh, expires_at = OAuthTokenManager.refresh_microsoft_token(
            integration_id="int-1",
            access_token="enc-access",
            refresh_token="enc-refresh",
            expires_at="2030-01-01T00:00:00+00:00",
            provider="onedrive",
        )

    assert access == "access"
    assert refresh == "refresh"
    assert expires_at == "2030-01-01T00:00:00+00:00"


def test_refresh_microsoft_token_updates_db_on_refresh(monkeypatch):
    monkeypatch.setattr(settings, "MICROSOFT_CLIENT_ID", "client-id")
    monkeypatch.setattr(settings, "MICROSOFT_CLIENT_SECRET", "client-secret")
    monkeypatch.setattr(settings, "MICROSOFT_TENANT_ID", "common")

    supabase = MagicMock()
    supabase.table.return_value.update.return_value.eq.return_value.execute.return_value = MagicMock(data=[{"id": "int-1"}])

    class FakeResponse:
        status_code = 200

        def json(self):
            return {"access_token": "new-token", "refresh_token": "new-refresh", "expires_in": 3600}

    with patch("core.security.decrypt_token", side_effect=["access", "refresh"]), \
         patch("core.security.encrypt_token", side_effect=lambda value: f"enc-{value}"), \
         patch("core.db.get_supabase", return_value=supabase), \
         patch("requests.post", return_value=FakeResponse()), \
         patch.object(OAuthTokenManager, "is_token_expired", return_value=True):
        access, refresh, expires_at = OAuthTokenManager.refresh_microsoft_token(
            integration_id="int-1",
            access_token="enc-access",
            refresh_token="enc-refresh",
            expires_at="2020-01-01T00:00:00+00:00",
            provider="sharepoint",
        )

    assert access == "new-token"
    assert refresh == "new-refresh"
    assert expires_at is not None
    supabase.table.assert_called_with("user_integrations")


def test_refresh_microsoft_token_raises_without_refresh_token():
    with patch("core.security.decrypt_token", return_value=None):
        with pytest.raises(TokenRefreshError):
            OAuthTokenManager.refresh_microsoft_token(
                integration_id="int-1",
                access_token="enc-access",
                refresh_token=None,
                expires_at=None,
                provider="onedrive",
            )


def test_get_valid_credentials_google(monkeypatch):
    monkeypatch.setattr(settings, "GOOGLE_CLIENT_ID", "client-id")
    monkeypatch.setattr(settings, "GOOGLE_CLIENT_SECRET", "client-secret")

    with patch.object(OAuthTokenManager, "refresh_google_token", return_value=("access", "expires")), \
         patch("core.security.decrypt_token", return_value="refresh"):
        creds = OAuthTokenManager.get_valid_credentials(
            {"id": "int-1", "access_token": "enc", "refresh_token": "enc"},
            "google_drive",
        )

    assert creds["access_token"] == "access"
    assert creds["refresh_token"] == "refresh"


def test_get_valid_credentials_notion():
    with patch.object(OAuthTokenManager, "refresh_notion_token", return_value=("access", "expires")), \
         patch("core.security.decrypt_token", return_value="refresh"):
        creds = OAuthTokenManager.get_valid_credentials(
            {"id": "int-1", "access_token": "enc", "refresh_token": "enc"},
            "notion",
        )

    assert creds["access_token"] == "access"
    assert creds["refresh_token"] == "refresh"


def test_get_valid_credentials_onedrive():
    with patch.object(OAuthTokenManager, "refresh_microsoft_token", return_value=("access", "refresh", "expires")):
        creds = OAuthTokenManager.get_valid_credentials(
            {"id": "int-1", "access_token": "enc", "refresh_token": "enc"},
            "onedrive",
        )

    assert creds["access_token"] == "access"
    assert creds["refresh_token"] == "refresh"


def test_refresh_notion_token_returns_decrypted_access():
    with patch("core.security.decrypt_token", return_value="access-token"):
        access, expires_at = OAuthTokenManager.refresh_notion_token(
            integration_id="int-1",
            access_token="enc-access",
            refresh_token=None,
            expires_at="2099-01-01T00:00:00+00:00",
        )

    assert access == "access-token"
    assert expires_at == "2099-01-01T00:00:00+00:00"


def test_get_valid_credentials_unknown_provider_uses_tokens():
    with patch("core.security.decrypt_token", side_effect=["access", "refresh"]):
        creds = OAuthTokenManager.get_valid_credentials(
            {"id": "int-1", "access_token": "enc-access", "refresh_token": "enc-refresh"},
            "other",
        )

    assert creds["access_token"] == "access"
    assert creds["refresh_token"] == "refresh"


def test_get_valid_credentials_wraps_unexpected_errors():
    with patch.object(OAuthTokenManager, "refresh_google_token", side_effect=RuntimeError("boom")):
        with pytest.raises(TokenRefreshError):
            OAuthTokenManager.get_valid_credentials(
                {"id": "int-1", "access_token": "enc"},
                "google_drive",
            )


def test_get_valid_credentials_reraises_token_refresh_error():
    with patch.object(OAuthTokenManager, "refresh_google_token", side_effect=TokenRefreshError("bad")):
        with pytest.raises(TokenRefreshError):
            OAuthTokenManager.get_valid_credentials(
                {"id": "int-1", "access_token": "enc"},
                "google_drive",
            )


def test_with_token_refresh_retries_on_token_error():
    integration = {"id": "int-1", "access_token": "old"}
    calls = {"count": 0}

    def flaky_call(*args, **kwargs):
        calls["count"] += 1
        if calls["count"] == 1:
            raise Exception("invalid_grant")
        return "ok"

    decorated = with_token_refresh("google_drive")(flaky_call)

    with patch.object(OAuthTokenManager, "get_valid_credentials", return_value={"access_token": "new"}):
        result = decorated(integration)

    assert result == "ok"
    assert calls["count"] == 2
    assert integration["access_token"] == "new"


def test_with_token_refresh_updates_kwargs_integration():
    integration = {"id": "int-1", "access_token": "old"}
    calls = {"count": 0}

    def flaky_call(*args, **kwargs):
        calls["count"] += 1
        if calls["count"] == 1:
            raise Exception("invalid_grant")
        return "ok"

    decorated = with_token_refresh("google_drive")(flaky_call)

    with patch.object(OAuthTokenManager, "get_valid_credentials", return_value={"access_token": "new"}):
        result = decorated(integration=integration)

    assert result == "ok"
    assert integration["access_token"] == "new"


def test_with_token_refresh_raises_when_refresh_fails():
    integration = {"id": "int-1", "access_token": "old"}

    def failing_call(*args, **kwargs):
        raise Exception("401 unauthorized")

    decorated = with_token_refresh("google_drive")(failing_call)

    with patch.object(OAuthTokenManager, "get_valid_credentials", side_effect=TokenRefreshError("bad")):
        with pytest.raises(Exception, match="Integration requires reconnection"):
            decorated(integration)


def test_with_token_refresh_reraises_non_token_errors():
    def failing_call(*_args, **_kwargs):
        raise Exception("network down")

    decorated = with_token_refresh("google_drive")(failing_call)

    with pytest.raises(Exception, match="network down"):
        decorated({"id": "int-1"})
