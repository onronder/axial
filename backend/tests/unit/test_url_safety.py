from unittest.mock import patch

import pytest

from connectors.base import ConnectorTransientError
from connectors.url_safety import (
    GRAPH_API_DOMAINS,
    MICROSOFT_DOWNLOAD_REDIRECT_DOMAINS,
    normalize_hostname,
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
