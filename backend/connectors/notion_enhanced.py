"""
Notion Connector for Unified Ingestion Pipeline.

Production connector with automatic OAuth token refresh.
"""

import logging
from typing import AsyncIterator, Dict, Any, Optional

from connectors.enhanced import EnhancedConnector, SourceDocument, SourceType
from connectors.notion import NotionConnector as LegacyNotionConnector
from connectors.base import ConnectorDocument

logger = logging.getLogger(__name__)


class NotionConnectorEnhanced(EnhancedConnector):
    """
    Enhanced Notion connector for unified pipeline.
    
    Features:
    - Automatic OAuth token refresh via OAuthTokenManager
    - Wraps legacy NotionConnector for backward compatibility
    - Provides new SourceDocument interface
    """
    
    def __init__(self):
        self.legacy = LegacyNotionConnector()
    
    @property
    def connector_type(self) -> SourceType:
        return SourceType.NOTION
    
    async def fetch_documents(
        self, 
        item_ids: list[str],
        credentials: Optional[Dict[str, Any]] = None,
        **kwargs
    ) -> AsyncIterator[SourceDocument]:
        """
        Fetch pages/databases from Notion with automatic token refresh.
        
        Args:
            item_ids: List of Notion page/database IDs
            credentials: Dict with 'integration_id' for token refresh
            **kwargs: Additional options (user_id, etc.)
        
        The credentials dict should contain:
        - integration_id: Database ID of user_integration (for token refresh)
        
        Token refresh is handled automatically by the legacy NotionConnector
        via OAuthTokenManager when integration_id is provided.
        """
        user_id = kwargs.get("user_id")
        
        # Pass credentials with integration_id to legacy connector
        # The legacy connector will use OAuthTokenManager for token refresh
        config = {
            "user_id": user_id,
            "item_ids": item_ids,
            "credentials": credentials,  # Contains integration_id
            "provider": "notion"
        }
        
        logger.info(f"[Notion] Fetching {len(item_ids)} items for user {user_id}")
        
        # Fetch documents using legacy connector (with token refresh)
        async for doc in await self.legacy.ingest(config):
            # Convert ConnectorDocument to SourceDocument
            content = doc.page_content
            
            yield SourceDocument(
                content=content,
                metadata=doc.metadata,
                source_type=SourceType.NOTION,
                source_id=doc.metadata.get("page_id", "unknown"),
                filename=doc.metadata.get("title", "untitled"),
                mime_type="text/markdown",  # Notion exports as markdown
                size_bytes=len(content.encode('utf-8')),
                parent_id=doc.metadata.get("parent_id")
            )
    
    async def authorize(self, user_id: str) -> bool:
        """Check if user has valid Notion credentials."""
        return await self.legacy.authorize(user_id)
    
    async def list_items(self, user_id: str, parent_id: Optional[str] = None):
        """List pages/databases from Notion."""
        return await self.legacy.list_items(user_id, parent_id)
    
    async def ingest(self, config: Dict[str, Any]) -> AsyncIterator[ConnectorDocument]:
        """Legacy method - maintains backward compatibility."""
        return self.legacy.ingest(config)
    
    def validate_credentials(self, credentials: Dict[str, Any]) -> bool:
        """
        Validate Notion credentials.
        
        For OAuth connectors, we only need integration_id.
        The actual token refresh is handled by OAuthTokenManager.
        """
        # Accept either integration_id (new) or access_token (legacy)
        return "integration_id" in credentials or "access_token" in credentials
