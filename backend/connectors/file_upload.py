"""
File Upload Connector for Unified Ingestion Pipeline.

This connector fetches files from Supabase Storage (ephemeral-staging bucket).
It's the simplest connector and serves as a reference implementation.
"""

import logging
from typing import AsyncIterator, Dict, Any, Optional

from connectors.enhanced import EnhancedConnector, SourceDocument, SourceType, ItemNotFoundError
from core.db import get_supabase

logger = logging.getLogger(__name__)

STAGING_BUCKET = "ephemeral-staging"


class FileUploadConnector(EnhancedConnector):
    """
    Connector for direct file uploads.
    
    Fetches files from Supabase Storage that were uploaded via presigned URLs.
    """
    
    @property
    def connector_type(self) -> SourceType:
        return SourceType.FILE_UPLOAD
    
    async def fetch_documents(
        self, 
        item_ids: list[str],  # storage_paths
        credentials: Optional[Dict[str, Any]] = None,
        **kwargs
    ) -> AsyncIterator[SourceDocument]:
        """
        Fetch files from Supabase Storage.
        
        Args:
            item_ids: List of storage paths in ephemeral-staging bucket
            credentials: Not used for file uploads
            **kwargs: Additional options
        """
        supabase = get_supabase()
        
        for storage_path in item_ids:
            try:
                logger.info(f"[FileUpload] Fetching: {storage_path}")
                
                # Download from storage
                file_data = supabase.storage.from_(STAGING_BUCKET).download(storage_path)
                
                if not file_data:
                    raise ItemNotFoundError(f"File not found: {storage_path}")
                
                # Extract metadata from path
                # Path format: uploads/{user_id}/{uuid}/{filename}
                filename = storage_path.split("/")[-1]
                
                # Detect MIME type from filename extension
                mime_type = self._detect_mime_type(filename)
                
                yield SourceDocument(
                    content=file_data,
                    metadata={
                        "storage_path": storage_path,
                        "upload_method": "direct"
                    },
                    source_type=SourceType.FILE_UPLOAD,
                    source_id=storage_path,
                    filename=filename,
                    mime_type=mime_type,
                    size_bytes=len(file_data)
                )
                
                logger.info(f"[FileUpload] Fetched {filename} ({len(file_data)} bytes)")
                
            except Exception as e:
                logger.error(f"[FileUpload] Failed to fetch {storage_path}: {e}")
                raise
    
    def _detect_mime_type(self, filename: str) -> str:
        """Detect MIME type from filename extension."""
        ext = filename.lower().split(".")[-1] if "." in filename else ""
        
        mime_types = {
            "pdf": "application/pdf",
            "txt": "text/plain",
            "docx": "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
            "doc": "application/msword",
            "html": "text/html",
            "md": "text/markdown",
            "csv": "text/csv",
            "json": "application/json"
        }
        
        return mime_types.get(ext, "application/octet-stream")
    
    async def authorize(self, user_id: str) -> bool:
        """File uploads don't require authorization."""
        return True
    
    async def list_items(self, user_id: str, parent_id: Optional[str] = None):
        """File uploads don't support browsing."""
        return []
    
    async def ingest(self, config: Dict[str, Any]):
        """Legacy method - redirects to fetch_documents."""
        item_ids = config.get("item_ids", [])
        credentials = config.get("credentials")
        user_id = config.get("user_id")
        
        async for doc in self.fetch_documents(item_ids, credentials, user_id=user_id):
            # Convert to legacy ConnectorDocument
            yield doc.to_connector_document()
    
    def validate_credentials(self, credentials: Dict[str, Any]) -> bool:
        """No credentials needed for file upload."""
        return True
