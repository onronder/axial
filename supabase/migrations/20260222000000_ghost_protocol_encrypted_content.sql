-- Migration: Ghost Protocol - Encrypted Content with Decoupled Search
--
-- This migration implements the "Zero-Retention" architecture:
-- 1. Adds content_search (TSVECTOR) column for keyword search
-- 2. content column will store encrypted text (application-level encryption)
-- 3. RPCs handle type-safe insertion with TSVECTOR conversion
-- 4. Hybrid search uses pre-computed TSVECTOR instead of on-the-fly conversion
--
-- Security Model:
-- - content: ENCRYPTED (AES-256 via Fernet) - stores sensitive text
-- - content_search: PLAINTEXT STEMS - only lexemes, not full text
--   (e.g., "financial strategy" -> "financ strategi")
--   This cannot reconstruct the original document.

BEGIN;

-- =============================================================================
-- STEP 1: Add content_search column for pre-computed TSVECTOR
-- =============================================================================

-- Add TSVECTOR column if it doesn't exist
DO $$
BEGIN
    IF NOT EXISTS (
        SELECT 1 FROM information_schema.columns 
        WHERE table_name = 'document_chunks' 
        AND column_name = 'content_search'
    ) THEN
        ALTER TABLE document_chunks ADD COLUMN content_search TSVECTOR;
        RAISE NOTICE 'Added content_search column to document_chunks';
    END IF;
END $$;

-- Create GIN index for fast keyword search
CREATE INDEX IF NOT EXISTS idx_document_chunks_content_search 
ON document_chunks USING GIN(content_search);


-- =============================================================================
-- STEP 2: RPC for single chunk insertion (type-safe)
-- =============================================================================
-- This handles TSVECTOR conversion server-side to avoid client type issues

DROP FUNCTION IF EXISTS ingest_document_chunk(UUID, UUID, TEXT, TEXT, VECTOR(1536), INT);

CREATE OR REPLACE FUNCTION ingest_document_chunk(
    p_id UUID,
    p_document_id UUID,
    p_content_encrypted TEXT,
    p_content_plaintext TEXT,
    p_embedding VECTOR(1536),
    p_chunk_index INT
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
        embedding,
        chunk_index
    ) VALUES (
        COALESCE(p_id, gen_random_uuid()),
        p_document_id,
        p_content_encrypted,
        to_tsvector('english', COALESCE(p_content_plaintext, '')),
        p_embedding,
        p_chunk_index
    )
    RETURNING id INTO v_inserted_id;
    
    RETURN v_inserted_id;
END;
$$;


-- =============================================================================
-- STEP 3: RPC for batch chunk insertion (high-performance)
-- =============================================================================
-- Accepts JSONB array of chunks for efficient bulk insert

DROP FUNCTION IF EXISTS ingest_document_chunks_batch(JSONB);

CREATE OR REPLACE FUNCTION ingest_document_chunks_batch(
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
        embedding,
        chunk_index
    )
    SELECT
        COALESCE((chunk->>'id')::UUID, gen_random_uuid()),
        (chunk->>'document_id')::UUID,
        chunk->>'content_encrypted',
        to_tsvector('english', COALESCE(chunk->>'content_plaintext', '')),
        (chunk->>'embedding')::VECTOR(1536),
        (chunk->>'chunk_index')::INT
    FROM jsonb_array_elements(p_chunks) AS chunk
    RETURNING id, document_chunks.chunk_index;
END;
$$;


-- =============================================================================
-- STEP 4: Update hybrid_search to use pre-computed TSVECTOR
-- =============================================================================
-- Falls back to on-the-fly computation if content_search is NULL (migration period)

