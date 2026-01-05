"""
Connector Registry for Unified Ingestion Pipeline.

This module provides a centralized registry for all data source connectors.
New connectors can be registered here or dynamically via register_connector().
"""

from typing import Dict, Type
from connectors.base import BaseConnector
from connectors.enhanced import EnhancedConnector
from connectors.drive import DriveConnector
from connectors.file_upload import FileUploadConnector

# Connector registry
CONNECTORS: Dict[str, Type[EnhancedConnector]] = {
    "file_upload": FileUploadConnector,
    "google_drive": DriveConnector,
    # Add more connectors here as they're migrated
}


def get_connector(connector_type: str) -> EnhancedConnector:
    """
    Get connector instance by type.
    
    Args:
        connector_type: Type identifier (e.g., 'file_upload', 'google_drive')
        
    Returns:
        Connector instance
        
    Raises:
        ValueError: If connector type is unknown
    """
    connector_class = CONNECTORS.get(connector_type)
    
    if not connector_class:
        raise ValueError(f"Unknown connector type: {connector_type}")
    
    return connector_class()


def register_connector(connector_type: str, connector_class: Type[EnhancedConnector]):
    """
    Register a new connector (for plugins or dynamic registration).
    
    Args:
        connector_type: Type identifier
        connector_class: Connector class (must extend EnhancedConnector)
    """
    if not issubclass(connector_class, EnhancedConnector):
        raise TypeError(f"Connector must extend EnhancedConnector")
    
    CONNECTORS[connector_type] = connector_class


def list_connectors() -> list[str]:
    """Get list of registered connector types."""
    return list(CONNECTORS.keys())
