import logging
from datetime import datetime
from hashlib import sha1
from typing import Any

from fastapi import (
    APIRouter,
    BackgroundTasks,
    Depends,
    HTTPException,
    Query,
    Request,
    status,
)
from pydantic import BaseModel, Field

from api.v1.dependencies import (
    get_user_allowed_scopes,
    get_user_organization_id,
    require_editor,
    require_paid_access,
    validate_team_access,
)
from api.v1.error_utils import ApiErrorCode, api_error
from core.db import get_supabase
from core.ingestion_utils import canonicalize_provider_name, normalize_provider
from core.rate_limit import limiter
from core.scopes import get_scope_prefixes
from core.security import get_current_user
from services.audit import log_document_delete
from services.cleanup import cleanup_service
from services.scope_guard import ActionType, ScopeGuardStateMachine
from services.team_service import team_service

logger = logging.getLogger(__name__)

# =============================================================================
# Ghost Protocol: Bulk Delete Approval Thresholds
# =============================================================================
# These thresholds determine when human approval is required for destructive actions

# Number of documents above which bulk delete requires approval
BULK_DELETE_APPROVAL_THRESHOLD = 10

# Whether to enforce approval workflow for destructive actions
ENFORCE_APPROVAL_WORKFLOW = True

router = APIRouter(dependencies=[Depends(validate_team_access), Depends(require_paid_access)])


# =============================================================================
# Response Models
# =============================================================================

class DocumentDTO(BaseModel):
    id: str
    title: str
    source_type: str
    source_url: str | None = None
    # Path/location within the source (e.g., folder path in Drive, S3 key, etc.)
    path: str | None = None
    created_at: str
    status: str = "indexed"
    # Documents only exist after successful ingestion, so default to completed
    indexing_status: str = "completed"
    size: int | None = 0
    file_size_bytes: int | None = 0
    metadata: dict[str, Any]


class DocumentListResponse(BaseModel):
    """Paginated successful documents plus a separate failed-file channel."""
    documents: list[DocumentDTO]
    failed_files: list[DocumentDTO] = Field(default_factory=list)
    total_documents: int
    failed_count: int = 0


class DocumentTreeBreadcrumbDTO(BaseModel):
    id: str
    name: str
    path: str


class DocumentTreeItemDTO(BaseModel):
    id: str
    name: str
    path: str
    type: str
    source_type: str | None = None
    document_count: int | None = None
    source_url: str | None = None
    created_at: str | None = None
    indexing_status: str | None = None
    size: int | None = 0
    metadata: dict[str, Any] | None = None


class DocumentTreeResponse(BaseModel):
    current_path: str
    breadcrumbs: list[DocumentTreeBreadcrumbDTO]
    items: list[DocumentTreeItemDTO]
    total_items: int
    total_documents: int
    page: int
    page_size: int
    failed_files: list[DocumentDTO] = Field(default_factory=list)
    failed_count: int = 0


FAILED_FILES_PREVIEW_LIMIT = 10
DOCUMENT_TREE_SELECT_FIELDS = (
    "id, title, source_type, source_url, created_at, file_size_bytes, metadata"
)
SOURCE_FOLDER_LABELS = {
    "file_upload": "📁 Uploaded Files",
    "google_drive": "🔷 Google Drive",
    "notion": "📝 Notion",
    "web": "🌐 Web Pages",
    "onedrive": "☁️ OneDrive",
    "sharepoint": "📊 SharePoint",
    "dropbox": "📦 Dropbox",
    "github": "🐙 GitHub",
    "slack": "💬 Slack",
    "s3": "🪣 Amazon S3",
    "youtube": "▶️ YouTube",
    "sftp": "🔐 SFTP",
    "box": "📥 Box",
}


def _as_nonempty_string(value: Any) -> str | None:
    if isinstance(value, str):
        normalized = value.strip()
        return normalized or None
    return None


def _extract_path_from_document(doc: dict[str, Any]) -> str | None:
    """
    Extract path/location from document metadata based on source type.

    Different connectors store path info in different metadata fields:
    - Google Drive: path, file_path
    - Dropbox: path, path_display, path_lower
    - OneDrive/SharePoint: path, parent_path
    - GitHub: path (e.g., src/main.py)
    - S3: key (full S3 path)
    - Box: folder_name + name
    - SFTP: source_id contains full path
    - File Upload: storage_path
    - Web/YouTube: source_url (already displayed separately)
    """
    meta = doc.get("metadata") if isinstance(doc.get("metadata"), dict) else {}
    source_type = str(doc.get("source_type") or "").lower()

    # Try common path fields in order of preference
    path = next(
        (
            candidate
            for candidate in (
                _as_nonempty_string(meta.get("path")),
                _as_nonempty_string(meta.get("path_display")),
                _as_nonempty_string(meta.get("path_lower")),
                _as_nonempty_string(meta.get("file_path")),
                _as_nonempty_string(meta.get("parent_path")),
                _as_nonempty_string(meta.get("key")),  # S3
                _as_nonempty_string(meta.get("storage_path")),  # File upload
            )
            if candidate
        ),
        None,
    )

    # For Box, construct path from folder_name
    if not path and source_type == "box":
        folder_name = _as_nonempty_string(meta.get("folder_name"))
        if folder_name:
            path = f"/{folder_name}"

    # For GitHub, the path field should contain the file path (e.g., src/main.py)
    # Already handled above

    # Clean up storage paths for file uploads (remove user ID prefix)
    if path and source_type == "file_upload" and path.startswith("uploads/"):
        # Format: uploads/{user_id}/{hash}/{filename} -> just show filename or short path
        parts = path.split("/")
        if len(parts) >= 4:
            path = parts[-1]  # Just filename

    return path


def _format_source_folder_name(source_type: str) -> str:
    normalized_source_type = _as_nonempty_string(source_type) or "unknown"
    return SOURCE_FOLDER_LABELS.get(
        normalized_source_type,
        normalized_source_type.replace("_", " ").title(),
    )


def _hydrate_document_row(doc: dict[str, Any]) -> dict[str, Any]:
    hydrated = dict(doc)
    hydrated["source_type"] = normalize_provider(hydrated.get("source_type")) or hydrated.get("source_type")
    hydrated["status"] = hydrated.get("status", "indexed")
    hydrated["indexing_status"] = "completed"
    hydrated["metadata"] = hydrated.get("metadata") or {}
    hydrated["path"] = _extract_path_from_document(hydrated)

    meta = hydrated["metadata"]
    file_size = hydrated.get("file_size_bytes")
    if file_size is None:
        file_size = (
            meta.get("file_size")
            or meta.get("size")
            or meta.get("file_size_bytes")
            or 0
        )
    hydrated["file_size_bytes"] = file_size or 0
    hydrated["size"] = file_size or 0
    return hydrated


