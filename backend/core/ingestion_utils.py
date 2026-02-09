"""
Ingestion normalization and Ghost Protocol helpers.

Provides:
- Provider/source_type naming normalization
- Ghost Protocol: Encrypted chunk content preparation
- Ghost Protocol: RPC-based chunk insertion with TSVECTOR support
"""

from __future__ import annotations

import logging
from typing import Any
from uuid import uuid4

from core.scopes import (
    CANONICAL_PROVIDER_BY_ALIAS,
    SCOPE_PREFIX_BY_PROVIDER,
    canonicalize_provider,
)

KNOWN_PROVIDER_ALIASES = set(SCOPE_PREFIX_BY_PROVIDER.keys())

logger = logging.getLogger(__name__)


def normalize_provider(value: str | None) -> str | None:
    """
    Normalize provider names to canonical values used in DB and jobs.
    """
    if value is None:
        return None
    normalized = value.strip().lower()
    normalized = normalized.replace(" ", "_").replace("-", "_")
    return normalized


def require_canonical_provider(value: str | None) -> str:
    """
    Normalize provider names and reject deprecated aliases at API boundaries.
    """
    normalized = normalize_provider(value)
    if not normalized:
        raise ValueError("provider is required")
    if normalized in CANONICAL_PROVIDER_BY_ALIAS:
        raise ValueError(f"Deprecated provider value: {normalized}")
    from connectors import CONNECTORS
    supported = set(CONNECTORS.keys())
    if normalized not in supported:
        if normalized in KNOWN_PROVIDER_ALIASES:
            raise ValueError(f"Deprecated provider value: {normalized}")
        raise ValueError(f"Unsupported provider value: {normalized}")
    return normalized


def normalize_source_type(value: str | None) -> str | None:
    """
    Normalize document source_type values to canonical values.
    """
    return canonicalize_provider(value)


def canonicalize_provider_name(value: str | None) -> str | None:
    """
    Normalize provider names and coerce known aliases to canonical providers.
    """
    return canonicalize_provider(value)


# =============================================================================
# GHOST PROTOCOL: Encrypted Content Ingestion
# =============================================================================

def prepare_chunks_for_ghost_protocol(
    chunks_payload: list[dict[str, Any]],
    document_id: str,
) -> tuple[list[dict[str, Any]], bool]:
    """
    Prepare chunk records for Ghost Protocol insertion.

    Encrypts content and prepares plaintext for TSVECTOR generation.
    Returns both the transformed payload and whether encryption was applied.

    Args:
        chunks_payload: List of chunk dicts with 'content', 'embedding', 'chunk_index'
        document_id: UUID of the parent document

    Returns:
        Tuple of (prepared_chunks, encryption_applied)
        - prepared_chunks: List of dicts ready for RPC insertion
        - encryption_applied: True if chunks were encrypted

    Example:
        >>> chunks = [{"content": "Hello world", "embedding": [...], "chunk_index": 0}]
        >>> prepared, encrypted = prepare_chunks_for_ghost_protocol(chunks, "doc-123")
        >>> prepared[0]["content_encrypted"]  # Encrypted
        'gAAAAA...'
        >>> prepared[0]["content_plaintext"]  # Original for TSVECTOR
        'Hello world'
    """
    from core.security import HAS_CHUNK_ENCRYPTION, encrypt_text

    prepared_chunks = []

    for chunk in chunks_payload:
        content = chunk.get("content") or ""

        if HAS_CHUNK_ENCRYPTION:
            # Encrypt content for storage
            content_encrypted = encrypt_text(content)
            content_plaintext = content  # Keep original for search index
        else:
            # No encryption - store as-is (dev/test mode)
            content_encrypted = content
            content_plaintext = content

        # Prepare chunk for RPC
        prepared_chunk = {
            "id": str(uuid4()),
            "document_id": str(document_id),
            "content_encrypted": content_encrypted,
            "content_plaintext": content_plaintext,
            "embedding": chunk.get("embedding"),
            "chunk_index": chunk.get("chunk_index", 0),
        }
        prepared_chunks.append(prepared_chunk)

    return prepared_chunks, HAS_CHUNK_ENCRYPTION


