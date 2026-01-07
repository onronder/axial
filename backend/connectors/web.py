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
from .base import BaseConnector, ConnectorDocument, ConnectorItem
import trafilatura
import requests

logger = logging.getLogger(__name__)

# YouTube URL patterns
YOUTUBE_PATTERNS = [
    r'(?:https?://)?(?:www\.)?youtube\.com/watch\?v=([a-zA-Z0-9_-]{11})',
    r'(?:https?://)?(?:www\.)?youtu\.be/([a-zA-Z0-9_-]{11})',
    r'(?:https?://)?(?:www\.)?youtube\.com/embed/([a-zA-Z0-9_-]{11})',
]


class WebConnector(BaseConnector):
    """
    Advanced Web Connector with sitemap, recursion, and YouTube support.
    
    Implements the discovery and extraction capabilities.
    The recursive crawling loop is handled by the Celery worker.
    """
    
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

    async def list_items(self, user_id: str, parent_id: Optional[str] = None) -> List[ConnectorItem]:
        """
        List previously crawled URLs.
        Queries web_crawl_configs table to show crawl history.
        """
        try:
            from core.db import get_supabase
            supabase = get_supabase()
            
            # Query crawl history from DB
            # Note: supabase-py client is synchronous, so .execute() blocks.
            response = supabase.table("web_crawl_configs").select("*").eq("user_id", user_id).order("created_at", desc=True).limit(50).execute()
            
            items = []
            if response.data:
                for config in response.data:
                    items.append(ConnectorItem(
                        id=config["id"],
                        name=config["root_url"],
                        type="web_crawl",
                        metadata={
                            "status": config.get("status", "unknown"),
                            "pages_found": config.get("total_pages_found", 0),
                            "crawl_type": config.get("crawl_type", "single"),
                            "created_at": config.get("created_at"),
                            "depth": config.get("depth", 1)
                        }
                    ))
            
            return items
            
        except Exception as e:
            logger.error(f"❌ [Web] Failed to list crawl history: {e}")
            return []

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
        try:
            from usp.tree import sitemap_tree_for_homepage
            
            # Parse the sitemap tree
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
            
            # Try to get transcript (auto-generated or manual)
            transcript_list = YouTubeTranscriptApi.list_transcripts(video_id)
            
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
    

    async def ingest(self, config: Dict[str, Any]) -> "AsyncIterator[ConnectorDocument]":
        """Async wrapper for ingestion (Streaming)."""
        from starlette.concurrency import iterate_in_threadpool
        return iterate_in_threadpool(self._ingest_implementation(config))

    def ingest_sync(self, config: Dict[str, Any]) -> "Iterator[ConnectorDocument]":
        """Synchronous ingestion generator (used by worker tasks)."""
        return self._ingest_implementation(config)

    def _ingest_implementation(self, config: Dict[str, Any]) -> "Iterator[ConnectorDocument]":
        """
        Ingests web pages or YouTube videos (Generator).
        
        Config keys:
            - 'item_ids': List of URLs to ingest
            - 'respect_robots': bool (default True)
        
        Yields:
            ConnectorDocument objects
        """
        urls = config.get("item_ids", [])
        respect_robots = config.get("respect_robots", True)
        
        for url in urls:
            try:
                if not self.is_safe_url(url):
                    logger.warning(f"⚠️ [Web] Unsafe URL blocked: {url}")
                    continue

                # Check robots.txt if enabled
                if respect_robots and not self.check_robots_txt(url, self.USER_AGENT):
                    logger.info(f"🚫 [Web] Blocked by robots.txt: {url}")
                    continue
                
                # Handle YouTube URLs
                if self.is_youtube_url(url):
                    transcript = self.fetch_youtube_transcript(url)
                    if transcript:
                        yield ConnectorDocument(
                            page_content=transcript,
                            metadata=self.get_youtube_metadata(url)
                        )
                    continue
                
                # Standard web page
                html = self.fetch_html(url)
                if html:
                    text = trafilatura.extract(
                        html,
                        include_comments=False,
                        include_tables=True,
                        include_links=False,
                        output_format="txt"
                    )
                    metadata = trafilatura.extract_metadata(html)
                    
                    if text and text.strip():
                        title = metadata.title if metadata and metadata.title else url
                        yield ConnectorDocument(
                            page_content=text,
                            metadata={
                                "source": "web",
                                "title": title,
                                "source_url": url,
                                "author": metadata.author if metadata else None,
                                "date": str(metadata.date) if metadata and metadata.date else None,
                            }
                        )
                        logger.info(f"✅ [Web] Scraped: {url}")
                    else:
                        logger.warning(f"⚠️ [Web] No text extracted from: {url}")
                else:
                    logger.warning(f"⚠️ [Web] Failed to download: {url}")
                    
            except Exception as e:
                logger.error(f"❌ [Web] Failed to scrape {url}: {e}")
        
        logger.info(f"📥 [WebConnector] Ingestion stream ended")
    
    def fetch_html(self, url: str, max_bytes: int = None) -> Optional[str]:
        """
        Fetch raw HTML content for link extraction.
        
        Used by the worker for recursive crawling.
        """
        try:
            max_bytes = max_bytes or self.MAX_HTML_BYTES
            response = self.session.get(
                url,
                timeout=(10, 30),
                allow_redirects=True,
                stream=True
            )
            response.raise_for_status()

            content_type = (response.headers.get("Content-Type") or "").lower()
            if content_type and not any(ct in content_type for ct in self.ALLOWED_CONTENT_TYPES):
                logger.info(f"⚠️ [Web] Skipping non-HTML content: {url} ({content_type})")
                response.close()
                return None

            content_length = response.headers.get("Content-Length")
            if content_length and int(content_length) > max_bytes:
                logger.info(f"⚠️ [Web] Skipping large page ({content_length} bytes): {url}")
                response.close()
                return None

            chunks = []
            total = 0
            for chunk in response.iter_content(chunk_size=8192):
                if not chunk:
                    continue
                total += len(chunk)
                if total > max_bytes:
                    logger.info(f"⚠️ [Web] Page exceeded max size ({max_bytes} bytes): {url}")
                    response.close()
                    return None
                chunks.append(chunk)

            encoding = response.encoding or "utf-8"
            html = b"".join(chunks).decode(encoding, errors="replace")
            response.close()
            return html
        except Exception as e:
            logger.error(f"❌ [Web] HTML fetch failed for {url}: {e}")
            return None

    def is_safe_url(self, url: str) -> bool:
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

    @lru_cache(maxsize=256)
    def _get_robots_parser(self, robots_url: str):
        from urllib.robotparser import RobotFileParser
        rp = RobotFileParser()
        try:
            response = self.session.get(robots_url, timeout=(10, 30))
            if response.status_code >= 400:
                return rp
            rp.parse(response.text.splitlines())
        except Exception as e:
            logger.warning(f"⚠️ [Web] robots.txt fetch failed for {robots_url}: {e}")
        return rp
