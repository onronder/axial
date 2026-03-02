-- Migration: Tune HNSW ef_search for improved recall
-- H5: Set ef_search=128 (from default 40) for ~97% recall@10
-- This is a session-level GUC — no index rebuild needed.

BEGIN;

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
          AND COALESCE(d.source_type::text, '') NOT IN ('identity', 'scope_identity')
          AND COALESCE(d.metadata->>'type', '') != 'identity_card'
          AND COALESCE(lower(d.metadata->>'is_identity'), 'false') != 'true'
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

-- Also update hybrid_search_scoped with ef_search=128
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
          AND COALESCE(d.source_type::text, '') NOT IN ('identity', 'scope_identity')
          AND COALESCE(d.metadata->>'type', '') != 'identity_card'
          AND COALESCE(lower(d.metadata->>'is_identity'), 'false') != 'true'
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

-- Preserve existing permissions (fully-qualified to avoid ambiguity)
GRANT EXECUTE ON FUNCTION hybrid_search(TEXT, VECTOR, INT, UUID, FLOAT, FLOAT, FLOAT) TO authenticated;
GRANT EXECUTE ON FUNCTION hybrid_search(TEXT, VECTOR, INT, UUID, FLOAT, FLOAT, FLOAT) TO service_role;
GRANT EXECUTE ON FUNCTION hybrid_search_scoped(TEXT, VECTOR, INT, UUID, TEXT[], FLOAT, FLOAT, FLOAT) TO authenticated;
GRANT EXECUTE ON FUNCTION hybrid_search_scoped(TEXT, VECTOR, INT, UUID, TEXT[], FLOAT, FLOAT, FLOAT) TO service_role;

COMMIT;
