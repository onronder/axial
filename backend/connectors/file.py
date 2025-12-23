"""
File Connector

Handles direct file uploads via FastAPI UploadFile.
Uses the centralized DocumentParser service for text extraction.
"""

from typing import List, Any
from fastapi import UploadFile
from .base import BaseConnector, ConnectorDocument
from services.parsers import DocumentParser
import logging

logger = logging.getLogger(__name__)


class FileConnector(BaseConnector):
    """
    Connector for direct file uploads.
    
    Delegates text extraction to the centralized DocumentParser service
    to ensure consistent parsing across all ingestion methods.
    """
    
    async def authorize(self, user_id: str) -> bool:
        """File uploads don't require authorization."""
        return True

    async def list_items(self, user_id: str, parent_id: Any = None) -> List[Any]:
        """File uploads don't have a list operation."""
        return []

    async def ingest(self, user_id: str, item_ids: List[str]) -> List[ConnectorDocument]:
        """Not used for file uploads - use process() instead."""
        raise NotImplementedError("FileConnector uses process() with UploadFile, not ingest() with IDs.")

    async def process(self, source: UploadFile, **kwargs) -> List[ConnectorDocument]:
        """
        Process an UploadFile: Read bytes and extract text via DocumentParser.
        
        Args:
            source: FastAPI UploadFile object
            **kwargs: Additional options, including 'metadata' dict to merge
            
        Returns:
            List of ConnectorDocument with extracted text
        """
        filename = source.filename or "unknown"
        content_type = source.content_type or "application/octet-stream"
        
        logger.info(f"📄 [FileConnector] Processing file: {filename} ({content_type})")
        
        # 1. Read file bytes
        try:
            file_bytes = await source.read()
            logger.info(f"📄 [FileConnector] Read {len(file_bytes)} bytes from {filename}")
        except Exception as e:
            logger.error(f"❌ [FileConnector] Failed to read file {filename}: {e}")
            return []
        
        # 2. Extract text using centralized DocumentParser
        text_content = DocumentParser.extract_text(file_bytes, content_type)
        
        if not text_content or not text_content.strip():
            logger.warning(f"⚠️ [FileConnector] No text extracted from {filename}")
            return []
        
        logger.info(f"📄 [FileConnector] Extracted {len(text_content)} chars from {filename}")
        
        # 3. Build metadata
        base_metadata = kwargs.get("metadata", {})
        base_metadata["filename"] = filename
        base_metadata["content_type"] = content_type
        
        # 4. Return as single document (chunking happens in ingest.py)
        return [ConnectorDocument(
            page_content=text_content,
            metadata=base_metadata
        )]
