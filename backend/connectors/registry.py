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
}


def get_connector_manifest(connector_type: str) -> dict | None:
    return CONNECTOR_REGISTRY.get(connector_type)