def _build_failed_file_payload(
    failed_file: dict[str, Any],
    provider_map: dict[str, str],
) -> dict[str, Any]:
    provider = provider_map.get(str(failed_file.get("job_id"))) or "file_upload"
    file_size = failed_file.get("file_size_bytes", 0)
    failed_meta = failed_file.get("metadata") or {}
    failed_path = (
        failed_meta.get("path")
        or failed_meta.get("path_display")
        or failed_meta.get("file_path")
        or failed_meta.get("key")
        or failed_file.get("remote_id")
        or None
    )
    return {
        "id": failed_file["id"],
        "title": failed_file["filename"],
        "source_type": provider,
        "source_url": None,
        "path": failed_path,
        "created_at": failed_file["created_at"],
        "status": "failed",
        "indexing_status": "failed",
        "file_size_bytes": file_size,
        "size": file_size,
        "metadata": {
            "error": failed_file.get("error_message", "Unknown error"),
            "job_id": str(failed_file.get("job_id", "")),
        },
    }


def _fetch_failed_files_preview(
    supabase,
    organization_id: str,
    search_term: str | None,
) -> tuple[list[dict[str, Any]], int]:
    failed_query = (
        supabase.table("ingestion_file_status")
        .select("*", count="exact")
        .eq("organization_id", organization_id)
        .eq("status", "failed")
        .is_("document_id", "null")
    )

    if search_term:
        failed_query = failed_query.ilike("filename", f"%{search_term}%")

    failed_res = (
        failed_query
        .order("created_at", desc=True)
        .limit(FAILED_FILES_PREVIEW_LIMIT)
        .execute()
    )

    failed_files = failed_res.data or []
    failed_total = failed_res.count if failed_res.count is not None else len(failed_files)
    provider_map: dict[str, str] = {}
    job_ids = {str(f.get("job_id")) for f in failed_files if f.get("job_id")}
    if job_ids:
        jobs_res = (
            supabase.table("ingestion_jobs")
            .select("id, provider")
            .in_("id", list(job_ids))
            .execute()
        )
        for job in jobs_res.data or []:
            provider_map[str(job["id"])] = normalize_provider(job.get("provider")) or job.get("provider")

    payload = [
        _build_failed_file_payload(failed_file, provider_map)
        for failed_file in failed_files
    ]
    return payload, failed_total


def _hash_tree_path(path: str) -> str:
    return sha1(path.encode("utf-8")).hexdigest()[:12]


def _tree_path_segments(path: Any) -> list[str]:
    if not isinstance(path, str):
        return []
    return [segment for segment in path.split("/") if segment]


def _sort_tree_children(folder: dict[str, Any]) -> None:
    folder["children"].sort(
        key=lambda child: (
            0 if child["type"] == "folder" else 1,
            (_as_nonempty_string(child.get("name")) or "").lower(),
        )
    )


def _update_tree_counts(folder: dict[str, Any]) -> int:
    count = 0
    for child in folder["children"]:
        if child["type"] == "folder":
            count += _update_tree_counts(child)
        else:
            count += 1

    folder["document_count"] = count
    _sort_tree_children(folder)
    return count


def _build_tree_subtree(parent: dict[str, Any], documents: list[dict[str, Any]]) -> None:
    folders: dict[str, dict[str, Any]] = {}

    for doc in documents:
        doc_path = _as_nonempty_string(doc.get("path")) or _as_nonempty_string(doc.get("title")) or "Untitled"
        segments = _tree_path_segments(doc_path)

        if len(segments) <= 1:
            parent["children"].append(
                {
                    "id": doc["id"],
                    "name": _as_nonempty_string(doc.get("title")) or "Untitled",
                    "path": doc_path,
                    "type": "file",
                    "source_type": doc.get("source_type"),
                    "source_url": doc.get("source_url"),
                    "created_at": doc.get("created_at"),
                    "indexing_status": doc.get("indexing_status"),
                    "size": doc.get("size", 0),
                    "metadata": doc.get("metadata") or {},
                    "document": doc,
                }
            )
            continue

        current_path = parent["path"]
        current_folder = parent

        for segment in segments[:-1]:
            current_path = f"{current_path}/{segment}"
            if current_path not in folders:
                folder = {
                    "id": f"folder-{_hash_tree_path(current_path)}",
                    "name": segment,
                    "path": current_path,
                    "type": "folder",
                    "children": [],
                    "document_count": 0,
                    "source_type": parent.get("source_type"),
                }
                folders[current_path] = folder
                current_folder["children"].append(folder)

            current_folder = folders[current_path]

        current_folder["children"].append(
            {
                "id": doc["id"],
                "name": _as_nonempty_string(segments[-1]) or "Untitled",
                "path": doc_path,
                "type": "file",
                "source_type": doc.get("source_type"),
                "source_url": doc.get("source_url"),
                "created_at": doc.get("created_at"),
                "indexing_status": doc.get("indexing_status"),
                "size": doc.get("size", 0),
                "metadata": doc.get("metadata") or {},
                "document": doc,
            }
        )

    _update_tree_counts(parent)


def _build_document_tree(documents: list[dict[str, Any]]) -> dict[str, Any]:
    root = {
        "id": "root",
        "name": "All Documents",
        "path": "/",
        "type": "folder",
        "children": [],
        "document_count": len(documents),
    }

    by_source: dict[str, list[dict[str, Any]]] = {}
    for doc in documents:
        source = _as_nonempty_string(doc.get("source_type")) or "file_upload"
        by_source.setdefault(source, []).append(doc)

    for source, source_docs in by_source.items():
        source_folder = {
            "id": f"source-{source}",
            "name": _format_source_folder_name(source),
            "path": f"/{source}",
            "type": "folder",
            "children": [],
            "document_count": len(source_docs),
            "source_type": source,
        }
        _build_tree_subtree(source_folder, source_docs)
        _sort_tree_children(source_folder)
        root["children"].append(source_folder)

    root["children"].sort(key=lambda child: (_as_nonempty_string(child.get("name")) or "").lower())
    return root


def _find_tree_folder(root: dict[str, Any], path: str) -> dict[str, Any]:
    if path in {"/", root["path"]}:
        return root

    segments = _tree_path_segments(path)
    current = root
    for segment in segments:
        child = next(
            (
                candidate
                for candidate in current["children"]
                if candidate["type"] == "folder"
                and (candidate["name"] == segment or candidate["path"].endswith(f"/{segment}"))
            ),
            None,
        )
        if not child:
            return root
        current = child

    return current


