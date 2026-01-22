"""
Web Connector - Advanced Web Crawling

Ingests web pages using Trafilatura for robust article extraction.
Supports:
- Single page crawling
- Sitemap.xml parsing
- Recursive link extraction
- YouTube transcript extraction (with residential proxy support)
- robots.txt respect

The connector provides discovery capabilities; looping logic is in the Celery worker.
"""

import re
import os
import time
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
from core.url_utils import is_youtube_url, extract_youtube_video_id, YOUTUBE_URL_PATTERNS

logger = logging.getLogger(__name__)

# =============================================================================
# Bright Data Unlocker API Configuration
# =============================================================================
# YouTube aggressively blocks cloud provider IPs. We use Bright Data's 
# Unlocker API to bypass this restriction with residential IP routing.
#
# API Docs: https://docs.brightdata.com/scraping-automation/web-unlocker/web-unlocker-api

BRIGHTDATA_API_URL = "https://api.brightdata.com/request"


def _get_brightdata_config() -> Dict[str, Any]:
    """
    Load Bright Data Unlocker API configuration from settings.
    
    Returns a dict with API settings. Lazy-loaded to avoid import cycles.
    """
    try:
        from core.config import settings
        return {
            "api_key": settings.BRIGHTDATA_API_KEY,
            "zone": settings.BRIGHTDATA_UNLOCKER_ZONE,
            "timeout": settings.BRIGHTDATA_TIMEOUT,
            "retry_count": settings.BRIGHTDATA_RETRY_COUNT,
            "retry_delay": settings.BRIGHTDATA_RETRY_DELAY,
            "direct_fallback": settings.YOUTUBE_DIRECT_FALLBACK,
        }
    except Exception:
        # Fallback to environment variables if settings not available
        return {
            "api_key": os.getenv("BRIGHTDATA_API_KEY"),
            "zone": os.getenv("BRIGHTDATA_UNLOCKER_ZONE", "axio_unlocker"),
            "timeout": int(os.getenv("BRIGHTDATA_TIMEOUT", "60")),
            "retry_count": int(os.getenv("BRIGHTDATA_RETRY_COUNT", "3")),
            "retry_delay": float(os.getenv("BRIGHTDATA_RETRY_DELAY", "2.0")),
            "direct_fallback": os.getenv("YOUTUBE_DIRECT_FALLBACK", "true").lower() == "true",
        }


def _fetch_via_brightdata_unlocker(url: str, config: Dict[str, Any]) -> Optional[str]:
    """
    Fetch a URL's content via Bright Data Unlocker API.
    
    Args:
        url: Target URL to fetch
        config: Bright Data configuration dict
        
    Returns:
        Response content as string, or None on failure
    """
    api_key = config.get("api_key")
    zone = config.get("zone", "axio_unlocker")
    timeout = config.get("timeout", 60)
    
    if not api_key:
        logger.warning("⚠️ [BrightData] API key not configured")
        return None
    
    headers = {
        "Content-Type": "application/json",
        "Authorization": f"Bearer {api_key}",
    }
    
    payload = {
        "zone": zone,
        "url": url,
        "format": "raw",
    }
    
    try:
        response = requests.post(
            BRIGHTDATA_API_URL,
            headers=headers,
            json=payload,
            timeout=timeout
        )
        
        if response.status_code == 200:
            logger.debug(f"✅ [BrightData] Successfully fetched: {url}")
            return response.text
        else:
            logger.warning(
                f"⚠️ [BrightData] Request failed ({response.status_code}): {url} - {response.text[:200]}"
            )
            return None
            
    except requests.Timeout:
        logger.warning(f"⚠️ [BrightData] Request timed out ({timeout}s): {url}")
        return None
    except Exception as e:
        logger.error(f"❌ [BrightData] Request failed: {url} - {e}")
        return None


class YouTubeProxyError(Exception):
    """Raised when YouTube transcript fetch fails due to proxy/IP issues."""
    
    def __init__(self, message: str, is_ip_blocked: bool = False, original_error: Exception = None):
        super().__init__(message)
        self.is_ip_blocked = is_ip_blocked
        self.original_error = original_error


