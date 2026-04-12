# Wave 4 — Web Connector SSRF Hardening (TOCTOU + Surface Gaps)

**Status:** DESIGN LOCK — APPROVED for implementation  
**Priority:** PRE-GO-LIVE BLOCKER  
**Commit base:** d736cd9 (Wave 3 complete)

---

## Problem Statement

`WebConnector` (`backend/connectors/web.py`) has a TOCTOU (Time-of-Check-
to-Time-of-Use) SSRF vulnerability and several additional unprotected HTTP
request paths discovered during deep audit.

### Vulnerability Inventory

| ID | Severity | Location | Description |
|----|----------|----------|-------------|
| W1 | CRITICAL | TOCTOU gap | `_enforce_public_endpoint()` resolves DNS, discards IPs. `trafilatura.fetch_url()` / `session.get()` resolves DNS again. Attacker changes DNS between check and fetch. |
| W2 | HIGH | `_get_robots_parser()` line 1183 | `requests.get(robots_url)` with zero SSRF checks. `robots_url` constructed from user-supplied URL netloc (line 464). |
| W3 | HIGH | `parse_sitemap()` redirect | Line 306: `self.session.get(sitemap_url, allow_redirects=True)` — redirect targets not validated. |
| W3b | HIGH | `parse_sitemap()` line 323 | `sitemap_tree_for_homepage(sitemap_url)` performs its own HTTP fetches outside SafeAdapter. Even with safe session, this library path bypasses all SSRF controls. |
| W4 | MEDIUM | `_parse_sitemap_basic()` recursion line 362 | Nested sitemap URLs fetched without `_enforce_public_endpoint()`. No recursion depth limit. |
| W5 | MEDIUM | `fetch_html()` redirect via trafilatura | Line 1055: trafilatura follows redirects internally. No redirect target validation. |

**Out of scope for Wave 4** (separate risk surface, not web connector):
- YouTube transcript paths (lines 528-539, 575, 694) use either
  `youtube_transcript_api` library (fixed YouTube domains) or Bright Data
  proxy (external service, not local fetch). SSRF risk is minimal and
  architectural fix would require library-level changes.

---

## Solution Design

### Approach: Thread-Local DNS Pinning + Consistent Enforcement

The core fix is a custom `requests.HTTPAdapter` that performs DNS resolution
once, validates all IPs are public, and pins the connection to the
validated IP via thread-local scoping — eliminating both the TOCTOU window
and cross-request bleed risk.

### Step 1 — Create `SafeAdapter` in `url_safety.py`

Add to the existing `backend/connectors/url_safety.py`:

```python
import threading
import socket
import ipaddress
import urllib3
from urllib.parse import urlparse
from requests.adapters import HTTPAdapter

_thread_local = threading.local()
_original_create_connection = urllib3.util.connection.create_connection

def _ssrf_safe_create_connection(address, *args, **kwargs):
    """Drop-in replacement for urllib3 create_connection that checks
    thread-local DNS overrides before connecting."""
    host, port = address
    overrides = getattr(_thread_local, "dns_overrides", None)
    if overrides:
        normalized = normalize_hostname(host)
        if normalized in overrides:
            pinned_ip = overrides[normalized]
            return _original_create_connection(
                (pinned_ip, port), *args, **kwargs)
    return _original_create_connection(address, *args, **kwargs)

# Install ONCE at module import — no repeated global mutation
urllib3.util.connection.create_connection = _ssrf_safe_create_connection


class SafeAdapter(HTTPAdapter):
    """HTTPAdapter that pins connections to pre-validated public IPs.

    Resolves DNS once during send(), validates all IPs are public,
    then sets a thread-local override so that urllib3's connection
    function uses the validated IP instead of re-resolving DNS.

    Thread safety: overrides are stored in threading.local(), so
    concurrent requests in other threads see their own (or no)
    overrides. The global create_connection replacement is installed
    once at module import and is itself stateless — it just reads
    thread-local data.
    """

    def send(self, request, stream=False, timeout=None, verify=True,
             cert=None, proxies=None):
        parsed = urlparse(request.url)
        hostname = parsed.hostname

        if not hostname:
            return super().send(request, stream=stream, timeout=timeout,
                                verify=verify, cert=cert, proxies=proxies)

        # Normalize for consistent override key (case, trailing dot)
        norm_hostname = normalize_hostname(hostname)

        # Resolve and validate ALL IPs
        try:
            infos = socket.getaddrinfo(hostname, None)
        except socket.gaierror as exc:
            raise ConnectorTransientError(
                f"SSRF: DNS resolution failed for {hostname}") from exc

        if not infos:
            raise ConnectorTransientError(
                f"SSRF: no DNS records for {hostname}")

        pinned_ip = None
        for info in infos:
            ip = ipaddress.ip_address(info[4][0])
            if not is_public_ip(ip):
                raise ConnectorTransientError(
                    f"SSRF: DNS resolved to non-public IP {ip} for {hostname}")
            if pinned_ip is None:
                pinned_ip = str(ip)

        # Set thread-local override — only THIS thread's requests
        # will use the pinned IP. Other threads are unaffected.
        # Set thread-local override using normalized key
        if not hasattr(_thread_local, "dns_overrides"):
            _thread_local.dns_overrides = {}
        _thread_local.dns_overrides[norm_hostname] = pinned_ip
        try:
            return super().send(request, stream=stream, timeout=timeout,
                                verify=verify, cert=cert, proxies=proxies)
        finally:
            # Clean up to avoid stale entries
            _thread_local.dns_overrides.pop(norm_hostname, None)
```

