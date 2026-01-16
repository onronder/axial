"""
Scope identity synthesis and persistence.

Generates a narrative identity card and persists it to scope_identities
and the vector store.
"""

from __future__ import annotations

import json
import os
from datetime import datetime, timezone
from typing import Dict, Iterable, List, Optional

from connectors.enhanced import SourceDocument
from core.db import get_supabase
from core.exceptions import QuotaExceededError
from core.quotas import get_plan_limits
from services.embeddings import generate_embeddings_batch_sync
from services.team_service import team_service

MAX_DOCS_FOR_IDENTITY = 1000
MAX_TREE_DEPTH = 3
MAX_SUMMARY_CHARS = 2000


def _infer_scope_type(scope_id: str) -> str:
    """
    Infer the identity type from scope_id URI scheme.
    
    Maps canonical URI schemes to human-readable identity types.
    Supports all connector schemes defined in core/scopes.py.
    """
    scheme = (scope_id or "").split("://", 1)[0].lower()
    return {
        # Cloud storage
        "github": "github_repo",
        "s3": "s3_bucket",
        "box": "box_folder",
        "dropbox": "dropbox_folder",
        # Google
        "gdrive": "gdrive_folder",
        "google_drive": "gdrive_folder",
        "drive": "gdrive_folder",
        # Microsoft
        "onedrive": "onedrive_folder",
        "sharepoint": "sharepoint_folder",
        # Other connectors
        "notion": "notion_workspace",
        "sftp": "sftp_server",
        "web": "web_domain",
        "upload": "file_upload",
        "file_upload": "file_upload",
    }.get(scheme, "unknown")


def _collect_paths(documents: Iterable[SourceDocument]) -> List[str]:
    paths: List[str] = []
    for doc in documents:
        metadata = doc.metadata or {}
        path = (
            metadata.get("path")
            or metadata.get("key")
            or metadata.get("storage_path")
            or metadata.get("filename")
            or doc.filename
        )
        if path:
            paths.append(str(path))
    return paths


def _build_ascii_tree(paths: List[str], max_depth: int = MAX_TREE_DEPTH, max_children: int = 10) -> str:
    tree: Dict[str, Dict] = {}
    for path in paths:
        parts = [p for p in str(path).strip("/").split("/") if p]
        if not parts:
            continue
        node = tree
        for part in parts:
            node = node.setdefault(part, {})

    def _render(node: Dict[str, Dict], prefix: str, depth: int, lines: List[str]) -> None:
        if depth >= max_depth:
            return
        children = sorted(node.keys())
        visible = children[:max_children]
        for name in visible:
            lines.append(f"{prefix}|-- {name}")
            _render(node[name], f"{prefix}|   ", depth + 1, lines)
        remaining = len(children) - len(visible)
        if remaining > 0:
            lines.append(f"{prefix}|-- ... ({remaining} more)")

    lines: List[str] = []
    _render(tree, "", 0, lines)
    return "\n".join(lines) if lines else "(no structure available)"


