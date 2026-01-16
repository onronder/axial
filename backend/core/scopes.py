"""
Scope URI helpers.

Enforces canonical scope_id formats across connectors.

This module is the SINGLE SOURCE OF TRUTH for scope URI generation.
All connectors MUST use build_scope_uri() to generate scope IDs.
"""

from __future__ import annotations

from typing import Any, Dict, Optional
from urllib.parse import urlparse

SCOPE_PREFIX_BY_PROVIDER: Dict[str, str] = {
    "box": "box://",
    "dropbox": "dropbox://",
    "file_upload": "upload://",
    "upload": "upload://",
    "github": "github://",
    "google_drive": "gdrive://",
    "drive": "gdrive://",
    "gdrive": "gdrive://",
    "notion": "notion://",
    "onedrive": "onedrive://",
    "s3": "s3://",
    "sftp": "sftp://",
    "sharepoint": "sharepoint://",
    "web": "web://",
}


def _require(metadata: Dict[str, Any], *keys: str) -> str:
    for key in keys:
        value = metadata.get(key)
        if value:
            return str(value)
    raise ValueError(f"Missing required metadata field(s): {', '.join(keys)}")


def _optional(metadata: Dict[str, Any], *keys: str) -> Optional[str]:
    """Get optional value from metadata, return None if not found."""
    for key in keys:
        value = metadata.get(key)
        if value:
            return str(value)
    return None


def _normalize_source_type(source_type: str) -> str:
    if not source_type:
        raise ValueError("source_type is required")
    return str(source_type).strip().lower().replace(" ", "_").replace("-", "_")


def _normalize_path(value: str) -> str:
    return str(value or "").strip().strip("/")


def _extract_domain(url: str) -> str:
    if not url:
        raise ValueError("Missing required metadata field(s): url")
    parsed = urlparse(url)
    if not parsed.netloc:
        parsed = urlparse(f"https://{url}")
    if not parsed.netloc:
        raise ValueError(f"Invalid URL for web scope: {url}")
    # Normalize: lowercase and strip www.
    domain = parsed.netloc.lower()
    if domain.startswith("www."):
        domain = domain[4:]
    return domain