**Why thread-local instead of global monkeypatch scope:**
- `_ssrf_safe_create_connection` is installed once at module load — no
  repeated mutation of `urllib3.util.connection.create_connection`
- The function itself is pure: it reads thread-local `dns_overrides` dict
- Each thread has its own dict via `threading.local()`
- Other threads (Celery workers, background tasks) making their own HTTP
  requests see empty overrides → normal DNS resolution
- Even under gevent/eventlet, greenlets get their own thread-local if
  the runtime patches `threading.local` (which both do by default)
- No cross-request bleed: override is set only for the duration of
  `super().send()` and cleaned up in `finally`

### Step 2 — Create `safe_session()` factory in `url_safety.py`

```python
def safe_session(headers: dict | None = None) -> requests.Session:
    """Create a requests.Session with SSRF-safe DNS pinning."""
    session = requests.Session()
    session.trust_env = False  # Disable HTTP_PROXY / HTTPS_PROXY / NO_PROXY
    adapter = SafeAdapter()
    session.mount("https://", adapter)
    session.mount("http://", adapter)
    if headers:
        session.headers.update(headers)
    return session
```

**`trust_env = False` rationale:** This design's security model is built
on direct DNS resolution + IP pinning. If `requests` honors environment
proxy variables (`HTTP_PROXY`, `HTTPS_PROXY`), traffic routes through the
proxy and the "resolve → validate → pin" chain becomes meaningless — the
proxy does its own DNS resolution. Setting `trust_env = False` ensures
all requests go direct, preserving the pinning guarantee.
```

### Step 3 — Replace session in WebConnector.__init__()

**File:** `web.py`, line 230

Replace:
```python
self.session = requests.Session()
```
With:
```python
from connectors.url_safety import safe_session
self.session = safe_session(self.DEFAULT_HEADERS)
```

This single change fixes **W1 (TOCTOU)** for all `self.session.get/post`
calls because the adapter validates + pins DNS on every request.

**Also remove `_enforce_public_endpoint()` calls that are now redundant:**
- Line 277 in `fetch_file_content()` — remove (adapter handles it)
- Line 303 in `parse_sitemap()` — remove (adapter handles it)
- Line 1053 in `fetch_html()` — remove (adapter handles it)

Keep `_enforce_public_endpoint()` method itself for backward compat (other
code may call it).

### Step 4 — Fix `fetch_html()` trafilatura path (W1 + W5)

`trafilatura.fetch_url()` at line 1055 uses its own internal requests
session, bypassing our SafeAdapter. Replace it with `self.session.get()`.

Replace the `fetch_html()` method:

```python
def fetch_html(self, url: str, max_bytes: int = None) -> str | None:
    try:
        with connector_fetch_limit("web"):
            response = self._safe_get(url)

        html = response.text
        if html and max_bytes and len(html.encode("utf-8")) > max_bytes:
            raise ConnectorTransientError("Content too large")
        return html
    except ConnectorTransientError:
        raise
    except ConnectorAuthError:
        raise
    except ConnectorRateLimitError:
        raise
    except Exception as e:
        logger.error(f"❌ [Web] HTML fetch failed for {url}: {e}")
        raise ConnectorTransientError(str(e)) from e
