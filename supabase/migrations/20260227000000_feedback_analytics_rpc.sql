-- =============================================================================
-- Feedback Analytics RPC Functions
-- =============================================================================
-- Adds two RPC functions for the analytics dashboard:
-- 1. get_source_metrics_filtered - date-filtered source quality metrics
-- 2. get_feedback_trend - daily positive/negative counts for trend chart
-- =============================================================================

-- 1. Source metrics with date filtering
-- Falls back to the materialized view when no dates are provided,
-- but runs a direct query with WHERE clauses when dates are given.
CREATE OR REPLACE FUNCTION public.get_source_metrics_filtered(
    p_organization_id UUID,
    p_from_date TIMESTAMPTZ DEFAULT NULL,
    p_to_date TIMESTAMPTZ DEFAULT NULL,
    p_min_feedback_count INT DEFAULT 5,
    p_sort_by TEXT DEFAULT 'negative_rate_pct',
    p_sort_order TEXT DEFAULT 'desc',
    p_limit INT DEFAULT 20
)
RETURNS TABLE (
    source_label TEXT,
    source_type TEXT,
    source_url TEXT,
    positive_count BIGINT,
    negative_count BIGINT,
    total_feedback BIGINT,
    negative_rate_pct NUMERIC,
    last_feedback_at TIMESTAMPTZ
)
LANGUAGE plpgsql
SECURITY DEFINER
SET search_path = public
AS $$
BEGIN
    RETURN QUERY
    SELECT
        src->>'label' AS source_label,
        src->>'type' AS source_type,
        src->>'url' AS source_url,
        COUNT(*) FILTER (WHERE mf.rating = 'positive') AS positive_count,
        COUNT(*) FILTER (WHERE mf.rating = 'negative') AS negative_count,
        COUNT(*) AS total_feedback,
        ROUND(
            COUNT(*) FILTER (WHERE mf.rating = 'negative')::NUMERIC
            / NULLIF(COUNT(*), 0) * 100, 2
        ) AS negative_rate_pct,
        MAX(mf.created_at) AS last_feedback_at
    FROM message_feedback mf,
         jsonb_array_elements(mf.sources_snapshot) AS src
    WHERE mf.organization_id = p_organization_id
      AND (p_from_date IS NULL OR mf.created_at >= p_from_date)
      AND (p_to_date IS NULL OR mf.created_at <= p_to_date)
      AND src->>'label' IS NOT NULL
    GROUP BY src->>'label', src->>'type', src->>'url'
    HAVING COUNT(*) >= p_min_feedback_count
    ORDER BY
        CASE WHEN p_sort_by = 'negative_rate_pct' AND p_sort_order = 'desc'
             THEN ROUND(COUNT(*) FILTER (WHERE mf.rating = 'negative')::NUMERIC / NULLIF(COUNT(*), 0) * 100, 2)
        END DESC NULLS LAST,
        CASE WHEN p_sort_by = 'negative_rate_pct' AND p_sort_order = 'asc'
             THEN ROUND(COUNT(*) FILTER (WHERE mf.rating = 'negative')::NUMERIC / NULLIF(COUNT(*), 0) * 100, 2)
        END ASC NULLS LAST,
        CASE WHEN p_sort_by = 'total_feedback' AND p_sort_order = 'desc'
             THEN COUNT(*)
        END DESC NULLS LAST,
        CASE WHEN p_sort_by = 'total_feedback' AND p_sort_order = 'asc'
             THEN COUNT(*)
        END ASC NULLS LAST,
        CASE WHEN p_sort_by = 'negative_count' AND p_sort_order = 'desc'
             THEN COUNT(*) FILTER (WHERE mf.rating = 'negative')
        END DESC NULLS LAST,
        CASE WHEN p_sort_by = 'negative_count' AND p_sort_order = 'asc'
             THEN COUNT(*) FILTER (WHERE mf.rating = 'negative')
        END ASC NULLS LAST
    LIMIT p_limit;
END;
$$;

-- 2. Daily feedback trend for the chart
CREATE OR REPLACE FUNCTION public.get_feedback_trend(
    p_organization_id UUID,
    p_from_date TIMESTAMPTZ DEFAULT NULL,
    p_to_date TIMESTAMPTZ DEFAULT NULL
)
RETURNS TABLE (
    date DATE,
    positive_count BIGINT,
    negative_count BIGINT
)
LANGUAGE plpgsql
SECURITY DEFINER
SET search_path = public
AS $$
BEGIN
    RETURN QUERY
    SELECT
        mf.created_at::date AS date,
        COUNT(*) FILTER (WHERE mf.rating = 'positive') AS positive_count,
        COUNT(*) FILTER (WHERE mf.rating = 'negative') AS negative_count
    FROM message_feedback mf
    WHERE mf.organization_id = p_organization_id
      AND (p_from_date IS NULL OR mf.created_at >= p_from_date)
      AND (p_to_date IS NULL OR mf.created_at <= p_to_date)
    GROUP BY mf.created_at::date
    ORDER BY mf.created_at::date ASC;
END;
$$;
