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
    scheme = (scope_id or "").split("://", 1)[0]
    return {
        "github": "github_repo",
        "s3": "s3_bucket",
        "box": "box_folder",
        "dropbox": "dropbox_folder",
        "gdrive": "gdrive_folder",
        "google_drive": "gdrive_folder",
        "notion": "notion_workspace",
        "web": "web_domain",
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
    """
    if not scope_id:
        raise ValueError("scope_id is required for identity synthesis")
    if not documents:
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

    existing_scope = (
        supabase.table("scope_identities")
        .select("id")
        .eq("organization_id", organization_id)
        .eq("id", scope_id)
        .limit(1)
        .execute()
    )
    has_existing = bool(existing_scope.data)

    if not has_existing and max_scopes > 0:
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

    supabase.table("scope_identities").upsert(
        {
            "id": scope_id,
            "organization_id": organization_id,
            "user_id": user_id,
            "type": inferred_type,
            "summary": summary,
            "file_tree": ascii_tree,
            "attributes": {
                "file_count": file_count,
                "total_file_count": total_files,
                "stats_sampled": sampled,
                "languages": unique_extensions,
                "size": total_size_bytes,
            },
            "last_ingested_at": now,
            "updated_at": now,
        },
        on_conflict="organization_id,id",
    ).execute()

    source_id = f"identity::{scope_id}"
    doc_title = f"Scope Identity: {scope_id}"
    metadata = {
        "scope_id": scope_id,
        "type": "identity_card",
        "is_identity": True,
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