```

Where `_safe_get()` is a shared redirect-following helper (see Step 7).

**Why not keep trafilatura.fetch_url?** Because trafilatura manages its
own HTTP session and we cannot inject SafeAdapter into it. Using
`self.session.get()` keeps all HTTP requests on our controlled session.

**Note:** Callers pass the returned HTML to `trafilatura.extract()` for
content extraction. `trafilatura.extract()` is pure HTML parsing with no
HTTP — this change is transparent.

### Step 5 — Fix `_get_robots_parser()` (W2)

**File:** `web.py`, line 1183

Change `requests.get(robots_url, ...)` → `self.session.get(robots_url, ...)`

This puts robots.txt fetches through the SafeAdapter pipeline.

### Step 6 — Remove `ultimate-sitemap-parser` from network path (W3b)

**File:** `web.py`, lines 321-331

`sitemap_tree_for_homepage(sitemap_url)` (line 323) performs its own HTTP
fetches outside our SafeAdapter — it has its own internal HTTP client that
we cannot control. This means even with SafeAdapter on `self.session`, the
primary sitemap path bypasses all SSRF protections.

**Fix:** Remove `sitemap_tree_for_homepage` from the network path entirely.
Promote `_parse_sitemap_basic()` to the primary parser, feeding it
pre-fetched XML from our safe session.

Replace `parse_sitemap()`:

```python
def parse_sitemap(self, sitemap_url: str) -> list[str]:
    """Parse sitemap.xml and extract page URLs.
    
    All HTTP fetches go through self.session (SafeAdapter) to
    ensure SSRF protection. ultimate-sitemap-parser is NOT used
    for fetching — only our safe session touches the network.
    """
    try:
        with connector_fetch_limit("web"):
            response = self._safe_get(sitemap_url)
        # _safe_get() already calls raise_for_status(), so if we
        # reach here the status is 2xx. Only content checks remain.

        content_type = response.headers.get("Content-Type", "").lower()
        body_lower = (response.text or "").strip().lower()

        if "xml" not in content_type:
            logger.warning("⚠️ [Web] Sitemap not xml (%s): %s",
                           content_type, sitemap_url)
            return []
        if body_lower.startswith("<!doctype html") or body_lower.startswith("<html"):
            logger.warning("⚠️ [Web] Sitemap is HTML: %s", sitemap_url)
            return []

        urls = self._parse_sitemap_xml(response.content)
        logger.info("📍 [Web] Parsed sitemap: %d URLs from %s",
                     len(urls), sitemap_url)
        return urls

    except ConnectorTransientError:
        raise
    except Exception as e:
        logger.error("❌ [Web] Sitemap parsing failed for %s: %s",
                      sitemap_url, e)
        return []


def _parse_sitemap_xml(self, xml_content: bytes, _depth: int = 0) -> list[str]:
    """Parse sitemap XML. Handles sitemap index (nested) and regular.
    
    Recursion depth is bounded to prevent infinite chains.
    All nested sitemap fetches go through self.session (SafeAdapter).
    """
    if _depth > 3:
        logger.warning("⚠️ [Web] Sitemap recursion depth exceeded")
        return []

    from bs4 import BeautifulSoup
    soup = BeautifulSoup(xml_content, "lxml-xml")

    # Check for sitemap index
    sitemaps = soup.find_all("sitemap")
    if sitemaps:
        urls = []
        for sitemap in sitemaps:
            loc = sitemap.find("loc")
            if not loc or not loc.text.strip():
                continue
            nested_url = loc.text.strip()
            try:
                with connector_fetch_limit("web"):
                    nested_response = self._safe_get(nested_url)
                urls.extend(self._parse_sitemap_xml(
                    nested_response.content, _depth=_depth + 1))
            except Exception as e:
                logger.warning("⚠️ [Web] Nested sitemap fetch failed: %s: %s",
                                nested_url, e)
                continue
        return urls

    # Regular sitemap — extract URLs
    urls = []
    for url_tag in soup.find_all("url"):
        loc = url_tag.find("loc")
        if loc and loc.text.strip():
            urls.append(loc.text.strip())
    return urls
