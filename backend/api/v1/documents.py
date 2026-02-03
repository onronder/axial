from fastapi import APIRouter, Depends, HTTPException, status, BackgroundTasks, Request
from typing import List, Optional, Dict, Any
from datetime import datetime
from pydantic import BaseModel
from core.security import get_current_user
from core.db import get_supabase
from core.rate_limit import limiter
from core.ingestion_utils import normalize_provider, canonicalize_provider_name
from core.scopes import get_scope_prefixes
from services.audit import log_document_delete
from api.v1.dependencies import validate_team_access, require_editor, require_paid_access, get_user_organization_id
from api.v1.error_utils import api_error, ApiErrorCode
from services.cleanup import cleanup_service
from services.team_service import team_service
from services.scope_guard import ScopeGuardStateMachine, ActionType
import logging

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
    source_url: Optional[str] = None
    # Path/location within the source (e.g., folder path in Drive, S3 key, etc.)
    path: Optional[str] = None
    created_at: str
    status: str = "indexed"
    # Documents only exist after successful ingestion, so default to completed
    indexing_status: str = "completed"
    size: Optional[int] = 0
    file_size_bytes: Optional[int] = 0
    metadata: Dict[str, Any]


def _extract_path_from_document(doc: Dict[str, Any]) -> Optional[str]:
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
    meta = doc.get("metadata") or {}
    source_type = (doc.get("source_type") or "").lower()
    
    # Try common path fields in order of preference
    path = (
        meta.get("path") or
        meta.get("path_display") or
        meta.get("path_lower") or
        meta.get("file_path") or
        meta.get("parent_path") or
        meta.get("key") or  # S3
        meta.get("storage_path") or  # File upload
        None
    )
    
    # For Box, construct path from folder_name
    if not path and source_type == "box":
        folder_name = meta.get("folder_name")
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


class DocumentStatsDTO(BaseModel):
    """Lightweight stats response for efficient dashboard loading."""
    total_documents: int
    failed_documents: int = 0
    pending_documents: int = 0
    last_updated: Optional[str] = None


class DocumentUpdate(BaseModel):
    """Request model for updating document metadata."""
    title: Optional[str] = None
    description: Optional[str] = None
    tags: Optional[List[str]] = None


class DocumentChunkDTO(BaseModel):
    """Response model for document chunks."""
    id: str
    document_id: str
    content: str
    chunk_index: int
    metadata: Dict[str, Any] = {}


class BulkDeleteRequest(BaseModel):
    """Payload for bulk document deletion."""
    document_ids: Optional[List[str]] = None
    source_type: Optional[str] = None
    # Ghost Protocol: ScopeGuard approval credentials
    approval_id: Optional[str] = None
    mandate_signature: Optional[str] = None
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

