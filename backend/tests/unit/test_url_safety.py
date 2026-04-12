import threading
from unittest.mock import patch

import pytest
import requests
from requests.adapters import HTTPAdapter

from connectors.base import ConnectorTransientError
from connectors.url_safety import (
    GRAPH_API_DOMAINS,
    MICROSOFT_DOWNLOAD_REDIRECT_DOMAINS,
    SafeAdapter,
    _ssrf_safe_create_connection,
    _thread_local,
    normalize_hostname,
    safe_session,
    validate_redirect_url,
)


def test_normalize_hostname_strips_case_whitespace_and_trailing_dot():
    assert normalize_hostname("  EXAMPLE.COM. ") == "example.com"


def test_validate_redirect_url_allows_expected_download_domain():
    url = "https://Tenant.SharePoint.com/path/file"

    with patch("connectors.url_safety.is_safe_host", return_value=True):
        assert validate_redirect_url(url, MICROSOFT_DOWNLOAD_REDIRECT_DOMAINS) == url


def test_validate_redirect_url_allows_graph_domain_with_trailing_dot():
    url = "https://graph.microsoft.com./v1.0/me/drive"

    with patch("connectors.url_safety.is_safe_host", return_value=True):
        assert validate_redirect_url(url, GRAPH_API_DOMAINS) == url


def test_validate_redirect_url_rejects_non_https():
    with pytest.raises(ConnectorTransientError, match="invalid scheme"):
        validate_redirect_url("http://tenant.sharepoint.com/path", MICROSOFT_DOWNLOAD_REDIRECT_DOMAINS)


def test_validate_redirect_url_rejects_disallowed_hostname():
    with pytest.raises(ConnectorTransientError, match="blocked redirect"):
        validate_redirect_url("https://evil.example.com/path", MICROSOFT_DOWNLOAD_REDIRECT_DOMAINS)


def test_validate_redirect_url_rejects_non_public_hostname():
    with patch("connectors.url_safety.is_safe_host", return_value=False):
        with pytest.raises(ConnectorTransientError, match="blocked redirect"):
            validate_redirect_url(
                "https://tenant.sharepoint.com/path",
                MICROSOFT_DOWNLOAD_REDIRECT_DOMAINS,
            )


def test_safe_session_mounts_adapter_on_both_schemes():
    session = safe_session()
    assert isinstance(session.adapters["https://"], SafeAdapter)
    assert isinstance(session.adapters["http://"], SafeAdapter)


def test_safe_session_disables_trust_env():
    session = safe_session()
    assert session.trust_env is False


def test_safe_adapter_normalizes_hostname_for_override():
    adapter = SafeAdapter()
    request = requests.Request("GET", "https://Example.COM./path").prepare()
    response = requests.Response()
    response.status_code = 200
    response._content = b""
    response.url = request.url
    called_addresses: list[tuple[str, int]] = []

    def fake_create_connection(address, *args, **kwargs):
        called_addresses.append(address)
        return object()

    def fake_parent_send(self, request, **kwargs):
        _ssrf_safe_create_connection(("example.com", 443))
        return response

    with patch("connectors.url_safety.socket.getaddrinfo", return_value=[("", "", "", "", ("8.8.8.8", 0))]), patch(
        "connectors.url_safety._original_create_connection",
        side_effect=fake_create_connection,
    ), patch.object(HTTPAdapter, "send", fake_parent_send):
        adapter.send(request)

    assert called_addresses == [("8.8.8.8", 443)]
    assert getattr(_thread_local, "dns_overrides", {}) == {}


def test_safe_adapter_cleans_thread_local_on_error():
    adapter = SafeAdapter()
    request = requests.Request("GET", "https://example.com/path").prepare()

    def boom(self, request, **kwargs):
        raise RuntimeError("send failed")

    with patch("connectors.url_safety.socket.getaddrinfo", return_value=[("", "", "", "", ("8.8.8.8", 0))]), patch.object(
        HTTPAdapter,
        "send",
        boom,
    ):
        with pytest.raises(RuntimeError, match="send failed"):
            adapter.send(request)

    assert getattr(_thread_local, "dns_overrides", {}) == {}


def test_safe_adapter_thread_isolation():
    results: list[tuple[str, int]] = []

    def fake_create_connection(address, *args, **kwargs):
        results.append(address)
        return object()

    _thread_local.dns_overrides = {"example.com": "8.8.8.8"}
    try:
        with patch("connectors.url_safety._original_create_connection", side_effect=fake_create_connection):
            worker = threading.Thread(
                target=lambda: _ssrf_safe_create_connection(("example.com", 443))
            )
            worker.start()
            worker.join()
    finally:
        _thread_local.dns_overrides = {}

    assert results == [("example.com", 443)]
