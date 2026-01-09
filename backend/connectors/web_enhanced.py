"""
Web Connector for Unified Ingestion Pipeline.

This wraps the existing WebConnector and adapts it to the new EnhancedConnector interface.
"""

import logging
import inspect
import asyncio
from typing import AsyncIterator, Dict, Any, Optional

from connectors.enhanced import EnhancedConnector, SourceDocument, SourceType
from connectors.web import WebConnector as LegacyWebConnector
from connectors.base import ConnectorDocument

logger = logging.getLogger(__name__)


class WebConnectorEnhanced(EnhancedConnector):
    """
    Enhanced Web connector for unified pipeline.
    
    Wraps the existing WebConnector to maintain backward compatibility
    while providing the new SourceDocument interface.
    """
    
    def __init__(self):
        self.legacy = LegacyWebConnector()
    
    @property
    def connector_type(self) -> SourceType:
        return SourceType.WEB
    
    async def fetch_documents(
        self, 
        item_ids: list[str],  # URLs
        credentials: Optional[Dict[str, Any]] = None,
        **kwargs
    ) -> AsyncIterator[SourceDocument]:
        """
        Fetch web pages.
        
        Args:
            item_ids: List of URLs to crawl
            credentials: Not used for web crawling
            **kwargs: Additional options (user_id, respect_robots, etc.)
        """
        user_id = kwargs.get("user_id")
        respect_robots = kwargs.get("respect_robots", True)
        
        # Use legacy connector's ingest method
        config = {
            "user_id": user_id,
            "item_ids": item_ids,
            "credentials": credentials,
            "provider": "web",
            "respect_robots": respect_robots
        }
        
        logger.info(f"[Web] Fetching {len(item_ids)} URLs for user {user_id}")
        
        # Fetch documents using legacy connector
        legacy_stream = self.legacy.ingest(config)
        if inspect.isawaitable(legacy_stream):
            legacy_stream = await legacy_stream

        if hasattr(legacy_stream, "__aiter__"):
            async for doc in legacy_stream:
                content = doc.page_content
                source_url = doc.metadata.get("source_url", item_ids[0] if item_ids else "unknown")

                title = doc.metadata.get("title", source_url.split("/")[-1] or "webpage")
                yield SourceDocument(
                    content=content,
                    metadata=doc.metadata,
                    source_type=SourceType.WEB,
                    source_id=source_url,
                    filename=f"{title}.html",
                    mime_type="text/html",
                    size_bytes=len(content.encode("utf-8")),
                )
            return

        for doc in legacy_stream:
            content = doc.page_content
            source_url = doc.metadata.get("source_url", item_ids[0] if item_ids else "unknown")
            title = doc.metadata.get("title", source_url.split("/")[-1] or "webpage")
            yield SourceDocument(
                content=content,
                metadata=doc.metadata,
                source_type=SourceType.WEB,
                source_id=source_url,
                filename=f"{title}.html",
                mime_type="text/html",
                size_bytes=len(content.encode("utf-8")),
            )

    def fetch_documents_sync(
        self,
        item_ids: list[str],
        credentials: Optional[Dict[str, Any]] = None,
        **kwargs
    ):
        """
        Synchronous fetch for worker pipelines (no asyncio/event loop required).
        """
        user_id = kwargs.get("user_id")
        respect_robots = kwargs.get("respect_robots", True)
        config = {
            "user_id": user_id,
            "item_ids": item_ids,
            "credentials": credentials,
            "provider": "web",
            "respect_robots": respect_robots,
        }

        legacy_stream = None
        if hasattr(self.legacy, "ingest_sync"):
            legacy_stream = self.legacy.ingest_sync(config)
        else:
            legacy_stream = self.legacy.ingest(config)
            if inspect.isawaitable(legacy_stream):
                legacy_stream = asyncio.run(legacy_stream)

        for doc in legacy_stream:
            content = doc.page_content
            source_url = doc.metadata.get("source_url", item_ids[0] if item_ids else "unknown")
            title = doc.metadata.get("title", source_url.split("/")[-1] or "webpage")
            yield SourceDocument(
                content=content,
                metadata=doc.metadata,
                source_type=SourceType.WEB,
                source_id=source_url,
                filename=f"{title}.html",
                mime_type="text/html",
                size_bytes=len(content.encode("utf-8")),
            )
    
    async def authorize(self, user_id: str) -> bool:
        """Web crawling doesn't require authorization."""
        return True
    
    async def list_items(self, user_id: str, parent_id: Optional[str] = None):
        """Web crawling doesn't support browsing."""
        return []
    
    async def ingest(self, config: Dict[str, Any]) -> AsyncIterator[ConnectorDocument]:
        """Legacy method - maintains backward compatibility."""
        stream = self.legacy.ingest(config)
        if inspect.isawaitable(stream):
            return await stream
        return stream
    
    def validate_credentials(self, credentials: Dict[str, Any]) -> bool:
        """No credentials needed for web crawling."""
        return True