```

This replaces both `sitemap_tree_for_homepage()` and the old
`_parse_sitemap_basic()` with a single method that:
- Fetches via `self.session` (SafeAdapter) — SSRF-safe
- Has recursion depth limit of 3
- Handles both sitemap index and regular sitemaps

**Note:** `ultimate-sitemap-parser` import can remain in requirements.txt
(other code may use it), but it is no longer called from the network-facing
sitemap path. If no other code uses it, it can be removed in a follow-up
cleanup.

### Step 7 — Create shared `_safe_get()` redirect helper

Multiple methods need manual redirect following with SafeAdapter validation
per hop. Extract a shared helper:

```python
def _safe_get(self, url: str, **kwargs) -> requests.Response:
    """GET with URL policy check + manual redirect following through SafeAdapter.
    
    Security layers per request:
    1. _is_safe_url() — scheme (http/https only), no embedded credentials,
       hostname present. Applied to initial URL and every redirect target.
    2. SafeAdapter — DNS resolve, validate all IPs public, pin connection
       to validated IP. Applied automatically by self.session.
    3. Redirect limit — max 5 hops.
    
    Relative Location headers are resolved against the current response
    URL via urljoin before policy check.
    """
    from urllib.parse import urljoin

    kwargs.setdefault("timeout", (10, 30))
    kwargs.setdefault("headers", self.DEFAULT_HEADERS)
    kwargs["allow_redirects"] = False

    # URL policy check on initial URL
    if not self._is_safe_url(url):
        raise ConnectorTransientError(
            f"SSRF: URL failed policy check: {url}")

    response = self.session.get(url, **kwargs)
    redirect_count = 0

    while response.status_code in {301, 302, 303, 307, 308}:
        redirect_count += 1
        if redirect_count > 5:
            response.close()
            raise ConnectorTransientError(
                f"Too many redirects (>{5}) from {url}")
        location = response.headers.get("Location")
        if not location:
            response.close()
            raise ConnectorTransientError(
                f"Redirect {response.status_code} missing Location header")
        response.close()
        # Resolve relative Location against current URL
        location = urljoin(response.url, location)
        # URL policy check on redirect target
        if not self._is_safe_url(location):
            raise ConnectorTransientError(
                f"SSRF: redirect target failed policy check: {location}")
        # SafeAdapter validates DNS + pins IP on each hop
        response = self.session.get(location, **kwargs)

    response.raise_for_status()
    return response
```

**Relative redirect handling:** `urljoin(response.url, location)` correctly
resolves both absolute (`https://other.com/path`) and relative (`/path`,
`../path`) Location headers against the current response URL. This is
required because real CDNs and web servers commonly return relative
redirects.

This helper is used by `fetch_html()`, `parse_sitemap()`, and
`_parse_sitemap_xml()` (for nested fetches).

---

## Implementation Order

1. **Step 1+2:** SafeAdapter (thread-local) + safe_session() in url_safety.py
2. **Step 7:** `_safe_get()` helper in web.py (used by subsequent steps)
3. **Step 3:** Replace session in WebConnector (fixes W1 for session paths)
4. **Step 4:** Replace trafilatura.fetch_url with _safe_get (fixes W1+W5)
5. **Step 5:** Fix robots.txt (fixes W2)
6. **Step 6:** Replace sitemap_tree_for_homepage with _parse_sitemap_xml
   (fixes W3, W3b, W4)

All steps ship in one commit.

---

## Required Tests

### `backend/tests/unit/test_url_safety.py` (extend)

| Test | What it verifies |
|------|-----------------|
| `test_safe_adapter_blocks_private_ip_resolution` | SafeAdapter raises ConnectorTransientError when hostname resolves to 127.0.0.1 |
| `test_safe_adapter_allows_public_ip_resolution` | SafeAdapter permits request when hostname resolves to public IP |
| `test_safe_adapter_cleans_thread_local_on_error` | `_thread_local.dns_overrides` is cleaned up even if request fails |
| `test_safe_adapter_thread_isolation` | Override set in one thread is NOT visible in another thread |
| `test_safe_adapter_normalizes_hostname_for_override` | `Example.COM.` and `example.com` use the same override key |
| `test_safe_session_mounts_adapter_on_both_schemes` | safe_session() has SafeAdapter on http:// and https:// |
| `test_safe_session_disables_trust_env` | safe_session().trust_env is False |

