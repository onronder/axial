-- Restore visibility of org-level (NULL scope_id) documents in scoped retrieval.
-- This regressed when hybrid_search_scoped was rewritten for per-language FTS.

CREATE OR REPLACE FUNCTION public.hybrid_search_scoped(
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
    search_language := COALESCE(NULLIF(BTRIM(search_language), ''), 'simple');

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
          AND (filter_scope_ids IS NULL OR d.scope_id = ANY(filter_scope_ids) OR d.scope_id IS NULL)
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
          AND (filter_scope_ids IS NULL OR d.scope_id = ANY(filter_scope_ids) OR d.scope_id IS NULL)
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

GRANT EXECUTE ON FUNCTION public.hybrid_search_scoped(TEXT, VECTOR, INT, UUID, TEXT[], FLOAT, FLOAT, FLOAT, TEXT) TO authenticated;
GRANT EXECUTE ON FUNCTION public.hybrid_search_scoped(TEXT, VECTOR, INT, UUID, TEXT[], FLOAT, FLOAT, FLOAT, TEXT) TO service_role;

NOTIFY pgrst, 'reload config';
