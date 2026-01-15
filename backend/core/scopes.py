"""
Scope URI helpers.

Enforces canonical scope_id formats across connectors.
"""

from __future__ import annotations

from typing import Any, Dict
from urllib.parse import urlparse


def _require(metadata: Dict[str, Any], *keys: str) -> str:
    for key in keys:
        value = metadata.get(key)
        if value:
            return str(value)
    raise ValueError(f"Missing required metadata field(s): {', '.join(keys)}")


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
    return parsed.netloc.lower()


def build_scope_uri(source_type: str, metadata: Dict[str, Any]) -> str:
    """
    Build a canonical scope URI for a given source type.

    Supported formats:
    - GitHub: github://{org}/{repo}@{branch}
    - S3: s3://{bucket}/{prefix}
    - Box: box://folder/{folder_id}:{folder_name}
    - Dropbox: dropbox://{namespace_id}/{path}
    - Google Drive: gdrive://{drive_id}/{folder_id}:{name}
    - Notion: notion://{workspace_id}/{page_id}:{title}
    - Web: web://{domain}
    """
    metadata = metadata or {}
    source_type = _normalize_source_type(source_type)

    if source_type == "github":
        repository = metadata.get("repository") or metadata.get("repo")
        if repository and "/" in repository:
            org, repo = repository.split("/", 1)
        else:
            org = _require(metadata, "org", "owner")
            repo = repository or _require(metadata, "repo", "repo_name", "name")
        branch = metadata.get("branch") or metadata.get("ref") or metadata.get("default_branch") or "main"
        return f"github://{org}/{repo}@{branch}"

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

    if source_type == "box":
        folder_id = _require(metadata, "folder_id", "parent_id")
        folder_name = _require(metadata, "folder_name", "parent_name", "root_folder_name")
        return f"box://folder/{folder_id}:{folder_name}"

    if source_type == "dropbox":
        namespace_id = _require(metadata, "namespace_id")
        path = _require(metadata, "path", "path_display", "path_lower")
        path = _normalize_path(path)
        return f"dropbox://{namespace_id}/{path}"

    if source_type in {"google_drive", "gdrive"}:
        drive_id = _require(metadata, "drive_id", "shared_drive_id")
        folder_id = _require(metadata, "folder_id", "parent_id")
        name = _require(metadata, "name", "folder_name")
        return f"gdrive://{drive_id}/{folder_id}:{name}"

    if source_type == "notion":
        workspace_id = _require(metadata, "workspace_id")
        page_id = _require(metadata, "page_id", "id")
        title = _require(metadata, "title", "name")
        return f"notion://{workspace_id}/{page_id}:{title}"

    if source_type == "web":
        url = metadata.get("url") or metadata.get("source_url")
        domain = _extract_domain(url)
        return f"web://{domain}"

    if source_type == "file_upload":
        storage_path = _require(metadata, "storage_path")
        return f"file_upload://{storage_path}"

    raise ValueError(f"Unsupported source_type for scope URI: {source_type}")
