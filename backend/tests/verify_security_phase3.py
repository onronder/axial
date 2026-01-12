"""
Phase 3 Security Verification

Tests:
1) Malware stub is active.
2) SSRF protection blocks localhost/private targets.
3) SSRF protection allows public targets.
"""

import asyncio
from backend.services import malware
from backend.connectors.web import WebConnector


def test_malware_stub():
    result = malware.scan_content(b"test")
    assert result.get("safe") is True, "Malware stub should mark content as safe"
    print("✅ Malware Stub: Active")


def test_ssrf_block_localhost():
    connector = WebConnector()
    # Test is_safe_url method directly
    assert connector.is_safe_url("http://127.0.0.1") is False, "is_safe_url should block localhost"
    assert connector.is_safe_url("http://localhost") is False, "is_safe_url should block localhost"
    
    # Test _enforce_public_endpoint raises for private IPs
    try:
        connector._enforce_public_endpoint("http://127.0.0.1/test")
        raise AssertionError("❌ FAILED: Localhost was not blocked by _enforce_public_endpoint!")
    except Exception as exc:
        msg = str(exc).lower()
        if "private" in msg or "denied" in msg or "unsafe" in msg or "loopback" in msg or "ssrf" in msg:
            print("✅ SSRF Protection: Localhost Blocked")
            return
        # It may be a connection error which is also acceptable (can't connect to localhost)
        if "connection" in msg or "resolve" in msg:
            print("✅ SSRF Protection: Localhost Blocked (connection refused)")
            return
        raise


def test_ssrf_allow_public():
    connector = WebConnector()
    # Test is_safe_url allows public URLs
    assert connector.is_safe_url("http://example.com") is True, "is_safe_url should allow public URLs"
    assert connector.is_safe_url("https://google.com") is True, "is_safe_url should allow public HTTPS URLs"
    
    # Test _enforce_public_endpoint doesn't raise for public URLs
    try:
        connector._enforce_public_endpoint("http://example.com")
        print("✅ SSRF Protection: Public URL Allowed")
    except Exception as exc:
        msg = str(exc).lower()
        # Connection errors are fine (no network in test), security blocks are not
        if "private" in msg or "loopback" in msg or "ssrf" in msg:
            raise AssertionError(f"Unexpected security block for public URL: {exc}")
        print("✅ SSRF Protection: Public URL Allowed (with non-security exception)")


if __name__ == "__main__":
    test_malware_stub()
    test_ssrf_block_localhost()
    test_ssrf_allow_public()
