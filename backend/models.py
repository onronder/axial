"""
Backend Models

Defines Pydantic and SQLModel schemas for the application.
"""

from pydantic import BaseModel
from sqlmodel import SQLModel, Field
from typing import Dict, Any, Optional, List
from datetime import datetime
from uuid import UUID, uuid4


# =============================================================================
# SQLModel Table Definitions (ORM)
# =============================================================================

class ConnectorDefinition(SQLModel, table=True):
    """
    Defines available connector types (google_drive, notion, web, etc.)
    This table is seeded via migration and rarely changes.
    """
    __tablename__ = "connector_definitions"
    
    id: UUID = Field(default_factory=uuid4, primary_key=True)
    type: str = Field(unique=True, index=True)  # 'google_drive', 'notion', 'web'
    name: str  # 'Google Drive', 'Notion'
    description: Optional[str] = None
    icon_path: Optional[str] = None
    category: Optional[str] = None  # 'Cloud Storage', 'Knowledge Base', 'Web'
    is_active: bool = Field(default=True)
    created_at: Optional[datetime] = Field(default_factory=datetime.utcnow)


class UserIntegration(SQLModel, table=True):
    """
    Stores a user's connected integrations with OAuth tokens.
    Uses connector_definition_id FK to link to connector type.
    """
    __tablename__ = "user_integrations"
    
    id: UUID = Field(default_factory=uuid4, primary_key=True)
    user_id: UUID = Field(index=True)
    connector_definition_id: UUID = Field(foreign_key="connector_definitions.id", index=True)
    access_token: Optional[str] = None
    refresh_token: Optional[str] = None
    expires_at: Optional[datetime] = None
    last_sync_at: Optional[datetime] = None
    created_at: Optional[datetime] = Field(default_factory=datetime.utcnow)
    updated_at: Optional[datetime] = Field(default_factory=datetime.utcnow)


# =============================================================================
# Pydantic Response Schemas (API)
# =============================================================================

class ConnectorDefinitionResponse(BaseModel):
    """API response for a connector definition."""
    id: str
    type: str
    name: str
    description: Optional[str] = None
    icon_path: Optional[str] = None
    category: Optional[str] = None
    is_active: bool = True

    class Config:
        from_attributes = True


class UserIntegrationResponse(BaseModel):
    """API response for a user's connected integration."""
    id: str
    connector_definition_id: str
    connector_type: Optional[str] = None
    connector_name: Optional[str] = None
    connector_icon: Optional[str] = None
    category: Optional[str] = None
    connected: bool = True
    last_sync_at: Optional[datetime] = None

    class Config:
        from_attributes = True


class IntegrationStatusResponse(BaseModel):
    """API response for integration status check."""
    available: List[ConnectorDefinitionResponse]
    connected: List[UserIntegrationResponse]


# =============================================================================
# Legacy Pydantic Schemas (for backwards compatibility)
# =============================================================================

class IngestRequest(BaseModel):
    """Request schema for document ingestion."""
    client_id: str
    filename: str
    content: str
    metadata: Optional[Dict[str, Any]] = {}


class IngestResponse(BaseModel):
    """Response schema for document ingestion."""
    status: str
    doc_id: str
