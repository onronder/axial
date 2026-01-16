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
from services.cleanup import cleanup_service
from services.team_service import team_service
import logging

logger = logging.getLogger(__name__)

router = APIRouter(dependencies=[Depends(validate_team_access), Depends(require_paid_access)])


# =============================================================================
# Response Models
# =============================================================================

class DocumentDTO(BaseModel):
    id: str
    title: str
    source_type: str
    source_url: Optional[str] = None
    created_at: str
    status: str = "indexed"
    # Documents only exist after successful ingestion, so default to completed
    indexing_status: str = "completed"
    size: Optional[int] = 0
    file_size_bytes: Optional[int] = 0
    metadata: Dict[str, Any]


class DocumentStatsDTO(BaseModel):
    """Lightweight stats response for efficient dashboard loading."""
    total_documents: int
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
    
    Uses efficient count query - O(1) performance instead of O(n) data transfer.
    Used by frontend to check if team needs onboarding.
    """
    supabase = get_supabase()
    
    try:
        # Use count query - only fetches count, not actual data (org-wide)
        count_response = supabase.table("documents")\
            .select("id", count="exact")\
            .eq("organization_id", organization_id)\
            .neq("source_type", "identity")\
            .neq("source_type", "scope_identity")\
            .execute()
        
        total = count_response.count if count_response.count is not None else 0
        
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
            last_updated=last_updated
        )
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to fetch stats: {str(e)}")



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
            
        # Enrich completed documents with status
        docs = []
        for d in db_res.data:
            d["source_type"] = normalize_provider(d.get("source_type")) or d.get("source_type")
            d['status'] = d.get('status', 'indexed')
            d['indexing_status'] = 'completed'
            d["metadata"] = d.get("metadata") or {}
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
                    docs.append({
                        "id": f["id"],
                        "title": f["filename"],
                        "source_type": provider,
                        "source_url": None,
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
        raise HTTPException(status_code=500, detail=f"Failed to fetch documents: {str(e)}")

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
    """
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
            from services.audit import audit_logger
            audit_logger.log(
                background_tasks,
                user_id=user_id,
                action="document.bulk_delete",
                resource_type="document",
                resource_id="bulk",
                details={
                    "deleted_count": len(deleted),
                    "source_type": payload.source_type,
                },
                request=request
            )
        except Exception:
            pass

    return {
        "status": "success",
        "deleted": len(deleted),
        "failed": failed
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
        doc_response = supabase.table("documents")\
            .select("title")\
            .eq("id", doc_id)\
            .eq("organization_id", organization_id)\
            .single()\
            .execute()
        if not doc_response.data:
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
        raise HTTPException(status_code=500, detail=f"Failed to delete document: {str(e)}")


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
        raise HTTPException(status_code=500, detail=f"Failed to update document: {str(e)}")


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
    """
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
            .select("id, document_id, content, chunk_index, metadata")\
            .eq("document_id", document_id)\
            .order("chunk_index", desc=False)\
            .range(offset, offset + limit - 1)\
            .execute()
        
        return chunks_response.data or []
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to fetch chunks: {str(e)}")
