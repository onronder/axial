-- Migration: Harden hybrid search, fix NULL org leakage, cap match_count,
-- optimize messages RLS, validate search_language
--
-- Fixes:
-- 1.8  - NULL org_id guard prevents cross-org data leakage
-- 1.9  - Cap match_count to prevent DoS, reduce CTE multiplier
-- 2.6  - Replace correlated EXISTS in messages RLS with IN-subquery
-- 3.10 - Validate search_language parameter

BEGIN;

-- ==========================================================================
-- Fix 1.8 + 1.9 + 3.10: hybrid_search with NULL guard, match_count cap, language validation
-- ==========================================================================

-- Drop existing 8-param hybrid_search (from multilang migration)
DROP FUNCTION IF EXISTS hybrid_search(TEXT, VECTOR, INT, UUID, FLOAT, FLOAT, FLOAT, TEXT);

CREATE OR REPLACE FUNCTION hybrid_search(
    query_text TEXT,
    query_embedding VECTOR(1536),
    match_count INT DEFAULT 10,
    filter_org_id UUID DEFAULT NULL,
    vector_weight FLOAT DEFAULT 0.7,
    keyword_weight FLOAT DEFAULT 0.3,
    similarity_threshold FLOAT DEFAULT 0.25,
    search_language TEXT DEFAULT 'english'
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
    -- Fix 1.8: Reject NULL org_id to prevent cross-org data leakage
    IF filter_org_id IS NULL THEN
        RAISE EXCEPTION 'filter_org_id is required and cannot be NULL';
    END IF;

    -- Fix 1.9: Cap match_count to prevent DoS
    match_count := LEAST(match_count, 100);

    -- Fix 3.10: Validate search_language
    IF search_language NOT IN ('english', 'french', 'german', 'spanish', 'italian',
                               'portuguese', 'dutch', 'russian', 'swedish', 'norwegian',
                               'danish', 'finnish', 'hungarian', 'romanian', 'turkish',
                               'simple') THEN
        search_language := 'simple';
    END IF;

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
        WHERE d.organization_id = filter_org_id
          AND COALESCE(d.source_type::text, '') NOT IN ('identity', 'scope_identity')
          AND COALESCE(d.metadata->>'type', '') != 'identity_card'
          AND COALESCE(lower(d.metadata->>'is_identity'), 'false') != 'true'
          AND (1 - (dc.embedding <=> query_embedding)) >= similarity_threshold
        ORDER BY dc.embedding <=> query_embedding
        LIMIT match_count * 2
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
                to_tsvector(search_language, dc.content),
                plainto_tsquery(search_language, query_text),
                32
            )::FLOAT as score,
            ROW_NUMBER() OVER (
                ORDER BY ts_rank_cd(
                    to_tsvector(search_language, dc.content),
                    plainto_tsquery(search_language, query_text),
                    32
                ) DESC
            ) as rank
        FROM document_chunks dc
        JOIN documents d ON dc.document_id = d.id
        WHERE d.organization_id = filter_org_id
          AND COALESCE(d.source_type::text, '') NOT IN ('identity', 'scope_identity')
          AND COALESCE(d.metadata->>'type', '') != 'identity_card'
          AND COALESCE(lower(d.metadata->>'is_identity'), 'false') != 'true'
          AND to_tsvector(search_language, dc.content)
              @@ plainto_tsquery(search_language, query_text)
        ORDER BY score DESC
        LIMIT match_count * 2
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

-- ==========================================================================
-- Fix 1.8 + 1.9 + 3.10: hybrid_search_scoped with same guards
-- ==========================================================================

-- Drop existing 9-param hybrid_search_scoped (from multilang migration)
DROP FUNCTION IF EXISTS hybrid_search_scoped(TEXT, VECTOR, INT, UUID, TEXT[], FLOAT, FLOAT, FLOAT, TEXT);

