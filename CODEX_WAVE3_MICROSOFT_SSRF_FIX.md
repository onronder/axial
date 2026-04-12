# Wave 3 — Microsoft Connector SSRF Hardening

**Status:** DESIGN LOCK — ready for implementation  
**Priority:** PRE-GO-LIVE BLOCKER  
**Commit base:** 7d633a9 (Wave 2 complete)

---

## Problem Statement

`MicrosoftGraphConnector` (`backend/connectors/microsoft.py`) has two SSRF
vectors that allow the connector to make HTTP requests to arbitrary URLs,
including internal network addresses (169.254.169.254 metadata service,
10.0.0.0/8, localhost, etc.).

### Vector 1 — Download Redirect (CRITICAL)

**Location:** `_download_content()` lines 374-402

The connector requests `/drives/{drive_id}/items/{item_id}/content` with
`allow_redirects=False`, then manually follows the `Location` header at
line 387 **without any domain or IP validation**:

```python
# Line 387 — current code, DANGEROUS
response = self._request_with_retry("GET", location, headers={}, stream=True)
```

Microsoft Graph normally redirects downloads to a `*.sharepoint.com` or
`*.1drv.com` CDN URL. However, if a response is tampered with (MITM, proxy
injection, compromised Graph edge) or the token has elevated scopes, the
`Location` header could point anywhere.

**Risk:** Arbitrary HTTP GET to any URL from the backend server context.
Attacker can reach cloud metadata endpoints, internal services, or
exfiltrate data via DNS.

### Vector 2 — Delta/Pagination URL Trust (HIGH)

**Location:** `_delta_listing()` lines 279-300, `_paged_items()` lines 404-409

Both methods follow URLs from Microsoft Graph response bodies without
validation:

- `_delta_listing()` line 280: If stored `delta_token` starts with "http",
  it is used directly as a URL
- `_delta_listing()` line 294-295: `@odata.nextLink` and `@odata.deltaLink`
  are followed verbatim
- `_paged_items()` line 409: `@odata.nextLink` followed verbatim

If the database is compromised (stored delta_token replaced) or a Graph
response is tampered with, these URLs route requests to arbitrary hosts.

---

## Solution Design

### Approach: Shared URL Validator Module

Extract SSRF validation from `web.py` into a shared module, then apply it
at all three trust boundaries in `microsoft.py`.

### Step 1 — Create `backend/connectors/url_safety.py`

Extract these functions from `web.py` (lines 1063-1166) into a standalone
module with **no class dependency**:

```
def is_public_ip(ip: ipaddress.IPv4Address | ipaddress.IPv6Address) -> bool
def is_safe_host(hostname: str) -> bool
def validate_redirect_url(url: str, allowed_domains: frozenset[str]) -> str
def is_safe_url(url: str) -> bool   # generic: http(s), no creds, public IP
```

`is_safe_url` is the generic version (allows HTTP, no domain allowlist,
just scheme + credential + public IP checks) — matches existing
`WebConnector._is_safe_url()` semantics exactly. `validate_redirect_url`
is the strict version (HTTPS only, domain allowlist required, same IP
checks). Two functions, shared IP primitives.

**`validate_redirect_url` specification:**

1. Parse `url` with `urllib.parse.urlparse`
2. Reject if scheme is not `https` (Microsoft CDN always uses HTTPS)
3. Reject if `parsed.username` or `parsed.password` present
4. Extract `hostname` — reject if None or empty
5. Check hostname against `allowed_domains` (suffix match, e.g.
   `sharepoint.com` matches `tenant-my.sharepoint.com`). This is the
   **primary defense** — only Microsoft-controlled CDN domains are allowed.
6. Resolve hostname via `socket.getaddrinfo` — reject if ANY resolved IP
   is private/loopback/link-local/reserved/multicast/unspecified (reuse
   `is_public_ip` logic)
7. Return the validated URL string on success
8. Raise `ConnectorTransientError("SSRF: blocked redirect to {hostname}")`
   on failure with WARNING-level log

