from typing import Dict, Type
from connectors.drive import DriveConnector
from connectors.file_upload import FileUploadConnector
from connectors.notion import NotionConnector
from connectors.web import WebConnector

# Connector registry - ALL 4 connectors migrated
CONNECTORS: Dict[str, Type] = {
    "file_upload": FileUploadConnector,
    "google_drive": DriveConnector,
    "notion": NotionConnector,
    "web": WebConnector,
}


def get_connector(connector_type: str):
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
