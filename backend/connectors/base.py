from abc import ABC, abstractmethod
from typing import List, Dict, Any, Optional
from pydantic import BaseModel

class ConnectorDocument(BaseModel):
    page_content: str
    metadata: Dict[str, Any]

class ConnectorItem(BaseModel):
    id: str
    name: str
    type: str # 'file' or 'folder'
    mime_type: Optional[str] = None
    icon: Optional[str] = None
    parent_id: Optional[str] = None

class BaseConnector(ABC):
    @abstractmethod
    async def authorize(self, user_id: str) -> bool:
        """Check if the user has valid credentials for this provider."""
        pass

    @abstractmethod
    async def list_items(self, user_id: str, parent_id: Optional[str] = None) -> List[ConnectorItem]:
        """List files/folders from the provider."""
        pass

    @abstractmethod
    def ingest(self, config: Dict[str, Any]) -> List[ConnectorDocument]:
        """
        Worker-side ingestion (Synchronous).
        Args:
            config: Dict containing 'user_id', 'item_ids', 'credentials', 'provider'.
        Returns:
            List of ConnectorDocument objects.
        """
        pass
