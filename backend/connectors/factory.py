"""
Connector Factory - DEPRECATED

This file is deprecated. Use connectors/__init__.py get_connector() instead.
Kept for backward compatibility only.
"""

from .base import BaseConnector
from .web import WebConnector
from .drive import DriveConnector
from .notion import NotionConnector
from .file_upload import FileUploadConnector

def get_connector(source_type: str) -> BaseConnector:
    """
    Factory function to get the appropriate connector for a source type.
    
    DEPRECATED: Use connectors.get_connector() from __init__.py instead.
    
    Supports aliases for backward compatibility:
    - 'google_drive' and 'drive' both map to DriveConnector
    - 'file' and 'file_upload' both map to FileUploadConnector
    """
    if source_type in ("file", "file_upload"):
        return FileUploadConnector()
    elif source_type == "web":
        return WebConnector()
    elif source_type in ("drive", "google_drive"):
        return DriveConnector()
    elif source_type == "notion":
        return NotionConnector()
    else:
        raise ValueError(f"Unknown source type: {source_type}")
