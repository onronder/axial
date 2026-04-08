-- =============================================================================
-- Migration: Re-grant Ghost Protocol ingest RPC permissions
-- Created: 2026-04-07
--
-- Purpose:
-- - Remove migration-order coupling after CREATE OR REPLACE of ingest RPCs
-- - Explicitly re-assert execute permissions for both authenticated users
--   and service_role on Ghost Protocol ingest functions
-- =============================================================================

BEGIN;

GRANT EXECUTE ON FUNCTION public.ingest_document_chunk(
    UUID,
    UUID,
    TEXT,
    TEXT,
    VECTOR(1536),
    INT
) TO authenticated;

GRANT EXECUTE ON FUNCTION public.ingest_document_chunks_batch(JSONB) TO authenticated;

GRANT EXECUTE ON FUNCTION public.ingest_document_chunk(
    UUID,
    UUID,
    TEXT,
    TEXT,
    VECTOR(1536),
    INT
) TO service_role;

GRANT EXECUTE ON FUNCTION public.ingest_document_chunks_batch(JSONB) TO service_role;

NOTIFY pgrst, 'reload config';

COMMIT;
