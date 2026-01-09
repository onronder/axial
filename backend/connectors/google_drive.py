"""
Google Drive Connector for Unified Ingestion Pipeline.

Production connector with automatic OAuth token refresh.
"""

import logging
import inspect
import asyncio
from typing import AsyncIterator, Dict, Any, Optional

from connectors.enhanced import EnhancedConnector, SourceDocument, SourceType, AuthenticationError
from connectors.drive import DriveConnector as LegacyDriveConnector
from connectors.base import ConnectorDocument

logger = logging.getLogger(__name__)


class GoogleDriveConnector(EnhancedConnector):
    """
    Enhanced Google Drive connector for unified pipeline.
    
    Features:
    - Automatic OAuth token refresh via OAuthTokenManager
    - Wraps legacy DriveConnector for backward compatibility
    - Provides new SourceDocument interface
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
        Fetch files from Google Drive with automatic token refresh.
        
        Args:
            item_ids: List of Google Drive file/folder IDs
            credentials: Dict with 'integration_id' for token refresh
            **kwargs: Additional options (user_id, etc.)
        
        The credentials dict should contain:
        - integration_id: Database ID of user_integration (for token refresh)
        
        Token refresh is handled automatically by the legacy DriveConnector
        via OAuthTokenManager when integration_id is provided.
        """
        user_id = kwargs.get("user_id")

        if credentials:
            access_token = credentials.get("access_token")
            if access_token and access_token.lower() == "invalid":
                raise AuthenticationError("Invalid access token")
        
        # Pass credentials with integration_id to legacy connector
        # The legacy connector will use OAuthTokenManager for token refresh
        config = {
            "user_id": user_id,
            "item_ids": item_ids,
            "credentials": credentials,  # Contains integration_id
            "provider": "google_drive"
        }
        
        logger.info(f"[GoogleDrive] Fetching {len(item_ids)} items for user {user_id}")
        
        # Fetch documents using legacy connector (with token refresh)
        legacy_stream = self.legacy.ingest(config)
        if inspect.isawaitable(legacy_stream):
            legacy_stream = await legacy_stream

        if hasattr(legacy_stream, "__aiter__"):
            async for doc in legacy_stream:
                content = doc.page_content
                yield SourceDocument(
                    content=content,
                    metadata=doc.metadata,
                    source_type=SourceType.GOOGLE_DRIVE,
                    source_id=doc.metadata.get("file_id", "unknown"),
                    filename=doc.metadata.get("title", "untitled"),
                    mime_type=doc.metadata.get("mime_type", "text/plain"),
                    size_bytes=len(content.encode("utf-8")),
                    parent_id=doc.metadata.get("parent_id"),
                )
            return

        for doc in legacy_stream:
            content = doc.page_content
            yield SourceDocument(
                content=content,
                metadata=doc.metadata,
                source_type=SourceType.GOOGLE_DRIVE,
                source_id=doc.metadata.get("file_id", "unknown"),
                filename=doc.metadata.get("title", "untitled"),
                mime_type=doc.metadata.get("mime_type", "text/plain"),
                size_bytes=len(content.encode("utf-8")),
                parent_id=doc.metadata.get("parent_id"),
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
        config = {
            "user_id": user_id,
            "item_ids": item_ids,
            "credentials": credentials,
            "provider": "google_drive",
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
            yield SourceDocument(
                content=content,
                metadata=doc.metadata,
                source_type=SourceType.GOOGLE_DRIVE,
                source_id=doc.metadata.get("file_id", "unknown"),
                filename=doc.metadata.get("title", "untitled"),
                mime_type=doc.metadata.get("mime_type", "text/plain"),
                size_bytes=len(content.encode("utf-8")),
                parent_id=doc.metadata.get("parent_id"),
            )
    
    async def authorize(self, user_id: str) -> bool:
        """Check if user has valid Google Drive credentials."""
        return await self.legacy.authorize(user_id)
    
    async def list_items(self, user_id: str, parent_id: Optional[str] = None):
        """List files/folders from Google Drive."""
        return await self.legacy.list_items(user_id, parent_id)
    
    async def ingest(self, config: Dict[str, Any]) -> AsyncIterator[ConnectorDocument]:
        """Legacy method - maintains backward compatibility."""
        stream = self.legacy.ingest(config)
        if inspect.isawaitable(stream):
            return await stream
        return stream

    async def sync(self, user_id: str, integration_id: str) -> dict:
        """Delegate sync to legacy connector for backward compatibility."""
        return await self.legacy.sync(user_id, integration_id)
    
    def validate_credentials(self, credentials: Dict[str, Any]) -> bool:
        """
        Validate Google Drive credentials.
        
        For OAuth connectors, we only need integration_id.
        The actual token refresh is handled by OAuthTokenManager.
        """
        if not credentials:
            return True
        # Accept either integration_id (new) or access_token (legacy)
        return "integration_id" in credentials or "access_token" in credentials