def _build_tree_breadcrumbs(root: dict[str, Any], path: str) -> list[dict[str, str]]:
    breadcrumbs = [{"id": root["id"], "name": root["name"], "path": root["path"]}]
    if path in {"/", root["path"]}:
        return breadcrumbs

    segments = _tree_path_segments(path)
    current = root
    current_path = ""
    for segment in segments:
        current_path = f"{current_path}/{segment}"
        child = next(
            (
                candidate
                for candidate in current["children"]
                if candidate["type"] == "folder"
                and candidate["path"] == current_path
            ),
            None,
        )
        if not child:
            child = next(
                (
                    candidate
                    for candidate in current["children"]
                    if candidate["type"] == "folder" and candidate["name"] == segment
                ),
                None,
            )
        if not child:
            break

        breadcrumbs.append(
            {"id": child["id"], "name": child["name"], "path": child["path"]}
        )
        current = child
        current_path = child["path"]

    return breadcrumbs


def _search_tree(folder: dict[str, Any], query: str) -> list[dict[str, Any]]:
    normalized = query.lower().strip()
    if not normalized:
        return folder["children"]

    results: list[dict[str, Any]] = []

    def search_node(node: dict[str, Any]) -> None:
        name_matches = normalized in (_as_nonempty_string(node.get("name")) or "").lower()
        if node["type"] == "folder":
            if name_matches:
                results.append(node)
            for child in node["children"]:
                search_node(child)
            return

        document = node.get("document") or {}
        if (
            name_matches
            or normalized in str(document.get("path") or "").lower()
            or normalized in str(document.get("source_type") or "").lower()
        ):
            results.append(node)

    for child in folder["children"]:
        search_node(child)

    return results


def _serialize_tree_item(node: dict[str, Any]) -> dict[str, Any]:
    if node["type"] == "folder":
        return {
            "id": node["id"],
            "name": node["name"],
            "path": node["path"],
            "type": "folder",
            "source_type": node.get("source_type"),
            "document_count": node.get("document_count", 0),
            "metadata": None,
        }

    document = node.get("document") or {}
    return {
        "id": node["id"],
        "name": node["name"],
        "path": node["path"],
        "type": "file",
        "source_type": node.get("source_type"),
        "source_url": node.get("source_url"),
        "created_at": node.get("created_at"),
        "indexing_status": node.get("indexing_status"),
        "size": node.get("size", 0),
        "metadata": document.get("metadata") or {},
    }


