from typing import Dict, Type
from connectors.base import BaseConnector
from connectors.enhanced import EnhancedConnector
from connectors.drive import DriveConnector
from connectors.file_upload import FileUploadConnector
from connectors.google_drive import GoogleDriveConnector

# Connector registry
CONNECTORS: Dict[str, Type[EnhancedConnector]] = {
    "file_upload": FileUploadConnector,
    "google_drive": GoogleDriveConnector,
    # Legacy alias
    "drive": GoogleDriveConnector,
    # Add more connectors here as they're migrated
}
