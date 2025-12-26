-- Migration: Optimize Vector Search for High Scale (100k+ users)
-- Created: 2025-12-26
-- Purpose: HNSW indexing for sub-second search, atomic batch ingestion

-- ============================================================
-- 1. ENABLE REQUIRED EXTENSIONS
-- ============================================================

-- pg_trgm for fast text similarity search
CREATE EXTENSION IF NOT EXISTS pg_trgm;

-- Ensure pgvector is enabled (should already exist)
CREATE EXTENSION IF NOT EXISTS vector;


-- ============================================================
-- 2. HNSW INDEX FOR VECTOR SEARCH (Critical for Scale)
-- ============================================================
-- HNSW (Hierarchical Navigable Small World) provides:
-- - O(log n) search time vs O(n) for brute force
-- - Maintains high recall (>95%)
-- - Essential for 100k+ users with millions of chunks

-- Drop existing index if it's IVFFlat (slower for our use case)
DROP INDEX IF EXISTS document_chunks_embedding_idx;

-- Create HNSW index with tuned parameters
-- m = 16: Good balance of memory vs recall
-- ef_construction = 64: Build quality (higher = better recall, slower build)
CREATE INDEX IF NOT EXISTS document_chunks_embedding_hnsw 
ON document_chunks USING hnsw (embedding vector_cosine_ops) 
WITH (m = 16, ef_construction = 64);


-- ============================================================
-- 3. GIN INDEX FOR METADATA FILTERING
-- ============================================================
-- Enables fast filtering by source_type, file_id, etc.

CREATE INDEX IF NOT EXISTS documents_metadata_gin 
ON documents USING gin (metadata);

-- Index for user_id lookups (likely already exists but ensure it does)
CREATE INDEX IF NOT EXISTS documents_user_id_idx 
ON documents (user_id);

CREATE INDEX IF NOT EXISTS document_chunks_document_id_idx 
ON document_chunks (document_id);


-- ============================================================
-- 4. ATOMIC INGESTION RPC FUNCTION
-- ============================================================
-- Performs document + chunks insertion in a SINGLE transaction
-- Benefits:
-- - All-or-nothing: No partial data on failure
-- - Faster: Single DB roundtrip vs multiple API calls
-- - Less network overhead: Chunks sent as JSONB array

CREATE OR REPLACE FUNCTION ingest_document_with_chunks(
    p_user_id UUID,
    p_doc_title TEXT,
    p_source_type TEXT,
    p_source_url TEXT,
    p_metadata JSONB,
    p_chunks JSONB
) RETURNS UUID AS $$
DECLARE
    v_doc_id UUID;
    chunk_record JSONB;
    v_chunk_index INT := 0;
BEGIN
    -- 1. Insert Parent Document
    INSERT INTO documents (user_id, title, source_type, source_url, metadata, created_at)
    VALUES (p_user_id, p_doc_title, p_source_type, p_source_url, p_metadata, NOW())
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
$$ LANGUAGE plpgsql SECURITY DEFINER;

-- Grant execute to authenticated users
GRANT EXECUTE ON FUNCTION ingest_document_with_chunks TO authenticated;
GRANT EXECUTE ON FUNCTION ingest_document_with_chunks TO service_role;


-- ============================================================
-- 5. BATCH DELETE FUNCTION (For Document Cleanup)
-- ============================================================
-- Deletes document and all its chunks atomically

CREATE OR REPLACE FUNCTION delete_document_with_chunks(
    p_document_id UUID,
    p_user_id UUID
) RETURNS BOOLEAN AS $$
DECLARE
    v_deleted BOOLEAN := FALSE;
BEGIN
    -- Verify ownership before delete
    IF EXISTS (SELECT 1 FROM documents WHERE id = p_document_id AND user_id = p_user_id) THEN
        -- Delete chunks first (foreign key constraint)
        DELETE FROM document_chunks WHERE document_id = p_document_id;
        
        -- Delete parent document
        DELETE FROM documents WHERE id = p_document_id AND user_id = p_user_id;
        
        v_deleted := TRUE;
    END IF;
    
    RETURN v_deleted;
END;
$$ LANGUAGE plpgsql SECURITY DEFINER;

GRANT EXECUTE ON FUNCTION delete_document_with_chunks TO authenticated;
GRANT EXECUTE ON FUNCTION delete_document_with_chunks TO service_role;


-- ============================================================
-- 6. OPTIMIZED VECTOR SEARCH FUNCTION
-- ============================================================
-- Pre-filters by user_id, then does vector similarity search

CREATE OR REPLACE FUNCTION search_similar_chunks(
    p_user_id UUID,
    p_query_embedding vector,
    p_limit INT DEFAULT 5,
    p_similarity_threshold FLOAT DEFAULT 0.7
) RETURNS TABLE (
    chunk_id UUID,
    document_id UUID,
    content TEXT,
    similarity FLOAT,
    doc_title TEXT,
    source_type TEXT,
    source_url TEXT
) AS $$
BEGIN
    RETURN QUERY
    SELECT 
        dc.id as chunk_id,
        dc.document_id,
        dc.content,
        1 - (dc.embedding <=> p_query_embedding) as similarity,
        d.title as doc_title,
        d.source_type,
        d.source_url
    FROM document_chunks dc
    JOIN documents d ON dc.document_id = d.id
    WHERE d.user_id = p_user_id
      AND 1 - (dc.embedding <=> p_query_embedding) >= p_similarity_threshold
    ORDER BY dc.embedding <=> p_query_embedding
    LIMIT p_limit;
END;
$$ LANGUAGE plpgsql SECURITY DEFINER;

GRANT EXECUTE ON FUNCTION search_similar_chunks TO authenticated;
GRANT EXECUTE ON FUNCTION search_similar_chunks TO service_role;


-- ============================================================
-- 7. ANALYZE TABLES (Update Statistics for Query Planner)
-- ============================================================
ANALYZE documents;
ANALYZE document_chunks;


-- Refresh Supabase Schema Cache
NOTIFY pgrst, 'reload config';