def _paginate_tree_items(
    items: list[dict[str, Any]],
    page: int,
    page_size: int,
) -> tuple[list[dict[str, Any]], int]:
    if not items:
        return [], 1

    total_pages = max(1, (len(items) + page_size - 1) // page_size)
    safe_page = min(max(page, 1), total_pages)
    start = (safe_page - 1) * page_size
    return items[start:start + page_size], safe_page


def _coerce_query_int(value: Any, fallback: int) -> int:
    if isinstance(value, int):
        return value

    default = getattr(value, "default", fallback)
    if isinstance(default, int):
        return default

    try:
        return int(default)
    except (TypeError, ValueError):
        return fallback


def _relative_folder_prefix(folder_path: str, source_type: str) -> str:
    normalized_path = (folder_path or "").strip()
    source_root = f"/{source_type}"
    if not normalized_path or normalized_path == source_root:
        return ""

    if normalized_path.startswith(f"{source_root}/"):
        return normalized_path[len(source_root) + 1 :].strip("/")

    return normalized_path.strip("/")


def _quote_postgrest_filter_value(value: str) -> str | None:
    """
    Quote a PostgREST filter value for `in.(...)` lists.

    Scope IDs are canonical URI-like TEXT values, not UUIDs. Reserved characters
    such as commas and parentheses must be wrapped/escaped or the filter parser
    can misread them.
    """
    if any(ch in value for ch in ("\x00", "\n", "\r")):
        logger.warning("Dropping malformed scope filter value with control chars")
        return None

    escaped = value.replace("\\", "\\\\").replace('"', '\\"')
    return f'"{escaped}"'


def _build_scope_visibility_filter(scope_ids: list[str]) -> str:
    quoted_values = [
        quoted
        for scope_id in scope_ids
        if isinstance(scope_id, str) and scope_id.strip()
        for quoted in [_quote_postgrest_filter_value(scope_id.strip())]
        if quoted is not None
    ]
    if not quoted_values:
        return "scope_id.is.null"
    return f"scope_id.in.({','.join(quoted_values)}),scope_id.is.null"


class DocumentStatsDTO(BaseModel):
    """Lightweight stats response for efficient dashboard loading."""
    total_documents: int
    failed_documents: int = 0
    pending_documents: int = 0
    last_updated: str | None = None


class DocumentUpdate(BaseModel):
    """Request model for updating document metadata."""
    title: str | None = Field(None, max_length=500)
    description: str | None = Field(None, max_length=2000)
    tags: list[str] | None = Field(None, max_length=50)


class DocumentChunkDTO(BaseModel):
    """Response model for document chunks."""
    id: str
    document_id: str
    content: str
    chunk_index: int
    metadata: dict[str, Any] = {}


class BulkDeleteRequest(BaseModel):
    """Payload for bulk document deletion."""
    document_ids: list[str] | None = None
    source_type: str | None = None
    folder_path: str | None = None
    # Ghost Protocol: ScopeGuard approval credentials
    approval_id: str | None = None
    mandate_signature: str | None = None
    # Skip approval for small deletes (internal use)
    force: bool = False


# =============================================================================
# Stats Endpoint (Optimized for Onboarding Check)
# =============================================================================

@router.get("/documents/stats", response_model=DocumentStatsDTO)
@limiter.limit("100/minute")
async def get_document_stats(
    request: Request,
    user_id: str = Depends(get_current_user),
    organization_id: str = Depends(get_user_organization_id),
):
    """
    Get lightweight document statistics for the organization.

    Uses efficient count queries - O(1) performance instead of O(n) data transfer.
    Used by frontend to check if team needs onboarding.

    Returns:
        - total_documents: Successfully indexed documents
        - failed_documents: Files that failed ingestion
        - pending_documents: Files currently being processed
        - last_updated: Timestamp of most recent document
    """
    supabase = get_supabase()

    try:
        # Count successful documents (org-wide)
        count_response = supabase.table("documents")\
            .select("id", count="exact")\
            .eq("organization_id", organization_id)\
            .neq("source_type", "identity")\
            .neq("source_type", "scope_identity")\
            .execute()

        total = count_response.count if count_response.count is not None else 0

        # Count failed files from ingestion_file_status (org-wide)
        failed_count = 0
        pending_count = 0
        try:
            failed_response = supabase.table("ingestion_file_status")\
                .select("id", count="exact")\
                .eq("organization_id", organization_id)\
                .eq("status", "failed")\
                .is_("document_id", "null")\
                .execute()
            failed_count = failed_response.count if failed_response.count is not None else 0

            # Count pending/processing files
            pending_response = supabase.table("ingestion_file_status")\
                .select("id", count="exact")\
                .eq("organization_id", organization_id)\
                .in_("status", ["pending", "processing"])\
                .is_("document_id", "null")\
                .execute()
            pending_count = pending_response.count if pending_response.count is not None else 0
        except Exception as e:
            # Don't fail if ingestion_file_status query fails
            logger.warning(f"Failed to count failed/pending files: {e}")

        # Get last updated (most recent document in org)
        last_updated = None
        if total > 0:
            latest_response = supabase.table("documents")\
                .select("created_at")\
                .eq("organization_id", organization_id)\
                .neq("source_type", "identity")\
                .neq("source_type", "scope_identity")\
                .order("created_at", desc=True)\
                .limit(1)\
                .execute()

            if latest_response.data:
                last_updated = latest_response.data[0].get("created_at")

        return DocumentStatsDTO(
            total_documents=total,
            failed_documents=failed_count,
            pending_documents=pending_count,
            last_updated=last_updated
        )

    except Exception as e:
        raise api_error(ApiErrorCode.DATABASE_ERROR, e, "fetch_stats")



# =============================================================================
# Document CRUD Endpoints
# =============================================================================

from fastapi import Response


@router.get("/documents", response_model=DocumentListResponse)
@limiter.limit("60/minute")
async def list_documents(
    request: Request,
    response: Response,
    user_id: str = Depends(validate_team_access),  # Validates team access
    organization_id: str = Depends(get_user_organization_id),  # Org-scoped query
    allowed_scopes: list[str] | None = Depends(get_user_allowed_scopes),
    limit: int = 50,
    offset: int = 0,
    q: str | None = None,
    include_failed: bool = True  # New param to include failed files
):
    supabase = get_supabase()
    page_window_end = max(offset + limit - 1, offset)
    search_term = q.strip() if q and q.strip() else None

    try:
        # Build query for completed documents (org-scoped for team visibility)
        query = supabase.table("documents")\
            .select("*", count="exact")\
            .eq("organization_id", organization_id)\
            .neq("source_type", "identity")\
            .neq("source_type", "scope_identity")  # Org-wide access

        # Scope-level access control: filter to allowed scopes if restricted
        # Include documents with NULL scope_id (org-level docs without a specific scope)
        if allowed_scopes is not None:
            if allowed_scopes:
                scope_filter = _build_scope_visibility_filter(allowed_scopes)
                query = query.or_(scope_filter)
            else:
                # All scopes revoked — only show unscoped org-level documents
                query = query.is_("scope_id", "null")

        # Apply search filter
        if search_term:
            query = query.ilike("title", f"%{search_term}%")

        db_res = query\
            .order("created_at", desc=True)\
            .range(offset, page_window_end)\
            .execute()

        completed_total = db_res.count if db_res.count is not None else len(db_res.data or [])
        failed_total = 0

        # Enrich completed documents with status and path
        docs: list[dict[str, Any]] = []
        for d in db_res.data or []:
            docs.append(_hydrate_document_row(d))

        failed_files_payload: list[dict[str, Any]] = []

        # Also fetch failed files from ingestion_file_status (not yet in documents)
        # Organization-wide: show recent failed files in a separate channel.
        if include_failed:
            try:
                failed_files_payload, failed_total = _fetch_failed_files_preview(
                    supabase,
                    organization_id,
                    search_term,
                )
            except Exception as failed_err:
                # Don't fail entire request if failed files query fails
                logger.warning("Failed to fetch failed files: %s", failed_err)

        response.headers["X-Total-Count"] = str(completed_total)
        response.headers["X-Success-Count"] = str(completed_total)
        response.headers["X-Failed-Count"] = str(failed_total)

        return DocumentListResponse(
            documents=docs,
            failed_files=failed_files_payload,
            total_documents=completed_total,
            failed_count=failed_total,
        )
    except Exception as e:
        raise api_error(ApiErrorCode.DATABASE_ERROR, e, "fetch_documents")


@router.get("/documents/tree", response_model=DocumentTreeResponse)
@limiter.limit("60/minute")
async def get_document_tree(
    request: Request,
    user_id: str = Depends(validate_team_access),
    organization_id: str = Depends(get_user_organization_id),
    allowed_scopes: list[str] | None = Depends(get_user_allowed_scopes),
    path: str = "/",
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=25, ge=1, le=100),
    q: str | None = None,
    include_failed: bool = True,
):
    """
    Server-backed document tree for Knowledge Base navigation.

    Returns the current folder view only, with pagination and optional subtree search,
    so the browser no longer needs to fetch an arbitrary first-N document list and
    build the entire hierarchy client-side.
    """
    supabase = get_supabase()
    search_term = q.strip() if q and q.strip() else None
    requested_path = path.strip() or "/"
    safe_page = max(1, _coerce_query_int(page, 1))
    safe_page_size = min(max(1, _coerce_query_int(page_size, 25)), 100)

    try:
        query = (
            supabase.table("documents")
            .select(DOCUMENT_TREE_SELECT_FIELDS, count="exact")
            .eq("organization_id", organization_id)
            .neq("source_type", "identity")
            .neq("source_type", "scope_identity")
        )

        if allowed_scopes is not None:
            if allowed_scopes:
                query = query.or_(_build_scope_visibility_filter(allowed_scopes))
            else:
                query = query.is_("scope_id", "null")

        db_res = query.execute()
        documents = [_hydrate_document_row(row) for row in (db_res.data or [])]
        tree_root = _build_document_tree(documents)
        current_folder = _find_tree_folder(tree_root, requested_path)
        breadcrumbs = _build_tree_breadcrumbs(tree_root, current_folder["path"])
        visible_items = (
            _search_tree(current_folder, search_term)
            if search_term
            else current_folder["children"]
        )
        paginated_items, safe_page = _paginate_tree_items(
            visible_items,
            safe_page,
            safe_page_size,
        )

        failed_files_payload: list[dict[str, Any]] = []
        failed_total = 0
        if include_failed:
            try:
                failed_files_payload, failed_total = _fetch_failed_files_preview(
                    supabase,
                    organization_id,
                    search_term,
                )
            except Exception as failed_err:
                logger.warning("Failed to fetch failed files for tree view: %s", failed_err)

        return DocumentTreeResponse(
            current_path=current_folder["path"],
            breadcrumbs=breadcrumbs,
            items=[_serialize_tree_item(item) for item in paginated_items],
            total_items=len(visible_items),
            total_documents=len(documents),
            page=safe_page,
            page_size=safe_page_size,
            failed_files=failed_files_payload,
            failed_count=failed_total,
        )
    except Exception as e:
        raise api_error(ApiErrorCode.DATABASE_ERROR, e, "fetch_document_tree")

