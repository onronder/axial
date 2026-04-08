BEGIN;

ALTER TABLE public.rag_analytics
    ADD COLUMN IF NOT EXISTS request_id UUID;

UPDATE public.rag_analytics
SET request_id = gen_random_uuid()
WHERE request_id IS NULL;

ALTER TABLE public.rag_analytics
    ALTER COLUMN request_id SET NOT NULL;

ALTER TABLE public.rag_analytics
    ALTER COLUMN message_id DROP NOT NULL;

ALTER TABLE public.rag_analytics
    ADD COLUMN IF NOT EXISTS completion_status TEXT;

UPDATE public.rag_analytics
SET completion_status = CASE
    WHEN message_id IS NULL THEN 'save_failure'
    ELSE 'success'
END
WHERE completion_status IS NULL;

ALTER TABLE public.rag_analytics
    ALTER COLUMN completion_status SET DEFAULT 'success';

ALTER TABLE public.rag_analytics
    ALTER COLUMN completion_status SET NOT NULL;

DO $$
BEGIN
    IF NOT EXISTS (
        SELECT 1
        FROM pg_constraint
        WHERE conname = 'rag_analytics_completion_status_check'
    ) THEN
        ALTER TABLE public.rag_analytics
            ADD CONSTRAINT rag_analytics_completion_status_check
            CHECK (
                completion_status IN (
                    'success',
                    'partial_stream_failure',
                    'pre_stream_failure',
                    'save_failure'
                )
            );
    END IF;
END;
$$;

ALTER TABLE public.rag_analytics
    ADD COLUMN IF NOT EXISTS partial_response_length INTEGER;

ALTER TABLE public.rag_analytics
    ADD COLUMN IF NOT EXISTS citations_stripped_count INTEGER NOT NULL DEFAULT 0;

CREATE INDEX IF NOT EXISTS idx_rag_analytics_request_id
ON public.rag_analytics (request_id);

COMMENT ON TABLE public.rag_analytics IS 'Request-level RAG analytics keyed by request_id. Stores retrieval, rerank, scope, citation, stream terminal status, and faithfulness diagnostics.';

NOTIFY pgrst, 'reload schema';

COMMIT;