**`allowed_domains` for Microsoft Graph download redirects:**

```python
MICROSOFT_DOWNLOAD_REDIRECT_DOMAINS: frozenset[str] = frozenset({
    "sharepoint.com",       # SharePoint/OneDrive CDN (primary)
    "1drv.com",             # OneDrive short links / CDN
})
```

This allowlist is intentionally narrow: only domains that Microsoft Graph
actually redirects file downloads to. The wider Microsoft ecosystem
(`microsoft.com`, `office.com`, `windows.net`, `live.com`, etc.) is NOT
included because download redirects do not legitimately target those
domains. A narrow list is the primary SSRF defense — widening it defeats
the purpose.

If a new legitimate CDN domain is observed in production (e.g. from
download redirect logs), it can be added explicitly with a comment
explaining the evidence.

**Domain matching rule:** Before matching, normalize the hostname:
`hostname.strip().lower().rstrip(".")`. Then check: hostname must either
equal or end with `.{domain}` for any domain in the set. Example:
`Tenant-My.SharePoint.com.` → normalized to `tenant-my.sharepoint.com`
→ matches because it ends with `.sharepoint.com`.

This normalization must also apply inside `validate_redirect_url` before
the domain allowlist check. Consistent lowercase + trailing dot strip
prevents bypass via case tricks or DNS trailing dot notation.

### Step 2 — Refactor `web.py` to use shared module (narrow scope)

Extract ONLY the IP/host-level primitives into the shared module. Do NOT
move or alter `WebConnector._is_safe_url()` — it has different semantics
(allows HTTP, no domain allowlist) that must not change.

Specifically:
- `web.py` imports `is_public_ip` and `is_safe_host` from `url_safety`
- `WebConnector._is_public_ip()` becomes a thin wrapper: `return is_public_ip(ip)`
- `WebConnector._is_safe_host()` becomes a thin wrapper: `return is_safe_host(hostname)`
- `WebConnector._is_safe_url()` stays as-is in `web.py` (unchanged logic)
- `WebConnector._enforce_public_endpoint()` stays as-is (TOCTOU is Wave 4)

**Cache preservation:** `WebConnector._is_safe_host()` currently has
`@lru_cache(maxsize=512)` and tests call `connector._is_safe_host.cache_clear()`.
The wrapper MUST preserve this contract:

```python
@lru_cache(maxsize=512)
def _is_safe_host(self, hostname: str) -> bool:
    return is_safe_host(hostname)
```

The shared `is_safe_host()` in `url_safety.py` should NOT have its own
`@lru_cache` — caching stays at the caller level to avoid double-cache
and to preserve the existing `cache_clear()` test surface.

This ensures zero behavior change in `web.py` while eliminating IP/host
validation duplication.

### Step 3 — Harden `_download_content()`

**File:** `microsoft.py`, method `_download_content()`

Replace line 387 with:

```python
from connectors.url_safety import validate_redirect_url, MICROSOFT_DOWNLOAD_REDIRECT_DOMAINS

# After extracting location from headers:
location = validate_redirect_url(location, MICROSOFT_DOWNLOAD_REDIRECT_DOMAINS)
response = self._request_with_retry("GET", location, headers={}, stream=True)
```

This is the primary fix. All download redirects must pass domain allowlist
+ IP safety checks before the request fires.

### Step 4 — Harden `_delta_listing()` and `_paged_items()`

**`_delta_listing()`** — add Graph URL validation at line 280 and line 295.

Use the shared `validate_redirect_url` from `url_safety.py` with a
Graph-specific allowlist. This ensures both domain check AND IP safety
check run on pagination/delta URLs (defense-in-depth):

```python
GRAPH_API_DOMAINS: frozenset[str] = frozenset({
    "graph.microsoft.com",
})

def _validate_graph_url(self, url: str) -> str:
    """Ensure odata pagination/delta URLs point to Microsoft Graph.
    Uses shared validator for domain + IP safety checks."""
    return validate_redirect_url(url, GRAPH_API_DOMAINS)
```

