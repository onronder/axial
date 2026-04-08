BEGIN;

CREATE TABLE IF NOT EXISTS public.rag_analytics (
    id UUID NOT NULL DEFAULT gen_random_uuid(),
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    organization_id UUID NOT NULL,
    conversation_id UUID,
    message_id UUID NOT NULL,
    user_id UUID,
    query_text TEXT NOT NULL,
    search_query TEXT,
    selected_scope_id TEXT,
    allowed_scope_ids JSONB,
    guardrail_language TEXT,
    guardrail_intent TEXT,
    guardrail_complexity TEXT,
    has_document_context BOOLEAN NOT NULL DEFAULT false,
    retrieval_doc_count INTEGER NOT NULL DEFAULT 0,
    high_quality_doc_count INTEGER NOT NULL DEFAULT 0,
    source_count INTEGER NOT NULL DEFAULT 0,
    top_similarity DOUBLE PRECISION,
    avg_similarity DOUBLE PRECISION,
    rerank_applied BOOLEAN NOT NULL DEFAULT false,
    top_rerank_score DOUBLE PRECISION,
    avg_rerank_score DOUBLE PRECISION,
    scope_classification TEXT,
    scope_dominance_ratio DOUBLE PRECISION,
    cached BOOLEAN NOT NULL DEFAULT false,
    no_answer BOOLEAN NOT NULL DEFAULT false,
    llm_provider TEXT,
    llm_model TEXT,
    llm_prompt_tokens INTEGER,
    llm_completion_tokens INTEGER,
    llm_total_tokens INTEGER,
    faithfulness_passed BOOLEAN,
    faithfulness_score DOUBLE PRECISION,
    faithfulness_warning TEXT,
    user_feedback TEXT CHECK (user_feedback IN ('positive', 'negative')),
    PRIMARY KEY (id, created_at)
) PARTITION BY RANGE (created_at);

CREATE INDEX IF NOT EXISTS idx_rag_analytics_org_created
ON public.rag_analytics (organization_id, created_at DESC);

CREATE INDEX IF NOT EXISTS idx_rag_analytics_message_id
ON public.rag_analytics (message_id);

CREATE INDEX IF NOT EXISTS idx_rag_analytics_feedback
ON public.rag_analytics (user_feedback)
WHERE user_feedback IS NOT NULL;

CREATE OR REPLACE FUNCTION public.ensure_rag_analytics_partitions(p_months_ahead INTEGER DEFAULT 6)
RETURNS VOID
LANGUAGE plpgsql
SECURITY DEFINER
SET search_path = public
AS $$
DECLARE
    month_start DATE := date_trunc('month', CURRENT_DATE)::DATE;
    range_start DATE;
    range_end DATE;
    part_name TEXT;
    i INTEGER;
BEGIN
    FOR i IN 0..GREATEST(p_months_ahead, 0) LOOP
        range_start := (month_start + make_interval(months => i))::DATE;
        range_end := (month_start + make_interval(months => i + 1))::DATE;
        part_name := format('rag_analytics_%s', to_char(range_start, 'YYYY_MM'));

        EXECUTE format(
            'CREATE TABLE IF NOT EXISTS public.%I PARTITION OF public.rag_analytics FOR VALUES FROM (%L) TO (%L)',
            part_name,
            range_start::TEXT,
            range_end::TEXT
        );
    END LOOP;
END;
$$;

SELECT public.ensure_rag_analytics_partitions(6);

ALTER TABLE public.rag_analytics ENABLE ROW LEVEL SECURITY;

DROP POLICY IF EXISTS rag_analytics_service_role_all ON public.rag_analytics;
CREATE POLICY rag_analytics_service_role_all ON public.rag_analytics
    FOR ALL TO service_role
    USING (true)
    WITH CHECK (true);

REVOKE ALL ON public.rag_analytics FROM PUBLIC;
GRANT ALL ON public.rag_analytics TO service_role;
GRANT EXECUTE ON FUNCTION public.ensure_rag_analytics_partitions(INTEGER) TO service_role;

DO $do_block$
BEGIN
    IF EXISTS (SELECT 1 FROM pg_extension WHERE extname = 'pg_cron') THEN
        PERFORM cron.schedule(
            'ensure-rag-analytics-partitions',
            '0 1 1 * *',
            'SELECT public.ensure_rag_analytics_partitions(6)'
        );
        RAISE NOTICE '[RAGAnalytics] pg_cron job scheduled for monthly partition maintenance';
    ELSE
        RAISE NOTICE '[RAGAnalytics] pg_cron not available - manual partition maintenance required';
    END IF;
EXCEPTION
    WHEN OTHERS THEN
        RAISE NOTICE '[RAGAnalytics] Could not schedule pg_cron job: %', SQLERRM;
END;
$do_block$;

COMMENT ON TABLE public.rag_analytics IS 'Request-level RAG analytics keyed by message_id. Stores retrieval, rerank, scope, and faithfulness diagnostics.';

COMMIT;