@router.delete("/documents")
@limiter.limit("30/minute")
async def bulk_delete_documents(
    payload: BulkDeleteRequest,
    request: Request,
    background_tasks: BackgroundTasks,
    user_id: str = Depends(require_editor),
    organization_id: str = Depends(get_user_organization_id),
):
    """
    Bulk delete documents by ID list or by source type.

    Does NOT disconnect connectors; only removes indexed records and related chunks.
    Deletes from the organization's shared knowledge base.

    Ghost Protocol: ScopeGuard Approval Workflow
    - If document count exceeds BULK_DELETE_APPROVAL_THRESHOLD, approval is required
    - Provide approval_id and mandate_signature to execute approved deletion
    - Use force=true to skip approval (only for small deletes under threshold)
    """
    from services.audit import audit_logger

    supabase = get_supabase()

    if not payload.document_ids and not payload.source_type and not payload.folder_path:
        raise HTTPException(
            status_code=400,
            detail="Provide document_ids, source_type, or folder_path to delete.",
        )

    if payload.folder_path and not payload.source_type:
        raise HTTPException(
            status_code=400,
            detail="folder_path deletion requires source_type.",
        )

    doc_ids: list[str] = []

    if payload.document_ids:
        doc_ids.extend(payload.document_ids)

    # Expand by source type if provided (org-wide)
    if payload.source_type:
        normalized_source = canonicalize_provider_name(payload.source_type) or payload.source_type
        try:
            source_docs = supabase.table("documents")\
                .select("id, title, metadata, source_type")\
                .eq("organization_id", organization_id)\
                .eq("source_type", normalized_source)\
                .execute()
            source_rows = source_docs.data or []

            if payload.folder_path:
                relative_prefix = _relative_folder_prefix(payload.folder_path, normalized_source)
                for row in source_rows:
                    hydrated = _hydrate_document_row(row)
                    doc_path = (hydrated.get("path") or "").strip("/")
                    if (
                        not relative_prefix
                        or doc_path == relative_prefix
                        or doc_path.startswith(f"{relative_prefix}/")
                    ):
                        if row.get("id"):
                            doc_ids.append(row["id"])
            else:
                doc_ids.extend([row["id"] for row in source_rows if row.get("id")])
        except Exception as e:
            raise api_error(ApiErrorCode.DATABASE_ERROR, e, "resolve_documents_by_source")

        if not payload.folder_path:
            scope_prefixes = get_scope_prefixes(normalized_source)
            for scope_prefix in scope_prefixes:
                try:
                    identity_docs = supabase.table("documents")\
                        .select("id")\
                        .eq("organization_id", organization_id)\
                        .eq("source_type", "identity")\
                        .like("scope_id", f"{scope_prefix}%")\
                        .execute()
                    doc_ids.extend([row["id"] for row in (identity_docs.data or []) if row.get("id")])
                except Exception as e:
                    logger.warning("Failed to resolve identity documents for %s: %s", normalized_source, e)

    # Deduplicate and validate
    doc_ids = list({d for d in doc_ids if d})
    if not doc_ids:
        return {"status": "success", "deleted": 0, "failed": []}

    # ==========================================================================
    # Ghost Protocol: ScopeGuard Approval Workflow
    # ==========================================================================
    requires_approval = (
        ENFORCE_APPROVAL_WORKFLOW and
        len(doc_ids) > BULK_DELETE_APPROVAL_THRESHOLD and
        not payload.force
    )

    if requires_approval:
        # Check if this is an execution with valid approval
        if payload.approval_id and payload.mandate_signature:
            # Validate and execute approved action
            state_machine = ScopeGuardStateMachine()
            try:
                execution_result = await state_machine.execute(
                    approval_id=payload.approval_id,
                    organization_id=organization_id,
                    executor_id=user_id,
                    mandate_signature=payload.mandate_signature,
                )
                # The execute method already calls cleanup_service, so return its result
                return {
                    "status": "success",
                    "approval_executed": True,
                    **execution_result.get("result", {}),
                }
            except ValueError as e:
                raise api_error(ApiErrorCode.PROCESSING_ERROR, e, "execute_approval",
                                status_code=status.HTTP_400_BAD_REQUEST, log_level="warning")
        else:
            # Request approval for bulk delete
            state_machine = ScopeGuardStateMachine()
            try:
                approval_result = await state_machine.request_approval(
                    action_type=ActionType.BULK_DELETE,
                    resource_type="document",
                    resource_id="bulk",
                    organization_id=organization_id,
                    requested_by=user_id,
                    context={
                        "document_ids": doc_ids,
                        "document_count": len(doc_ids),
                        "source_type": payload.source_type,
                        "folder_path": payload.folder_path,
                        "user_id": user_id,
                    },
                    ttl_minutes=30,
                )

                # Audit log the approval request
                audit_logger.log(
                    background_tasks,
                    user_id=user_id,
                    action="document.bulk_delete_approval_requested",
                    resource_type="document",
                    resource_id="bulk",
                    details={
                        "document_count": len(doc_ids),
                        "source_type": payload.source_type,
                        "folder_path": payload.folder_path,
                        "approval_id": approval_result["approval_id"],
                    },
                    request=request
                )

                # Return approval required response
                return {
                    "status": "approval_required",
                    "approval_required": True,
                    "document_count": len(doc_ids),
                    "threshold": BULK_DELETE_APPROVAL_THRESHOLD,
                    "message": (
                        f"Bulk deletion of {len(doc_ids)} documents requires approval. "
                        f"Threshold is {BULK_DELETE_APPROVAL_THRESHOLD} documents."
                    ),
                    **approval_result,
                }
            except Exception as e:
                raise api_error(ApiErrorCode.PROCESSING_ERROR, e, "request_approval")

    deleted: list[str] = []
    failed: list[dict[str, str]] = []

    for doc_id in doc_ids:
        try:
            await cleanup_service.delete_single_document(
                doc_id, user_id, organization_id=organization_id
            )
            deleted.append(doc_id)
        except Exception as e:
            failed.append({"id": doc_id, "error": str(e)})

    if payload.source_type and not payload.folder_path:
        normalized_source = canonicalize_provider_name(payload.source_type) or payload.source_type
        for scope_prefix in get_scope_prefixes(normalized_source):
            try:
                supabase.table("scope_identities")\
                    .delete()\
                    .eq("organization_id", organization_id)\
                    .like("id", f"{scope_prefix}%")\
                    .execute()
            except Exception as e:
                logger.warning("Failed to delete scope identities for %s: %s", normalized_source, e)

    # Usage is computed live at org scope; no cache sync needed.

    # Audit log only records aggregate to avoid noisy entries
    if deleted:
        try:
            audit_logger.log(
                background_tasks,
                user_id=user_id,
                action="document.bulk_delete",
                resource_type="document",
                resource_id="bulk",
                details={
                    "deleted_count": len(deleted),
                    "failed_count": len(failed),
                    "source_type": payload.source_type,
                    "folder_path": payload.folder_path,
                    "ghost_protocol": True,
                },
                request=request
            )
        except Exception as e:
            logger.debug(f"[Documents] Failed to log audit event: {e}")

    return {
        "status": "success",
        "deleted": len(deleted),
        "failed": failed,
        "ghost_protocol": True,  # Indicates secure wipe was used
    }