def insert_chunks_with_ghost_protocol(
    supabase: Any,
    document_id: str,
    chunks_payload: list[dict[str, Any]],
    batch_size: int = 100,
    context: str = "",
) -> int:
    """
    Insert chunks using Ghost Protocol RPC (type-safe TSVECTOR).

    Uses the `ingest_document_chunks_batch` RPC which:
    - Accepts encrypted content and plaintext separately
    - Generates TSVECTOR server-side from plaintext
    - Handles type conversion safely

    Falls back to direct insert if RPC is not available.

    Args:
        supabase: Supabase client
        document_id: UUID of the parent document
        chunks_payload: List of chunk dicts with 'content', 'embedding', 'chunk_index'
        batch_size: Number of chunks per RPC call
        context: Logging context string

    Returns:
        Number of successfully inserted chunks

    Raises:
        Exception: If all insert attempts fail
    """

    if not chunks_payload:
        return 0

    # Prepare chunks for Ghost Protocol
    prepared_chunks, encryption_applied = prepare_chunks_for_ghost_protocol(
        chunks_payload, document_id
    )

    total_inserted = 0

    # Process in batches
    for i in range(0, len(prepared_chunks), batch_size):
        batch = prepared_chunks[i:i + batch_size]

        try:
            # Try RPC-based insertion (Ghost Protocol)
            result = supabase.rpc(
                "ingest_document_chunks_batch",
                {"p_chunks": batch}
            ).execute()

            if result.data:
                total_inserted += len(result.data)
                logger.debug(
                    f"🔐 [GhostProtocol] Inserted {len(result.data)} chunks "
                    f"{'(encrypted)' if encryption_applied else '(plaintext)'} "
                    f"{context}"
                )

        except Exception as rpc_error:
            # Check if it's a "function doesn't exist" error
            error_str = str(rpc_error).lower()
            if "function" in error_str and "does not exist" in error_str:
                logger.warning(
                    f"⚠️ [GhostProtocol] RPC not available, falling back to direct insert: {rpc_error}"
                )
                # Fallback to direct insert (legacy mode)
                return _insert_chunks_direct(supabase, document_id, chunks_payload, batch_size, context)

            logger.error(f"❌ [GhostProtocol] RPC insertion failed: {rpc_error}")
            raise

    return total_inserted


def _insert_chunks_direct(
    supabase: Any,
    document_id: str,
    chunks_payload: list[dict[str, Any]],
    batch_size: int,
    context: str,
) -> int:
    """
    Fallback: Insert chunks directly without RPC (legacy mode).

    Used when Ghost Protocol RPC is not deployed yet.
    Content is still encrypted if CHUNK_ENCRYPTION_KEY is set.
    """
    from core.db_utils import insert_rows_with_retry
    from core.security import HAS_CHUNK_ENCRYPTION, encrypt_text

    total_inserted = 0

    for i in range(0, len(chunks_payload), batch_size):
        batch = chunks_payload[i:i + batch_size]

        # Prepare batch for direct insert
        insert_batch = []
        for chunk in batch:
            content = chunk.get("content") or ""

            # Encrypt if available
            if HAS_CHUNK_ENCRYPTION:
                content = encrypt_text(content)

            insert_batch.append({
                "document_id": str(document_id),
                "content": content,
                "embedding": chunk.get("embedding"),
                "chunk_index": chunk.get("chunk_index", 0),
            })

        try:
            insert_rows_with_retry(
                supabase,
                "document_chunks",
                insert_batch,
                context=f"doc_id={document_id} batch={i // batch_size + 1} {context}",
            )
            total_inserted += len(insert_batch)
        except Exception as e:
            logger.error(f"❌ [DirectInsert] Failed batch {i // batch_size + 1}: {e}")
            continue

    return total_inserted