### `backend/tests/unit/test_web_connector.py` (extend)

| Test | What it verifies |
|------|-----------------|
| `test_fetch_html_uses_safe_session_not_trafilatura` | fetch_html calls self.session.get, not trafilatura.fetch_url |
| `test_safe_get_resolves_relative_redirect` | `Location: /path` resolved via urljoin against response.url |
| `test_safe_get_redirect_limit_enforced` | >5 redirects raises ConnectorTransientError |
| `test_safe_get_redirect_missing_location_raises` | 302 without Location header raises ConnectorTransientError (not silent pass) |
| `test_safe_get_checks_url_policy_on_initial` | `ftp://host`, `http://user:pass@host`, URL without hostname all raise |
| `test_safe_get_checks_url_policy_on_redirect_target` | Redirect to `ftp://evil` or `http://user:pass@evil` raises |
| `test_robots_txt_uses_safe_session` | _get_robots_parser uses self.session.get, not bare requests.get |
| `test_sitemap_uses_safe_session_not_usp` | parse_sitemap does NOT call sitemap_tree_for_homepage |
| `test_sitemap_nested_fetched_via_safe_get` | Nested sitemap URLs fetched through _safe_get (SafeAdapter) |
| `test_sitemap_recursion_depth_limited` | Nested sitemaps beyond depth 3 are rejected |
| `test_session_uses_safe_adapter` | WebConnector.session has SafeAdapter mounted |

---

## Acceptance Criteria

All nine must be true before Wave 4 is closed:

1. **TOCTOU eliminated:** All HTTP requests in WebConnector go through
   `SafeAdapter` which resolves DNS once, validates IPs, and pins the
   connection to the validated IP via thread-local override
2. **No cross-request bleed:** DNS pinning uses `threading.local()`, not
   global state. Override is cleaned up in `finally` block. A concurrent
   request in another thread sees normal DNS resolution.
3. **No proxy bypass:** `safe_session()` sets `trust_env = False` so that
   `HTTP_PROXY` / `HTTPS_PROXY` environment variables cannot route traffic
   around the DNS pinning pipeline
4. **Hostname normalization consistent:** Both the override set
   (SafeAdapter.send) and lookup (_ssrf_safe_create_connection) use
   `normalize_hostname()` — `strip().lower().rstrip(".")` — preventing
   case/trailing-dot mismatches that would silently fall through to
   unpinned DNS resolution
5. **robots.txt protected:** `_get_robots_parser()` uses `self.session`
   (SafeAdapter), not bare `requests.get()`
6. **trafilatura bypassed for HTTP:** `fetch_html()` uses `_safe_get()`
   instead of `trafilatura.fetch_url()`. Trafilatura is only used for
   content extraction (`trafilatura.extract()`), not HTTP fetching.
7. **ultimate-sitemap-parser bypassed for HTTP:** `parse_sitemap()` does
   NOT call `sitemap_tree_for_homepage()`. All sitemap fetches go through
   `_safe_get()` → SafeAdapter. XML parsing uses BeautifulSoup locally.
8. **Redirects validated with relative support:** `_safe_get()` uses
   `allow_redirects=False` with manual redirect following. Each hop goes
   through SafeAdapter. Relative `Location` headers resolved via
   `urljoin(response.url, location)`. Max 5 hops.
9. All new tests pass, all existing web connector tests pass

---

## Explicitly Out of Scope

- **YouTube transcript fetching** — uses `youtube_transcript_api` library
  (fixed YouTube domains) or Bright Data proxy (external service). Not a
  local SSRF vector.
- **Bright Data API calls** — hardcoded URL, external proxy service
- **trafilatura content extraction** — only `trafilatura.extract()` is
  used after this change, which is pure HTML parsing (no HTTP)
- **ultimate-sitemap-parser removal from requirements** — library stays
  in deps but is no longer called from the network path. Removal is a
  follow-up cleanup task.
- **_is_safe_host LRU cache** — per-instance, 512 entries, unchanged
- **DNS TTL-aware caching** — SafeAdapter resolves fresh per-request,
  correct for security
- **Sitemap recursion depth > 3** — 3 levels covers virtually all real
  sitemap structures; deeper nesting is suspicious
