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

2. INGESTION (ingest):
   - If an item_id is a FOLDER: Recursively fetch ALL nested files
   - If an item_id is a FILE: Process that single file
   - Max recursion depth: 10 levels (to prevent infinite loops)
   - Track processed IDs to avoid circular references
   - Return ConnectorDocument objects with extracted text content

3. SELECTION (Frontend):
   - Users CAN select BOTH folders and files
   - Selecting a folder = ingest everything inside it
   - This is the expected behavior for ALL connectors

Example folder ingestion pattern:
    if is_folder(item_id):
        files = get_all_files_recursive(item_id)
        for file in files:
            documents.append(process_file(file))
"""

from abc import ABC, abstractmethod
from typing import List, Dict, Any, Optional, AsyncIterator
from pydantic import BaseModel


class ConnectorDocument(BaseModel):
    """
    Represents a processed document ready for embedding.
    
    Attributes:
        page_content: The extracted text content of the document
        metadata: Source information (title, source_url, file_id, etc.)
    """
    page_content: str
    metadata: Dict[str, Any]


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
    - ingest(): Extract content for embedding (supports recursive folder ingestion)
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

    @abstractmethod
    async def ingest(self, config: Dict[str, Any]) -> "AsyncIterator[ConnectorDocument]":
        """
        Worker-side ingestion (Async Wrapper).
        
        IMPORTANT BEHAVIOR:
        - Must be implemented as an async wrapper returning an iterator (stream)
        - use iterate_in_threadpool to stream results from blocking implementation
        - If an item_id is a FOLDER: Recursively yield nested files (max depth: 10)
        - If an item_id is a FILE: Yield that single file
        - Track processed IDs to prevent infinite loops from circular references
        
        Args:
            config: Dict containing:
                - 'user_id': The user's ID for multi-tenancy
                - 'item_ids': List of file/folder IDs to ingest
                - 'credentials': Decrypted OAuth credentials
                - 'provider': Provider type string
                
        Returns:
            AsyncIterator yielding ConnectorDocument objects
        """
        pass
