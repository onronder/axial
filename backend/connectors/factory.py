from .base import BaseConnector
from .file import FileConnector
from .web import WebConnector

def get_connector(source_type: str) -> BaseConnector:
    if source_type == "file":
        return FileConnector()
    elif source_type == "web":
        return WebConnector()
    else:
        raise ValueError(f"Unknown source type: {source_type}")
