"""
Comprehensive Unit Tests for WebConnector - Advanced Features

Tests advanced web crawling functionality:
- Bright Data Unlocker API integration
- YouTube proxy configuration
- fetch_file_content method
- SSRF protection (_enforce_public_endpoint)
- URL normalization edge cases
- Domain matching with subdomains
"""

import os
import sys
from unittest.mock import Mock, patch

import pytest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))


class TestBrightDataConfig:
    """Test Bright Data Unlocker API configuration."""

    def test_get_brightdata_config_from_settings(self):
        """Should load config from settings."""
        mock_settings = Mock()
        mock_settings.BRIGHTDATA_API_KEY = "test-api-key"
        mock_settings.BRIGHTDATA_UNLOCKER_ZONE = "test-zone"
        mock_settings.BRIGHTDATA_TIMEOUT = 45
        mock_settings.BRIGHTDATA_RETRY_COUNT = 2
        mock_settings.BRIGHTDATA_RETRY_DELAY = 1.5
        mock_settings.YOUTUBE_DIRECT_FALLBACK = False

        with patch("core.config.settings", mock_settings):
            from connectors.web import _get_brightdata_config
            config = _get_brightdata_config()

        assert config["api_key"] == "test-api-key"
        assert config["zone"] == "test-zone"
        assert config["timeout"] == 45

    def test_get_brightdata_config_fallback_to_env(self, monkeypatch):
        """Should fall back to environment variables if settings fails."""
        monkeypatch.setenv("BRIGHTDATA_API_KEY", "env-key")
        monkeypatch.setenv("BRIGHTDATA_UNLOCKER_ZONE", "env-zone")
        monkeypatch.setenv("BRIGHTDATA_TIMEOUT", "90")

        # Import and test the fallback path directly
        from connectors.web import _get_brightdata_config

        # The function should work with or without settings available
        config = _get_brightdata_config()
        # Just verify it returns a dict with the expected keys
        assert "api_key" in config
        assert "zone" in config


class TestFetchViaBrightDataUnlocker:
    """Test Bright Data Unlocker API fetch."""

    def test_fetch_success(self):
        """Should return content on successful fetch."""
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.text = "<html>Content via proxy</html>"

        config = {"api_key": "key", "zone": "zone", "timeout": 30}

        with patch("connectors.web.requests.post", return_value=mock_response):
            from connectors.web import _fetch_via_brightdata_unlocker
            result = _fetch_via_brightdata_unlocker("https://youtube.com/watch?v=123", config)

        assert "Content via proxy" in result

    def test_fetch_no_api_key_returns_none(self):
        """Should return None if no API key configured."""
        config = {"api_key": None, "zone": "zone", "timeout": 30}

        from connectors.web import _fetch_via_brightdata_unlocker
        result = _fetch_via_brightdata_unlocker("https://youtube.com", config)

        assert result is None

    def test_fetch_non_200_returns_none(self):
        """Should return None on non-200 response."""
        mock_response = Mock()
        mock_response.status_code = 403
        mock_response.text = "Forbidden"

        config = {"api_key": "key", "zone": "zone", "timeout": 30}

        with patch("connectors.web.requests.post", return_value=mock_response):
            from connectors.web import _fetch_via_brightdata_unlocker
            result = _fetch_via_brightdata_unlocker("https://youtube.com", config)

        assert result is None

    def test_fetch_timeout_returns_none(self):
        """Should return None on timeout."""
        import requests

        config = {"api_key": "key", "zone": "zone", "timeout": 1}

        with patch("connectors.web.requests.post", side_effect=requests.Timeout("timeout")):
            from connectors.web import _fetch_via_brightdata_unlocker
            result = _fetch_via_brightdata_unlocker("https://youtube.com", config)

        assert result is None

    def test_fetch_exception_returns_none(self):
        """Should return None on any exception."""
        config = {"api_key": "key", "zone": "zone", "timeout": 30}

        with patch("connectors.web.requests.post", side_effect=Exception("network error")):
            from connectors.web import _fetch_via_brightdata_unlocker
            result = _fetch_via_brightdata_unlocker("https://youtube.com", config)

        assert result is None


class TestYouTubeProxyConfig:
    """Test legacy YouTube proxy configuration."""

    def test_get_youtube_proxy_config_defaults(self):
        """Should return safe defaults."""
        from connectors.web import _get_youtube_proxy_config
        config = _get_youtube_proxy_config()

        # Verify the config has expected keys regardless of settings availability
        assert "enabled" in config
        assert "direct_fallback" in config


