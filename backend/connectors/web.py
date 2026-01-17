"""
Web Connector - Advanced Web Crawling

Ingests web pages using Trafilatura for robust article extraction.
Supports:
- Single page crawling
- Sitemap.xml parsing
- Recursive link extraction
- YouTube transcript extraction
- robots.txt respect

The connector provides discovery capabilities; looping logic is in the Celery worker.
"""

import re
import logging
import ipaddress
import socket
from functools import lru_cache
from typing import List, Dict, Any, Optional, Set, Iterator, AsyncIterator
from urllib.parse import urlparse, urljoin, urlunparse, parse_qsl, urlencode
from connectors.enhanced import EnhancedConnector, SourceDocument, SourceType
from connectors.base import (
    BaseConnector,
    ConnectorAuthError,
    ConnectorRateLimitError,
    ConnectorTransientError,
    RemoteFile,
)
import trafilatura
import requests
from connectors.limits import connector_fetch_limit
from core.scopes import build_scope_uri

logger = logging.getLogger(__name__)

# YouTube URL patterns
YOUTUBE_PATTERNS = [
    r'(?:https?://)?(?:www\.)?youtube\.com/watch\?v=([a-zA-Z0-9_-]{11})',
    r'(?:https?://)?(?:www\.)?youtu\.be/([a-zA-Z0-9_-]{11})',
    r'(?:https?://)?(?:www\.)?youtube\.com/embed/([a-zA-Z0-9_-]{11})',
    r'(?:https?://)?(?:www\.)?youtube\.com/shorts/([a-zA-Z0-9_-]{11})',
]


