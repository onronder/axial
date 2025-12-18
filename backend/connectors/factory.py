from .base import BaseConnector
from .file import FileConnector
from .web import WebConnector
from .drive import DriveConnector

def get_connector(source_type: str) -> BaseConnector:
    if source_type == "file":
        return FileConnector()
    elif source_type == "web":
        return WebConnector()
    elif source_type == "drive":
        return DriveConnector()
    else:
        raise ValueError(f"Unknown source type: {source_type}")