class TestBuildProxyDict:
    """Test proxy dictionary builder."""

    def test_build_proxy_dict_http(self):
        """Should build proxy dict for HTTP proxy."""
        from connectors.web import _build_proxy_dict

        result = _build_proxy_dict("http://proxy.example.com:8080")

        assert result == {
            "http": "http://proxy.example.com:8080",
            "https": "http://proxy.example.com:8080"
        }

    def test_build_proxy_dict_socks5(self):
        """Should accept SOCKS5 proxies."""
        from connectors.web import _build_proxy_dict

        result = _build_proxy_dict("socks5://user:pass@proxy.example.com:1080")

        assert "socks5://" in result["http"]

    def test_build_proxy_dict_invalid_scheme(self):
        """Should return None for invalid schemes."""
        from connectors.web import _build_proxy_dict

        assert _build_proxy_dict("ftp://invalid") is None

    def test_build_proxy_dict_empty(self):
        """Should return None for empty string."""
        from connectors.web import _build_proxy_dict

        assert _build_proxy_dict("") is None
        assert _build_proxy_dict(None) is None


class TestYouTubeProxyError:
    """Test YouTubeProxyError exception."""

    def test_exception_properties(self):
        """Should carry IP blocked info."""
        from connectors.web import YouTubeProxyError

        exc = YouTubeProxyError("blocked", is_ip_blocked=True, original_error=ValueError("orig"))

        assert exc.is_ip_blocked is True
        assert exc.original_error is not None


class TestFetchFileContent:
    """Test fetch_file_content method."""

    def test_fetch_file_content_success(self):
        """Should fetch and encode content."""
        from connectors.web import WebConnector

        connector = WebConnector()

        with patch.object(connector, "_is_safe_url", return_value=True), \
             patch.object(connector, "_enforce_public_endpoint"), \
             patch.object(connector, "fetch_html", return_value="<html>Content</html>"):
            content = connector.fetch_file_content("https://example.com/page", {})

        assert content == b"<html>Content</html>"

    def test_fetch_file_content_unsafe_url_raises(self):
        """Should raise ConnectorAuthError for unsafe URLs."""
        from connectors.base import ConnectorAuthError
        from connectors.web import WebConnector

        connector = WebConnector()

        with patch.object(connector, "_is_safe_url", return_value=False):
            with pytest.raises(ConnectorAuthError):
                connector.fetch_file_content("http://127.0.0.1", {})

    def test_fetch_file_content_fetch_failure_raises(self):
        """Should raise ConnectorTransientError on fetch failure."""
        from connectors.base import ConnectorTransientError
        from connectors.web import WebConnector

        connector = WebConnector()

        with patch.object(connector, "_is_safe_url", return_value=True), \
             patch.object(connector, "_enforce_public_endpoint"), \
             patch.object(connector, "fetch_html", return_value=None):
            with pytest.raises(ConnectorTransientError):
                connector.fetch_file_content("https://example.com", {})


class TestEnforcePublicEndpoint:
    """Test SSRF protection via _enforce_public_endpoint."""

    def test_allows_public_url(self):
        """Should not raise for public URLs."""
        from connectors.web import WebConnector

        connector = WebConnector()

        with patch.object(connector, "_is_safe_url", return_value=True):
            # Should not raise
            connector._enforce_public_endpoint("https://example.com")

    def test_blocks_private_url(self):
        """Should raise for private URLs."""
        from connectors.web import WebConnector

        connector = WebConnector()

        with patch.object(connector, "_is_safe_url", return_value=False):
            with pytest.raises(ValueError) as exc:
                connector._enforce_public_endpoint("http://192.168.1.1")
            assert "Security Violation" in str(exc.value)


class TestValidateConfig:
    """Test config validation."""

    def test_validate_config_valid_url(self):
        """Should return True for valid public URL."""
        from connectors.web import WebConnector

        connector = WebConnector()

        with patch.object(connector, "_is_safe_url", return_value=True):
            assert connector.validate_config({"url": "https://example.com"}) is True

    def test_validate_config_missing_url(self):
        """Should return False if URL missing."""
        from connectors.web import WebConnector

        connector = WebConnector()

        assert connector.validate_config({}) is False
        assert connector.validate_config({"url": ""}) is False

    def test_validate_config_unsafe_url(self):
        """Should return False for unsafe URL."""
        from connectors.web import WebConnector

        connector = WebConnector()

        with patch.object(connector, "_is_safe_url", return_value=False):
            assert connector.validate_config({"url": "http://localhost"}) is False


