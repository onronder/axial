-- =============================================================================
-- Fix Hybrid Search Source Type Casting
-- =============================================================================
-- The source_type column is an enum but needs to be returned as TEXT
-- to avoid type mismatch errors in the API response
-- 
-- IMPORTANT: Must DROP functions first because return type is changing
-- =============================================================================

-- Drop existing functions first (required when changing return type)
DROP FUNCTION IF EXISTS hybrid_search(TEXT, VECTOR(1536), INT, UUID, FLOAT, FLOAT, FLOAT);
DROP FUNCTION IF EXISTS match_documents(VECTOR(1536), FLOAT, INT, UUID);

-- Recreate hybrid_search with proper type casting
CREATE OR REPLACE FUNCTION hybrid_search(
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
    source_type TEXT,  -- Return as TEXT, not enum
    title TEXT,
    metadata JSONB,
    vector_score FLOAT,
    keyword_score FLOAT,
    combined_score FLOAT
) AS $$
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
            d.source_type::text as source_type,  -- Cast enum to text
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
            d.source_type::text as source_type,  -- Cast enum to text
            d.title,
            d.metadata,
            ts_rank_cd(
                to_tsvector('english', dc.content), 
                plainto_tsquery('english', query_text),
                32 -- normalization: divide by document length
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
$$ LANGUAGE plpgsql STABLE;

-- Recreate match_documents with proper type casting
CREATE OR REPLACE FUNCTION match_documents(
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
) AS $$
BEGIN
    RETURN QUERY
    SELECT 
        dc.id,
        dc.content,
        dc.document_id,
        dc.chunk_index,
        d.source_type::text as source_type,  -- Cast enum to text
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
$$ LANGUAGE plpgsql STABLE;

-- Grant permissions
GRANT EXECUTE ON FUNCTION hybrid_search TO authenticated;
GRANT EXECUTE ON FUNCTION hybrid_search TO service_role;
GRANT EXECUTE ON FUNCTION match_documents TO authenticated;
GRANT EXECUTE ON FUNCTION match_documents TO service_role;

-- Notify PostgREST to reload schema cache
NOTIFY pgrst, 'reload config';
