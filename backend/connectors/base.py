from abc import ABC, abstractmethod
from typing import List, Dict, Any
from pydantic import BaseModel

class ConnectorDocument(BaseModel):
    page_content: str
    metadata: Dict[str, Any]

class BaseConnector(ABC):
    @abstractmethod
    async def process(self, source: Any, **kwargs) -> List[ConnectorDocument]:
        """
        Process the input source (File, URL, API) and return a list of standard documents.
        """
        pass