# Legacy proxy support (deprecated in favor of Unlocker API)
def _get_youtube_proxy_config() -> Dict[str, Any]:
    """Legacy proxy config - kept for backwards compatibility."""
    try:
        from core.config import settings
        return {
            "proxy_url": settings.YOUTUBE_PROXY_URL,
            "enabled": settings.YOUTUBE_PROXY_ENABLED,
            "timeout": settings.YOUTUBE_PROXY_TIMEOUT,
            "retry_count": settings.YOUTUBE_PROXY_RETRY_COUNT,
            "retry_delay": settings.YOUTUBE_PROXY_RETRY_DELAY,
            "direct_fallback": settings.YOUTUBE_DIRECT_FALLBACK,
        }
    except Exception:
        return {
            "proxy_url": os.getenv("YOUTUBE_PROXY_URL"),
            "enabled": False,
            "timeout": 30,
            "retry_count": 3,
            "retry_delay": 1.0,
            "direct_fallback": True,
        }


def _build_proxy_dict(proxy_url: str) -> Optional[Dict[str, str]]:
    """Build a proxies dict for requests library (legacy)."""
    if not proxy_url:
        return None
    try:
        parsed = urlparse(proxy_url)
        if parsed.scheme not in ("http", "https", "socks5", "socks5h"):
            return None
        return {"http": proxy_url, "https": proxy_url}
    except Exception:
        return None

