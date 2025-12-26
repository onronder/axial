"""
Backend Models

Defines Pydantic and SQLModel schemas for the application.
"""

from pydantic import BaseModel
from sqlmodel import SQLModel, Field
from typing import Dict, Any, Optional, List
from datetime import datetime
from uuid import UUID, uuid4
from enum import Enum


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


# =============================================================================
# Ingestion Job Tracking
# =============================================================================

from enum import Enum as PyEnum


class JobStatus(str, PyEnum):
    """Status of an ingestion job."""
    PENDING = "pending"
    PROCESSING = "processing"
    COMPLETED = "completed"
    FAILED = "failed"


class IngestionJob(SQLModel, table=True):
    """
    Tracks the progress of background ingestion tasks.
    Used for polling-based progress updates to the frontend.
    """
    __tablename__ = "ingestion_jobs"
    
    id: UUID = Field(default_factory=uuid4, primary_key=True)
    user_id: UUID = Field(index=True)
    provider: str
    total_files: int = Field(default=0)
    processed_files: int = Field(default=0)
    status: str = Field(default="pending")  # pending, processing, completed, failed
    error_message: Optional[str] = None
    created_at: Optional[datetime] = Field(default_factory=datetime.utcnow)
    updated_at: Optional[datetime] = Field(default_factory=datetime.utcnow)


class IngestionJobResponse(BaseModel):
    """API response for ingestion job status."""
    id: str
    provider: str
    total_files: int
    processed_files: int
    status: str
    percent: float  # Calculated: (processed_files / total_files) * 100
    error_message: Optional[str] = None
    created_at: Optional[datetime] = None
    
    class Config:
        from_attributes = True


# =============================================================================
# Notification Models
# =============================================================================

class NotificationType(str, Enum):
    """Type of notification."""
    INFO = "info"
    SUCCESS = "success"
    WARNING = "warning"
    ERROR = "error"


class Notification(SQLModel, table=True):
    """
    User notification for operation lifecycle events.
    Tracks success, warning, error, and info events.
    """
    __tablename__ = "notifications"
    
    id: UUID = Field(default_factory=uuid4, primary_key=True)
    user_id: UUID = Field(index=True)
    title: str
    message: Optional[str] = None
    type: str = Field(default="info")  # info, success, warning, error
    is_read: bool = Field(default=False)
    # Note: renamed from 'metadata' to avoid shadowing SQLModel.metadata attribute
    extra_data: Optional[str] = Field(default=None)  # JSON string for metadata
    created_at: Optional[datetime] = Field(default_factory=datetime.utcnow)


class NotificationResponse(BaseModel):
    """API response for a notification."""
    id: str
    title: str
    message: Optional[str] = None
    type: str
    is_read: bool
    metadata: Optional[Dict[str, Any]] = None
    created_at: Optional[datetime] = None
    
    class Config:
        from_attributes = True


class NotificationListResponse(BaseModel):
    """API response for notification list."""
    notifications: List["NotificationResponse"]
    total: int
    unread_count: int


class UnreadCountResponse(BaseModel):
    """Lightweight response for unread count."""
    count: int


# =============================================================================
# Web Crawl Configuration Models
# =============================================================================

class CrawlType(str, Enum):
    """Type of web crawl to perform."""
    SINGLE = "single"           # Single page only
    RECURSIVE = "recursive"     # Follow internal links up to max_depth
    SITEMAP = "sitemap"        # Parse sitemap.xml for URLs


class CrawlStatus(str, Enum):
    """Status of a web crawl job."""
    PENDING = "pending"
    DISCOVERING = "discovering"  # Finding URLs from sitemap/links
    PROCESSING = "processing"    # Actively crawling pages
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"


class WebCrawlConfig(SQLModel, table=True):
    """
    Tracks web crawl job configurations and progress.
    Supports single, recursive, and sitemap-based crawling.
    """
    __tablename__ = "web_crawl_configs"
    
    id: UUID = Field(default_factory=uuid4, primary_key=True)
    user_id: UUID = Field(index=True)
    
    # Crawl Configuration
    root_url: str                                    # Starting URL
    crawl_type: str = Field(default="single")        # single, recursive, sitemap
    max_depth: int = Field(default=1)                # Max recursion depth (1-10)
    respect_robots_txt: bool = Field(default=True)   # Respect robots.txt
    
    # Progress Tracking
    status: str = Field(default="pending")           # pending, discovering, processing, completed, failed
    total_pages_found: int = Field(default=0)        # URLs discovered
    pages_ingested: int = Field(default=0)           # URLs successfully processed
    pages_failed: int = Field(default=0)             # URLs that failed
    
    # Error Handling
    error_message: Optional[str] = None
    
    # Timestamps
    created_at: Optional[datetime] = Field(default_factory=datetime.utcnow)
    updated_at: Optional[datetime] = Field(default_factory=datetime.utcnow)
    completed_at: Optional[datetime] = None
    
    # Task Reference
    celery_task_id: Optional[str] = None


class WebCrawlConfigResponse(BaseModel):
    """API response for web crawl configuration."""
    id: str
    root_url: str
    crawl_type: str
    max_depth: int
    status: str
    total_pages_found: int
    pages_ingested: int
    pages_failed: int
    percent: float  # Calculated: (pages_ingested / total_pages_found) * 100
    error_message: Optional[str] = None
    created_at: Optional[datetime] = None
    completed_at: Optional[datetime] = None
    
    class Config:
        from_attributes = True
