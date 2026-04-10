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
        "capabilities": ["html_content"],
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
    "github": {
        "id": "github",
        "name": "GitHub",
        "capabilities": ["code_aware", "incremental_sync", "text_content"],
        "rate_limit_rpm": 80,  # 5000/hour = 83/min, use 80 for safety margin
    },
    "box": {
        "id": "box",
        "name": "Box",
        "capabilities": ["binary_content", "incremental_sync", "enterprise"],
        "rate_limit_rpm": 600,  # Business accounts: 1000/min, use 600 for safety
    },
    "s3": {
        "id": "s3",
        "name": "Amazon S3",
        "capabilities": ["binary_content", "incremental_sync", "glacier_aware"],
        "rate_limit_rpm": 1000,  # S3 has no rate limit, but we self-limit
        "auth_type": "form",  # IAM credentials, not OAuth
        "enterprise_only": True,  # Requires Enterprise plan
    },
}


def get_connector_manifest(connector_type: str) -> dict | None:
    return CONNECTOR_REGISTRY.get(connector_type)
