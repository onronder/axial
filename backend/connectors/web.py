"""
Web Connector

Ingests web pages using Trafilatura for robust article extraction.
"""

from typing import List, Dict, Any, Optional
from .base import BaseConnector, ConnectorDocument, ConnectorItem
import trafilatura
import logging

logger = logging.getLogger(__name__)


class WebConnector(BaseConnector):
    async def authorize(self, user_id: str) -> bool:
        # Web connector is public/open, always authorized
        return True

    async def list_items(self, user_id: str, parent_id: Optional[str] = None) -> List[ConnectorItem]:
        # MVP: Web connector is stateless, the user provides the URL at ingest time.
        # Future: Could list previously crawled URLs from DB.
        return []

    def ingest(self, config: Dict[str, Any]) -> List[ConnectorDocument]:
        """
        Ingests web pages using Trafilatura.
        Config keys: 'item_ids' (List of URLs)
        """
        urls = config.get("item_ids", [])
        documents = []
        
        for url in urls:
            try:
                downloaded = trafilatura.fetch_url(url)
                if downloaded:
                    text = trafilatura.extract(downloaded, include_comments=False, include_tables=True)
                    metadata = trafilatura.extract_metadata(downloaded)
                    
                    if text:
                        title = metadata.title if metadata and metadata.title else url
                        documents.append(ConnectorDocument(
                            page_content=text,
                            metadata={
                                "source": "web",
                                "title": title,
                                "source_url": url
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
