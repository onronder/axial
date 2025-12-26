-- =============================================================================
-- Security Hardening: Fix Mutable Search Path Vulnerabilities
-- =============================================================================
-- Created: 2025-12-26
-- Purpose: Fix "Function Search Path Mutable" security warnings flagged by
--          Supabase Security Advisor
-- 
-- All functions are updated with:
--   SET search_path = public
-- This prevents potential schema injection attacks where malicious objects
-- in other schemas could intercept function calls.
-- =============================================================================


-- ============================================================
-- 1. FIX: ingest_document_with_chunks
-- ============================================================

CREATE OR REPLACE FUNCTION public.ingest_document_with_chunks(
    p_user_id UUID,
    p_doc_title TEXT,
    p_source_type TEXT,
    p_source_url TEXT,
    p_metadata JSONB,
    p_chunks JSONB
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
$$;


-- ============================================================
-- 2. FIX: delete_document_with_chunks
-- ============================================================

CREATE OR REPLACE FUNCTION public.delete_document_with_chunks(
    p_document_id UUID,
    p_user_id UUID
) RETURNS BOOLEAN 
LANGUAGE plpgsql 
SECURITY DEFINER
SET search_path = public
AS $$
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
$$;


-- ============================================================
-- 3. FIX: search_similar_chunks
-- ============================================================

CREATE OR REPLACE FUNCTION public.search_similar_chunks(
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
) 
LANGUAGE plpgsql 
SECURITY DEFINER
SET search_path = public
AS $$
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
$$;


-- ============================================================
-- 4. FIX: hybrid_search
-- ============================================================

CREATE OR REPLACE FUNCTION public.hybrid_search(
    query_text TEXT,
    query_embedding VECTOR(1536),
    match_count INT DEFAULT 10,
    filter_user_id UUID DEFAULT NULL,
    vector_weight FLOAT DEFAULT 0.7,
    keyword_weight FLOAT DEFAULT 0.3,
    similarity_threshold FLOAT DEFAULT 0.3
)
RETURNS TABLE (
    id UUID,
    content TEXT,
    document_id UUID,
    chunk_index INT,
    source_type TEXT,
    title TEXT,
    metadata JSONB,
    vector_score FLOAT,
    keyword_score FLOAT,
    combined_score FLOAT
) 
LANGUAGE plpgsql 
STABLE
SET search_path = public
AS $$
BEGIN
    RETURN QUERY
    WITH 
    -- Semantic search using vector similarity
    semantic AS (
        SELECT 
            dc.id,
            dc.content,
            dc.document_id,
            dc.chunk_index,
            d.source_type::text as source_type,
            d.title,
            d.metadata,
            (1 - (dc.embedding <=> query_embedding))::FLOAT as score,
            ROW_NUMBER() OVER (ORDER BY dc.embedding <=> query_embedding) as rank
        FROM document_chunks dc
        JOIN documents d ON dc.document_id = d.id
        WHERE (filter_user_id IS NULL OR d.user_id = filter_user_id)
          AND (1 - (dc.embedding <=> query_embedding)) > similarity_threshold
        LIMIT match_count * 3
    ),
    
    -- Keyword search using PostgreSQL full-text search
    keyword AS (
        SELECT 
            dc.id,
            dc.content,
            dc.document_id,
            dc.chunk_index,
            d.source_type::text as source_type,
            d.title,
            d.metadata,
            ts_rank_cd(
                to_tsvector('english', dc.content), 
                plainto_tsquery('english', query_text),
                32
            )::FLOAT as score,
            ROW_NUMBER() OVER (
                ORDER BY ts_rank_cd(
                    to_tsvector('english', dc.content), 
                    plainto_tsquery('english', query_text),
                    32
                ) DESC
            ) as rank
        FROM document_chunks dc
        JOIN documents d ON dc.document_id = d.id
        WHERE (filter_user_id IS NULL OR d.user_id = filter_user_id)
          AND to_tsvector('english', dc.content) @@ plainto_tsquery('english', query_text)
        LIMIT match_count * 3
    ),
    
    -- Combine using Reciprocal Rank Fusion (RRF)
    combined AS (
        SELECT 
            COALESCE(s.id, k.id) as id,
            COALESCE(s.content, k.content) as content,
            COALESCE(s.document_id, k.document_id) as document_id,
            COALESCE(s.chunk_index, k.chunk_index) as chunk_index,
            COALESCE(s.source_type, k.source_type) as source_type,
            COALESCE(s.title, k.title) as title,
            COALESCE(s.metadata, k.metadata) as metadata,
            COALESCE(s.score, 0)::FLOAT as vector_score,
            COALESCE(k.score, 0)::FLOAT as keyword_score,
            (
                vector_weight * COALESCE(1.0 / (60 + s.rank), 0) + 
                keyword_weight * COALESCE(1.0 / (60 + k.rank), 0)
            )::FLOAT as combined_score
        FROM semantic s
        FULL OUTER JOIN keyword k ON s.id = k.id
    )
    
    SELECT 
        c.id,
        c.content,
        c.document_id,
        c.chunk_index,
        c.source_type,
        c.title,
        c.metadata,
        c.vector_score,
        c.keyword_score,
        c.combined_score
    FROM combined c
    ORDER BY c.combined_score DESC
    LIMIT match_count;
END;
$$;


-- ============================================================
-- 5. FIX: match_documents
-- ============================================================

CREATE OR REPLACE FUNCTION public.match_documents(
    query_embedding VECTOR(1536),
    match_threshold FLOAT DEFAULT 0.5,
    match_count INT DEFAULT 5,
    filter_user_id UUID DEFAULT NULL
)
RETURNS TABLE (
    id UUID,
    content TEXT,
    document_id UUID,
    chunk_index INT,
    source_type TEXT,
    title TEXT,
    metadata JSONB,
    similarity FLOAT
) 
LANGUAGE plpgsql 
STABLE
SET search_path = public
AS $$
BEGIN
    RETURN QUERY
    SELECT 
        dc.id,
        dc.content,
        dc.document_id,
        dc.chunk_index,
        d.source_type::text as source_type,
        d.title,
        d.metadata,
        (1 - (dc.embedding <=> query_embedding))::FLOAT as similarity
    FROM document_chunks dc
    JOIN documents d ON dc.document_id = d.id
    WHERE (filter_user_id IS NULL OR d.user_id = filter_user_id)
      AND (1 - (dc.embedding <=> query_embedding)) > match_threshold
    ORDER BY dc.embedding <=> query_embedding
    LIMIT match_count;
END;
$$;


-- ============================================================
-- 6. FIX: update_sync_state_timestamp (Trigger Function)
-- ============================================================

CREATE OR REPLACE FUNCTION public.update_sync_state_timestamp()
RETURNS TRIGGER 
LANGUAGE plpgsql
SET search_path = public
AS $$
BEGIN
    NEW.updated_at = NOW();
    RETURN NEW;
END;
$$;


-- ============================================================
-- 7. NEW: increment_crawl_counter (For Distributed Crawler)
-- ============================================================
-- Atomic counter increment for tracking crawl progress

CREATE OR REPLACE FUNCTION public.increment_crawl_counter(
    p_crawl_id UUID,
    p_field TEXT
) RETURNS VOID 
LANGUAGE plpgsql 
SECURITY DEFINER
SET search_path = public
AS $$
BEGIN
    IF p_field = 'pages_ingested' THEN
        UPDATE web_crawl_configs 
        SET pages_ingested = COALESCE(pages_ingested, 0) + 1,
            updated_at = NOW()
        WHERE id = p_crawl_id;
    ELSIF p_field = 'pages_failed' THEN
        UPDATE web_crawl_configs 
        SET pages_failed = COALESCE(pages_failed, 0) + 1,
            updated_at = NOW()
        WHERE id = p_crawl_id;
    END IF;
END;
$$;

GRANT EXECUTE ON FUNCTION public.increment_crawl_counter TO authenticated;
GRANT EXECUTE ON FUNCTION public.increment_crawl_counter TO service_role;


-- ============================================================
-- RE-GRANT PERMISSIONS (Ensure they're still in place)
-- ============================================================

GRANT EXECUTE ON FUNCTION public.ingest_document_with_chunks TO authenticated;
GRANT EXECUTE ON FUNCTION public.ingest_document_with_chunks TO service_role;
GRANT EXECUTE ON FUNCTION public.delete_document_with_chunks TO authenticated;
GRANT EXECUTE ON FUNCTION public.delete_document_with_chunks TO service_role;
GRANT EXECUTE ON FUNCTION public.search_similar_chunks TO authenticated;
GRANT EXECUTE ON FUNCTION public.search_similar_chunks TO service_role;
GRANT EXECUTE ON FUNCTION public.hybrid_search TO authenticated;
GRANT EXECUTE ON FUNCTION public.hybrid_search TO service_role;
GRANT EXECUTE ON FUNCTION public.match_documents TO authenticated;
GRANT EXECUTE ON FUNCTION public.match_documents TO service_role;


-- ============================================================
-- NOTIFY POSTGREST TO RELOAD SCHEMA
-- ============================================================

NOTIFY pgrst, 'reload config';


-- ============================================================
-- COMMENTS
-- ============================================================

COMMENT ON FUNCTION public.ingest_document_with_chunks IS 
'Atomic ingestion: Creates document and all chunks in single transaction. SECURITY: Fixed search_path.';

COMMENT ON FUNCTION public.delete_document_with_chunks IS 
'Atomic deletion: Removes document and all chunks. SECURITY: Fixed search_path.';

COMMENT ON FUNCTION public.search_similar_chunks IS 
'Vector similarity search with user isolation. SECURITY: Fixed search_path.';

COMMENT ON FUNCTION public.hybrid_search IS 
'Hybrid vector + keyword search using RRF. SECURITY: Fixed search_path.';

COMMENT ON FUNCTION public.match_documents IS 
'Simple vector similarity search. SECURITY: Fixed search_path.';

COMMENT ON FUNCTION public.increment_crawl_counter IS 
'Atomic counter for distributed crawler progress tracking. SECURITY: Fixed search_path.';