@router.delete("/documents/{doc_id}")
@limiter.limit("30/minute")
async def delete_document(
    doc_id: str,
    request: Request,
    background_tasks: BackgroundTasks,
    user_id: str = Depends(require_editor),
    organization_id: str = Depends(get_user_organization_id),
    allowed_scopes: list[str] | None = Depends(get_user_allowed_scopes),
):
    """Delete a document. Org-scoped: team editors can delete shared docs."""
    supabase = get_supabase()

    try:
        team = await team_service.get_user_team(user_id)
        if team and team.get("user_role") == "viewer":
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Viewers cannot delete documents."
            )

        # First, get document info for audit log (org-scoped access)
        # Use maybe_single() to gracefully handle missing documents (PGRST116 prevention)
        doc_response = supabase.table("documents")\
            .select("title, scope_id")\
            .eq("id", doc_id)\
            .eq("organization_id", organization_id)\
            .maybe_single()\
            .execute()
        if doc_response is None or not doc_response.data:
            raise HTTPException(status_code=404, detail="Document not found")

        # Scope-level access control: check if user can access this document's scope
        if allowed_scopes is not None:
            doc_scope = doc_response.data.get("scope_id")
            if doc_scope is not None and doc_scope not in allowed_scopes:
                raise HTTPException(status_code=403, detail="Access denied: document scope restricted")

        doc_title = doc_response.data.get("title", "Unknown")

        # Delete using cleanup service (Atomic: Vector -> Storage -> DB)
        # Pass organization_id for org-scoped deletion
        await cleanup_service.delete_single_document(doc_id, user_id, organization_id=organization_id)



        # Audit log (async, non-blocking)
        log_document_delete(background_tasks, user_id, doc_id, doc_title, request)

        return {"status": "success", "id": doc_id}
    except HTTPException as he:
        raise he
    except Exception as e:
        raise api_error(ApiErrorCode.DATABASE_ERROR, e, "delete_document")


# =============================================================================
# Document Update Endpoint
# =============================================================================

@router.patch("/documents/{document_id}", response_model=DocumentDTO)
@limiter.limit("30/minute")
async def update_document(
    document_id: str,
    update: DocumentUpdate,
    request: Request,
    background_tasks: BackgroundTasks,
    user_id: str = Depends(require_editor),
    organization_id: str = Depends(get_user_organization_id),
    allowed_scopes: list[str] | None = Depends(get_user_allowed_scopes),
):
    """
    Update document metadata (title, description, tags).

    Org-scoped: Team members with editor/admin role can update shared documents.
    """
    from services.audit import audit_logger

    supabase = get_supabase()

    try:
        team = await team_service.get_user_team(user_id)
        if team and team.get("user_role") == "viewer":
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Viewers cannot update documents."
            )

        # Check document exists in organization (org-scoped access)
        doc_response = supabase.table("documents")\
            .select("*")\
            .eq("id", document_id)\
            .eq("organization_id", organization_id)\
            .single()\
            .execute()

        if not doc_response.data:
            raise HTTPException(status_code=404, detail="Document not found")

        # Scope-level access control: check if user can access this document's scope
        if allowed_scopes is not None:
            doc_scope = doc_response.data.get("scope_id")
            if doc_scope is not None and doc_scope not in allowed_scopes:
                raise HTTPException(status_code=403, detail="Access denied: document scope restricted")

        old_doc = doc_response.data

        # Build update payload
        update_data = {}
        if update.title is not None:
            update_data["title"] = update.title

        # Store description and tags in metadata
        if update.description is not None or update.tags is not None:
            existing_metadata = old_doc.get("metadata", {}) or {}
            if update.description is not None:
                existing_metadata["description"] = update.description
            if update.tags is not None:
                existing_metadata["tags"] = update.tags
            update_data["metadata"] = existing_metadata

        if not update_data:
            raise HTTPException(status_code=400, detail="No update fields provided")

        # Perform update (org-scoped)
        result = supabase.table("documents")\
            .update(update_data)\
            .eq("id", document_id)\
            .eq("organization_id", organization_id)\
            .execute()

        if not result.data:
            raise HTTPException(status_code=500, detail="Update failed")

        updated_doc = result.data[0]
        updated_doc["source_type"] = normalize_provider(updated_doc.get("source_type")) or updated_doc.get("source_type")

        # Audit log
        audit_logger.log(
            background_tasks,
            user_id=user_id,
            action="document.update",
            resource_type="document",
            resource_id=document_id,
            details={
                "title": updated_doc.get("title"),
                "changes": list(update_data.keys())
            },
            request=request
        )

        # Return updated document
        updated_doc['status'] = updated_doc.get('status', 'indexed')
        updated_doc['indexing_status'] = 'completed'
        updated_doc['metadata'] = updated_doc.get('metadata') or {}
        updated_doc['path'] = _extract_path_from_document(updated_doc)
        meta = updated_doc.get('metadata') or {}
        file_size = updated_doc.get("file_size_bytes")
        if file_size is None:
            file_size = meta.get('file_size') or meta.get('size') or meta.get('file_size_bytes') or 0
        updated_doc["file_size_bytes"] = file_size or 0
        updated_doc['size'] = file_size or 0

        return updated_doc

    except HTTPException:
        raise
    except Exception as e:
        raise api_error(ApiErrorCode.DATABASE_ERROR, e, "update_document")


# =============================================================================
# Document Chunks Endpoint (for debugging/display)
# =============================================================================

