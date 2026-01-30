-- =============================================================================
-- Migration: Secure Materialized View Access
-- Created: 2026-01-30
-- Purpose: Restrict direct API access to source_feedback_metrics view
-- 
-- WARNING ADDRESSED:
--   "Materialized view is accessible to anon and authenticated roles"
--   https://supabase.com/docs/guides/database/database-linter
-- 
-- SECURITY RATIONALE:
--   The source_feedback_metrics view aggregates sensitive analytics data.
--   Direct access should be restricted to:
--   1. Backend service role (for admin API endpoints)
--   2. Authenticated users via secure RPC function (if needed)
--
-- IMPACT ASSESSMENT:
--   - Frontend uses /api/py/analytics/feedback/sources endpoint (not direct)
--   - Backend uses service_role for queries (already authorized)
--   - No direct PostgREST access expected
-- =============================================================================

BEGIN;

-- =============================================================================
-- 1. REVOKE DIRECT ACCESS FROM PUBLIC ROLES
-- =============================================================================
-- Remove direct SELECT access from anon and authenticated roles.
-- Access will only be possible via:
--   a) Backend API with admin authorization check
--   b) service_role access (for backend)
--   c) New secure RPC function (for direct frontend needs)

DO $$
BEGIN
    -- Check if the view exists before attempting revoke
    IF EXISTS (
        SELECT 1 FROM pg_matviews 
        WHERE schemaname = 'public' 
        AND matviewname = 'source_feedback_metrics'
    ) THEN
        EXECUTE 'REVOKE SELECT ON public.source_feedback_metrics FROM anon';
        EXECUTE 'REVOKE SELECT ON public.source_feedback_metrics FROM authenticated';
        RAISE NOTICE 'Revoked direct access to source_feedback_metrics from anon and authenticated';
    ELSE
        RAISE NOTICE 'source_feedback_metrics view not found, skipping';
    END IF;
EXCEPTION
    WHEN OTHERS THEN
        RAISE NOTICE 'Error revoking permissions: %', SQLERRM;
END;
$$;

-- =============================================================================
-- 2. CREATE SECURE ACCESSOR FUNCTION
-- =============================================================================
-- If frontend needs direct access (without going through /api/py), this
-- function provides a secure alternative with organization scoping.
-- 
-- SECURITY: DEFINER runs as the function owner (postgres) with service privileges
-- BUT we explicitly check auth.uid() and organization membership.

CREATE OR REPLACE FUNCTION public.get_source_feedback_metrics(
    p_organization_id UUID,
    p_min_feedback_count INT DEFAULT 5,
    p_sort_by TEXT DEFAULT 'negative_rate_pct',
    p_sort_order TEXT DEFAULT 'desc',
    p_limit INT DEFAULT 20
)
RETURNS TABLE (
    organization_id UUID,
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
STABLE
SECURITY DEFINER
SET search_path = public, pg_catalog
AS $$
DECLARE
    v_user_id UUID;
    v_is_admin BOOLEAN;
BEGIN
    -- Get current user
    v_user_id := auth.uid();
    
    -- Must be authenticated
    IF v_user_id IS NULL THEN
        RAISE EXCEPTION 'Authentication required';
    END IF;
    
    -- Must be member of the organization
    IF NOT public.is_org_member(p_organization_id, v_user_id) THEN
        RAISE EXCEPTION 'Access denied: not a member of this organization';
    END IF;
    
    -- Check if user is admin (optional: restrict to admins only)
    SELECT EXISTS (
        SELECT 1 FROM public.team_members tm
        WHERE tm.organization_id = p_organization_id
        AND tm.user_id = v_user_id
        AND tm.role IN ('owner', 'admin')
    ) INTO v_is_admin;
    
    IF NOT v_is_admin THEN
        RAISE EXCEPTION 'Access denied: admin role required';
    END IF;
    
    -- Validate parameters
    IF p_sort_by NOT IN ('negative_rate_pct', 'total_feedback', 'negative_count', 'positive_count') THEN
        p_sort_by := 'negative_rate_pct';
    END IF;
    
    IF p_sort_order NOT IN ('asc', 'desc') THEN
        p_sort_order := 'desc';
    END IF;
    
    IF p_limit > 50 THEN
        p_limit := 50;
    END IF;
    
    -- Return filtered data
    RETURN QUERY
    SELECT 
        sfm.organization_id,
        sfm.source_label,
        sfm.source_type,
        sfm.source_url,
        sfm.positive_count,
        sfm.negative_count,
        sfm.total_feedback,
        sfm.negative_rate_pct,
        sfm.last_feedback_at
    FROM public.source_feedback_metrics sfm
    WHERE sfm.organization_id = p_organization_id
    AND sfm.total_feedback >= p_min_feedback_count
    ORDER BY 
        CASE WHEN p_sort_by = 'negative_rate_pct' AND p_sort_order = 'desc' THEN sfm.negative_rate_pct END DESC NULLS LAST,
        CASE WHEN p_sort_by = 'negative_rate_pct' AND p_sort_order = 'asc' THEN sfm.negative_rate_pct END ASC NULLS LAST,
        CASE WHEN p_sort_by = 'total_feedback' AND p_sort_order = 'desc' THEN sfm.total_feedback END DESC,
        CASE WHEN p_sort_by = 'total_feedback' AND p_sort_order = 'asc' THEN sfm.total_feedback END ASC,
        CASE WHEN p_sort_by = 'negative_count' AND p_sort_order = 'desc' THEN sfm.negative_count END DESC,
        CASE WHEN p_sort_by = 'negative_count' AND p_sort_order = 'asc' THEN sfm.negative_count END ASC,
        CASE WHEN p_sort_by = 'positive_count' AND p_sort_order = 'desc' THEN sfm.positive_count END DESC,
        CASE WHEN p_sort_by = 'positive_count' AND p_sort_order = 'asc' THEN sfm.positive_count END ASC
    LIMIT p_limit;
END;
$$;

-- Grant execute to authenticated users (function handles authorization internally)
GRANT EXECUTE ON FUNCTION public.get_source_feedback_metrics(UUID, INT, TEXT, TEXT, INT) 
    TO authenticated;

-- Grant to service role for backend
GRANT EXECUTE ON FUNCTION public.get_source_feedback_metrics(UUID, INT, TEXT, TEXT, INT) 
    TO service_role;

-- Add documentation comment
COMMENT ON FUNCTION public.get_source_feedback_metrics IS 
'Secure accessor for source_feedback_metrics.
Requires authenticated user with admin role in the specified organization.

Parameters:
  p_organization_id: UUID of the organization
  p_min_feedback_count: Minimum feedback count to include (default 5)
  p_sort_by: Sort column - negative_rate_pct, total_feedback, negative_count, positive_count
  p_sort_order: asc or desc (default desc)
  p_limit: Max rows to return (max 50)

Returns: Table of source metrics for the organization';

-- =============================================================================
-- 3. VERIFY SETUP
-- =============================================================================
-- Run this query after migration to verify:
-- 
-- SELECT 
--     grantor, grantee, privilege_type, is_grantable
-- FROM information_schema.role_table_grants 
-- WHERE table_name = 'source_feedback_metrics';
--
-- Expected: No rows for 'anon' or 'authenticated'

COMMIT;
