"""
Shared URL and hostname safety helpers for connector SSRF protection.
"""

from __future__ import annotations

import ipaddress
import logging
import socket
from collections.abc import Callable
from urllib.parse import urlparse

from connectors.base import ConnectorTransientError

logger = logging.getLogger(__name__)

MICROSOFT_DOWNLOAD_REDIRECT_DOMAINS: frozenset[str] = frozenset(
    {
        "sharepoint.com",
        "1drv.com",
    }
)

GRAPH_API_DOMAINS: frozenset[str] = frozenset({"graph.microsoft.com"})


def normalize_hostname(hostname: str) -> str:
    return hostname.strip().lower().rstrip(".")


def is_public_ip(ip: ipaddress.IPv4Address | ipaddress.IPv6Address) -> bool:
    return not (
        ip.is_private
        or ip.is_loopback
        or ip.is_link_local
        or ip.is_reserved
        or ip.is_multicast
        or ip.is_unspecified
    )


def is_safe_host(
    hostname: str,
    *,
    resolver: Callable[..., list[tuple]] = socket.getaddrinfo,
) -> bool:
    try:
        ip = ipaddress.ip_address(hostname)
        return is_public_ip(ip)
    except ValueError:
        try:
            infos = resolver(hostname, None)
        except socket.gaierror:
            return False

        for info in infos:
            addr = info[4][0]
            try:
                ip = ipaddress.ip_address(addr)
            except ValueError:
                return False
            if not is_public_ip(ip):
                return False
        return True


def is_safe_url(url: str) -> bool:
    try:
        parsed = urlparse(url)
        if parsed.scheme not in {"http", "https"}:
            return False
        if parsed.username or parsed.password:
            return False
        hostname = parsed.hostname
        if not hostname:
            return False
        return is_safe_host(hostname)
    except Exception:
        return False


def _hostname_matches_allowed_domain(hostname: str, allowed_domain: str) -> bool:
    normalized_host = normalize_hostname(hostname)
    normalized_allowed = normalize_hostname(allowed_domain)
    return normalized_host == normalized_allowed or normalized_host.endswith(f".{normalized_allowed}")


def validate_redirect_url(url: str, allowed_domains: frozenset[str]) -> str:
    parsed = urlparse(url)
    if parsed.scheme != "https":
        raise ConnectorTransientError(f"SSRF: blocked redirect due to invalid scheme: {parsed.scheme or 'missing'}")
    if parsed.username or parsed.password:
        raise ConnectorTransientError("SSRF: blocked redirect with embedded credentials")

    hostname = parsed.hostname
    if not hostname:
        raise ConnectorTransientError("SSRF: blocked redirect with missing hostname")

    if not any(_hostname_matches_allowed_domain(hostname, domain) for domain in allowed_domains):
        logger.warning("⚠️ [URLSafety] Blocked redirect to disallowed hostname: %s", hostname)
        raise ConnectorTransientError(f"SSRF: blocked redirect to {hostname}")

    if not is_safe_host(normalize_hostname(hostname)):
        logger.warning("⚠️ [URLSafety] Blocked redirect to non-public hostname: %s", hostname)
        raise ConnectorTransientError(f"SSRF: blocked redirect to {hostname}")

    return url