# Alias for backward compatibility
YOUTUBE_PATTERNS = YOUTUBE_URL_PATTERNS


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
    
    def _is_youtube_url(self, url: str) -> bool:
        """Check if a URL is a YouTube video. Uses shared utility."""
        return is_youtube_url(url)
    
    # Backward-compatible alias
    is_youtube_url = _is_youtube_url
    
    def _extract_youtube_video_id(self, url: str) -> Optional[str]:
        """Extract video ID from a YouTube URL. Uses shared utility."""
        return extract_youtube_video_id(url)
    
    # Backward-compatible alias
    extract_youtube_video_id = _extract_youtube_video_id
    
    def fetch_youtube_transcript(self, video_url: str) -> Optional[str]:
        """
        Fetch transcript from a YouTube video using Bright Data Unlocker API.
        
        This method handles YouTube's aggressive IP blocking of cloud providers by:
        1. Using Bright Data Unlocker API (primary method)
        2. Falling back to direct connection if Unlocker fails (configurable)
        3. Implementing retry logic with exponential backoff
        
        Args:
            video_url: YouTube video URL
            
        Returns:
            Full transcript text or None if not available
        """
        video_id = self._extract_youtube_video_id(video_url)
        if not video_id:
            logger.warning(f"⚠️ [YouTube] Could not extract video ID from: {video_url}")
            return None
        
        # Load Bright Data configuration
        bd_config = _get_brightdata_config()
        retry_count = bd_config["retry_count"]
        retry_delay = bd_config["retry_delay"]
        direct_fallback = bd_config["direct_fallback"]
        
        # Attempt 1: Try Bright Data Unlocker API
        if bd_config.get("api_key"):
            logger.info(f"🔒 [YouTube] Attempting transcript fetch via Bright Data Unlocker: {video_id}")
            result = self._fetch_transcript_via_unlocker(video_id, video_url, bd_config)
            if result is not None:
                return result
            logger.warning(f"⚠️ [YouTube] Bright Data Unlocker failed for {video_id}")
        else:
            logger.info(f"ℹ️ [YouTube] Bright Data API key not configured, using direct connection")
        
        # Attempt 2: Direct connection fallback
        if direct_fallback:
            logger.info(f"🔄 [YouTube] Attempting direct connection fallback: {video_id}")
            result = self._fetch_transcript_with_retry(
                video_id=video_id,
                video_url=video_url,
                proxies=None,
                retry_count=retry_count,
                retry_delay=retry_delay,
                attempt_name="direct_fallback",
            )
            if result is not None:
                return result
        
        # All attempts failed
        logger.error(f"❌ [YouTube] All transcript fetch attempts failed for {video_url}")
        return None
    
    def _fetch_transcript_via_unlocker(
        self,
        video_id: str,
        video_url: str,
        config: Dict[str, Any],
    ) -> Optional[str]:
        """
        Fetch YouTube transcript using Bright Data Unlocker API.
        
        This method extracts the embedded captions data from the YouTube page
        HTML, which YouTube includes as JSON in the page source.
        
        Args:
            video_id: YouTube video ID
            video_url: Full YouTube URL
            config: Bright Data configuration dict
            
        Returns:
            Transcript text or None if not available
        """
        import json
        import html
        
        retry_count = config.get("retry_count", 3)
        retry_delay = config.get("retry_delay", 2.0)
        
        for attempt in range(retry_count):
            try:
                # Canonical YouTube URL for consistency
                canonical_url = f"https://www.youtube.com/watch?v={video_id}"
                
                # Fetch page via Bright Data Unlocker API
                page_html = _fetch_via_brightdata_unlocker(canonical_url, config)
                
                if not page_html:
                    if attempt < retry_count - 1:
                        delay = retry_delay * (2 ** attempt)
                        logger.warning(
                            f"⚠️ [YouTube/Unlocker] Attempt {attempt + 1}/{retry_count} failed. "
                            f"Retrying in {delay:.1f}s..."
                        )
                        time.sleep(delay)
                        continue
                    return None
                
                # Extract captions from page HTML
                transcript_text = self._extract_captions_from_html(page_html, video_id)
                
                if transcript_text:
                    logger.info(
                        f"✅ [YouTube/Unlocker] Fetched transcript: "
                        f"{len(transcript_text)} chars from {video_id}"
                    )
                    return transcript_text
                
                # Page fetched but no captions found
                logger.warning(f"⚠️ [YouTube/Unlocker] No captions found in page for: {video_id}")
                return None
                
            except Exception as e:
                if attempt < retry_count - 1:
                    delay = retry_delay * (2 ** attempt)
                    logger.warning(
                        f"⚠️ [YouTube/Unlocker] Attempt {attempt + 1}/{retry_count} error: {e}. "
                        f"Retrying in {delay:.1f}s..."
                    )
                    time.sleep(delay)
                else:
                    logger.error(f"❌ [YouTube/Unlocker] Failed after {retry_count} attempts: {e}")
        
        return None
    
    def _extract_captions_from_html(self, page_html: str, video_id: str) -> Optional[str]:
        """
        Extract captions/transcript from YouTube page HTML.
        
        YouTube embeds caption data as JSON in the page source within
        the ytInitialPlayerResponse variable.
        
        Args:
            page_html: Raw HTML of YouTube video page
            video_id: Video ID for logging
            
        Returns:
            Transcript text or None if not found
        """
        import json
        import html as html_module
        import re
        
        try:
            # Look for ytInitialPlayerResponse JSON in the page
            pattern = r'var ytInitialPlayerResponse\s*=\s*(\{.+?\});'
            match = re.search(pattern, page_html)
            
            if not match:
                # Try alternative pattern (sometimes it's in a different format)
                pattern = r'ytInitialPlayerResponse\s*=\s*(\{.+?\});'
                match = re.search(pattern, page_html)
            
            if not match:
                logger.warning(f"⚠️ [YouTube] Could not find ytInitialPlayerResponse for {video_id}")
                return None
            
            player_response = json.loads(match.group(1))
            
            # Check for playability issues
            playability = player_response.get("playabilityStatus", {})
            status = playability.get("status")
            
            if status == "ERROR":
                reason = playability.get("reason", "Unknown error")
                logger.warning(f"⚠️ [YouTube] Video unavailable: {video_id} - {reason}")
                return None
            
            if status == "LOGIN_REQUIRED":
                logger.warning(f"⚠️ [YouTube] Video requires login: {video_id}")
                return None
            
            # Get captions info
            captions = player_response.get("captions", {})
            caption_tracks = captions.get("playerCaptionsTracklistRenderer", {}).get("captionTracks", [])
            
            if not caption_tracks:
                logger.warning(f"⚠️ [YouTube] No caption tracks available for: {video_id}")
                return None
            
            # Prefer English, then any available language
            selected_track = None
            for track in caption_tracks:
                lang = track.get("languageCode", "")
                if lang.startswith("en"):
                    # Prefer manual captions over auto-generated
                    if track.get("kind") != "asr" or selected_track is None:
                        selected_track = track
                        if track.get("kind") != "asr":
                            break  # Found manual English, stop looking
            
            if not selected_track and caption_tracks:
                selected_track = caption_tracks[0]  # Fallback to first available
            
            if not selected_track:
                return None
            
            # Fetch the actual captions
            captions_url = selected_track.get("baseUrl")
            if not captions_url:
                logger.warning(f"⚠️ [YouTube] No captions URL for: {video_id}")
                return None
            
            # Fetch captions XML via Bright Data
            bd_config = _get_brightdata_config()
            captions_xml = _fetch_via_brightdata_unlocker(captions_url, bd_config)
            
            if not captions_xml:
                logger.warning(f"⚠️ [YouTube] Failed to fetch captions XML for: {video_id}")
                return None
            
            # Parse captions XML
            return self._parse_captions_xml(captions_xml, video_id)
            
        except json.JSONDecodeError as e:
            logger.warning(f"⚠️ [YouTube] Failed to parse player response JSON: {e}")
            return None
        except Exception as e:
            logger.error(f"❌ [YouTube] Error extracting captions from HTML: {e}")
            return None
    
    def _parse_captions_xml(self, xml_content: str, video_id: str) -> Optional[str]:
        """
        Parse YouTube captions XML format.
        
        YouTube returns captions in XML format like:
        <transcript>
            <text start="0.12" dur="2.34">Caption text here</text>
            ...
        </transcript>
        
        Args:
            xml_content: Raw XML captions content
            video_id: Video ID for logging
            
        Returns:
            Combined transcript text
        """
        import html as html_module
        
        try:
            from bs4 import BeautifulSoup
            
            soup = BeautifulSoup(xml_content, "lxml-xml")
            text_elements = soup.find_all("text")
            
            if not text_elements:
                # Try HTML parser as fallback
                soup = BeautifulSoup(xml_content, "html.parser")
                text_elements = soup.find_all("text")
            
            if not text_elements:
                logger.warning(f"⚠️ [YouTube] No text elements in captions XML for: {video_id}")
                return None
            
            text_parts = []
            for elem in text_elements:
                text = elem.get_text() if hasattr(elem, 'get_text') else str(elem.string or "")
                # Decode HTML entities
                text = html_module.unescape(text)
                if text.strip():
                    text_parts.append(text.strip())
            
            if not text_parts:
                return None
            
            return " ".join(text_parts)
            
        except Exception as e:
            logger.error(f"❌ [YouTube] Error parsing captions XML for {video_id}: {e}")
            return None
    
    def _fetch_transcript_with_retry(
        self,
        video_id: str,
        video_url: str,
        proxies: Optional[Dict[str, str]],
        retry_count: int,
        retry_delay: float,
        attempt_name: str,
    ) -> Optional[str]:
        """
        Fetch transcript with retry logic and exponential backoff (direct connection).
        
        Note: This is the fallback method using youtube-transcript-api directly.
        For proxy support, use the Bright Data Unlocker API method instead.
        
        Args:
            video_id: YouTube video ID
            video_url: Full YouTube URL (for logging)
            proxies: Deprecated - not used in current API version
            retry_count: Number of retry attempts
            retry_delay: Base delay between retries
            attempt_name: Name of this attempt for logging
            
        Returns:
            Transcript text or None if all retries failed
        """
        try:
            from youtube_transcript_api import YouTubeTranscriptApi
            from youtube_transcript_api._errors import (
                TranscriptsDisabled,
                NoTranscriptFound,
                VideoUnavailable,
            )
        except ImportError:
            logger.error("❌ [YouTube] youtube-transcript-api not installed")
            return None
        
        # IP block error signatures
        IP_BLOCK_SIGNATURES = [
            "YouTube is blocking requests from your IP",
            "IP belonging to a cloud provider",
            "RequestBlocked",
            "IpBlocked",
            "too many requests",
            "blocked by YouTube",
        ]
        
        for attempt in range(retry_count):
            try:
                # Create API instance (direct connection only - proxies not supported in newer API)
                ytt_api = YouTubeTranscriptApi()
                
                # Try to get transcript list (no proxy support in current API version)
                transcript_list = ytt_api.list(video_id)
                
                # Prefer manual transcripts, fall back to auto-generated
                transcript = self._select_best_transcript(transcript_list)
                
                if not transcript:
                    logger.warning(f"⚠️ [YouTube] No transcript available for: {video_id}")
                    return None
                
                # Fetch and combine transcript segments
                segments = transcript.fetch()
                full_text = self._extract_transcript_text(segments, video_id)
                
                proxy_status = "via proxy" if proxies else "direct"
                logger.info(
                    f"✅ [YouTube] Fetched transcript ({proxy_status}): "
                    f"{len(full_text)} chars from {video_id}"
                )
                return full_text
                
            except (TranscriptsDisabled, NoTranscriptFound) as e:
                # These are permanent failures - no point retrying
                logger.warning(f"⚠️ [YouTube] Transcript not available for {video_id}: {e}")
                return None
                
            except VideoUnavailable as e:
                # Video is private, deleted, or region-locked
                logger.warning(f"⚠️ [YouTube] Video unavailable {video_id}: {e}")
                return None
                
            except Exception as e:
                error_str = str(e)
                
                # Check if this is an IP block error
                is_ip_blocked = any(sig.lower() in error_str.lower() for sig in IP_BLOCK_SIGNATURES)
                
                if is_ip_blocked:
                    logger.warning(
                        f"⚠️ [YouTube] IP blocked ({attempt_name}, attempt {attempt + 1}/{retry_count}): {video_id}"
                    )
                    # Don't retry IP blocks - they need different approach
                    return None
                
                # Log retry attempt
                if attempt < retry_count - 1:
                    delay = retry_delay * (2 ** attempt)  # Exponential backoff
                    logger.warning(
                        f"⚠️ [YouTube] Attempt {attempt + 1}/{retry_count} failed for {video_id}: {e}. "
                        f"Retrying in {delay:.1f}s..."
                    )
                    time.sleep(delay)
                else:
                    logger.error(
                        f"❌ [YouTube] Transcript fetch failed for {video_url} "
                        f"({attempt_name}, {retry_count} attempts): {e}"
                    )
        
        return None
    
    def _select_best_transcript(self, transcript_list) -> Optional[Any]:
        """
        Select the best available transcript from the list.
        
        Preference order:
        1. Manual English transcript
        2. Auto-generated English transcript
        3. Any available transcript (first available language)
        
        Args:
            transcript_list: TranscriptList from youtube-transcript-api
            
        Returns:
            Selected Transcript object or None
        """
        # Try manual English first
        try:
            return transcript_list.find_manually_created_transcript(['en', 'en-US', 'en-GB'])
        except Exception:
            pass
        
        # Try auto-generated English
        try:
            return transcript_list.find_generated_transcript(['en', 'en-US', 'en-GB'])
        except Exception:
            pass
        
        # Fallback: any available language
        try:
            for transcript in transcript_list:
                return transcript
        except Exception:
            pass
        
        return None
    
    def _extract_transcript_text(self, segments, video_id: str) -> str:
        """
        Extract text from transcript segments.
        
        Handles both legacy dict format and new object format (v1.2.0+).
        
        Args:
            segments: List of transcript segments
            video_id: Video ID for logging
            
        Returns:
            Combined transcript text
        """
        text_parts = []
        
        for seg in segments:
            if isinstance(seg, dict):
                # Legacy dict format: {"text": "...", "start": ..., "duration": ...}
                text_parts.append(seg.get("text", ""))
            elif hasattr(seg, "text"):
                # New FetchedTranscriptSnippet object format (v1.2.0+)
                text_parts.append(seg.text)
            else:
                # Fallback: convert to string
                logger.warning(f"⚠️ [YouTube] Unknown segment type for {video_id}: {type(seg).__name__}")
                text_parts.append(str(seg))
        
        return " ".join(text_parts)
    
    def get_youtube_metadata(self, video_url: str) -> Dict[str, str]:
        """Get basic metadata for a YouTube video."""
        video_id = self._extract_youtube_video_id(video_url)
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

                if self._is_youtube_url(url):
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