CREATE OR REPLACE FUNCTION hybrid_search_scoped(
    query_text TEXT,
    query_embedding VECTOR(1536),
    match_count INT DEFAULT 10,
    filter_org_id UUID DEFAULT NULL,
    filter_scope_ids TEXT[] DEFAULT NULL,
    vector_weight FLOAT DEFAULT 0.7,
    keyword_weight FLOAT DEFAULT 0.3,
    similarity_threshold FLOAT DEFAULT 0.25,
    search_language TEXT DEFAULT 'english'
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
    -- Fix 1.8: Reject NULL org_id to prevent cross-org data leakage
    IF filter_org_id IS NULL THEN
        RAISE EXCEPTION 'filter_org_id is required and cannot be NULL';
    END IF;

    -- Fix 1.9: Cap match_count to prevent DoS
    match_count := LEAST(match_count, 100);

    -- Fix 3.10: Validate search_language
    IF search_language NOT IN ('english', 'french', 'german', 'spanish', 'italian',
                               'portuguese', 'dutch', 'russian', 'swedish', 'norwegian',
                               'danish', 'finnish', 'hungarian', 'romanian', 'turkish',
                               'simple') THEN
        search_language := 'simple';
    END IF;

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
        WHERE d.organization_id = filter_org_id
          AND (filter_scope_ids IS NULL OR d.scope_id = ANY(filter_scope_ids))
          AND COALESCE(d.source_type::text, '') NOT IN ('identity', 'scope_identity')
          AND COALESCE(d.metadata->>'type', '') != 'identity_card'
          AND COALESCE(lower(d.metadata->>'is_identity'), 'false') != 'true'
          AND (1 - (dc.embedding <=> query_embedding)) >= similarity_threshold
        ORDER BY dc.embedding <=> query_embedding
        LIMIT match_count * 2
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
                to_tsvector(search_language, dc.content),
                plainto_tsquery(search_language, query_text),
                32
            )::FLOAT as score,
            ROW_NUMBER() OVER (
                ORDER BY ts_rank_cd(
                    to_tsvector(search_language, dc.content),
                    plainto_tsquery(search_language, query_text),
                    32
                ) DESC
            ) as rank
        FROM document_chunks dc
        JOIN documents d ON dc.document_id = d.id
        WHERE d.organization_id = filter_org_id
          AND (filter_scope_ids IS NULL OR d.scope_id = ANY(filter_scope_ids))
          AND COALESCE(d.source_type::text, '') NOT IN ('identity', 'scope_identity')
          AND COALESCE(d.metadata->>'type', '') != 'identity_card'
          AND COALESCE(lower(d.metadata->>'is_identity'), 'false') != 'true'
          AND to_tsvector(search_language, dc.content)
              @@ plainto_tsquery(search_language, query_text)
        ORDER BY score DESC
        LIMIT match_count * 2
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

-- ==========================================================================
-- Fix 2.6: Optimize messages RLS - replace correlated EXISTS with IN subquery
-- ==========================================================================

-- Drop the existing per-row correlated EXISTS policy
DROP POLICY IF EXISTS "messages_org_select" ON messages;

-- New optimized policy: materializes accessible conversation IDs once
CREATE POLICY "messages_org_select" ON messages
    FOR SELECT
    USING (
        conversation_id IN (
            SELECT c.id FROM conversations c
            WHERE public.is_org_member(c.organization_id, (SELECT auth.uid()))
        )
    );

-- Ensure index exists for the join
CREATE INDEX IF NOT EXISTS idx_messages_conversation_id ON messages(conversation_id);

-- ==========================================================================
-- Grants
-- ==========================================================================

GRANT EXECUTE ON FUNCTION hybrid_search(TEXT, VECTOR, INT, UUID, FLOAT, FLOAT, FLOAT, TEXT) TO authenticated;
GRANT EXECUTE ON FUNCTION hybrid_search(TEXT, VECTOR, INT, UUID, FLOAT, FLOAT, FLOAT, TEXT) TO service_role;
GRANT EXECUTE ON FUNCTION hybrid_search_scoped(TEXT, VECTOR, INT, UUID, TEXT[], FLOAT, FLOAT, FLOAT, TEXT) TO authenticated;
GRANT EXECUTE ON FUNCTION hybrid_search_scoped(TEXT, VECTOR, INT, UUID, TEXT[], FLOAT, FLOAT, FLOAT, TEXT) TO service_role;

COMMIT;
