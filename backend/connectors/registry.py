"""
Connector registry and manifest metadata.

Each connector entry describes capabilities and defaults for rate limits.
"""

CONNECTOR_REGISTRY = {
    "google_drive": {
        "id": "google_drive",
        "name": "Google Drive",
        "capabilities": ["incremental_sync", "binary_content"],
        "rate_limit_rpm": 600,  # default RPM throttle if not overridden
    },
    "notion": {
        "id": "notion",
        "name": "Notion",
        "capabilities": ["incremental_sync", "html_content"],
        "rate_limit_rpm": 60,
    },
    "web": {
        "id": "web",
        "name": "Web",
        "capabilities": ["crawl", "sitemap"],
        "rate_limit_rpm": 120,
    },
    "sftp": {
        "id": "sftp",
        "name": "SFTP",
        "capabilities": ["binary_content", "incremental_sync"],
        "rate_limit_rpm": 60,
    },
    "onedrive": {
        "id": "onedrive",
        "name": "OneDrive",
        "capabilities": ["binary_content", "incremental_sync"],
        "rate_limit_rpm": 120,
        "implementation": "microsoft",
        "target_type": "onedrive",
    },
    "sharepoint": {
        "id": "sharepoint",
        "name": "SharePoint",
        "capabilities": ["binary_content", "incremental_sync"],
        "rate_limit_rpm": 120,
        "implementation": "microsoft",
        "target_type": "sharepoint",
    },
    "dropbox": {
        "id": "dropbox",
        "name": "Dropbox",
        "capabilities": ["binary_content", "incremental_sync", "team_spaces"],
        "rate_limit_rpm": 720,  # Dropbox allows ~12 calls/sec baseline
    },
}


def get_connector_manifest(connector_type: str) -> dict | None:
    return CONNECTOR_REGISTRY.get(connector_type)