This reuses the same `validate_redirect_url` pipeline (scheme check →
credential check → domain allowlist → DNS resolve → IP safety) but with
`{"graph.microsoft.com"}` as the allowlist instead of the download CDN
domains. A single code path, two different allowlists.

**URL classification in `_delta_listing()` — replace `startswith("http")`
with parse-based detection:**

```python
def _delta_listing(self, config, drive_id, delta_token):
    if delta_token:
        parsed = urlparse(delta_token)
        if parsed.scheme in {"http", "https"} and parsed.hostname:
            # Absolute URL (stored deltaLink) — validate
            url = self._validate_graph_url(delta_token)
            params = None
        elif parsed.scheme and parsed.scheme not in {"http", "https"}:
            # Unexpected scheme — reject
            raise ConnectorTransientError(
                f"SSRF: unexpected scheme in delta token: {parsed.scheme}")
        else:
            # Opaque token string — use as query param
            url = f"{GRAPH_BASE_URL}/drives/{drive_id}/root/delta"
            params = {"token": delta_token}
    else:
        url = f"{GRAPH_BASE_URL}/drives/{drive_id}/root/delta"
        params = None

    # ... rest of loop unchanged, but validate nextLink/deltaLink:
    while url:
        data = self._get_json(config, url, params=params)
        items.extend(data.get("value", []))
        raw_delta = data.get("@odata.deltaLink")
        if raw_delta:
            delta_link = self._validate_graph_url(raw_delta)
        next_link = data.get("@odata.nextLink")
        url = self._validate_graph_url(next_link) if next_link else None
        params = None
```

**`_paged_items()`** — line 409:

```python
url = data.get("@odata.nextLink")
if url:
    url = self._validate_graph_url(url)
```

### Step 5 — Harden `_get_json()`

`_get_json()` at line 411 accepts any URL parameter. It's called from
`_delta_listing`, `_paged_items`, `_list_children`, `_resolve_drive_id`.
All legitimate callers pass either `GRAPH_BASE_URL`-prefixed strings or
`@odata.nextLink` values.

Add a guard at the entry of `_get_json()`:

```python
def _get_json(self, config: dict, url: str, params: dict | None = None) -> dict:
    parsed = urlparse(url)
    if parsed.scheme and parsed.hostname:
        self._validate_graph_url(url)
    # ... rest unchanged
```

This provides defense-in-depth: even if a caller forgets to validate, the
low-level JSON fetch will catch non-Graph URLs.

---

## Implementation Order

1. **Step 1:** Create `url_safety.py` with extracted functions + tests
2. **Step 2:** Refactor `web.py` imports (regression-safe, no behavior change)
3. **Step 3:** Harden `_download_content()` (critical fix)
4. **Step 4:** Harden `_delta_listing()` + `_paged_items()` (high fix)
5. **Step 5:** Harden `_get_json()` (defense-in-depth)

Steps 1-3 are the minimum viable fix. Steps 4-5 close the secondary vector.
All five must ship together in one commit.

---

## Required Tests

### `backend/tests/unit/test_url_safety.py` (new file)

| Test | What it verifies |
|------|-----------------|
| `test_validate_redirect_allows_sharepoint_cdn` | `https://tenant-my.sharepoint.com/path` passes |
| `test_validate_redirect_allows_1drv` | `https://abc.1drv.com/file` passes |
| `test_validate_redirect_blocks_arbitrary_domain` | `https://evil.com/steal` raises |
| `test_validate_redirect_blocks_internal_ip` | `https://169.254.169.254/metadata` raises |
| `test_validate_redirect_blocks_localhost` | `https://localhost:8080/` raises |
| `test_validate_redirect_blocks_http_scheme` | `http://sharepoint.com/path` raises (not HTTPS) |
| `test_validate_redirect_blocks_no_hostname` | `file:///etc/passwd` raises |
| `test_validate_redirect_blocks_credentials_in_url` | `https://user:pass@sharepoint.com` raises |
| `test_is_safe_host_blocks_private_ranges` | 10.x, 172.16.x, 192.168.x all blocked |
| `test_is_safe_host_allows_public_ip` | 8.8.8.8, 1.1.1.1 allowed |
| `test_is_safe_url_allows_http_public` | `http://example.com` passes (generic, allows HTTP) |
| `test_is_safe_url_blocks_private_ip` | `http://10.0.0.1/path` raises |
| `test_validate_redirect_blocks_wide_microsoft` | `https://login.microsoftonline.com` blocked (not in narrow CDN list) |