CREATE OR REPLACE FUNCTION hybrid_search(
    query_text TEXT,
    query_embedding VECTOR(1536),
    match_count INT DEFAULT 10,
    filter_org_id UUID DEFAULT NULL,
    vector_weight FLOAT DEFAULT 0.7,
    keyword_weight FLOAT DEFAULT 0.3,
    similarity_threshold FLOAT DEFAULT 0.25
)
RETURNS TABLE (
    id UUID,
    content TEXT,
    document_id UUID,
    chunk_index INT,
    source_type TEXT,
    scope_id TEXT,
    title TEXT,
    metadata JSONB,
    vector_score FLOAT,
    keyword_score FLOAT,
    combined_score FLOAT
) AS $$
BEGIN
    RETURN QUERY
    WITH semantic_results AS (
        SELECT 
            dc.id,
            dc.content,
            dc.document_id,
            dc.chunk_index,
            d.source_type::text as source_type,
            d.scope_id,
            d.title,
            d.metadata,
            (1 - (dc.embedding <=> query_embedding))::FLOAT as score,
            ROW_NUMBER() OVER (ORDER BY dc.embedding <=> query_embedding) as rank
        FROM document_chunks dc
        JOIN documents d ON dc.document_id = d.id
        WHERE (filter_org_id IS NULL OR d.organization_id = filter_org_id)
          AND COALESCE(d.source_type::text, '') NOT IN ('identity', 'scope_identity')
          AND COALESCE(d.metadata->>'type', '') != 'identity_card'
          AND COALESCE(lower(d.metadata->>'is_identity'), 'false') != 'true'
          AND (1 - (dc.embedding <=> query_embedding)) >= similarity_threshold
        ORDER BY dc.embedding <=> query_embedding
        LIMIT match_count * 3
    ),
    keyword_results AS (
        SELECT 
            dc.id,
            dc.content,
            dc.document_id,
            dc.chunk_index,
            d.source_type::text as source_type,
            d.scope_id,
            d.title,
            d.metadata,
            -- Use pre-computed TSVECTOR if available, fallback to on-the-fly
            ts_rank_cd(
                COALESCE(dc.content_search, to_tsvector('english', dc.content)), 
                plainto_tsquery('english', query_text),
                32
            )::FLOAT as score,
            ROW_NUMBER() OVER (
                ORDER BY ts_rank_cd(
                    COALESCE(dc.content_search, to_tsvector('english', dc.content)),
                    plainto_tsquery('english', query_text),
                    32
                ) DESC
            ) as rank
        FROM document_chunks dc
        JOIN documents d ON dc.document_id = d.id
        WHERE (filter_org_id IS NULL OR d.organization_id = filter_org_id)
          AND COALESCE(d.source_type::text, '') NOT IN ('identity', 'scope_identity')
          AND COALESCE(d.metadata->>'type', '') != 'identity_card'
          AND COALESCE(lower(d.metadata->>'is_identity'), 'false') != 'true'
          -- Use pre-computed TSVECTOR if available
          AND COALESCE(dc.content_search, to_tsvector('english', dc.content)) @@ plainto_tsquery('english', query_text)
        ORDER BY score DESC
        LIMIT match_count * 3
    ),
    combined AS (
        SELECT 
            COALESCE(s.id, k.id) as id,
            COALESCE(s.content, k.content) as content,
            COALESCE(s.document_id, k.document_id) as document_id,
            COALESCE(s.chunk_index, k.chunk_index) as chunk_index,
            COALESCE(s.source_type, k.source_type) as source_type,
            COALESCE(s.scope_id, k.scope_id) as scope_id,
            COALESCE(s.title, k.title) as title,
            COALESCE(s.metadata, k.metadata) as metadata,
            COALESCE(s.score, 0)::FLOAT as vector_score,
            COALESCE(k.score, 0)::FLOAT as keyword_score,
            (
                vector_weight * COALESCE(1.0 / (60 + s.rank), 0) + 
                keyword_weight * COALESCE(1.0 / (60 + k.rank), 0)
            )::FLOAT as combined_score
        FROM semantic_results s
        FULL OUTER JOIN keyword_results k ON s.id = k.id
    )
    SELECT 
        c.id,
        c.content,
        c.document_id,
        c.chunk_index,
        c.source_type,
        c.scope_id,
        c.title,
        c.metadata,
        c.vector_score,
        c.keyword_score,
        c.combined_score
    FROM combined c
    ORDER BY c.combined_score DESC
    LIMIT match_count;
END;
$$ LANGUAGE plpgsql STABLE;


-- =============================================================================
-- STEP 5: Update hybrid_search_scoped to use pre-computed TSVECTOR
-- =============================================================================

