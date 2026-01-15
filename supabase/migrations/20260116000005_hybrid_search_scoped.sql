-- =============================================================================
-- Phase 3: Scope-Aware Hybrid Search
-- =============================================================================
-- Extends hybrid_search to return scope_id for each chunk, enabling the
-- Dominance Guard to classify retrieval results by scope distribution.
-- =============================================================================

-- Drop existing functions to recreate with new signature
DROP FUNCTION IF EXISTS hybrid_search(TEXT, VECTOR(1536), INT, UUID, FLOAT, FLOAT, FLOAT);
DROP FUNCTION IF EXISTS hybrid_search_scoped(TEXT, VECTOR(1536), INT, UUID, TEXT[], FLOAT, FLOAT, FLOAT);

-- Create scope-aware hybrid search function
CREATE OR REPLACE FUNCTION hybrid_search(
    query_text TEXT,
    query_embedding VECTOR(1536),
    match_count INT DEFAULT 10,
    filter_user_id UUID DEFAULT NULL,
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
    scope_id TEXT,           -- NEW: Canonical scope URI
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
            d.scope_id,        -- Include scope_id from documents
            d.title,
            d.metadata,
            (1 - (dc.embedding <=> query_embedding))::FLOAT as score,
            ROW_NUMBER() OVER (ORDER BY dc.embedding <=> query_embedding) as rank
        FROM document_chunks dc
        JOIN documents d ON dc.document_id = d.id
        WHERE (filter_user_id IS NULL OR d.user_id = filter_user_id)
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

-- Create filtered scope search for explicit scope selection
CREATE OR REPLACE FUNCTION hybrid_search_scoped(
    query_text TEXT,
    query_embedding VECTOR(1536),
    match_count INT DEFAULT 10,
    filter_user_id UUID DEFAULT NULL,
    filter_scope_ids TEXT[] DEFAULT NULL,  -- Optional: restrict to specific scopes
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
        WHERE (filter_user_id IS NULL OR d.user_id = filter_user_id)
          AND (filter_scope_ids IS NULL OR d.scope_id = ANY(filter_scope_ids))
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
          AND (filter_scope_ids IS NULL OR d.scope_id = ANY(filter_scope_ids))
          AND to_tsvector('english', dc.content) @@ plainto_tsquery('english', query_text)
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

-- Grant permissions
GRANT EXECUTE ON FUNCTION hybrid_search TO authenticated;
GRANT EXECUTE ON FUNCTION hybrid_search TO service_role;
GRANT EXECUTE ON FUNCTION hybrid_search_scoped TO authenticated;
GRANT EXECUTE ON FUNCTION hybrid_search_scoped TO service_role;

-- Add comments
COMMENT ON FUNCTION hybrid_search IS 
'Scope-aware hybrid search combining vector similarity and keyword matching.
Returns scope_id for each chunk to enable Dominance Guard classification.';

COMMENT ON FUNCTION hybrid_search_scoped IS 
'Scope-filtered hybrid search. When filter_scope_ids is provided, only returns
chunks from those specific scopes. Used for explicit scope selection.';

-- Notify PostgREST to reload schema cache
NOTIFY pgrst, 'reload config';