class WebConnector(EnhancedConnector, BaseConnector):
    """
    Advanced Web Connector with sitemap, recursion, and YouTube support.
    
    Implements the discovery and extraction capabilities.
    The recursive crawling loop is handled by the Celery worker.
    """

    @property
    def connector_type(self) -> SourceType:
        return SourceType.WEB
    
    # User-Agent for polite crawling
    USER_AGENT = "AxioBot/1.0 (+https://axiohub.io/bot)"
    DEFAULT_HEADERS = {
        "User-Agent": USER_AGENT,
        "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
        "Accept-Language": "en-US,en;q=0.9",
    }
    ALLOWED_CONTENT_TYPES = ("text/html", "application/xhtml+xml", "text/plain")
    MAX_HTML_BYTES = 2_000_000  # 2MB safety cap for HTML fetch
    TRACKING_QUERY_PARAMS = {
        "utm_source",
        "utm_medium",
        "utm_campaign",
        "utm_term",
        "utm_content",
        "gclid",
        "fbclid",
        "mc_cid",
        "mc_eid",
    }

    def __init__(self) -> None:
        self.session = requests.Session()
        self.session.headers.update(self.DEFAULT_HEADERS)
    
    async def authorize(self, user_id: str) -> bool:
        """Web connector is public/open, always authorized."""
        return True

    def validate_config(self, config: dict) -> bool:
        url = config.get("url")
        return bool(url) and self._is_safe_url(url)

    async def list_files(self, config: dict, since: Optional[str] = None) -> List[RemoteFile]:
        """
        Treat list_files as discovery: accept a root URL and return it as a RemoteFile entry.
        """
        url = config.get("url")
        if not url:
            return []
        if not self._is_safe_url(url):
            raise ValueError(f"Security Violation: Access to private network denied for {url}")
        return [
            RemoteFile(
                id=url,
                name=url,
                mime_type="text/html",
                size=None,
                modified_at=None,
                parent_id=None,
                web_view_url=url,
            )
        ]

    def fetch_file_content(self, file_id: str, config: dict) -> bytes:
        """
        Fetch raw HTML/text for a given URL (file_id).
        """
        url = file_id
        if not self._is_safe_url(url):
            raise ConnectorAuthError("Unsafe URL blocked")
        self._enforce_public_endpoint(url)
        html = self.fetch_html(url)
        if html is None:
            raise ConnectorTransientError("Failed to fetch content")
        return html.encode("utf-8")

    # =========================================================================
    # DISCOVERY METHODS
    # =========================================================================
    
    def parse_sitemap(self, sitemap_url: str) -> List[str]:
        """
        Parse a sitemap.xml and extract all page URLs.
        
        Handles:
        - Standard sitemaps
        - Sitemap index files (nested sitemaps)
        - Compressed sitemaps (.gz)
        
        Args:
            sitemap_url: URL to sitemap.xml or sitemap index
            
        Returns:
            List of page URLs found in the sitemap
        """
        # Prefetch to ensure this looks like XML and not an HTML login page
        self._enforce_public_endpoint(sitemap_url)
        try:
            with connector_fetch_limit("web"):
                head = self.session.get(sitemap_url, timeout=(10, 30), allow_redirects=True)
            content_type = head.headers.get("Content-Type", "").lower()
            body_lower = (head.text or "").strip().lower()
            if head.status_code >= 400:
                logger.warning(f"⚠️ [Web] Sitemap preflight failed ({head.status_code}): {sitemap_url}")
                return []
            if "xml" not in content_type:
                logger.warning(f"⚠️ [Web] Sitemap preflight not xml ({content_type}): {sitemap_url}")
                return []
            if body_lower.startswith("<!doctype html") or body_lower.startswith("<html"):
                logger.warning(f"⚠️ [Web] Sitemap response is HTML (likely login/forbidden): {sitemap_url}")
                return []
        except Exception as e:
            logger.warning(f"⚠️ [Web] Sitemap preflight error for {sitemap_url}: {e}")
            # Fall through to best-effort parsing
        try:
            from usp.tree import sitemap_tree_for_homepage
            tree = sitemap_tree_for_homepage(sitemap_url)

            urls = []
            for page in tree.all_pages():
                if page.url:
                    urls.append(page.url)

            logger.info(f"📍 [Web] Parsed sitemap: {len(urls)} URLs from {sitemap_url}")
            return urls

        except ImportError:
            logger.warning("⚠️ [Web] ultimate-sitemap-parser not installed, falling back to basic parsing")
            return self._parse_sitemap_basic(sitemap_url)
        except Exception as e:
            logger.error(f"❌ [Web] Sitemap parsing failed for {sitemap_url}: {e}")
            return []
    
    def _parse_sitemap_basic(self, sitemap_url: str) -> List[str]:
        """Basic sitemap parser fallback using BeautifulSoup."""
        try:
            from bs4 import BeautifulSoup
            
            with connector_fetch_limit("web"):
                response = self.session.get(
                    sitemap_url,
                    timeout=(10, 30)
                )
            response.raise_for_status()
            
            soup = BeautifulSoup(response.content, "lxml-xml")
            
            # Check for sitemap index
            sitemaps = soup.find_all("sitemap")
            if sitemaps:
                urls = []
                for sitemap in sitemaps:
                    loc = sitemap.find("loc")
                    if loc:
                        # Recursively parse nested sitemap
                        urls.extend(self._parse_sitemap_basic(loc.text.strip()))
                return urls
            
            # Regular sitemap - extract URLs
            urls = []
            for url_tag in soup.find_all("url"):
                loc = url_tag.find("loc")
                if loc:
                    urls.append(loc.text.strip())
            
            return urls
            
        except Exception as e:
            logger.error(f"❌ [Web] Basic sitemap parsing failed: {e}")
            return []
    
    def extract_links(
        self,
        html_content: str,
        base_url: str,
        *,
        base_domain: Optional[str] = None,
        allow_subdomains: bool = False
    ) -> List[str]:
        """
        Extract internal links from HTML content.
        
        Only returns links on the same domain as base_url.
        Filters out anchors, javascript:, mailto:, etc.
        
        Args:
            html_content: Raw HTML string
            base_url: The page's URL (for resolving relative links)
            
        Returns:
            List of absolute URLs on the same domain
        """
        try:
            from bs4 import BeautifulSoup
            
            soup = BeautifulSoup(html_content, "html.parser")
            base_parsed = urlparse(base_url)
            base_domain = base_domain or self._normalize_hostname(base_parsed.hostname or "")
            
            links: Set[str] = set()
            
            for a_tag in soup.find_all("a", href=True):
                rel = a_tag.get("rel") or []
                if isinstance(rel, str):
                    rel = [rel]
                if any(r.lower() == "nofollow" for r in rel):
                    continue

                href = a_tag["href"]
                
                # Skip non-HTTP links
                if href.startswith(("#", "javascript:", "mailto:", "tel:", "data:")):
                    continue
                
                # Resolve relative URLs
                absolute_url = urljoin(base_url, href)
                normalized = self.normalize_url(absolute_url)
                if not normalized:
                    continue
                parsed = urlparse(normalized)
                
                # Only include same-domain links
                if self._is_allowed_domain(parsed.hostname or "", base_domain, allow_subdomains):
                    links.add(normalized)
            
            logger.debug(f"🔗 [Web] Extracted {len(links)} internal links from {base_url}")
            return list(links)
            
        except Exception as e:
            logger.error(f"❌ [Web] Link extraction failed for {base_url}: {e}")
            return []
    
    def check_robots_txt(self, url: str, user_agent: str = "*") -> bool:
        """
        Check if a URL is allowed by robots.txt.
        
        Args:
            url: The URL to check
            user_agent: User-agent to check rules for
            
        Returns:
            True if allowed to crawl, False if disallowed
        """
        try:
            parsed = urlparse(url)
            robots_url = f"{parsed.scheme}://{parsed.netloc}/robots.txt"
            rp = self._get_robots_parser(robots_url)
            return rp.can_fetch(user_agent, url)
        except Exception as e:
            # If robots.txt check fails, allow crawling (fail open)
            logger.warning(f"⚠️ [Web] robots.txt check failed for {url}: {e}")
            return True

    def get_crawl_delay(self, url: str, user_agent: str = "*") -> Optional[float]:
        """Return crawl-delay from robots.txt if provided."""
        try:
            parsed = urlparse(url)
            robots_url = f"{parsed.scheme}://{parsed.netloc}/robots.txt"
            rp = self._get_robots_parser(robots_url)
            delay = rp.crawl_delay(user_agent)
            if delay is None:
                return None
            return max(float(delay), 0.0)
        except Exception:
            return None
    
    # =========================================================================
    # YOUTUBE SUPPORT
    # =========================================================================
    
    def is_youtube_url(self, url: str) -> bool:
        """Check if a URL is a YouTube video."""
        return any(re.match(pattern, url) for pattern in YOUTUBE_PATTERNS)
    
    def extract_youtube_video_id(self, url: str) -> Optional[str]:
        """Extract video ID from a YouTube URL."""
        for pattern in YOUTUBE_PATTERNS:
            match = re.match(pattern, url)
            if match:
                return match.group(1)
        return None
    
    def fetch_youtube_transcript(self, video_url: str) -> Optional[str]:
        """
        Fetch transcript from a YouTube video.
        
        Args:
            video_url: YouTube video URL
            
        Returns:
            Full transcript text or None if not available
        """
        try:
            from youtube_transcript_api import YouTubeTranscriptApi
            from youtube_transcript_api._errors import (
                TranscriptsDisabled,
                NoTranscriptFound,
                VideoUnavailable
            )
            
            video_id = self.extract_youtube_video_id(video_url)
            if not video_id:
                logger.warning(f"⚠️ [YouTube] Could not extract video ID from: {video_url}")
                return None
            
            # Create API instance (new in v1.2.0)
            ytt_api = YouTubeTranscriptApi()
            
            # Try to get transcript (auto-generated or manual)
            transcript_list = ytt_api.list(video_id)
            
            # Prefer manual transcripts, fall back to auto-generated
            transcript = None
            try:
                transcript = transcript_list.find_manually_created_transcript(['en'])
            except:
                try:
                    transcript = transcript_list.find_generated_transcript(['en'])
                except:
                    # Try any available language
                    for t in transcript_list:
                        transcript = t
                        break
            
            if not transcript:
                logger.warning(f"⚠️ [YouTube] No transcript available for: {video_id}")
                return None
            
            # Fetch and combine transcript segments
            segments = transcript.fetch()
            full_text = " ".join([seg["text"] for seg in segments])
            
            logger.info(f"✅ [YouTube] Fetched transcript: {len(full_text)} chars from {video_id}")
            return full_text
            
        except ImportError:
            logger.error("❌ [YouTube] youtube-transcript-api not installed")
            return None
        except Exception as e:
            logger.error(f"❌ [YouTube] Transcript fetch failed for {video_url}: {e}")
            return None
    
    def get_youtube_metadata(self, video_url: str) -> Dict[str, str]:
        """Get basic metadata for a YouTube video."""
        video_id = self.extract_youtube_video_id(video_url)
        return {
            "source": "youtube",
            "video_id": video_id or "unknown",
            "source_url": video_url,
        }
    
    # =========================================================================
    # INGESTION
    # =========================================================================

    async def fetch_documents(
        self,
        item_ids: list[str],
        credentials: Optional[Dict[str, Any]] = None,
        **kwargs
    ) -> AsyncIterator[SourceDocument]:
        """Async wrapper for sync fetch."""
        for doc in self.fetch_documents_sync(item_ids, credentials, **kwargs):
            yield doc

    def fetch_documents_sync(
        self,
        item_ids: list[str],
        credentials: Optional[Dict[str, Any]] = None,
        **kwargs
    ) -> Iterator[SourceDocument]:
        """
        Fetch documents from web pages for ingestion pipeline.
        
        Scope ID Format: web://{domain}
        All pages from the same domain share a scope for quota/retrieval purposes.
        """
        urls = item_ids or []
        respect_robots = kwargs.get("respect_robots", True)

        for url in urls:
            try:
                if not self._is_safe_url(url):
                    logger.warning(f"⚠️ [Web] Unsafe URL blocked: {url}")
                    continue

                if respect_robots and not self.check_robots_txt(url, self.USER_AGENT):
                    logger.info(f"🚫 [Web] Blocked by robots.txt: {url}")
                    continue
                
                # Generate scope_id using canonical URI builder
                scope_id = build_scope_uri("web", {"url": url})

                if self.is_youtube_url(url):
                    transcript = self.fetch_youtube_transcript(url)
                    if transcript:
                        metadata = self.get_youtube_metadata(url)
                        metadata["scope_id"] = scope_id  # CRITICAL: Required for FK compliance
                        video_id = metadata.get("video_id", "youtube")
                        yield SourceDocument(
                            content=transcript,
                            metadata=metadata,
                            source_type=SourceType.YOUTUBE,  # Use dedicated YouTube type
                            source_id=url,
                            filename=f"{video_id}.txt",
                            mime_type="text/plain",
                            size_bytes=len(transcript.encode("utf-8")),
                        )
                    continue

                html = self.fetch_html(url)
                if html:
                    text = trafilatura.extract(
                        html,
                        include_comments=False,
                        include_tables=True,
                        include_links=False,
                        output_format="txt",
                    )
                    metadata = trafilatura.extract_metadata(html)

                    if text and text.strip():
                        title = metadata.title if metadata and metadata.title else url
                        yield SourceDocument(
                            content=text,
                            metadata={
                                "source": "web",
                                "title": title,
                                "source_url": url,
                                "author": metadata.author if metadata else None,
                                "date": str(metadata.date) if metadata and metadata.date else None,
                                "scope_id": scope_id,  # CRITICAL: Required for FK compliance
                            },
                            source_type=SourceType.WEB,
                            source_id=url,
                            filename=f"{title}.txt",
                            mime_type="text/plain",
                            size_bytes=len(text.encode("utf-8")),
                        )
                        logger.info(f"✅ [Web] Scraped: {url}")
                    else:
                        logger.warning(f"⚠️ [Web] No text extracted from: {url}")
                else:
                    logger.warning(f"⚠️ [Web] Failed to download: {url}")

            except Exception as e:
                logger.error(f"❌ [Web] Failed to scrape {url}: {e}")

        logger.info("📥 [WebConnector] Fetch stream ended")
    
    def fetch_html(self, url: str, max_bytes: int = None) -> Optional[str]:
        """
        Fetch raw HTML content for link extraction.
        
        Used by the worker for recursive crawling.
        """
        try:
            self._enforce_public_endpoint(url)
            with connector_fetch_limit("web"):
                html = trafilatura.fetch_url(url)
            if html is not None:
                if max_bytes and len(html.encode("utf-8")) > max_bytes:
                    raise ConnectorTransientError("Content too large")
                return html
            return None
        except ConnectorAuthError:
            raise
        except ConnectorRateLimitError:
            raise
        except Exception as e:
            logger.error(f"❌ [Web] HTML fetch failed for {url}: {e}")
            raise ConnectorTransientError(str(e)) from e

    def _is_safe_url(self, url: str) -> bool:
        """Basic SSRF protection: allow only public http(s) URLs."""
        try:
            parsed = urlparse(url)
            if parsed.scheme not in {"http", "https"}:
                return False
            if parsed.username or parsed.password:
                return False
            hostname = parsed.hostname
            if not hostname:
                return False
            return self._is_safe_host(hostname)
        except Exception:
            return False

    def is_safe_url(self, url: str) -> bool:
        """Public wrapper for URL safety check. Used by worker tasks."""
        return self._is_safe_url(url)

    @lru_cache(maxsize=512)
    def _is_safe_host(self, hostname: str) -> bool:
        try:
            ip = ipaddress.ip_address(hostname)
            return self._is_public_ip(ip)
        except ValueError:
            # Hostname: resolve and validate all IPs
            try:
                infos = socket.getaddrinfo(hostname, None)
            except socket.gaierror:
                return False

            for info in infos:
                addr = info[4][0]
                try:
                    ip = ipaddress.ip_address(addr)
                except ValueError:
                    return False
                if not self._is_public_ip(ip):
                    return False
            return True

    def normalize_url(self, url: str) -> Optional[str]:
        """Normalize URL for deduplication and safe comparisons."""
        if not url:
            return None
        try:
            raw = url.strip()
            parsed = urlparse(raw)
            if parsed.scheme not in {"http", "https"}:
                return None
            if not parsed.hostname:
                return None

            scheme = parsed.scheme.lower()
            host = parsed.hostname.lower()
            port = parsed.port
            if port and ((scheme == "http" and port == 80) or (scheme == "https" and port == 443)):
                port = None
            netloc = host if port is None else f"{host}:{port}"

            path = parsed.path or "/"
            path = re.sub("/{2,}", "/", path)
            if path != "/":
                path = path.rstrip("/")

            query = self._strip_tracking_params(parsed.query)
            return urlunparse((scheme, netloc, path, "", query, ""))
        except Exception:
            return None

    def _strip_tracking_params(self, query: str) -> str:
        params = []
        for key, value in parse_qsl(query, keep_blank_values=False):
            if key.lower() in self.TRACKING_QUERY_PARAMS:
                continue
            params.append((key, value))
        return urlencode(params, doseq=True)

    def _normalize_hostname(self, hostname: str) -> str:
        host = hostname.strip().lower().rstrip(".")
        if host.startswith("www."):
            return host[4:]
        return host

    def _is_allowed_domain(self, hostname: str, base_domain: str, allow_subdomains: bool) -> bool:
        host = self._normalize_hostname(hostname)
        base = self._normalize_hostname(base_domain)
        if allow_subdomains:
            return host == base or host.endswith(f".{base}")
        return host == base

    def is_allowed_domain(self, hostname: str, base_domain: str, allow_subdomains: bool) -> bool:
        """Public wrapper for domain allow-list checks."""
        return self._is_allowed_domain(hostname, base_domain, allow_subdomains)

    def _is_public_ip(self, ip) -> bool:
        return not (
            ip.is_private
            or ip.is_loopback
            or ip.is_link_local
            or ip.is_reserved
            or ip.is_multicast
            or ip.is_unspecified
        )

    def _enforce_public_endpoint(self, url: str) -> None:
        """
        Explicit SSRF guard: resolve hostname and block private/loopback/link-local targets.
        """
        parsed = urlparse(url)
        hostname = parsed.hostname
        if not hostname:
            raise ValueError("Security Violation: Access to private network denied.")

        try:
            ip_str = socket.gethostbyname(hostname)
            ip_obj = ipaddress.ip_address(ip_str)
        except Exception:
            raise ValueError("Security Violation: Access to private network denied.")

        if ip_obj.is_private or ip_obj.is_loopback or ip_obj.is_link_local:
            raise ValueError("Security Violation: Access to private network denied.")

    @lru_cache(maxsize=256)
    def _get_robots_parser(self, robots_url: str):
        from urllib.robotparser import RobotFileParser
        class _AllowAll:
            def can_fetch(self, *_args, **_kwargs):
                return True

            def crawl_delay(self, *_args, **_kwargs):
                return None

        rp = RobotFileParser()
        try:
            with connector_fetch_limit("web"):
                response = requests.get(robots_url, timeout=(10, 30), headers=self.DEFAULT_HEADERS)
                if response.status_code >= 400:
                    return _AllowAll()
                rp.parse(response.text.splitlines())
        except Exception as e:
            logger.warning(f"⚠️ [Web] robots.txt fetch failed for {robots_url}: {e}")
            return _AllowAll()
        return rp
