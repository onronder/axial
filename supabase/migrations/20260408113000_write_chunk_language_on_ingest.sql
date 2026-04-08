-- =============================================================================
-- Migration: Write document_chunks.language during Ghost Protocol ingest
-- Created: 2026-04-08
--
-- Purpose:
-- - Preserve ingest-time language metadata as ISO 639-1 lowercase codes
-- - Keep FTS strategy unchanged (`simple` on both ingest and query)
-- - Update both batch and single-row ingest RPCs so active and hardened paths
--   explicitly write language instead of relying on legacy column defaults
-- =============================================================================

BEGIN;

DROP FUNCTION IF EXISTS public.ingest_document_chunk(
    UUID,
    UUID,
    TEXT,
    TEXT,
    VECTOR(1536),
    INT
);

DROP FUNCTION IF EXISTS public.ingest_document_chunk(
    UUID,
    UUID,
    TEXT,
    TEXT,
    VECTOR(1536),
    INT,
    TEXT
);

CREATE FUNCTION public.ingest_document_chunk(
    p_id UUID,
    p_document_id UUID,
    p_content_encrypted TEXT,
    p_content_plaintext TEXT,
    p_embedding VECTOR(1536),
    p_chunk_index INT,
    p_language TEXT DEFAULT NULL
)
RETURNS UUID
LANGUAGE plpgsql
SECURITY DEFINER
SET search_path = public
AS $$
DECLARE
    v_inserted_id UUID;
BEGIN
    INSERT INTO document_chunks (
        id,
        document_id,
        content,
        content_search,
        language,
        embedding,
        chunk_index
    ) VALUES (
        COALESCE(p_id, gen_random_uuid()),
        p_document_id,
        p_content_encrypted,
        to_tsvector('simple', COALESCE(p_content_plaintext, '')),
        NULLIF(BTRIM(p_language), ''),
        p_embedding,
        p_chunk_index
    )
    RETURNING id INTO v_inserted_id;

    RETURN v_inserted_id;
END;
$$;

CREATE OR REPLACE FUNCTION public.ingest_document_chunks_batch(
    p_chunks JSONB
)
RETURNS TABLE(inserted_id UUID, chunk_index INT)
LANGUAGE plpgsql
SECURITY DEFINER
SET search_path = public
AS $$
BEGIN
    RETURN QUERY
    INSERT INTO document_chunks (
        id,
        document_id,
        content,
        content_search,
        language,
        embedding,
        chunk_index
    )
    SELECT
        COALESCE((chunk->>'id')::UUID, gen_random_uuid()),
        (chunk->>'document_id')::UUID,
        chunk->>'content_encrypted',
        to_tsvector('simple', COALESCE(chunk->>'content_plaintext', '')),
        NULLIF(BTRIM(chunk->>'language'), ''),
        (chunk->>'embedding')::VECTOR(1536),
        (chunk->>'chunk_index')::INT
    FROM jsonb_array_elements(p_chunks) AS chunk
    RETURNING id, document_chunks.chunk_index;
END;
$$;

GRANT EXECUTE ON FUNCTION public.ingest_document_chunk(
    UUID,
    UUID,
    TEXT,
    TEXT,
    VECTOR(1536),
    INT,
    TEXT
) TO authenticated;

GRANT EXECUTE ON FUNCTION public.ingest_document_chunks_batch(JSONB) TO authenticated;

GRANT EXECUTE ON FUNCTION public.ingest_document_chunk(
    UUID,
    UUID,
    TEXT,
    TEXT,
    VECTOR(1536),
    INT,
    TEXT
) TO service_role;

GRANT EXECUTE ON FUNCTION public.ingest_document_chunks_batch(JSONB) TO service_role;

NOTIFY pgrst, 'reload config';

COMMIT;
