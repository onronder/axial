from typing import Dict, Type
from connectors.base import BaseConnector
from connectors.enhanced import EnhancedConnector
from connectors.drive import DriveConnector
from connectors.file_upload import FileUploadConnector
from connectors.google_drive import GoogleDriveConnector
from connectors.notion_enhanced import NotionConnectorEnhanced
from connectors.web_enhanced import WebConnectorEnhanced

# Connector registry - ALL 4 connectors migrated
CONNECTORS: Dict[str, Type[EnhancedConnector]] = {
    "file_upload": FileUploadConnector,
    "google_drive": GoogleDriveConnector,
    "notion": NotionConnectorEnhanced,
    "web": WebConnectorEnhanced,
    # Legacy aliases
    "drive": GoogleDriveConnector,
    "file": FileUploadConnector,
}


def get_connector(connector_type: str) -> EnhancedConnector:
    """
    Get a connector instance by type.
    
    Args:
        connector_type: Type of connector (file_upload, google_drive, notion, web)
        
    Returns:
        Connector instance
        
    Raises:
        ValueError: If connector type is not registered
    """
    if connector_type not in CONNECTORS:
        raise ValueError(
            f"Unknown connector type: {connector_type}. "
            f"Available: {list(CONNECTORS.keys())}"
        )
    
    connector_class = CONNECTORS[connector_type]
    return connector_class()
