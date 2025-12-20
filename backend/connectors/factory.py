from .base import BaseConnector
from .file import FileConnector
from .web import WebConnector
from .drive import DriveConnector

def get_connector(source_type: str) -> BaseConnector:
    """
    Factory function to get the appropriate connector for a source type.
    
    Supports aliases for backward compatibility:
    - 'google_drive' and 'drive' both map to DriveConnector
    """
    if source_type == "file":
        return FileConnector()
    elif source_type == "web":
        return WebConnector()
    elif source_type in ("drive", "google_drive"):
        return DriveConnector()
    else:
        raise ValueError(f"Unknown source type: {source_type}")

