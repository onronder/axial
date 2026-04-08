-- =============================================================================
-- Migration: Fix FTS pipeline for Ghost Protocol with consistent 'simple' config
-- Created: 2026-04-07
--
-- Fixes:
-- 1. Restore keyword search to use document_chunks.content_search instead of
--    document_chunks.content (which may be encrypted under Ghost Protocol)
-- 2. Restore compliance tombstone exclusion in hybrid_search and
--    hybrid_search_scoped
-- 3. Normalize the short-term FTS strategy to 'simple' on both ingest and
--    query sides
-- 4. Update Ghost Protocol ingest RPCs to generate content_search with
--    to_tsvector('simple', ...)
--
-- Notes:
-- - search_language is kept in the function signature for API compatibility,
--   but normalized to 'simple' until a true per-row language strategy exists.
-- - Existing content_search rows still require application-side backfill.
-- =============================================================================

BEGIN;

-- =============================================================================
-- 1. Ghost Protocol ingest RPCs: generate TSVECTOR with 'simple'
-- =============================================================================

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
        to_tsvector('simple', COALESCE(p_content_plaintext, '')),
        p_embedding,
        p_chunk_index
    )
    RETURNING id INTO v_inserted_id;

    RETURN v_inserted_id;
END;
$$;

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
        to_tsvector('simple', COALESCE(chunk->>'content_plaintext', '')),
        (chunk->>'embedding')::VECTOR(1536),
        (chunk->>'chunk_index')::INT
    FROM jsonb_array_elements(p_chunks) AS chunk
    RETURNING id, document_chunks.chunk_index;
END;
$$;

-- =============================================================================
-- 2. hybrid_search: use content_search + restore tombstone exclusion
-- =============================================================================

