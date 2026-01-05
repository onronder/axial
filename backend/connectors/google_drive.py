"""
Google Drive Connector for Unified Ingestion Pipeline.

This wraps the existing DriveConnector and adapts it to the new EnhancedConnector interface.
"""

import logging
from typing import AsyncIterator, Dict, Any, Optional

from connectors.enhanced import EnhancedConnector, SourceDocument, SourceType
from connectors.drive import DriveConnector as LegacyDriveConnector
from connectors.base import ConnectorDocument

logger = logging.getLogger(__name__)


class GoogleDriveConnector(EnhancedConnector):
    """
    Enhanced Google Drive connector for unified pipeline.
    
    Wraps the existing DriveConnector to maintain backward compatibility
    while providing the new SourceDocument interface.
    """
    
    def __init__(self):
        self.legacy = LegacyDriveConnector()
    
    @property
    def connector_type(self) -> SourceType:
        return SourceType.GOOGLE_DRIVE
    
    async def fetch_documents(
        self, 
        item_ids: list[str],
        credentials: Optional[Dict[str, Any]] = None,
        **kwargs
    ) -> AsyncIterator[SourceDocument]:
        """
        Fetch files from Google Drive.
        
        Args:
            item_ids: List of Google Drive file/folder IDs
            credentials: OAuth credentials
            **kwargs: Additional options (user_id, etc.)
        """
        user_id = kwargs.get("user_id")
        
        # Use legacy connector's ingest method
        config = {
            "user_id": user_id,
            "item_ids": item_ids,
            "credentials": credentials,
            "provider": "google_drive"
        }
        
        logger.info(f"[GoogleDrive] Fetching {len(item_ids)} items for user {user_id}")
        
        # Fetch documents using legacy connector
        async for doc in self.legacy.ingest(config):
            # Convert ConnectorDocument to SourceDocument
            content = doc.page_content
            
            yield SourceDocument(
                content=content,
                metadata=doc.metadata,
                source_type=SourceType.GOOGLE_DRIVE,
                source_id=doc.metadata.get("file_id", "unknown"),
                filename=doc.metadata.get("title", "untitled"),
                mime_type=doc.metadata.get("mime_type", "text/plain"),
                size_bytes=len(content.encode('utf-8')),
                parent_id=doc.metadata.get("parent_id")
            )
    
    async def authorize(self, user_id: str) -> bool:
        """Check if user has valid Google Drive credentials."""
        return await self.legacy.authorize(user_id)
    
    async def list_items(self, user_id: str, parent_id: Optional[str] = None):
        """List files/folders from Google Drive."""
        return await self.legacy.list_items(user_id, parent_id)
    
    async def ingest(self, config: Dict[str, Any]) -> AsyncIterator[ConnectorDocument]:
        """Legacy method - maintains backward compatibility."""
        return self.legacy.ingest(config)
    
    def validate_credentials(self, credentials: Dict[str, Any]) -> bool:
        """Validate Google Drive OAuth credentials."""
        # Check if we have required OAuth fields
        required_fields = ["access_token"]
        return all(field in credentials for field in required_fields)
