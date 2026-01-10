"""
Base Connector Interface

All data source connectors must extend BaseConnector and implement its abstract methods.
This ensures consistent behavior across all integrations (Google Drive, Notion, Dropbox, etc.).

STANDARD CONNECTOR BEHAVIOR:
============================

1. BROWSING (list_items):
   - If parent_id is None/"root": Return TOP-LEVEL items only
   - If parent_id is a folder ID: Return direct children of that folder
   - Items should have type="folder" if they can contain children
   - Items should have type="file" if they are leaf content

2. SELECTION (Frontend):
   - Users CAN select BOTH folders and files
   - Selecting a folder = ingest everything inside it
   - This is the expected behavior for ALL connectors
"""

from abc import ABC, abstractmethod
from typing import List, Optional
from pydantic import BaseModel


class ConnectorItem(BaseModel):
    """
    Represents an item in the file browser (file or folder).
    
    Attributes:
        id: Unique identifier for this item (provider-specific)
        name: Display name for the item
        type: Either "file" or "folder"
              - "folder": Can be navigated into, selecting ingests all children
              - "file": Leaf node, can be directly ingested
        mime_type: Optional MIME type (e.g., "application/pdf")
        icon: Optional icon (emoji or icon name)
        parent_id: Optional parent folder ID
    """
    id: str
    name: str
    type: str  # 'file' or 'folder'
    mime_type: Optional[str] = None
    icon: Optional[str] = None
    parent_id: Optional[str] = None


class BaseConnector(ABC):
    """
    Abstract base class for all data source connectors.
    
    All connectors must implement:
    - authorize(): Check if user has valid credentials
    - list_items(): Browse files/folders for the file browser UI
    - list_items(): Browse files/folders for the file browser UI
    """
    
    @abstractmethod
    async def authorize(self, user_id: str) -> bool:
        """
        Check if the user has valid credentials for this provider.
        
        Args:
            user_id: The authenticated user's ID
            
        Returns:
            True if connected and credentials are valid
        """
        pass

    @abstractmethod
    async def list_items(self, user_id: str, parent_id: Optional[str] = None) -> List[ConnectorItem]:
        """
        List files/folders from the provider for the file browser UI.
        
        IMPORTANT: 
        - If parent_id is None or "root": Return TOP-LEVEL items only
        - If parent_id is a folder ID: Return direct children of that folder
        - All items that can contain children should have type="folder"
        
        Args:
            user_id: The authenticated user's ID
            parent_id: Optional folder ID to list children of
            
        Returns:
            List of ConnectorItem objects representing files and folders
        """
        pass
