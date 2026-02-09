"""
Connector Base Interface and Standard Exceptions

All ingestion connectors must implement BaseConnector for consistent behavior and error handling.
"""

from __future__ import annotations

from abc import ABC, abstractmethod
from collections.abc import Iterator
from dataclasses import dataclass
from datetime import datetime


# Standard exceptions for connector implementations
class ConnectorError(Exception):
    """Base connector error."""


class ConnectorAuthError(ConnectorError):
    """Authentication/authorization failed."""


class ConnectorRateLimitError(ConnectorError):
    """Provider rate limit encountered; caller may retry with backoff."""


class ConnectorTransientError(ConnectorError):
    """Transient provider error; safe to retry."""


@dataclass
class RemoteFile:
    id: str
    name: str
    mime_type: str | None
    size: int | None
    modified_at: datetime | None
    parent_id: str | None = None
    web_view_url: str | None = None


class BaseConnector(ABC):
    """Abstract base class for all ingestion connectors."""

    @abstractmethod
    def validate_config(self, config: dict) -> bool:
        """Validate connector-specific config (tokens, IDs, scopes)."""

    @abstractmethod
    def list_files(self, config: dict, since: datetime | None = None) -> Iterator[RemoteFile]:
        """Yield RemoteFile entries discoverable for ingestion."""

    @abstractmethod
    def fetch_file_content(self, file_id: str, config: dict) -> bytes:
        """Return raw file bytes for a given remote file id."""
