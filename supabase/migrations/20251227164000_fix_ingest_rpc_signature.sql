-- Migration: Fix ingest RPC function signature
-- Drops old signature and recreates with file_size_bytes parameter
-- Created: 2025-12-27

-- ============================================================
-- FIX: Drop old function signature first
-- ============================================================
-- The old function has 6 parameters, new one has 7
-- PostgreSQL treats these as different functions (overloading)

DROP FUNCTION IF EXISTS public.ingest_document_with_chunks(UUID, TEXT, TEXT, TEXT, JSONB, JSONB);

-- ============================================================
-- RECREATE: ingest_document_with_chunks with file_size_bytes
-- ============================================================

CREATE OR REPLACE FUNCTION public.ingest_document_with_chunks(
    p_user_id UUID,
    p_doc_title TEXT,
    p_source_type TEXT,
    p_source_url TEXT,
    p_metadata JSONB,
    p_chunks JSONB,
    p_file_size_bytes BIGINT DEFAULT 0  -- Track file size for quotas
) RETURNS UUID 
LANGUAGE plpgsql 
SECURITY DEFINER
SET search_path = public
AS $$
DECLARE
    v_doc_id UUID;
    chunk_record JSONB;
    v_chunk_index INT := 0;
BEGIN
    -- 1. Insert Parent Document with file_size_bytes
    INSERT INTO documents (user_id, title, source_type, source_url, metadata, file_size_bytes, created_at)
    VALUES (p_user_id, p_doc_title, p_source_type, p_source_url, p_metadata, COALESCE(p_file_size_bytes, 0), NOW())
    RETURNING id INTO v_doc_id;

    -- 2. Insert Chunks in a single transaction
    FOR chunk_record IN SELECT * FROM jsonb_array_elements(p_chunks)
    LOOP
        INSERT INTO document_chunks (
            document_id, 
            content, 
            embedding, 
            chunk_index, 
            created_at
        ) VALUES (
            v_doc_id,
            chunk_record->>'content',
            (chunk_record->>'embedding')::vector,
            COALESCE((chunk_record->>'chunk_index')::int, v_chunk_index),
            NOW()
        );
        v_chunk_index := v_chunk_index + 1;
    END LOOP;

    RETURN v_doc_id;
END;
$$;

-- Re-grant permissions (specific to 7-param version)
GRANT EXECUTE ON FUNCTION public.ingest_document_with_chunks(UUID, TEXT, TEXT, TEXT, JSONB, JSONB, BIGINT) TO authenticated;
GRANT EXECUTE ON FUNCTION public.ingest_document_with_chunks(UUID, TEXT, TEXT, TEXT, JSONB, JSONB, BIGINT) TO service_role;

-- Update comment
COMMENT ON FUNCTION public.ingest_document_with_chunks(UUID, TEXT, TEXT, TEXT, JSONB, JSONB, BIGINT) IS 
'Atomic ingestion: Creates document and all chunks in single transaction. 
Tracks file_size_bytes for quota enforcement. SECURITY: Fixed search_path.';

-- Notify PostgREST
NOTIFY pgrst, 'reload config';
