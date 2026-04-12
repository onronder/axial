"""
Shared URL and hostname safety helpers for connector SSRF protection.
"""

from __future__ import annotations

import ipaddress
import logging
import socket
import threading
from collections.abc import Callable
from urllib.parse import urlparse

import requests
import urllib3
from requests.adapters import HTTPAdapter

from connectors.base import ConnectorTransientError

logger = logging.getLogger(__name__)

_thread_local = threading.local()
_original_create_connection = urllib3.util.connection.create_connection
_NO_OVERRIDE = object()

MICROSOFT_DOWNLOAD_REDIRECT_DOMAINS: frozenset[str] = frozenset(
    {
        "sharepoint.com",
        "1drv.com",
    }
)

GRAPH_API_DOMAINS: frozenset[str] = frozenset({"graph.microsoft.com"})


def normalize_hostname(hostname: str) -> str:
    return hostname.strip().lower().rstrip(".")


def _ssrf_safe_create_connection(address, *args, **kwargs):
    """Drop-in replacement for urllib3 connection creation with pinned IP support."""
    host, port = address
    overrides = getattr(_thread_local, "dns_overrides", None)
    if overrides:
        normalized_host = normalize_hostname(host)
        pinned_ip = overrides.get(normalized_host)
        if pinned_ip:
            return _original_create_connection((pinned_ip, port), *args, **kwargs)
    return _original_create_connection(address, *args, **kwargs)


urllib3.util.connection.create_connection = _ssrf_safe_create_connection


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


class SafeAdapter(HTTPAdapter):
    """HTTP adapter that validates DNS answers and pins the connection to a validated IP."""

    def send(self, request, stream=False, timeout=None, verify=True, cert=None, proxies=None):
        parsed = urlparse(request.url)
        hostname = parsed.hostname

        if not hostname:
            return super().send(
                request,
                stream=stream,
                timeout=timeout,
                verify=verify,
                cert=cert,
                proxies=proxies,
            )

        normalized_host = normalize_hostname(hostname)

        try:
            infos = socket.getaddrinfo(hostname, None)
        except socket.gaierror as exc:
            raise ConnectorTransientError(
                f"SSRF: DNS resolution failed for {hostname}"
            ) from exc

        if not infos:
            raise ConnectorTransientError(f"SSRF: no DNS records for {hostname}")

        pinned_ip: str | None = None
        for info in infos:
            candidate = info[4][0]
            try:
                ip = ipaddress.ip_address(candidate)
            except ValueError as exc:
                raise ConnectorTransientError(
                    f"SSRF: DNS resolved to invalid address {candidate} for {hostname}"
                ) from exc

            if not is_public_ip(ip):
                raise ConnectorTransientError(
                    f"SSRF: DNS resolved to non-public IP {ip} for {hostname}"
                )
            if pinned_ip is None:
                pinned_ip = str(ip)

        if pinned_ip is None:
            raise ConnectorTransientError(f"SSRF: no usable DNS records for {hostname}")

        overrides = getattr(_thread_local, "dns_overrides", None)
        if overrides is None:
            overrides = {}
            _thread_local.dns_overrides = overrides

        previous = overrides.get(normalized_host, _NO_OVERRIDE)
        overrides[normalized_host] = pinned_ip
        try:
            return super().send(
                request,
                stream=stream,
                timeout=timeout,
                verify=verify,
                cert=cert,
                proxies=proxies,
            )
        finally:
            if previous is _NO_OVERRIDE:
                overrides.pop(normalized_host, None)
            else:
                overrides[normalized_host] = previous


def safe_session(headers: dict[str, str] | None = None) -> requests.Session:
    """Create a requests session with SSRF-safe DNS pinning enabled."""
    session = requests.Session()
    session.trust_env = False
    adapter = SafeAdapter()
    session.mount("https://", adapter)
    session.mount("http://", adapter)
    if headers:
        session.headers.update(headers)
    return session


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
