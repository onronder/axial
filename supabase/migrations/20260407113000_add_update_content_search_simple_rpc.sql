-- =============================================================================
-- Migration: Add helper RPC for content_search backfill
-- Created: 2026-04-07
--
-- Purpose:
-- - Support application-side Ghost Protocol backfill for existing chunks
-- - Recompute document_chunks.content_search using the globally normalized
--   'simple' regconfig without persisting plaintext content
-- =============================================================================

BEGIN;

DROP FUNCTION IF EXISTS public.update_content_search_simple(UUID, TEXT);

CREATE OR REPLACE FUNCTION public.update_content_search_simple(
    chunk_id UUID,
    plaintext TEXT
)
RETURNS VOID
LANGUAGE plpgsql
SECURITY DEFINER
SET search_path = public
AS $$
BEGIN
    UPDATE document_chunks
    SET content_search = to_tsvector('simple', COALESCE(plaintext, ''))
    WHERE id = chunk_id;
END;
$$;

GRANT EXECUTE ON FUNCTION public.update_content_search_simple(UUID, TEXT) TO service_role;

NOTIFY pgrst, 'reload config';

COMMIT;