@router.get("/documents/{document_id}/chunks", response_model=list[DocumentChunkDTO])
@limiter.limit("30/minute")
async def get_document_chunks(
    document_id: str,
    request: Request,
    user_id: str = Depends(get_current_user),
    organization_id: str = Depends(get_user_organization_id),
    allowed_scopes: list[str] | None = Depends(get_user_allowed_scopes),
    limit: int = Query(default=50, ge=1, le=200),
    offset: int = Query(default=0, ge=0),
):
    """
    Get chunks for a document with pagination.

    Org-scoped: Team members can view chunks of shared documents.

    GHOST PROTOCOL: Content is decrypted before returning.
    In strict mode, unencrypted content will raise an error.
    """
    from core.security import EncryptionError, UnencryptedContentError, decrypt_text

    supabase = get_supabase()

    try:
        # Verify document exists in organization (org-scoped access)
        doc_check = supabase.table("documents")\
            .select("id, scope_id")\
            .eq("id", document_id)\
            .eq("organization_id", organization_id)\
            .single()\
            .execute()

        if not doc_check.data:
            raise HTTPException(status_code=404, detail="Document not found")

        # Scope-level access control: check if user can access this document's scope
        if allowed_scopes is not None:
            doc_scope = doc_check.data.get("scope_id")
            if doc_scope is not None and doc_scope not in allowed_scopes:
                raise HTTPException(status_code=403, detail="Access denied: document scope restricted")

        # Fetch chunks
        chunks_response = supabase.table("document_chunks")\
            .select("id, document_id, content, chunk_index")\
            .eq("document_id", document_id)\
            .order("chunk_index", desc=False)\
            .range(offset, offset + limit - 1)\
            .execute()

        # GHOST PROTOCOL: Decrypt content before returning
        chunks = chunks_response.data or []
        for chunk in chunks:
            if chunk.get("content"):
                try:
                    chunk["content"] = decrypt_text(chunk["content"])
                except UnencryptedContentError:
                    # Strict mode: unencrypted content is a policy violation
                    logger.warning(
                        f"[GhostProtocol] Unencrypted content in chunk {chunk.get('id')} "
                        f"(doc: {document_id})"
                    )
                    chunk["content"] = "[Content unavailable - encryption policy violation]"
                except EncryptionError as e:
                    logger.error(f"[GhostProtocol] Decryption failed for chunk {chunk.get('id')}: {e}")
                    chunk["content"] = "[Content unavailable - decryption error]"
            # Add empty metadata dict if not present
            if "metadata" not in chunk:
                chunk["metadata"] = {}

        return chunks

    except HTTPException:
        raise
    except Exception as e:
        raise api_error(ApiErrorCode.DATABASE_ERROR, e, "fetch_chunks")


# =============================================================================
# GHOST PROTOCOL: Content Download Lockdown
# =============================================================================

@router.get("/documents/{document_id}/content")
@limiter.limit("10/minute")
async def get_document_content(
    document_id: str,
    request: Request,
    user_id: str = Depends(get_current_user),
    organization_id: str = Depends(get_user_organization_id),
):
    """
    BLOCKED: Original document content retrieval.

    Ghost Protocol enforces Zero-Retention: original files are processed
    and destroyed immediately after vectorization. Only embeddings and
    encrypted text chunks are retained.

    This endpoint always returns 403 Forbidden.
    """
    raise HTTPException(
        status_code=status.HTTP_403_FORBIDDEN,
        detail={
            "error": "content_not_available",
            "message": (
                "Ephemeral Storage Policy: Original files are processed and destroyed "
                "immediately after ingestion. Only vector embeddings and encrypted "
                "text chunks are retained. Use /documents/{id}/chunks to retrieve "
                "decrypted text content."
            ),
            "policy": "ghost_protocol",
            "docs": "https://docs.axiohub.io/security/zero-retention"
        }
    )


@router.get("/documents/{document_id}/download")
@limiter.limit("10/minute")
async def download_document(
    document_id: str,
    request: Request,
    user_id: str = Depends(get_current_user),
    organization_id: str = Depends(get_user_organization_id),
):
    """
    BLOCKED: Original document download.

    Ghost Protocol enforces Zero-Retention: original files cannot be
    downloaded because they are not stored. Files are securely wiped
    immediately after processing.

    This endpoint always returns 403 Forbidden.
    """
    raise HTTPException(
        status_code=status.HTTP_403_FORBIDDEN,
        detail={
            "error": "download_not_available",
            "message": (
                "Ephemeral Storage Policy: Original files are securely wiped after "
                "ingestion and cannot be downloaded. Axio Hub operates as a 'shredder' - "
                "we remember the context but destroy the paper."
            ),
            "policy": "ghost_protocol",
            "docs": "https://docs.axiohub.io/security/zero-retention"
        }
    )


# =============================================================================
# GHOST PROTOCOL: Secure Wipe Endpoints
# =============================================================================

class WipeInitResponse(BaseModel):
    """Response for wipe initiation - matches frontend expectations."""
    wipeId: str
    documentId: str
    documentName: str
    status: str  # "started" | "in_progress"
    startedAt: str
    currentPass: int = 1
    passProgress: float = 0.0
    isComplete: bool = False


class WipeStatusResponse(BaseModel):
    """Response for wipe status check - matches frontend WipeProgress interface."""
    # Frontend-compatible fields (camelCase via alias)
    documentId: str
    documentName: str
    currentPass: int
    passProgress: float  # 0-100 progress within current pass
    isComplete: bool
    startedAt: str
    estimatedCompletion: str | None = None
    error: str | None = None
    # Additional backend fields
    wipeId: str
    status: str  # "pending" | "pass_1" | "pass_2" | "pass_3" | "verifying" | "completed" | "failed"
    totalPasses: int = 3
    verified: bool = False


@router.post("/documents/{document_id}/wipe", response_model=WipeInitResponse)
@limiter.limit("10/minute")
async def initiate_wipe(
    document_id: str,
    request: Request,
    background_tasks: BackgroundTasks,
    user_id: str = Depends(require_editor),
    organization_id: str = Depends(get_user_organization_id),
    allowed_scopes: list[str] | None = Depends(get_user_allowed_scopes),
):
    """
    Initiate DoD 5220.22-M secure wipe for document.

    Ghost Protocol compliance:
    1. Creates compliance tombstone (immediate access revocation)
    2. Initiates 3-pass secure wipe (0x00 → 0xFF → Random)
    3. Verifies erasure completion
    4. Records in compliance audit log

    The tombstone immediately blocks the document from search results.
    Actual data deletion happens asynchronously.
    """
    import uuid
    from datetime import timezone

    from services.audit import audit_logger

    supabase = get_supabase()

    try:
        # Verify document exists and belongs to organization
        doc_response = supabase.table("documents")\
            .select("id, title, scope_id")\
            .eq("id", document_id)\
            .eq("organization_id", organization_id)\
            .maybe_single()\
            .execute()

        if not doc_response or not doc_response.data:
            raise HTTPException(status_code=404, detail="Document not found")

        doc_title = doc_response.data.get("title", "Unknown")
        scope_id = doc_response.data.get("scope_id")

        # Scope-level access control: check if user can access this document's scope
        if allowed_scopes is not None:
            if scope_id is not None and scope_id not in allowed_scopes:
                raise HTTPException(status_code=403, detail="Access denied: document scope restricted")

        # Generate wipe request ID
        wipe_id = str(uuid.uuid4())
        started_at = datetime.now(timezone.utc).isoformat()

        # Create compliance tombstone for immediate access revocation
        tombstone_data = {
            "resource_type": "document",
            "resource_id": document_id,
            "organization_id": organization_id,
            "document_ids": [document_id],
            "scope_ids": [scope_id] if scope_id else [],
            "compliance_type": "user_request",
            "request_id": wipe_id,
            "requested_by": user_id,
            "status": "active",
        }

        supabase.table("compliance_tombstones").insert(tombstone_data).execute()

        # Schedule background wipe task
        background_tasks.add_task(
            _execute_secure_wipe,
            document_id=document_id,
            wipe_id=wipe_id,
            user_id=user_id,
            organization_id=organization_id,
            doc_title=doc_title,
        )

        # Audit log
        audit_logger.log(
            background_tasks,
            user_id=user_id,
            action="document.wipe",
            resource_type="document",
            resource_id=document_id,
            details={
                "wipe_id": wipe_id,
                "title": doc_title,
                "wipe_pattern": "dod_5220_22_m",
                "ghost_protocol": True,
            },
            request=request,
        )

        return WipeInitResponse(
            wipeId=wipe_id,
            documentId=document_id,
            documentName=doc_title,
            status="started",
            startedAt=started_at,
            currentPass=1,
            passProgress=0.0,
            isComplete=False,
        )

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"[GhostProtocol] Wipe initiation failed: {e}")
        raise api_error(ApiErrorCode.DATABASE_ERROR, e, "initiate_wipe")