### `backend/tests/unit/test_microsoft_connector.py` (extend existing)

| Test | What it verifies |
|------|-----------------|
| `test_download_redirect_to_sharepoint_allowed` | 302 → `*.sharepoint.com` → content returned |
| `test_download_redirect_to_evil_domain_blocked` | 302 → `evil.com` → `ConnectorTransientError` |
| `test_download_redirect_to_metadata_ip_blocked` | 302 → `169.254.169.254` → `ConnectorTransientError` |
| `test_download_redirect_to_http_blocked` | 302 → `http://sharepoint.com` → `ConnectorTransientError` |
| `test_delta_pagination_graph_url_allowed` | `@odata.nextLink` = `https://graph.microsoft.com/...` → works |
| `test_delta_pagination_non_graph_url_blocked` | `@odata.nextLink` = `https://evil.com/...` → `ConnectorTransientError` |
| `test_delta_token_url_validates_graph_domain` | stored token `https://graph.microsoft.com/...` → works |
| `test_delta_token_url_rejects_non_graph` | stored token `https://evil.com/delta` → `ConnectorTransientError` |
| `test_get_json_rejects_non_graph_url` | direct `_get_json(config, "https://evil.com")` → `ConnectorTransientError` |
| `test_delta_token_opaque_string_uses_param` | non-URL token like `"abc123"` → used as `?token=abc123` param, not as URL |
| `test_delta_token_unexpected_scheme_rejected` | `ftp://evil.com/delta` → `ConnectorTransientError` |
| `test_existing_redirect_test_still_passes` | existing `test_download_content_follows_redirect` passes (update mock URL to `*.sharepoint.com`) |
| `test_web_connector_behavior_unchanged` | `WebConnector._is_safe_url("http://example.com")` still returns True (HTTP allowed in web context) |

---

## Acceptance Criteria

All six must be true before Wave 3 is closed:

1. `_download_content()` redirect follows ONLY URLs with hostnames matching
   `MICROSOFT_DOWNLOAD_REDIRECT_DOMAINS` (`sharepoint.com`, `1drv.com`)
   AND resolving to public IPs
2. `_delta_listing()` and `_paged_items()` follow ONLY `graph.microsoft.com`
   URLs for pagination/delta links, validated through the same shared
   `validate_redirect_url` pipeline (domain + IP safety)
3. `_get_json()` rejects non-Graph URLs as defense-in-depth
4. `url_safety.py` module exists with `is_public_ip`, `is_safe_host`,
   `is_safe_url` (generic), and `validate_redirect_url` (strict).
   `web.py` uses `is_public_ip` and `is_safe_host` from shared module
   with zero behavior change.
5. Delta token classification uses `urlparse`-based detection, not
   `startswith("http")`. Unexpected schemes are rejected.
6. All new tests pass, all existing Microsoft + web connector tests pass

---

## Explicitly Out of Scope

- **Web connector TOCTOU fix** — Wave 4 (IP pinning at request time)
- **Certificate pinning** — overkill for Graph API over TLS
- **Content-Type validation on downloads** — nice-to-have, not SSRF-related
- **Retry-After RFC date format** — low priority, not security-critical
- **Microsoft connector test coverage expansion** (beyond SSRF) — tech debt
- **`_get_json` params injection** — `params` is always from trusted code
  paths (internal dict construction), not an SSRF vector