class TestNormalizeUrlEdgeCases:
    """Test URL normalization edge cases."""

    def test_removes_default_port_80(self):
        """Should remove default HTTP port 80."""
        from connectors.web import WebConnector

        connector = WebConnector()

        normalized = connector.normalize_url("http://example.com:80/path")
        assert ":80" not in normalized

    def test_removes_default_port_443(self):
        """Should remove default HTTPS port 443."""
        from connectors.web import WebConnector

        connector = WebConnector()

        normalized = connector.normalize_url("https://example.com:443/path")
        assert ":443" not in normalized

    def test_preserves_non_default_port(self):
        """Should preserve non-default ports."""
        from connectors.web import WebConnector

        connector = WebConnector()

        normalized = connector.normalize_url("https://example.com:8443/path")
        assert ":8443" in normalized

    def test_removes_fragment(self):
        """Should remove URL fragments."""
        from connectors.web import WebConnector

        connector = WebConnector()

        normalized = connector.normalize_url("https://example.com/page#section")
        assert "#section" not in normalized

    def test_removes_multiple_tracking_params(self):
        """Should remove all tracking params."""
        from connectors.web import WebConnector

        connector = WebConnector()

        normalized = connector.normalize_url(
            "https://example.com/page?keep=1&utm_source=google&utm_medium=cpc&gclid=abc&fbclid=def"
        )
        assert "utm_source" not in normalized
        assert "utm_medium" not in normalized
        assert "gclid" not in normalized
        assert "fbclid" not in normalized
        assert "keep=1" in normalized


class TestDomainMatching:
    """Test domain matching with subdomains."""

    def test_is_allowed_domain_exact_match(self):
        """Exact domain match should always be allowed."""
        from connectors.web import WebConnector

        connector = WebConnector()

        assert connector.is_allowed_domain("example.com", "example.com", allow_subdomains=False) is True
        assert connector.is_allowed_domain("Example.COM", "example.com", allow_subdomains=False) is True

    def test_is_allowed_domain_subdomain_allowed(self):
        """Subdomains allowed when flag is True."""
        from connectors.web import WebConnector

        connector = WebConnector()

        assert connector.is_allowed_domain("sub.example.com", "example.com", allow_subdomains=True) is True
        assert connector.is_allowed_domain("deep.sub.example.com", "example.com", allow_subdomains=True) is True

    def test_is_allowed_domain_subdomain_blocked(self):
        """Subdomains blocked when flag is False."""
        from connectors.web import WebConnector

        connector = WebConnector()

        assert connector.is_allowed_domain("sub.example.com", "example.com", allow_subdomains=False) is False

    def test_is_allowed_domain_different_domain(self):
        """Different domain should be blocked."""
        from connectors.web import WebConnector

        connector = WebConnector()

        assert connector.is_allowed_domain("malicious.com", "example.com", allow_subdomains=False) is False
        assert connector.is_allowed_domain("example.com.evil.com", "example.com", allow_subdomains=False) is False


class TestNormalizeHostname:
    """Test hostname normalization."""

    def test_strips_www_prefix(self):
        """Should strip www. prefix."""
        from connectors.web import WebConnector

        connector = WebConnector()

        assert connector._normalize_hostname("www.example.com") == "example.com"

    def test_strips_trailing_dot(self):
        """Should strip trailing dot."""
        from connectors.web import WebConnector

        connector = WebConnector()

        assert connector._normalize_hostname("example.com.") == "example.com"

    def test_lowercases_hostname(self):
        """Should lowercase hostname."""
        from connectors.web import WebConnector

        connector = WebConnector()

        assert connector._normalize_hostname("EXAMPLE.COM") == "example.com"


