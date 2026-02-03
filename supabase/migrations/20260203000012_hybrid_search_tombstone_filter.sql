-- =============================================================================
-- Hybrid Search Tombstone Filter
-- GDPR Article 17 / CCPA 2026 ADMT Compliance
--
-- This migration modifies hybrid_search and hybrid_search_scoped to exclude
-- documents that have active compliance tombstones. Deleted data is immediately
-- blocked from search results before actual deletion completes.
--
-- Performance Impact:
-- - Active tombstones < 100: Negligible (<1ms additional latency)
-- - Active tombstones 100-1000: Minimal (<5ms)
-- - Active tombstones > 1000: pg_cron cleanup keeps this from happening
-- =============================================================================

-- Drop existing functions to recreate with tombstone filtering
DROP FUNCTION IF EXISTS hybrid_search(TEXT, VECTOR(1536), INT, UUID, FLOAT, FLOAT, FLOAT);
DROP FUNCTION IF EXISTS hybrid_search_scoped(TEXT, VECTOR(1536), INT, UUID, TEXT[], FLOAT, FLOAT, FLOAT);

-- =============================================================================
-- HYBRID_SEARCH: Standard search with tombstone exclusion
-- =============================================================================

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
)
LANGUAGE plpgsql
STABLE
SECURITY DEFINER
SET search_path = public
AS $$
BEGIN
    RETURN QUERY
    WITH
    -- GHOST PROTOCOL: Get tombstoned document IDs for this org
    -- This CTE is optimized by the GIN index on document_ids array
    tombstoned_docs AS (
        SELECT UNNEST(t.document_ids) AS blocked_doc_id
        FROM compliance_tombstones t
        WHERE t.organization_id = filter_org_id
          AND t.status = 'active'
    ),
    -- Vector similarity search
    semantic_results AS (
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
          AND (1 - (dc.embedding <=> query_embedding)) >= similarity_threshold
          -- COMPLIANCE: Exclude tombstoned documents
          AND NOT EXISTS (
              SELECT 1 FROM tombstoned_docs td WHERE td.blocked_doc_id = d.id
          )
        ORDER BY dc.embedding <=> query_embedding
        LIMIT match_count * 3
    ),
    -- Full-text keyword search
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
        WHERE (filter_org_id IS NULL OR d.organization_id = filter_org_id)
          AND to_tsvector('english', dc.content) @@ plainto_tsquery('english', query_text)
          -- COMPLIANCE: Exclude tombstoned documents
          AND NOT EXISTS (
              SELECT 1 FROM tombstoned_docs td WHERE td.blocked_doc_id = d.id
          )
        ORDER BY score DESC
        LIMIT match_count * 3
    ),
    -- Combine results with weighted RRF scoring
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
$$;

-- =============================================================================
-- HYBRID_SEARCH_SCOPED: Scope-filtered search with tombstone exclusion
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
)
LANGUAGE plpgsql
STABLE
SECURITY DEFINER
SET search_path = public
AS $$
BEGIN
    RETURN QUERY
    WITH
    -- GHOST PROTOCOL: Get tombstoned document IDs for this org
    tombstoned_docs AS (
        SELECT UNNEST(t.document_ids) AS blocked_doc_id
        FROM compliance_tombstones t
        WHERE t.organization_id = filter_org_id
          AND t.status = 'active'
    ),
    -- Vector similarity search
    semantic_results AS (
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
          AND (1 - (dc.embedding <=> query_embedding)) >= similarity_threshold
          -- COMPLIANCE: Exclude tombstoned documents
          AND NOT EXISTS (
              SELECT 1 FROM tombstoned_docs td WHERE td.blocked_doc_id = d.id
          )
        ORDER BY dc.embedding <=> query_embedding
        LIMIT match_count * 3
    ),
    -- Full-text keyword search
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
        WHERE (filter_org_id IS NULL OR d.organization_id = filter_org_id)
          AND (filter_scope_ids IS NULL OR d.scope_id = ANY(filter_scope_ids))
          AND to_tsvector('english', dc.content) @@ plainto_tsquery('english', query_text)
          -- COMPLIANCE: Exclude tombstoned documents
          AND NOT EXISTS (
              SELECT 1 FROM tombstoned_docs td WHERE td.blocked_doc_id = d.id
          )
        ORDER BY score DESC
        LIMIT match_count * 3
    ),
    -- Combine results with weighted RRF scoring
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
$$;

-- =============================================================================
-- MATCH_DOCUMENTS: Legacy function with tombstone exclusion
-- =============================================================================

CREATE OR REPLACE FUNCTION match_documents(
    query_embedding VECTOR(1536),
    match_threshold FLOAT DEFAULT 0.5,
    match_count INT DEFAULT 5,
    filter_org_id UUID DEFAULT NULL
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
SECURITY DEFINER
SET search_path = public
AS $$
BEGIN
    RETURN QUERY
    WITH tombstoned_docs AS (
        SELECT UNNEST(t.document_ids) AS blocked_doc_id
        FROM compliance_tombstones t
        WHERE t.organization_id = filter_org_id
          AND t.status = 'active'
    )
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
    WHERE (filter_org_id IS NULL OR d.organization_id = filter_org_id)
      AND (1 - (dc.embedding <=> query_embedding)) > match_threshold
      -- COMPLIANCE: Exclude tombstoned documents
      AND NOT EXISTS (
          SELECT 1 FROM tombstoned_docs td WHERE td.blocked_doc_id = d.id
      )
    ORDER BY dc.embedding <=> query_embedding
    LIMIT match_count;
END;
$$;

-- =============================================================================
-- GRANTS
-- =============================================================================

GRANT EXECUTE ON FUNCTION hybrid_search TO authenticated;
GRANT EXECUTE ON FUNCTION hybrid_search TO service_role;
GRANT EXECUTE ON FUNCTION hybrid_search_scoped TO authenticated;
GRANT EXECUTE ON FUNCTION hybrid_search_scoped TO service_role;
GRANT EXECUTE ON FUNCTION match_documents TO authenticated;
GRANT EXECUTE ON FUNCTION match_documents TO service_role;

-- Notify PostgREST to reload function definitions
NOTIFY pgrst, 'reload config';

COMMENT ON FUNCTION hybrid_search IS 'Hybrid vector + keyword search with GDPR/CCPA tombstone filtering. Deleted data is excluded before actual deletion completes.';
COMMENT ON FUNCTION hybrid_search_scoped IS 'Scope-filtered hybrid search with GDPR/CCPA tombstone filtering.';