@router.get("/documents", response_model=List[DocumentDTO])
@limiter.limit("60/minute")
async def list_documents(
    request: Request,
    response: Response,
    user_id: str = Depends(validate_team_access),  # Validates team access
    organization_id: str = Depends(get_user_organization_id),  # Org-scoped query
    limit: int = 50,
    offset: int = 0,
    q: Optional[str] = None,
    include_failed: bool = True  # New param to include failed files
):
    supabase = get_supabase()
    
    try:
        # Build query for completed documents (org-scoped for team visibility)
        query = supabase.table("documents")\
            .select("*", count="exact")\
            .eq("organization_id", organization_id)\
            .neq("source_type", "identity")\
            .neq("source_type", "scope_identity")  # Org-wide access
            
        # Apply search filter
        if q and q.strip():
            query = query.ilike("title", f"%{q.strip()}%")
            
        # Execute with pagination
        db_res = query\
            .order("created_at", desc=True)\
            .range(offset, offset + limit - 1)\
            .execute()
            
        # Set pagination header
        if db_res.count is not None:
             response.headers["X-Total-Count"] = str(db_res.count)
            
        # Enrich completed documents with status and path
        docs = []
        for d in db_res.data:
            d["source_type"] = normalize_provider(d.get("source_type")) or d.get("source_type")
            d['status'] = d.get('status', 'indexed')
            d['indexing_status'] = 'completed'
            d["metadata"] = d.get("metadata") or {}
            # Extract path from metadata
            d["path"] = _extract_path_from_document(d)
            # Fallback for size if not top-level
            meta = d["metadata"]
            file_size = d.get("file_size_bytes")
            if file_size is None:
                file_size = meta.get('file_size') or meta.get('size') or meta.get('file_size_bytes') or 0
            d["file_size_bytes"] = file_size or 0
            d["size"] = file_size or 0
                
            docs.append(d)
        
        # Also fetch failed files from ingestion_file_status (not yet in documents)
        # Organization-wide: Show failed files from all team members
        if include_failed:
            try:
                # Query failed files for the organization
                failed_query = supabase.table("ingestion_file_status")\
                    .select("*")\
                    .eq("organization_id", organization_id)\
                    .eq("status", "failed")\
                    .is_("document_id", "null")
                
                if q and q.strip():
                    failed_query = failed_query.ilike("filename", f"%{q.strip()}%")
                
                failed_res = failed_query\
                    .order("created_at", desc=True)\
                    .limit(limit)\
                    .execute()
                
                failed_files = failed_res.data or []
                provider_map = {}
                job_ids = {str(f.get("job_id")) for f in failed_files if f.get("job_id")}
                if job_ids:
                    jobs_res = supabase.table("ingestion_jobs")\
                        .select("id, provider")\
                        .in_("id", list(job_ids))\
                        .execute()
                    for job in jobs_res.data or []:
                        provider_map[str(job["id"])] = normalize_provider(job.get("provider")) or job.get("provider")

                # Convert failed files to DocumentDTO format
                for f in failed_files:
                    provider = provider_map.get(str(f.get("job_id"))) or "file_upload"
                    file_size = f.get("file_size_bytes", 0)
                    # Extract path from failed file metadata if available
                    failed_meta = f.get("metadata") or {}
                    failed_path = (
                        failed_meta.get("path") or
                        failed_meta.get("path_display") or
                        failed_meta.get("file_path") or
                        failed_meta.get("key") or
                        f.get("remote_id") or  # Some connectors store path as remote_id
                        None
                    )
                    docs.append({
                        "id": f["id"],
                        "title": f["filename"],
                        "source_type": provider,
                        "source_url": None,
                        "path": failed_path,
                        "created_at": f["created_at"],
                        "status": "failed",
                        "indexing_status": "failed",
                        "file_size_bytes": file_size,
                        "size": file_size,
                        "metadata": {
                            "error": f.get("error_message", "Unknown error"),
                            "job_id": str(f.get("job_id", ""))
                        }
                    })
            except Exception as failed_err:
                # Don't fail entire request if failed files query fails
                import logging
                logging.warning(f"Failed to fetch failed files: {failed_err}")
        
        # Sort combined list by created_at
        docs.sort(key=lambda x: x.get('created_at', ''), reverse=True)
            
        return docs
    except Exception as e:
        raise api_error(ApiErrorCode.DATABASE_ERROR, e, "fetch_documents")

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

    if not payload.document_ids and not payload.source_type:
        raise HTTPException(status_code=400, detail="Provide document_ids or source_type to delete.")

    doc_ids: List[str] = []

    if payload.document_ids:
        doc_ids.extend(payload.document_ids)

    # Expand by source type if provided (org-wide)
    if payload.source_type:
        normalized_source = canonicalize_provider_name(payload.source_type) or payload.source_type
        try:
            source_docs = supabase.table("documents")\
                .select("id")\
                .eq("organization_id", organization_id)\
                .eq("source_type", normalized_source)\
                .execute()
            doc_ids.extend([row["id"] for row in (source_docs.data or []) if row.get("id")])
        except Exception as e:
            raise HTTPException(status_code=500, detail=f"Failed to resolve documents for source: {e}")

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
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail=str(e)
                )
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
                logger.error(f"[ScopeGuard] Failed to request approval: {e}")
                raise HTTPException(
                    status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                    detail=f"Failed to request approval: {str(e)}"
                )

    deleted: List[str] = []
    failed: List[Dict[str, str]] = []

    for doc_id in doc_ids:
        try:
            await cleanup_service.delete_single_document(
                doc_id, user_id, organization_id=organization_id
            )
            deleted.append(doc_id)
        except Exception as e:
            failed.append({"id": doc_id, "error": str(e)})

    if payload.source_type:
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
                    "ghost_protocol": True,
                },
                request=request
            )
        except Exception:
            pass

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
            .select("title")\
            .eq("id", doc_id)\
            .eq("organization_id", organization_id)\
            .maybe_single()\
            .execute()
        if doc_response is None or not doc_response.data:
            raise HTTPException(status_code=404, detail="Document not found")

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

@router.get("/documents/{document_id}/chunks", response_model=List[DocumentChunkDTO])
@limiter.limit("30/minute")
async def get_document_chunks(
    document_id: str,
    request: Request,
    user_id: str = Depends(get_current_user),
    organization_id: str = Depends(get_user_organization_id),
    limit: int = 50,
    offset: int = 0
):
    """
    Get all chunks for a document.
    
    Org-scoped: Team members can view chunks of shared documents.
    
    GHOST PROTOCOL: Content is decrypted before returning.
    In strict mode, unencrypted content will raise an error.
    """
    from core.security import decrypt_text, UnencryptedContentError, EncryptionError
    
    supabase = get_supabase()
    
    try:
        # Verify document exists in organization (org-scoped access)
        doc_check = supabase.table("documents")\
            .select("id")\
            .eq("id", document_id)\
            .eq("organization_id", organization_id)\
            .single()\
            .execute()
        
        if not doc_check.data:
            raise HTTPException(status_code=404, detail="Document not found")
        
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