def build_scope_uri(source_type: str, metadata: Dict[str, Any]) -> str:
    """
    Build a canonical scope URI for a given source type.
    
    THIS IS THE SINGLE SOURCE OF TRUTH FOR SCOPE URI GENERATION.
    All connectors MUST use this function.

    Supported formats:
    - GitHub: github://{org}/{repo}@{branch}
    - S3: s3://{bucket}/{prefix}
    - Box: box://folder/{folder_id}:{folder_name}
    - Dropbox: dropbox://{folder_id_or_path}
    - Google Drive: gdrive://{folder_id}
    - OneDrive: onedrive://{drive_id}/{item_id}
    - SharePoint: sharepoint://{drive_id}/{item_id}
    - Notion: notion://{page_id}
    - SFTP: sftp://{host}/{root_path}
    - Web: web://{domain}
    - File Upload: upload://{user_id}/manual
    """
    metadata = metadata or {}
    source_type = _normalize_source_type(source_type)

    # ==========================================================================
    # GitHub: github://{org}/{repo}@{branch}
    # ==========================================================================
    if source_type == "github":
        repository = metadata.get("repository") or metadata.get("repo")
        if repository and "/" in repository:
            org, repo = repository.split("/", 1)
        else:
            org = _require(metadata, "org", "owner")
            repo = repository or _require(metadata, "repo", "repo_name", "name")
        branch = metadata.get("branch") or metadata.get("ref") or metadata.get("default_branch") or "main"
        return f"github://{org}/{repo}@{branch}"

    # ==========================================================================
    # S3: s3://{bucket}/{prefix}
    # ==========================================================================
    if source_type == "s3":
        bucket = _require(metadata, "bucket", "bucket_name")
        prefix = metadata.get("prefix")
        if prefix is None:
            key = metadata.get("key") or metadata.get("object_key")
            prefix = _normalize_path(key.rsplit("/", 1)[0]) if key and "/" in key else ""
        prefix = _normalize_path(prefix)
        if prefix:
            return f"s3://{bucket}/{prefix}"
        return f"s3://{bucket}/"

    # ==========================================================================
    # Box: box://folder/{folder_id}:{folder_name}
    # ==========================================================================
    if source_type == "box":
        folder_id = _require(metadata, "folder_id", "parent_id")
        folder_name = _require(metadata, "folder_name", "parent_name", "root_folder_name")
        return f"box://folder/{folder_id}:{folder_name}"

    # ==========================================================================
    # Dropbox: dropbox://{folder_id_or_path}
    # ==========================================================================
    if source_type == "dropbox":
        # Support both old format (namespace_id/path) and new simplified format
        folder_id = _optional(metadata, "folder_id", "dropbox_id", "id")
        path = _optional(metadata, "path", "path_display", "path_lower")
        namespace_id = _optional(metadata, "namespace_id")
        
        if folder_id:
            return f"dropbox://{folder_id}"
        elif namespace_id and path:
            return f"dropbox://{namespace_id}/{_normalize_path(path)}"
        elif path:
            return f"dropbox://{_normalize_path(path)}"
        else:
            raise ValueError("Dropbox scope requires folder_id or path")

    # ==========================================================================
    # Google Drive: gdrive://{folder_id}
    # ==========================================================================
    if source_type in {"google_drive", "gdrive", "drive"}:
        folder_id = _require(metadata, "folder_id", "item_id", "file_id", "parent_id")
        return f"gdrive://{folder_id}"

    # ==========================================================================
    # OneDrive: onedrive://{drive_id}/{item_id}
    # ==========================================================================
    if source_type == "onedrive":
        drive_id = _require(metadata, "drive_id")
        item_id = _optional(metadata, "item_id", "folder_id") or "root"
        return f"onedrive://{drive_id}/{item_id}"

    # ==========================================================================
    # SharePoint: sharepoint://{drive_id}/{item_id}
    # ==========================================================================
    if source_type == "sharepoint":
        drive_id = _require(metadata, "drive_id")
        item_id = _optional(metadata, "item_id", "folder_id") or "root"
        return f"sharepoint://{drive_id}/{item_id}"

    # ==========================================================================
    # Notion: notion://{page_id}
    # ==========================================================================
    if source_type == "notion":
        page_id = _require(metadata, "page_id", "id", "workspace_id")
        return f"notion://{page_id}"

    # ==========================================================================
    # SFTP: sftp://{host}/{root_path}
    # ==========================================================================
    if source_type == "sftp":
        host = _require(metadata, "host", "hostname")
        root_path = _optional(metadata, "root_path", "path")
        if root_path:
            return f"sftp://{host}/{_normalize_path(root_path)}"
        return f"sftp://{host}"

    # ==========================================================================
    # Web: web://{domain}
    # ==========================================================================
    if source_type == "web":
        url = metadata.get("url") or metadata.get("source_url")
        domain = _extract_domain(url)
        return f"web://{domain}"

    # ==========================================================================
    # File Upload: upload://{user_id}/manual
    # ==========================================================================
    if source_type in {"file_upload", "upload"}:
        user_id = _require(metadata, "user_id")
        return f"upload://{user_id}/manual"

    raise ValueError(f"Unsupported source_type for scope URI: {source_type}")


def infer_scope_type(scope_id: str) -> str:
    """
    Infer the scope type from a scope URI.
    
    Returns the source type string for identity type inference.
    """
    if not scope_id:
        return "unknown"
    
    scheme = scope_id.split("://")[0].lower() if "://" in scope_id else ""
    
    type_map = {
        "github": "github",
        "s3": "s3",
        "box": "box",
        "dropbox": "dropbox",
        "gdrive": "google_drive",
        "drive": "google_drive",
        "onedrive": "onedrive",
        "sharepoint": "sharepoint",
        "notion": "notion",
        "sftp": "sftp",
        "web": "web",
        "upload": "file_upload",
        "file_upload": "file_upload",
    }
    
    return type_map.get(scheme, "unknown")
