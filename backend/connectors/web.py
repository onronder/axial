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
from typing import List, Dict, Any, Optional, Set
from urllib.parse import urlparse, urljoin
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
            
            response = requests.get(
                sitemap_url,
                headers={"User-Agent": self.USER_AGENT},
                timeout=30
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
    
    def extract_links(self, html_content: str, base_url: str) -> List[str]:
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
            base_domain = base_parsed.netloc
            
            links: Set[str] = set()
            
            for a_tag in soup.find_all("a", href=True):
                href = a_tag["href"]
                
                # Skip non-HTTP links
                if href.startswith(("#", "javascript:", "mailto:", "tel:", "data:")):
                    continue
                
                # Resolve relative URLs
                absolute_url = urljoin(base_url, href)
                parsed = urlparse(absolute_url)
                
                # Only include same-domain links
                if parsed.netloc == base_domain:
                    # Normalize: remove fragments, ensure https
                    clean_url = f"{parsed.scheme}://{parsed.netloc}{parsed.path}"
                    if parsed.query:
                        clean_url += f"?{parsed.query}"
                    links.add(clean_url)
            
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
            from urllib.robotparser import RobotFileParser
            
            parsed = urlparse(url)
            robots_url = f"{parsed.scheme}://{parsed.netloc}/robots.txt"
            
            rp = RobotFileParser()
            rp.set_url(robots_url)
            rp.read()
            
            return rp.can_fetch(user_agent, url)
            
        except Exception as e:
            # If robots.txt check fails, allow crawling (fail open)
            logger.warning(f"⚠️ [Web] robots.txt check failed for {url}: {e}")
            return True
    
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
    
    def ingest(self, config: Dict[str, Any]) -> List[ConnectorDocument]:
        """
        Ingests web pages or YouTube videos.
        
        Config keys:
            - 'item_ids': List of URLs to ingest
            - 'respect_robots': bool (default True)
        
        Returns:
            List of ConnectorDocument objects
        """
        urls = config.get("item_ids", [])
        respect_robots = config.get("respect_robots", True)
        documents = []
        
        for url in urls:
            try:
                # Check robots.txt if enabled
                if respect_robots and not self.check_robots_txt(url, self.USER_AGENT):
                    logger.info(f"🚫 [Web] Blocked by robots.txt: {url}")
                    continue
                
                # Handle YouTube URLs
                if self.is_youtube_url(url):
                    transcript = self.fetch_youtube_transcript(url)
                    if transcript:
                        documents.append(ConnectorDocument(
                            page_content=transcript,
                            metadata=self.get_youtube_metadata(url)
                        ))
                    continue
                
                # Standard web page
                downloaded = trafilatura.fetch_url(url)
                if downloaded:
                    text = trafilatura.extract(
                        downloaded,
                        include_comments=False,
                        include_tables=True,
                        include_links=False,
                        output_format="txt"
                    )
                    metadata = trafilatura.extract_metadata(downloaded)
                    
                    if text and text.strip():
                        title = metadata.title if metadata and metadata.title else url
                        documents.append(ConnectorDocument(
                            page_content=text,
                            metadata={
                                "source": "web",
                                "title": title,
                                "source_url": url,
                                "author": metadata.author if metadata else None,
                                "date": str(metadata.date) if metadata and metadata.date else None,
                            }
                        ))
                        logger.info(f"✅ [Web] Scraped: {url}")
                    else:
                        logger.warning(f"⚠️ [Web] No text extracted from: {url}")
                else:
                    logger.warning(f"⚠️ [Web] Failed to download: {url}")
                    
            except Exception as e:
                logger.error(f"❌ [Web] Failed to scrape {url}: {e}")
        
        return documents
    
    def fetch_html(self, url: str) -> Optional[str]:
        """
        Fetch raw HTML content for link extraction.
        
        Used by the worker for recursive crawling.
        """
        try:
            response = requests.get(
                url,
                headers={"User-Agent": self.USER_AGENT},
                timeout=30
            )
            response.raise_for_status()
            return response.text
        except Exception as e:
            logger.error(f"❌ [Web] HTML fetch failed for {url}: {e}")
            return None
