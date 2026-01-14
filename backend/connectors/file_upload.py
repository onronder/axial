"""
File Upload Connector for Unified Ingestion Pipeline.

This connector fetches files from Supabase Storage (ephemeral-staging bucket).
It's the simplest connector and serves as a reference implementation.
"""

import logging
from typing import Any, AsyncIterator, Dict, Iterator, Optional

from connectors.base import ConnectorTransientError, RemoteFile
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
    
    def fetch_documents_sync(
        self,
        item_ids: list[str],
        credentials: Optional[Dict[str, Any]] = None,
        **kwargs
    ):
        """
        Synchronous fetch for worker pipelines (no asyncio/event loop required).
        """
        supabase = get_supabase()

        for storage_path in item_ids:
            try:
                logger.info(f"[FileUpload] Fetching: {storage_path}")

                file_data = supabase.storage.from_(STAGING_BUCKET).download(storage_path)
                if not file_data:
                    raise ItemNotFoundError(f"File not found: {storage_path}")

                filename = storage_path.split("/")[-1]
                mime_type = self._detect_mime_type(filename)

                yield SourceDocument(
                    content=file_data,
                    metadata={
                        "storage_path": storage_path,
                        "upload_method": "direct",
                    },
                    source_type=SourceType.FILE_UPLOAD,
                    source_id=storage_path,
                    filename=filename,
                    mime_type=mime_type,
                    size_bytes=len(file_data),
                )

                logger.info(f"[FileUpload] Fetched {filename} ({len(file_data)} bytes)")

            except Exception as e:
                logger.error(f"[FileUpload] Failed to fetch {storage_path}: {e}")
                raise

    async def fetch_documents(
        self,
        item_ids: list[str],  # storage_paths
        credentials: Optional[Dict[str, Any]] = None,
        **kwargs
    ) -> AsyncIterator[SourceDocument]:
        """
        Async wrapper for fetch. Delegates to sync implementation.
        """
        for doc in self.fetch_documents_sync(item_ids, credentials, **kwargs):
            yield doc
    
    def _detect_mime_type(self, filename: str) -> str:
        """Detect MIME type from filename extension."""
        ext = filename.lower().split(".")[-1] if "." in filename else ""
        
        mime_types = {
            "pdf": "application/pdf",
            "txt": "text/plain",
            "docx": "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
            "doc": "application/msword",
            "xlsx": "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
            "xls": "application/vnd.ms-excel",
            "pptx": "application/vnd.openxmlformats-officedocument.presentationml.presentation",
            "ppt": "application/vnd.ms-powerpoint",
            "html": "text/html",
            "md": "text/markdown",
            "csv": "text/csv",
            "json": "application/json",
            "xml": "application/xml",
            "eml": "message/rfc822",
            "msg": "application/vnd.ms-outlook",
            "rtf": "application/rtf",
        }
        
        return mime_types.get(ext, "application/octet-stream")
    
    async def authorize(self, user_id: str) -> bool:
        """File uploads don't require authorization."""
        return True

    def validate_config(self, config: Dict[str, Any]) -> bool:
        """
        Minimal validation: file uploads are already validated upstream.
        Accept a dict and optionally ensure path/storage_path is a string if provided.
        """
        if config is None:
            return True
        if not isinstance(config, dict):
            return False
        path = config.get("path") or config.get("storage_path")
        return path is None or isinstance(path, str)

    def list_files(self, config: Dict[str, Any], since: Optional[str] = None) -> Iterator[RemoteFile]:
        """File uploads don't support browsing; return empty iterator."""
        return iter([])

    def fetch_file_content(self, file_id: str, config: Dict[str, Any]) -> bytes:
        """
        Download bytes from Supabase Storage using the provided storage path or file_id.
        """
        storage_path = None
        if isinstance(config, dict):
            storage_path = config.get("path") or config.get("storage_path")
        storage_path = storage_path or file_id

        supabase = get_supabase()
        try:
            file_data = supabase.storage.from_(STAGING_BUCKET).download(storage_path)
        except Exception as exc:
            logger.error("File upload download failed for %s: %s", storage_path, exc)
            # Treat as transient; caller can retry or fail the job gracefully
            raise ConnectorTransientError(str(exc))

        if file_data is None:
            raise ItemNotFoundError(f"File not found: {storage_path}")

        if hasattr(file_data, "content"):
            file_data = file_data.content  # supabase client response

        if not isinstance(file_data, (bytes, bytearray)):
            raise ConnectorTransientError(f"Unexpected download type for {storage_path}: {type(file_data)}")

        return bytes(file_data)
    
    def validate_credentials(self, credentials: Dict[str, Any]) -> bool:
        """No credentials needed for file upload."""
        return True
