from pydantic import BaseModel
from typing import Dict, Any, Optional

class IngestRequest(BaseModel):
    client_id: str
    filename: str
    content: str
    metadata: Optional[Dict[str, Any]] = {}

class IngestResponse(BaseModel):
    status: str
    doc_id: str