CREATE OR REPLACE FUNCTION hybrid_search_scoped(
    query_text TEXT,
    query_embedding VECTOR(1536),
    match_count INT DEFAULT 10,
    filter_org_id UUID DEFAULT NULL,
    filter_scope_ids TEXT[] DEFAULT NULL,
    vector_weight FLOAT DEFAULT 0.7,
    keyword_weight FLOAT DEFAULT 0.3,
    similarity_threshold FLOAT DEFAULT 0.25
)
RETURNS TABLE (
    id UUID,
    content TEXT,
    document_id UUID,
    chunk_index INT,
    source_type TEXT,
    scope_id TEXT,
    title TEXT,
    metadata JSONB,
    vector_score FLOAT,
    keyword_score FLOAT,
    combined_score FLOAT
) AS $$
BEGIN
    RETURN QUERY
    WITH semantic_results AS (
        SELECT 
            dc.id,
            dc.content,
            dc.document_id,
            dc.chunk_index,
            d.source_type::text as source_type,
            d.scope_id,
            d.title,
            d.metadata,
            (1 - (dc.embedding <=> query_embedding))::FLOAT as score,
            ROW_NUMBER() OVER (ORDER BY dc.embedding <=> query_embedding) as rank
        FROM document_chunks dc
        JOIN documents d ON dc.document_id = d.id
        WHERE (filter_org_id IS NULL OR d.organization_id = filter_org_id)
          AND (filter_scope_ids IS NULL OR d.scope_id = ANY(filter_scope_ids))
          AND COALESCE(d.source_type::text, '') NOT IN ('identity', 'scope_identity')
          AND COALESCE(d.metadata->>'type', '') != 'identity_card'
          AND COALESCE(lower(d.metadata->>'is_identity'), 'false') != 'true'
          AND (1 - (dc.embedding <=> query_embedding)) >= similarity_threshold
        ORDER BY dc.embedding <=> query_embedding
        LIMIT match_count * 3
    ),
    keyword_results AS (
        SELECT 
            dc.id,
            dc.content,
            dc.document_id,
            dc.chunk_index,
            d.source_type::text as source_type,
            d.scope_id,
            d.title,
            d.metadata,
            -- Use pre-computed TSVECTOR if available, fallback to on-the-fly
            ts_rank_cd(
                COALESCE(dc.content_search, to_tsvector('english', dc.content)), 
                plainto_tsquery('english', query_text),
                32
            )::FLOAT as score,
            ROW_NUMBER() OVER (
                ORDER BY ts_rank_cd(
                    COALESCE(dc.content_search, to_tsvector('english', dc.content)),
                    plainto_tsquery('english', query_text),
                    32
                ) DESC
            ) as rank
        FROM document_chunks dc
        JOIN documents d ON dc.document_id = d.id
        WHERE (filter_org_id IS NULL OR d.organization_id = filter_org_id)
          AND (filter_scope_ids IS NULL OR d.scope_id = ANY(filter_scope_ids))
          AND COALESCE(d.source_type::text, '') NOT IN ('identity', 'scope_identity')
          AND COALESCE(d.metadata->>'type', '') != 'identity_card'
          AND COALESCE(lower(d.metadata->>'is_identity'), 'false') != 'true'
          -- Use pre-computed TSVECTOR if available
          AND COALESCE(dc.content_search, to_tsvector('english', dc.content)) @@ plainto_tsquery('english', query_text)
        ORDER BY score DESC
        LIMIT match_count * 3
    ),
    combined AS (
        SELECT 
            COALESCE(s.id, k.id) as id,
            COALESCE(s.content, k.content) as content,
            COALESCE(s.document_id, k.document_id) as document_id,
            COALESCE(s.chunk_index, k.chunk_index) as chunk_index,
            COALESCE(s.source_type, k.source_type) as source_type,
            COALESCE(s.scope_id, k.scope_id) as scope_id,
            COALESCE(s.title, k.title) as title,
            COALESCE(s.metadata, k.metadata) as metadata,
            COALESCE(s.score, 0)::FLOAT as vector_score,
            COALESCE(k.score, 0)::FLOAT as keyword_score,
            (
                vector_weight * COALESCE(1.0 / (60 + s.rank), 0) + 
                keyword_weight * COALESCE(1.0 / (60 + k.rank), 0)
            )::FLOAT as combined_score
        FROM semantic_results s
        FULL OUTER JOIN keyword_results k ON s.id = k.id
    )
    SELECT 
        c.id,
        c.content,
        c.document_id,
        c.chunk_index,
        c.source_type,
        c.scope_id,
        c.title,
        c.metadata,
        c.vector_score,
        c.keyword_score,
        c.combined_score
    FROM combined c
    ORDER BY c.combined_score DESC
    LIMIT match_count;
END;
$$ LANGUAGE plpgsql STABLE;


-- =============================================================================
-- STEP 6: Grant permissions for ingestion service
-- =============================================================================

-- Grant execute permissions to authenticated users
GRANT EXECUTE ON FUNCTION ingest_document_chunk(UUID, UUID, TEXT, TEXT, VECTOR(1536), INT) TO authenticated;
GRANT EXECUTE ON FUNCTION ingest_document_chunks_batch(JSONB) TO authenticated;

-- Grant to service role (for backend ingestion)
GRANT EXECUTE ON FUNCTION ingest_document_chunk(UUID, UUID, TEXT, TEXT, VECTOR(1536), INT) TO service_role;
GRANT EXECUTE ON FUNCTION ingest_document_chunks_batch(JSONB) TO service_role;


-- =============================================================================
-- STEP 7: Add comment documenting the encryption model
-- =============================================================================

COMMENT ON COLUMN document_chunks.content IS 
'ENCRYPTED (AES-256 Fernet). Contains the full chunk text, encrypted at application level. 
Decryption key is CHUNK_ENCRYPTION_KEY env var. 
Ghost Protocol: This column cannot be searched directly.';

COMMENT ON COLUMN document_chunks.content_search IS 
'PLAINTEXT STEMS (TSVECTOR). Contains only word stems for keyword search.
Example: "financial strategy document" -> ''document'' ''financ'' ''strategi''
Cannot reconstruct original text. Used by hybrid_search functions.';

COMMENT ON FUNCTION ingest_document_chunk IS
'Ghost Protocol RPC: Insert a single document chunk with type-safe TSVECTOR conversion.
Accepts encrypted content and plaintext for search index generation.';

COMMENT ON FUNCTION ingest_document_chunks_batch IS
'Ghost Protocol RPC: Insert multiple document chunks in a single transaction.
Accepts JSONB array with content_encrypted, content_plaintext, embedding, etc.
High-performance bulk insert for ingestion pipeline.';

COMMIT;
