"""
URL Validator Utility

SECURITY FIX: Prevents Server-Side Request Forgery (SSRF) attacks by validating
URLs before making HTTP requests to external services.

This module blocks:
- Localhost and loopback addresses
- Private IP ranges (10.x, 172.16-31.x, 192.168.x)
- Link-local addresses (169.254.x.x)
- Cloud metadata endpoints (169.254.169.254)
- IPv6 loopback and private addresses

Usage:
    from core.url_validator import is_safe_url, validate_url
    
    if is_safe_url(user_provided_url):
        response = requests.get(user_provided_url)
    
    # Or with exception:
    validate_url(user_provided_url)  # Raises ValueError if unsafe
"""

import ipaddress
import logging
import socket
from urllib.parse import urlparse
from typing import Optional, Set

logger = logging.getLogger(__name__)

# Blocked hostnames that could expose internal services
BLOCKED_HOSTNAMES: Set[str] = {
    'localhost',
    'localhost.localdomain',
    '127.0.0.1',
    '0.0.0.0',
    '::1',
    '::',
    # AWS/GCP/Azure metadata endpoints
    '169.254.169.254',
    'metadata.google.internal',
    'metadata.goog',
    # Kubernetes internal
    'kubernetes.default',
    'kubernetes.default.svc',
    'kubernetes.default.svc.cluster.local',
}

# Blocked URL schemes
BLOCKED_SCHEMES: Set[str] = {
    'file',
    'ftp',
    'gopher',
    'data',
    'javascript',
    'vbscript',
}

# Allowed schemes for HTTP requests
ALLOWED_SCHEMES: Set[str] = {
    'http',
    'https',
}


def _is_private_ip(ip_str: str) -> bool:
    """
    Check if an IP address is private, loopback, or link-local.
    
    Args:
        ip_str: String representation of IP address
        
    Returns:
        True if the IP is private/internal, False otherwise
    """
    try:
        ip = ipaddress.ip_address(ip_str)
        return (
            ip.is_private or
            ip.is_loopback or
            ip.is_link_local or
            ip.is_reserved or
            ip.is_multicast or
            ip.is_unspecified
        )
    except ValueError:
        # Not a valid IP address
        return False


def _resolve_hostname(hostname: str) -> Optional[str]:
    """
    Resolve a hostname to its IP address for validation.
    
    Args:
        hostname: The hostname to resolve
        
    Returns:
        The resolved IP address, or None if resolution fails
    """
    try:
        # Get IPv4 address
        return socket.gethostbyname(hostname)
    except socket.gaierror:
        return None


def is_safe_url(url: str, allow_internal: bool = False) -> bool:
    """
    Check if a URL is safe to request (not pointing to internal services).
    
    SECURITY: This function prevents SSRF attacks by blocking requests to:
    - Internal/private IP addresses
    - Localhost and loopback addresses
    - Cloud metadata endpoints
    - Blocked URL schemes (file://, ftp://, etc.)
    
    Args:
        url: The URL to validate
        allow_internal: If True, allows internal/private IPs (use with caution!)
        
    Returns:
        True if the URL is safe to request, False otherwise
    """
    if not url or not isinstance(url, str):
        return False
    
    try:
        parsed = urlparse(url.strip())
        
        # Check scheme
        scheme = (parsed.scheme or '').lower()
        if scheme in BLOCKED_SCHEMES:
            logger.warning(f"SSRF Protection: Blocked scheme '{scheme}' in URL")
            return False
        
        if scheme not in ALLOWED_SCHEMES:
            logger.warning(f"SSRF Protection: Unknown scheme '{scheme}' in URL")
            return False
        
        # Get hostname
        hostname = (parsed.hostname or '').lower().strip()
        if not hostname:
            logger.warning("SSRF Protection: Empty hostname in URL")
            return False
        
        # Check against blocked hostnames
        if hostname in BLOCKED_HOSTNAMES:
            logger.warning(f"SSRF Protection: Blocked hostname '{hostname}'")
            return False
        
        # Check for hostname ending with blocked suffixes
        blocked_suffixes = ['.local', '.internal', '.localhost', '.localdomain']
        for suffix in blocked_suffixes:
            if hostname.endswith(suffix):
                logger.warning(f"SSRF Protection: Blocked hostname suffix '{suffix}'")
                return False
        
        # Check if hostname is an IP address
        if _is_private_ip(hostname):
            if allow_internal:
                logger.debug(f"SSRF Protection: Allowing internal IP '{hostname}' (allow_internal=True)")
                return True
            logger.warning(f"SSRF Protection: Blocked private IP '{hostname}'")
            return False
        
        # Resolve hostname and check resolved IP
        resolved_ip = _resolve_hostname(hostname)
        if resolved_ip:
            if _is_private_ip(resolved_ip):
                if allow_internal:
                    logger.debug(f"SSRF Protection: Allowing internal resolved IP '{resolved_ip}' (allow_internal=True)")
                    return True
                logger.warning(f"SSRF Protection: Hostname '{hostname}' resolves to private IP '{resolved_ip}'")
                return False
        
        return True
        
    except Exception as e:
        logger.error(f"SSRF Protection: Error validating URL: {e}")
        return False


def validate_url(url: str, allow_internal: bool = False) -> str:
    """
    Validate a URL and raise ValueError if it's unsafe.
    
    Args:
        url: The URL to validate
        allow_internal: If True, allows internal/private IPs (use with caution!)
        
    Returns:
        The validated URL (stripped of whitespace)
        
    Raises:
        ValueError: If the URL is unsafe or invalid
    """
    if not url:
        raise ValueError("URL cannot be empty")
    
    url = url.strip()
    
    if not is_safe_url(url, allow_internal=allow_internal):
        raise ValueError(f"URL validation failed: potentially unsafe URL")
    
    return url


def sanitize_url_for_logging(url: str) -> str:
    """
    Sanitize a URL for safe logging (removes credentials, truncates).
    
    Args:
        url: The URL to sanitize
        
    Returns:
        A sanitized version safe for logging
    """
    if not url:
        return "<empty>"
    
    try:
        parsed = urlparse(url)
        # Remove credentials from URL
        safe_netloc = parsed.hostname or ""
        if parsed.port:
            safe_netloc += f":{parsed.port}"
        
        # Truncate path for logging
        path = parsed.path
        if len(path) > 50:
            path = path[:47] + "..."
        
        return f"{parsed.scheme}://{safe_netloc}{path}"
    except Exception:
        # If parsing fails, just truncate
        if len(url) > 100:
            return url[:97] + "..."
        return url
