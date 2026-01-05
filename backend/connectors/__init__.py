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