async def synthesize_and_save_identity(
    scope_id: str,
    documents: List[SourceDocument],
    organization_id: str,
    user_id: str,
    plan_code: Optional[str] = None,
) -> None:
    """
    Build and persist a scope identity card from a list of SourceDocuments.
    
    This function is called during finalize_job_task after ingestion completes.
    It transitions scope identities from 'placeholder' status (created during
    ingestion) to 'completed' status with full identity information.
    
    Args:
        scope_id: Canonical scope URI (e.g., 'github://owner/repo')
        documents: List of SourceDocument objects from the ingestion
        organization_id: The organization UUID
        user_id: The user who initiated the ingestion
        plan_code: Optional plan code for quota checks
        
    Raises:
        ValueError: If required parameters are missing
        QuotaExceededError: If scope limit exceeded (for new scopes)
    """
    import logging
    logger = logging.getLogger(__name__)
    
    if not scope_id:
        raise ValueError("scope_id is required for identity synthesis")
    if not documents:
        logger.debug(f"[ScopeIdentity] No documents for {scope_id[:50]}..., skipping synthesis")
        return
    if not organization_id:
        raise ValueError("organization_id is required for identity synthesis")
    if not user_id:
        raise ValueError("user_id is required for identity synthesis")

    total_files = len(documents)
    sample_docs = documents[:MAX_DOCS_FOR_IDENTITY]
    sampled = total_files > len(sample_docs)

    file_count = len(sample_docs)
    total_size_bytes = sum(int(getattr(doc, "size_bytes", 0) or 0) for doc in sample_docs)
    unique_extensions = sorted({
        os.path.splitext(getattr(doc, "filename", "") or "")[1].lower()
        for doc in sample_docs
        if getattr(doc, "filename", None)
    })
    if not unique_extensions:
        unique_extensions = ["(none)"]

    ascii_tree = _build_ascii_tree(_collect_paths(sample_docs))
    inferred_type = _infer_scope_type(scope_id)
    total_size_mb = total_size_bytes / (1024 * 1024) if total_size_bytes else 0.0

    if sampled:
        stats_line = f"Stats (sampled {file_count} of {total_files} files, {total_size_mb:.2f} MB)\n"
    else:
        stats_line = f"Stats: {file_count} files, {total_size_mb:.2f} MB\n"
    narrative = (
        "SCOPE IDENTITY DOCUMENT\n"
        "-----------------------\n"
        f"ID: {scope_id}\n"
        f"Type: {inferred_type}\n"
        f"{stats_line}"
        f"Languages: {', '.join(unique_extensions)}\n"
        "\n"
        "File Structure:\n"
        f"{ascii_tree}\n"
    )
    summary = narrative[:MAX_SUMMARY_CHARS]

    supabase = get_supabase()
    now = datetime.now(timezone.utc).isoformat()

    if not plan_code:
        try:
            plan_code = await team_service.get_effective_plan(user_id)
        except Exception:
            plan_code = "free"

    limits = get_plan_limits(plan_code)
    max_scopes = limits.max_scopes

    # Check if scope already exists (may be a placeholder from ingestion)
    existing_scope = (
        supabase.table("scope_identities")
        .select("id, status, attributes")
        .eq("organization_id", organization_id)
        .eq("id", scope_id)
        .limit(1)
        .execute()
    )
    has_existing = bool(existing_scope.data)
    existing_status = None
    is_placeholder_upgrade = False
    
    if has_existing:
        existing_rows = existing_scope.data
        if isinstance(existing_rows, dict):
            existing_rows = [existing_rows]
        if not isinstance(existing_rows, list):
            existing_rows = []
        existing_data = existing_rows[0] if existing_rows else {}
        existing_status = existing_data.get("status")
        existing_attrs = existing_data.get("attributes") or {}
        is_placeholder_upgrade = (
            existing_status == "placeholder" or 
            existing_attrs.get("is_placeholder", False)
        )
        
        if is_placeholder_upgrade:
            logger.info(
                f"[ScopeIdentity] Upgrading placeholder to completed: {scope_id[:50]}... "
                f"(org: {organization_id[:8]}...)"
            )

    # ==========================================================================
    # HARD QUOTA ENFORCEMENT (Polar-Managed Billing)
    # ==========================================================================
    # Business Rule: No Polar subscription (or trial) = No data ingestion.
    # If max_scopes is 0, the organization has no active subscription.
    # This is the "Hard Zero" rule - strictly enforced, no exceptions.
    # ==========================================================================
    
    if not has_existing:
        # HARD ZERO RULE: Block ALL new scopes if max_scopes <= 0
        if max_scopes <= 0:
            logger.warning(
                f"[ScopeIdentity] BLOCKED: No subscription for org {organization_id[:8]}... "
                f"(max_scopes={max_scopes}, plan={plan_code})"
            )
            raise QuotaExceededError(
                "Active subscription required. Please subscribe to ingest data.",
                {
                    "limit": 0,
                    "current": 0,
                    "plan": plan_code or "none",
                    "organization_id": organization_id,
                    "reason": "no_subscription",
                },
            )
        
        # Standard quota check for subscribed users
        scope_count = (
            supabase.table("scope_identities")
            .select("id", count="exact")
            .eq("organization_id", organization_id)
            .execute()
        )
        current_count = int(scope_count.count or 0)
        if current_count >= max_scopes:
            raise QuotaExceededError(
                "Scope limit reached for your plan.",
                {
                    "limit": max_scopes,
                    "current": current_count,
                    "plan": plan_code,
                    "organization_id": organization_id,
                },
            )

    # Upsert the completed identity (this upgrades placeholders or creates new)
    supabase.table("scope_identities").upsert(
        {
            "id": scope_id,
            "organization_id": organization_id,
            "user_id": user_id,
            "type": inferred_type,
            "status": "completed",
            "summary": summary,
            "file_tree": ascii_tree,
            "attributes": {
                "file_count": file_count,
                "total_file_count": total_files,
                "stats_sampled": sampled,
                "languages": unique_extensions,
                "size": total_size_bytes,
                "is_placeholder": False,
            },
            "last_ingested_at": now,
            "updated_at": now,
        },
        on_conflict="organization_id,id",
    ).execute()
    
    action = "upgraded" if is_placeholder_upgrade else ("updated" if has_existing else "created")
    logger.info(
        f"[ScopeIdentity] ✅ {action.capitalize()} identity for {scope_id[:50]}... "
        f"({total_files} files, {inferred_type})"
    )

    source_id = f"identity::{scope_id}"
    doc_title = f"Scope Identity: {scope_id}"
    metadata = {
        "scope_id": scope_id,
        "type": "identity_card",
        "is_identity": True,
        "source_type": "identity",
        "organization_id": organization_id,
    }
    embedding = generate_embeddings_batch_sync([summary])[0]
    embedding_text = json.dumps(embedding)

    response = supabase.rpc(
        "upsert_scope_identity_document",
        {
            "p_scope_id": scope_id,
            "p_organization_id": organization_id,
            "p_user_id": user_id,
            "p_type": inferred_type,
            "p_summary": summary,
            "p_file_tree": ascii_tree,
            "p_attributes": {
                "file_count": file_count,
                "total_file_count": total_files,
                "stats_sampled": sampled,
                "languages": unique_extensions,
                "size": total_size_bytes,
            },
            "p_last_ingested_at": now,
            "p_doc_title": doc_title,
            "p_source_id": source_id,
            "p_metadata": metadata,
            "p_file_size_bytes": len(summary.encode("utf-8")),
            "p_chunk_content": summary,
            "p_chunk_embedding": embedding_text,
        },
    ).execute()

    if response.data is None:
        raise RuntimeError("Failed to upsert scope identity document")