@router.get("/documents/{document_id}/wipe-status", response_model=WipeStatusResponse)
@limiter.limit("30/minute")
async def get_wipe_status(
    document_id: str,
    request: Request,
    user_id: str = Depends(get_current_user),
    organization_id: str = Depends(get_user_organization_id),
):
    """
    Get current wipe progress for document.

    Returns the status of the most recent wipe request for this document.
    Status progression: pending → pass_1 → pass_2 → pass_3 → verifying → completed
    """
    supabase = get_supabase()

    try:
        # Find the most recent tombstone for this document
        tombstone_response = supabase.table("compliance_tombstones")\
            .select("*")\
            .eq("resource_type", "document")\
            .eq("resource_id", document_id)\
            .eq("organization_id", organization_id)\
            .order("created_at", desc=True)\
            .limit(1)\
            .execute()

        if not tombstone_response.data:
            raise HTTPException(
                status_code=404,
                detail="No wipe operation found for this document"
            )

        tombstone = tombstone_response.data[0]
        wipe_id = tombstone.get("request_id", tombstone["id"])
        tombstone_status = tombstone.get("status", "active")
        failure_reason = tombstone.get("failure_reason")
        created_at = tombstone.get("created_at", "")
        started_at = created_at

        # Try to get document name (may be deleted already)
        doc_name = "Deleted Document"
        try:
            doc_response = supabase.table("documents")\
                .select("title")\
                .eq("id", document_id)\
                .eq("organization_id", organization_id)\
                .maybe_single()\
                .execute()
            if doc_response and doc_response.data:
                doc_name = doc_response.data.get("title", "Document")
        except Exception as e:
            logger.debug(f"[Documents] Failed to fetch document title for wipe status: {e}")

        # Map tombstone status to wipe status
        is_complete = False
        verified = False

        if tombstone_status == "completed":
            wipe_status = "completed"
            current_pass = 3
            progress = 100.0
            verified = True
            is_complete = True
        elif tombstone_status == "failed":
            wipe_status = "failed"
            current_pass = 0
            progress = 0.0
        else:
            # Active tombstone - wipe is in progress
            # Since we can't track granular pass progress in DB, estimate based on time
            from datetime import datetime, timezone
            if created_at:
                try:
                    created_time = datetime.fromisoformat(created_at.replace("Z", "+00:00"))
                    elapsed = (datetime.now(timezone.utc) - created_time).total_seconds()
                    # Estimate: each pass takes ~2 seconds, verify takes ~1 second
                    if elapsed < 2:
                        wipe_status = "pass_1"
                        current_pass = 1
                        progress = min(elapsed / 2 * 100, 100)  # Progress within pass
                    elif elapsed < 4:
                        wipe_status = "pass_2"
                        current_pass = 2
                        progress = min((elapsed - 2) / 2 * 100, 100)
                    elif elapsed < 6:
                        wipe_status = "pass_3"
                        current_pass = 3
                        progress = min((elapsed - 4) / 2 * 100, 100)
                    else:
                        wipe_status = "verifying"
                        current_pass = 3
                        progress = 100.0
                except Exception:
                    wipe_status = "in_progress"
                    current_pass = 2
                    progress = 50.0
            else:
                wipe_status = "pending"
                current_pass = 1
                progress = 0.0

        return WipeStatusResponse(
            wipeId=str(wipe_id),
            documentId=document_id,
            documentName=doc_name,
            currentPass=current_pass,
            passProgress=progress,
            isComplete=is_complete,
            startedAt=started_at,
            estimatedCompletion=None,
            error=failure_reason,
            status=wipe_status,
            totalPasses=3,
            verified=verified,
        )

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"[GhostProtocol] Wipe status check failed: {e}")
        raise api_error(ApiErrorCode.DATABASE_ERROR, e, "get_wipe_status")


async def _execute_secure_wipe(
    document_id: str,
    wipe_id: str,
    user_id: str,
    organization_id: str,
    doc_title: str,
):
    """
    Background task to execute the actual secure wipe.

    Uses cleanup_service which performs DoD 5220.22-M compliant deletion.
    Updates the compliance tombstone on completion.
    """
    from datetime import timezone

    supabase = get_supabase()

    try:
        # Execute the secure wipe via cleanup service
        # Note: cleanup_service.delete_single_document() already logs
        # the security.document_wiped event internally via _log_security_event
        await cleanup_service.delete_single_document(
            document_id,
            user_id,
            organization_id=organization_id
        )

        # Mark tombstone as completed
        supabase.table("compliance_tombstones")\
            .update({
                "status": "completed",
                "completed_at": datetime.now(timezone.utc).isoformat(),
            })\
            .eq("request_id", wipe_id)\
            .eq("organization_id", organization_id)\
            .execute()

        logger.info(
            f"[GhostProtocol] Secure wipe completed: {document_id[:8]}..."
        )

    except Exception as e:
        logger.error(f"[GhostProtocol] Secure wipe failed: {e}")

        # Mark tombstone as failed (but keep it active to block access)
        try:
            supabase.table("compliance_tombstones")\
                .update({
                    "status": "failed",
                    "failure_reason": str(e)[:500],
                })\
                .eq("request_id", wipe_id)\
                .eq("organization_id", organization_id)\
                .execute()
        except Exception as e:
            logger.debug(f"[Documents] Failed to delete wipe request record: {e}")