CREATE OR REPLACE FUNCTION hybrid_search(
    query_text TEXT,
    query_embedding VECTOR(1536),
    match_count INT DEFAULT 10,
    filter_org_id UUID DEFAULT NULL,
    vector_weight FLOAT DEFAULT 0.7,
    keyword_weight FLOAT DEFAULT 0.3,
    similarity_threshold FLOAT DEFAULT 0.25,
    search_language TEXT DEFAULT 'simple'
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
    -- Reject NULL org_id to prevent cross-org leakage.
    IF filter_org_id IS NULL THEN
        RAISE EXCEPTION 'filter_org_id is required and cannot be NULL';
    END IF;

    -- Cap match_count to prevent pathological scans.
    match_count := LEAST(match_count, 100);

    -- Short-term FTS strategy is globally normalized to 'simple'.
    search_language := 'simple';

    RETURN QUERY
    WITH tombstoned_docs AS (
        SELECT UNNEST(t.document_ids) AS blocked_doc_id
        FROM compliance_tombstones t
        WHERE t.organization_id = filter_org_id
          AND t.status = 'active'
    ),
    semantic_results AS (
        SELECT
            dc.id,
            dc.content,
            dc.document_id,
            dc.chunk_index,
            d.source_type::text AS source_type,
            d.scope_id,
            d.title,
            d.metadata,
            (1 - (dc.embedding <=> query_embedding))::FLOAT AS score,
            ROW_NUMBER() OVER (ORDER BY dc.embedding <=> query_embedding) AS rank
        FROM document_chunks dc
        JOIN documents d ON dc.document_id = d.id
        WHERE d.organization_id = filter_org_id
          AND COALESCE(d.source_type::text, '') NOT IN ('identity', 'scope_identity')
          AND COALESCE(d.metadata->>'type', '') != 'identity_card'
          AND COALESCE(lower(d.metadata->>'is_identity'), 'false') != 'true'
          AND (1 - (dc.embedding <=> query_embedding)) >= similarity_threshold
          AND NOT EXISTS (
              SELECT 1
              FROM tombstoned_docs td
              WHERE td.blocked_doc_id = d.id
          )
        ORDER BY dc.embedding <=> query_embedding
        LIMIT match_count * 2
    ),
    keyword_results AS (
        SELECT
            dc.id,
            dc.content,
            dc.document_id,
            dc.chunk_index,
            d.source_type::text AS source_type,
            d.scope_id,
            d.title,
            d.metadata,
            ts_rank_cd(
                dc.content_search,
                plainto_tsquery(search_language::regconfig, query_text),
                32
            )::FLOAT AS score,
            ROW_NUMBER() OVER (
                ORDER BY ts_rank_cd(
                    dc.content_search,
                    plainto_tsquery(search_language::regconfig, query_text),
                    32
                ) DESC
            ) AS rank
        FROM document_chunks dc
        JOIN documents d ON dc.document_id = d.id
        WHERE d.organization_id = filter_org_id
          AND COALESCE(d.source_type::text, '') NOT IN ('identity', 'scope_identity')
          AND COALESCE(d.metadata->>'type', '') != 'identity_card'
          AND COALESCE(lower(d.metadata->>'is_identity'), 'false') != 'true'
          AND dc.content_search @@ plainto_tsquery(search_language::regconfig, query_text)
          AND NOT EXISTS (
              SELECT 1
              FROM tombstoned_docs td
              WHERE td.blocked_doc_id = d.id
          )
        ORDER BY score DESC
        LIMIT match_count * 2
    ),
    combined AS (
        SELECT
            COALESCE(s.id, k.id) AS id,
            COALESCE(s.content, k.content) AS content,
            COALESCE(s.document_id, k.document_id) AS document_id,
            COALESCE(s.chunk_index, k.chunk_index) AS chunk_index,
            COALESCE(s.source_type, k.source_type) AS source_type,
            COALESCE(s.scope_id, k.scope_id) AS scope_id,
            COALESCE(s.title, k.title) AS title,
            COALESCE(s.metadata, k.metadata) AS metadata,
            COALESCE(s.score, 0)::FLOAT AS vector_score,
            COALESCE(k.score, 0)::FLOAT AS keyword_score,
            (
                vector_weight * COALESCE(1.0 / (60 + s.rank), 0) +
                keyword_weight * COALESCE(1.0 / (60 + k.rank), 0)
            )::FLOAT AS combined_score
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
-- 3. hybrid_search_scoped: same fix set with scope filter support
-- =============================================================================

CREATE OR REPLACE FUNCTION hybrid_search_scoped(
    query_text TEXT,
    query_embedding VECTOR(1536),
    match_count INT DEFAULT 10,
    filter_org_id UUID DEFAULT NULL,
    filter_scope_ids TEXT[] DEFAULT NULL,
    vector_weight FLOAT DEFAULT 0.7,
    keyword_weight FLOAT DEFAULT 0.3,
    similarity_threshold FLOAT DEFAULT 0.25,
    search_language TEXT DEFAULT 'simple'
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
    IF filter_org_id IS NULL THEN
        RAISE EXCEPTION 'filter_org_id is required and cannot be NULL';
    END IF;

    match_count := LEAST(match_count, 100);
    search_language := 'simple';

    RETURN QUERY
    WITH tombstoned_docs AS (
        SELECT UNNEST(t.document_ids) AS blocked_doc_id
        FROM compliance_tombstones t
        WHERE t.organization_id = filter_org_id
          AND t.status = 'active'
    ),
    semantic_results AS (
        SELECT
            dc.id,
            dc.content,
            dc.document_id,
            dc.chunk_index,
            d.source_type::text AS source_type,
            d.scope_id,
            d.title,
            d.metadata,
            (1 - (dc.embedding <=> query_embedding))::FLOAT AS score,
            ROW_NUMBER() OVER (ORDER BY dc.embedding <=> query_embedding) AS rank
        FROM document_chunks dc
        JOIN documents d ON dc.document_id = d.id
        WHERE d.organization_id = filter_org_id
          AND (filter_scope_ids IS NULL OR d.scope_id = ANY(filter_scope_ids))
          AND COALESCE(d.source_type::text, '') NOT IN ('identity', 'scope_identity')
          AND COALESCE(d.metadata->>'type', '') != 'identity_card'
          AND COALESCE(lower(d.metadata->>'is_identity'), 'false') != 'true'
          AND (1 - (dc.embedding <=> query_embedding)) >= similarity_threshold
          AND NOT EXISTS (
              SELECT 1
              FROM tombstoned_docs td
              WHERE td.blocked_doc_id = d.id
          )
        ORDER BY dc.embedding <=> query_embedding
        LIMIT match_count * 2
    ),
    keyword_results AS (
        SELECT
            dc.id,
            dc.content,
            dc.document_id,
            dc.chunk_index,
            d.source_type::text AS source_type,
            d.scope_id,
            d.title,
            d.metadata,
            ts_rank_cd(
                dc.content_search,
                plainto_tsquery(search_language::regconfig, query_text),
                32
            )::FLOAT AS score,
            ROW_NUMBER() OVER (
                ORDER BY ts_rank_cd(
                    dc.content_search,
                    plainto_tsquery(search_language::regconfig, query_text),
                    32
                ) DESC
            ) AS rank
        FROM document_chunks dc
        JOIN documents d ON dc.document_id = d.id
        WHERE d.organization_id = filter_org_id
          AND (filter_scope_ids IS NULL OR d.scope_id = ANY(filter_scope_ids))
          AND COALESCE(d.source_type::text, '') NOT IN ('identity', 'scope_identity')
          AND COALESCE(d.metadata->>'type', '') != 'identity_card'
          AND COALESCE(lower(d.metadata->>'is_identity'), 'false') != 'true'
          AND dc.content_search @@ plainto_tsquery(search_language::regconfig, query_text)
          AND NOT EXISTS (
              SELECT 1
              FROM tombstoned_docs td
              WHERE td.blocked_doc_id = d.id
          )
        ORDER BY score DESC
        LIMIT match_count * 2
    ),
    combined AS (
        SELECT
            COALESCE(s.id, k.id) AS id,
            COALESCE(s.content, k.content) AS content,
            COALESCE(s.document_id, k.document_id) AS document_id,
            COALESCE(s.chunk_index, k.chunk_index) AS chunk_index,
            COALESCE(s.source_type, k.source_type) AS source_type,
            COALESCE(s.scope_id, k.scope_id) AS scope_id,
            COALESCE(s.title, k.title) AS title,
            COALESCE(s.metadata, k.metadata) AS metadata,
            COALESCE(s.score, 0)::FLOAT AS vector_score,
            COALESCE(k.score, 0)::FLOAT AS keyword_score,
            (
                vector_weight * COALESCE(1.0 / (60 + s.rank), 0) +
                keyword_weight * COALESCE(1.0 / (60 + k.rank), 0)
            )::FLOAT AS combined_score
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
-- 4. Re-grant + reload
-- =============================================================================

GRANT EXECUTE ON FUNCTION hybrid_search(TEXT, VECTOR, INT, UUID, FLOAT, FLOAT, FLOAT, TEXT) TO authenticated;
GRANT EXECUTE ON FUNCTION hybrid_search(TEXT, VECTOR, INT, UUID, FLOAT, FLOAT, FLOAT, TEXT) TO service_role;
GRANT EXECUTE ON FUNCTION hybrid_search_scoped(TEXT, VECTOR, INT, UUID, TEXT[], FLOAT, FLOAT, FLOAT, TEXT) TO authenticated;
GRANT EXECUTE ON FUNCTION hybrid_search_scoped(TEXT, VECTOR, INT, UUID, TEXT[], FLOAT, FLOAT, FLOAT, TEXT) TO service_role;

NOTIFY pgrst, 'reload config';

COMMIT;