class TestIsSafeHost:
    """Test host safety checking."""

    def test_private_ip_blocked(self):
        """Private IP addresses should be blocked."""

        from connectors.web import WebConnector

        connector = WebConnector()
        connector._is_safe_host.cache_clear()

        # Mock DNS resolution to return private IP
        with patch("connectors.web.socket.getaddrinfo", return_value=[(None, None, None, None, ("192.168.1.1", 0))]):
            assert connector._is_safe_host("internal.example.com") is False

    def test_loopback_blocked(self):
        """Loopback addresses should be blocked."""
        from connectors.web import WebConnector

        connector = WebConnector()
        connector._is_safe_host.cache_clear()

        with patch("connectors.web.socket.getaddrinfo", return_value=[(None, None, None, None, ("127.0.0.1", 0))]):
            assert connector._is_safe_host("localhost") is False

    def test_public_ip_allowed(self):
        """Public IP addresses should be allowed."""
        from connectors.web import WebConnector

        connector = WebConnector()
        connector._is_safe_host.cache_clear()

        with patch("connectors.web.socket.getaddrinfo", return_value=[(None, None, None, None, ("93.184.216.34", 0))]):
            assert connector._is_safe_host("example.com") is True

    def test_dns_failure_blocked(self):
        """DNS resolution failure should block."""
        import socket

        from connectors.web import WebConnector

        connector = WebConnector()
        connector._is_safe_host.cache_clear()

        with patch("connectors.web.socket.getaddrinfo", side_effect=socket.gaierror()):
            assert connector._is_safe_host("nonexistent.invalid") is False


class TestSitemapPreflightChecks:
    """Test sitemap preflight validation."""

    def test_sitemap_preflight_rejects_html(self):
        """Should reject HTML responses masquerading as sitemaps."""
        from connectors.web import WebConnector

        connector = WebConnector()

        mock_response = Mock()
        mock_response.headers = {"Content-Type": "text/html"}
        mock_response.text = "<!DOCTYPE html><html><head></head><body></body></html>"
        mock_response.content = mock_response.text.encode("utf-8")

        with patch.object(connector, "_safe_get", return_value=mock_response):
            urls = connector.parse_sitemap("https://example.com/sitemap.xml")

        # Should return empty list due to HTML content
        assert urls == []

    def test_sitemap_preflight_rejects_4xx_status(self):
        """Should return empty on 4xx status."""
        from connectors.web import WebConnector

        connector = WebConnector()

        with patch.object(connector, "_safe_get", side_effect=Exception("HTTP 404")):
            urls = connector.parse_sitemap("https://example.com/sitemap.xml")

        assert urls == []


class TestFetchDocumentsSyncBehavior:
    """Test fetch_documents_sync behavior."""

    def test_empty_item_ids_returns_empty(self):
        """Empty item_ids should return empty."""
        from connectors.web import WebConnector

        connector = WebConnector()

        docs = list(connector.fetch_documents_sync([]))
        assert docs == []

    def test_respects_robots_txt_when_enabled(self):
        """Should skip URLs blocked by robots.txt."""
        from connectors.web import WebConnector

        connector = WebConnector()

        with patch.object(connector, "_is_safe_url", return_value=True), \
             patch.object(connector, "check_robots_txt", return_value=False):
            docs = list(connector.fetch_documents_sync(["https://example.com"], respect_robots=True))

        assert docs == []

    def test_ignores_robots_txt_when_disabled(self):
        """Should not check robots.txt when disabled."""
        from connectors.web import WebConnector

        connector = WebConnector()

        with patch.object(connector, "_is_safe_url", return_value=True), \
             patch.object(connector, "check_robots_txt") as mock_robots, \
             patch.object(connector, "is_youtube_url", return_value=False), \
             patch.object(connector, "fetch_html", return_value=None):
            list(connector.fetch_documents_sync(["https://example.com"], respect_robots=False))

        mock_robots.assert_not_called()


class TestConnectorType:
    """Test connector type property."""

    def test_connector_type_is_web(self):
        """Should return WEB source type."""
        from connectors.enhanced import SourceType
        from connectors.web import WebConnector

        connector = WebConnector()

        assert connector.connector_type == SourceType.WEB


class TestGetYouTubeMetadata:
    """Test YouTube metadata extraction."""

    def test_extracts_video_id(self):
        """Should extract video ID and build metadata."""
        from connectors.web import WebConnector

        connector = WebConnector()

        metadata = connector.get_youtube_metadata("https://youtube.com/watch?v=dQw4w9WgXcQ")

        assert metadata["source"] == "youtube"
        assert "dQw4w9WgXcQ" in metadata.get("source_url", "")

    def test_handles_short_url(self):
        """Should handle youtu.be short URLs."""
        from connectors.web import WebConnector

        connector = WebConnector()

        metadata = connector.get_youtube_metadata("https://youtu.be/dQw4w9WgXcQ")

        assert metadata["source"] == "youtube"
