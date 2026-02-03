-- =============================================================================
-- Security & Performance Fixes for Supabase Advisor Warnings
-- Migration: 20260203100000_fix_supabase_advisor_security.sql
--
-- Fixes:
--   P0 - RLS Policy Always True (1 issue)
--   P1 - Function Search Path Mutable (8 functions)
--   P2 - Auth RLS Initplan Performance (26 policies)
--
-- Best Practices Applied:
--   - All functions use SET search_path = '' for SQL injection prevention
--   - All table references are fully qualified (public.table_name)
--   - All auth.uid() calls wrapped with (SELECT ...) for single evaluation
--   - Service role policies properly scoped to service_role only
-- =============================================================================

-- ============================================================================
-- P0: FIX RLS POLICY ALWAYS TRUE
-- Issue: consent_audit_log has consent_audit_insert with WITH CHECK (true)
-- Risk: Anyone can INSERT audit records, potentially allowing log injection
-- ============================================================================

-- Drop the insecure policy
DROP POLICY IF EXISTS consent_audit_insert ON public.consent_audit_log;

-- Create secure INSERT policy that ensures organization membership
-- Audit records should only be created by authenticated users for their own orgs
CREATE POLICY consent_audit_insert ON public.consent_audit_log
    FOR INSERT
    TO authenticated
    WITH CHECK (
        -- User must be a member of the organization they're creating audit logs for
        organization_id IN (
            SELECT id FROM public.teams WHERE owner_id = (SELECT auth.uid())
        )
        OR
        organization_id IN (
            SELECT team_id FROM public.team_members 
            WHERE member_user_id = (SELECT auth.uid())
        )
    );

-- ============================================================================
-- P1: FIX FUNCTION SEARCH PATH MUTABLE
-- Issue: Functions without search_path can be exploited via SQL injection
-- Fix: SET search_path = '' and use fully qualified table names
-- ============================================================================

-- -----------------------------------------------------------------------------
-- 1. update_consent_updated_at (trigger function)
-- -----------------------------------------------------------------------------
CREATE OR REPLACE FUNCTION public.update_consent_updated_at()
RETURNS TRIGGER
LANGUAGE plpgsql
SECURITY INVOKER
SET search_path = ''
AS $$
BEGIN
    NEW.updated_at = now();
    RETURN NEW;
END;
$$;

-- -----------------------------------------------------------------------------
-- 2. update_tombstone_timestamp (trigger function)
-- -----------------------------------------------------------------------------
CREATE OR REPLACE FUNCTION public.update_tombstone_timestamp()
RETURNS TRIGGER
LANGUAGE plpgsql
SECURITY INVOKER
SET search_path = ''
AS $$
BEGIN
    NEW.updated_at = now();
    RETURN NEW;
END;
$$;

-- -----------------------------------------------------------------------------
-- 3. cleanup_expired_tombstones
-- -----------------------------------------------------------------------------
CREATE OR REPLACE FUNCTION public.cleanup_expired_tombstones()
RETURNS INTEGER
LANGUAGE plpgsql
SECURITY DEFINER
SET search_path = ''
AS $$
DECLARE
    deleted_count INTEGER;
BEGIN
    -- Delete completed/failed tombstones past expiration
    -- Using fully qualified table name
    DELETE FROM public.compliance_tombstones
    WHERE expires_at < now()
    AND status IN ('completed', 'failed');

    GET DIAGNOSTICS deleted_count = ROW_COUNT;

    -- Log cleanup for monitoring
    IF deleted_count > 0 THEN
        RAISE NOTICE '[ComplianceTombstones] Cleaned up % expired tombstones', deleted_count;
    END IF;

    RETURN deleted_count;
END;
$$;

-- -----------------------------------------------------------------------------
-- 4. is_document_tombstoned
-- -----------------------------------------------------------------------------
CREATE OR REPLACE FUNCTION public.is_document_tombstoned(
    p_document_id UUID,
    p_organization_id UUID
)
RETURNS BOOLEAN
LANGUAGE plpgsql
STABLE
SECURITY DEFINER
SET search_path = ''
AS $$
BEGIN
    RETURN EXISTS (
        SELECT 1 FROM public.compliance_tombstones
        WHERE organization_id = p_organization_id
        AND status = 'active'
        AND p_document_id = ANY(document_ids)
    );
END;
$$;

-- -----------------------------------------------------------------------------
-- 5. get_tombstoned_document_ids
-- -----------------------------------------------------------------------------
CREATE OR REPLACE FUNCTION public.get_tombstoned_document_ids(
    p_organization_id UUID
)
RETURNS UUID[]
LANGUAGE plpgsql
STABLE
SECURITY DEFINER
SET search_path = ''
AS $$
DECLARE
    result UUID[];
BEGIN
    SELECT ARRAY_AGG(DISTINCT unnest_id)
    INTO result
    FROM public.compliance_tombstones t,
         LATERAL UNNEST(t.document_ids) AS unnest_id
    WHERE t.organization_id = p_organization_id
    AND t.status = 'active';

    RETURN COALESCE(result, ARRAY[]::UUID[]);
END;
$$;

-- -----------------------------------------------------------------------------
-- 6. generate_gdpr_compliance_report
-- -----------------------------------------------------------------------------
CREATE OR REPLACE FUNCTION public.generate_gdpr_compliance_report(
    p_organization_id UUID,
    p_start_date TIMESTAMPTZ,
    p_end_date TIMESTAMPTZ
)
RETURNS JSONB
LANGUAGE plpgsql
STABLE
SECURITY DEFINER
SET search_path = ''
AS $$
DECLARE
    result JSONB;
BEGIN
    SELECT jsonb_build_object(
        'organization_id', p_organization_id,
        'period_start', p_start_date,
        'period_end', p_end_date,
        'total_requests', COUNT(*),
        'completed_requests', COUNT(*) FILTER (WHERE deletion_completed_at IS NOT NULL),
        'pending_requests', COUNT(*) FILTER (WHERE deletion_completed_at IS NULL),
        'compliant_requests', COUNT(*) FILTER (WHERE compliant = true),
        'overdue_requests', COUNT(*) FILTER (WHERE deletion_completed_at IS NULL AND deadline_at < now()),
        'compliance_rate', CASE
            WHEN COUNT(*) FILTER (WHERE deletion_completed_at IS NOT NULL) > 0
            THEN ROUND(
                100.0 * COUNT(*) FILTER (WHERE compliant = true) /
                COUNT(*) FILTER (WHERE deletion_completed_at IS NOT NULL),
                2
            )
            ELSE 100.0
        END,
        'avg_time_to_revoke_ms', ROUND(
            AVG(EXTRACT(EPOCH FROM (access_revoked_at - received_at)) * 1000)
            FILTER (WHERE access_revoked_at IS NOT NULL),
            2
        ),
        'avg_time_to_complete_hours', ROUND(
            AVG(EXTRACT(EPOCH FROM (deletion_completed_at - received_at)) / 3600)
            FILTER (WHERE deletion_completed_at IS NOT NULL),
            2
        ),
        'by_request_type', (
            SELECT jsonb_object_agg(request_type, cnt)
            FROM (
                SELECT request_type, COUNT(*) as cnt
                FROM public.compliance_audit_log
                WHERE organization_id = p_organization_id
                AND received_at BETWEEN p_start_date AND p_end_date
                AND regulation = 'gdpr'
                GROUP BY request_type
            ) sub
        ),
        'generated_at', now()
    )
    INTO result
    FROM public.compliance_audit_log
    WHERE organization_id = p_organization_id
    AND received_at BETWEEN p_start_date AND p_end_date
    AND regulation = 'gdpr';

    RETURN COALESCE(result, jsonb_build_object(
        'organization_id', p_organization_id,
        'total_requests', 0,
        'message', 'No GDPR requests in this period'
    ));
END;
$$;

-- -----------------------------------------------------------------------------
-- 7. get_pending_compliance_requests
-- -----------------------------------------------------------------------------
CREATE OR REPLACE FUNCTION public.get_pending_compliance_requests(
    p_organization_id UUID DEFAULT NULL
)
RETURNS TABLE (
    id UUID,
    organization_id UUID,
    request_type TEXT,
    regulation TEXT,
    received_at TIMESTAMPTZ,
    deadline_at TIMESTAMPTZ,
    days_remaining INTEGER,
    is_overdue BOOLEAN
)
LANGUAGE plpgsql
STABLE
SECURITY DEFINER
SET search_path = ''
AS $$
BEGIN
    RETURN QUERY
    SELECT
        cal.id,
        cal.organization_id,
        cal.request_type,
        cal.regulation,
        cal.received_at,
        cal.deadline_at,
        EXTRACT(DAY FROM (cal.deadline_at - now()))::INTEGER as days_remaining,
        cal.deadline_at < now() as is_overdue
    FROM public.compliance_audit_log cal
    WHERE cal.deletion_completed_at IS NULL
    AND (p_organization_id IS NULL OR cal.organization_id = p_organization_id)
    ORDER BY cal.deadline_at ASC;
END;
$$;

-- -----------------------------------------------------------------------------
-- 8. verify_compliance_timeline
-- -----------------------------------------------------------------------------
CREATE OR REPLACE FUNCTION public.verify_compliance_timeline(
    p_audit_id UUID
)
RETURNS JSONB
LANGUAGE plpgsql
STABLE
SECURITY DEFINER
SET search_path = ''
AS $$
DECLARE
    audit_record public.compliance_audit_log%ROWTYPE;
    issues TEXT[] := ARRAY[]::TEXT[];
BEGIN
    SELECT * INTO audit_record FROM public.compliance_audit_log WHERE id = p_audit_id;

    IF audit_record IS NULL THEN
        RETURN jsonb_build_object('valid', false, 'error', 'Audit record not found');
    END IF;

    -- Check timeline consistency
    IF audit_record.access_revoked_at < audit_record.received_at THEN
        issues := array_append(issues, 'access_revoked_at before received_at');
    END IF;

    IF audit_record.deletion_started_at IS NOT NULL
       AND audit_record.deletion_started_at < audit_record.access_revoked_at THEN
        issues := array_append(issues, 'deletion_started_at before access_revoked_at');
    END IF;

    IF audit_record.deletion_completed_at IS NOT NULL
       AND audit_record.deletion_started_at IS NOT NULL
       AND audit_record.deletion_completed_at < audit_record.deletion_started_at THEN
        issues := array_append(issues, 'deletion_completed_at before deletion_started_at');
    END IF;

    -- Check if access was revoked quickly (<1 second is good, <1 minute is acceptable)
    IF audit_record.access_revoked_at - audit_record.received_at > INTERVAL '1 minute' THEN
        issues := array_append(issues, 'slow_access_revocation (>1 minute)');
    END IF;

    RETURN jsonb_build_object(
        'valid', array_length(issues, 1) IS NULL,
        'issues', issues,
        'timeline', jsonb_build_object(
            'received_at', audit_record.received_at,
            'access_revoked_at', audit_record.access_revoked_at,
            'revocation_latency_ms', EXTRACT(EPOCH FROM (audit_record.access_revoked_at - audit_record.received_at)) * 1000,
            'deletion_started_at', audit_record.deletion_started_at,
            'deletion_completed_at', audit_record.deletion_completed_at,
            'compliant', audit_record.compliant
        )
    );
END;
$$;

-- ============================================================================
-- P2: FIX AUTH RLS INITPLAN PERFORMANCE
-- Issue: auth.uid() re-evaluated for each row, causing O(n) function calls
-- Fix: Wrap with (SELECT auth.uid()) to force single evaluation
-- ============================================================================

-- =============================================================================
-- MCP API KEYS POLICIES
-- =============================================================================

DROP POLICY IF EXISTS mcp_api_keys_select ON public.mcp_api_keys;
DROP POLICY IF EXISTS mcp_api_keys_insert ON public.mcp_api_keys;
DROP POLICY IF EXISTS mcp_api_keys_update ON public.mcp_api_keys;
DROP POLICY IF EXISTS mcp_api_keys_delete ON public.mcp_api_keys;
DROP POLICY IF EXISTS mcp_api_keys_service ON public.mcp_api_keys;

-- SELECT: Org members can view
CREATE POLICY mcp_api_keys_select ON public.mcp_api_keys
    FOR SELECT
    TO authenticated
    USING (
        organization_id IN (
            SELECT id FROM public.teams WHERE owner_id = (SELECT auth.uid())
            UNION
            SELECT team_id FROM public.team_members WHERE member_user_id = (SELECT auth.uid())
        )
    );

-- INSERT: Only owners can create
CREATE POLICY mcp_api_keys_insert ON public.mcp_api_keys
    FOR INSERT
    TO authenticated
    WITH CHECK (
        organization_id IN (
            SELECT id FROM public.teams WHERE owner_id = (SELECT auth.uid())
        )
    );

-- UPDATE: Only owners can update
CREATE POLICY mcp_api_keys_update ON public.mcp_api_keys
    FOR UPDATE
    TO authenticated
    USING (
        organization_id IN (
            SELECT id FROM public.teams WHERE owner_id = (SELECT auth.uid())
        )
    );

-- DELETE: Only owners can delete
CREATE POLICY mcp_api_keys_delete ON public.mcp_api_keys
    FOR DELETE
    TO authenticated
    USING (
        organization_id IN (
            SELECT id FROM public.teams WHERE owner_id = (SELECT auth.uid())
        )
    );

-- Service role: Full access (scoped to service_role only)
CREATE POLICY mcp_api_keys_service ON public.mcp_api_keys
    FOR ALL
    TO service_role
    USING (true)
    WITH CHECK (true);

-- =============================================================================
-- ORGANIZATION CONSENTS POLICIES
-- =============================================================================

DROP POLICY IF EXISTS org_consents_select ON public.organization_consents;
DROP POLICY IF EXISTS org_consents_insert ON public.organization_consents;
DROP POLICY IF EXISTS org_consents_update ON public.organization_consents;
DROP POLICY IF EXISTS org_consents_service ON public.organization_consents;

-- SELECT: Org members can read
CREATE POLICY org_consents_select ON public.organization_consents
    FOR SELECT
    TO authenticated
    USING (
        organization_id IN (
            SELECT id FROM public.teams WHERE owner_id = (SELECT auth.uid())
            UNION
            SELECT team_id FROM public.team_members WHERE member_user_id = (SELECT auth.uid())
        )
    );

-- INSERT: Only owners can create
CREATE POLICY org_consents_insert ON public.organization_consents
    FOR INSERT
    TO authenticated
    WITH CHECK (
        organization_id IN (
            SELECT id FROM public.teams WHERE owner_id = (SELECT auth.uid())
        )
    );

-- UPDATE: Only owners can update
CREATE POLICY org_consents_update ON public.organization_consents
    FOR UPDATE
    TO authenticated
    USING (
        organization_id IN (
            SELECT id FROM public.teams WHERE owner_id = (SELECT auth.uid())
        )
    );

-- Service role: Full access (scoped to service_role only)
CREATE POLICY org_consents_service ON public.organization_consents
    FOR ALL
    TO service_role
    USING (true)
    WITH CHECK (true);

-- =============================================================================
-- ACTION APPROVALS POLICIES
-- =============================================================================

DROP POLICY IF EXISTS action_approvals_select ON public.action_approvals;
DROP POLICY IF EXISTS action_approvals_insert ON public.action_approvals;
DROP POLICY IF EXISTS action_approvals_update ON public.action_approvals;
DROP POLICY IF EXISTS action_approvals_service ON public.action_approvals;

-- SELECT: Org members can view
CREATE POLICY action_approvals_select ON public.action_approvals
    FOR SELECT
    TO authenticated
    USING (
        organization_id IN (
            SELECT id FROM public.teams WHERE owner_id = (SELECT auth.uid())
            UNION
            SELECT team_id FROM public.team_members WHERE member_user_id = (SELECT auth.uid())
        )
    );

-- INSERT: Org members can create approval requests
CREATE POLICY action_approvals_insert ON public.action_approvals
    FOR INSERT
    TO authenticated
    WITH CHECK (
        organization_id IN (
            SELECT id FROM public.teams WHERE owner_id = (SELECT auth.uid())
            UNION
            SELECT team_id FROM public.team_members WHERE member_user_id = (SELECT auth.uid())
        )
    );

-- UPDATE: Only owners/admins can approve/reject
CREATE POLICY action_approvals_update ON public.action_approvals
    FOR UPDATE
    TO authenticated
    USING (
        organization_id IN (
            SELECT id FROM public.teams WHERE owner_id = (SELECT auth.uid())
        )
        OR
        organization_id IN (
            SELECT team_id FROM public.team_members
            WHERE member_user_id = (SELECT auth.uid())
            AND role = 'admin'
        )
    );

-- Service role: Full access (scoped to service_role only)
CREATE POLICY action_approvals_service ON public.action_approvals
    FOR ALL
    TO service_role
    USING (true)
    WITH CHECK (true);

-- =============================================================================
-- SCOPE CONSENTS POLICIES
-- =============================================================================

DROP POLICY IF EXISTS scope_consents_select ON public.scope_consents;
DROP POLICY IF EXISTS scope_consents_all ON public.scope_consents;
DROP POLICY IF EXISTS scope_consents_service ON public.scope_consents;

-- SELECT: Org members can read
CREATE POLICY scope_consents_select ON public.scope_consents
    FOR SELECT
    TO authenticated
    USING (
        organization_id IN (
            SELECT id FROM public.teams WHERE owner_id = (SELECT auth.uid())
            UNION
            SELECT team_id FROM public.team_members WHERE member_user_id = (SELECT auth.uid())
        )
    );

-- INSERT/UPDATE/DELETE: Owners and admins
CREATE POLICY scope_consents_modify ON public.scope_consents
    FOR ALL
    TO authenticated
    USING (
        organization_id IN (
            SELECT id FROM public.teams WHERE owner_id = (SELECT auth.uid())
        )
        OR
        organization_id IN (
            SELECT team_id FROM public.team_members
            WHERE member_user_id = (SELECT auth.uid())
            AND role = 'admin'
        )
    )
    WITH CHECK (
        organization_id IN (
            SELECT id FROM public.teams WHERE owner_id = (SELECT auth.uid())
        )
        OR
        organization_id IN (
            SELECT team_id FROM public.team_members
            WHERE member_user_id = (SELECT auth.uid())
            AND role = 'admin'
        )
    );

-- Service role: Full access (scoped to service_role only)
CREATE POLICY scope_consents_service ON public.scope_consents
    FOR ALL
    TO service_role
    USING (true)
    WITH CHECK (true);

-- =============================================================================
-- DOCUMENT CONSENTS POLICIES
-- =============================================================================

DROP POLICY IF EXISTS doc_consents_select ON public.document_consents;
DROP POLICY IF EXISTS doc_consents_all ON public.document_consents;
DROP POLICY IF EXISTS doc_consents_service ON public.document_consents;

-- SELECT: Org members can read
CREATE POLICY doc_consents_select ON public.document_consents
    FOR SELECT
    TO authenticated
    USING (
        organization_id IN (
            SELECT id FROM public.teams WHERE owner_id = (SELECT auth.uid())
            UNION
            SELECT team_id FROM public.team_members WHERE member_user_id = (SELECT auth.uid())
        )
    );

-- INSERT/UPDATE/DELETE: Owners, admins, and editors
CREATE POLICY doc_consents_modify ON public.document_consents
    FOR ALL
    TO authenticated
    USING (
        organization_id IN (
            SELECT id FROM public.teams WHERE owner_id = (SELECT auth.uid())
        )
        OR
        organization_id IN (
            SELECT team_id FROM public.team_members
            WHERE member_user_id = (SELECT auth.uid())
            AND role IN ('admin', 'editor')
        )
    )
    WITH CHECK (
        organization_id IN (
            SELECT id FROM public.teams WHERE owner_id = (SELECT auth.uid())
        )
        OR
        organization_id IN (
            SELECT team_id FROM public.team_members
            WHERE member_user_id = (SELECT auth.uid())
            AND role IN ('admin', 'editor')
        )
    );

-- Service role: Full access (scoped to service_role only)
CREATE POLICY doc_consents_service ON public.document_consents
    FOR ALL
    TO service_role
    USING (true)
    WITH CHECK (true);

-- =============================================================================
-- CONSENT AUDIT LOG POLICIES
-- =============================================================================

DROP POLICY IF EXISTS consent_audit_select ON public.consent_audit_log;
DROP POLICY IF EXISTS consent_audit_service ON public.consent_audit_log;

-- SELECT: Owners and admins can view
CREATE POLICY consent_audit_select ON public.consent_audit_log
    FOR SELECT
    TO authenticated
    USING (
        organization_id IN (
            SELECT id FROM public.teams WHERE owner_id = (SELECT auth.uid())
        )
        OR
        organization_id IN (
            SELECT team_id FROM public.team_members
            WHERE member_user_id = (SELECT auth.uid())
            AND role = 'admin'
        )
    );

-- Service role: Full access (scoped to service_role only)
CREATE POLICY consent_audit_service ON public.consent_audit_log
    FOR ALL
    TO service_role
    USING (true)
    WITH CHECK (true);

-- =============================================================================
-- COMPLIANCE TOMBSTONES POLICIES
-- =============================================================================

DROP POLICY IF EXISTS "Org members can view tombstones" ON public.compliance_tombstones;
DROP POLICY IF EXISTS "Admins can create tombstones" ON public.compliance_tombstones;
DROP POLICY IF EXISTS "Admins can update tombstones" ON public.compliance_tombstones;
DROP POLICY IF EXISTS "Service role full access" ON public.compliance_tombstones;

-- SELECT: Org members can view
CREATE POLICY tombstones_select ON public.compliance_tombstones
    FOR SELECT
    TO authenticated
    USING (
        organization_id IN (
            SELECT tm.team_id FROM public.team_members tm 
            WHERE tm.member_user_id = (SELECT auth.uid())
        )
    );

-- INSERT: Only owners/admins can create deletion requests
CREATE POLICY tombstones_insert ON public.compliance_tombstones
    FOR INSERT
    TO authenticated
    WITH CHECK (
        organization_id IN (
            SELECT tm.team_id FROM public.team_members tm
            WHERE tm.member_user_id = (SELECT auth.uid())
            AND tm.role IN ('admin', 'owner')
        )
    );

-- UPDATE: Only owners/admins can update status
CREATE POLICY tombstones_update ON public.compliance_tombstones
    FOR UPDATE
    TO authenticated
    USING (
        organization_id IN (
            SELECT tm.team_id FROM public.team_members tm
            WHERE tm.member_user_id = (SELECT auth.uid())
            AND tm.role IN ('admin', 'owner')
        )
    );

-- Service role: Full access (scoped to service_role only)
CREATE POLICY tombstones_service ON public.compliance_tombstones
    FOR ALL
    TO service_role
    USING (true)
    WITH CHECK (true);

-- =============================================================================
-- COMPLIANCE AUDIT LOG POLICIES
-- =============================================================================

DROP POLICY IF EXISTS "Admins can view compliance logs" ON public.compliance_audit_log;
DROP POLICY IF EXISTS "Service role full access" ON public.compliance_audit_log;

-- SELECT: Only owners/admins can view sensitive compliance logs
CREATE POLICY compliance_audit_select ON public.compliance_audit_log
    FOR SELECT
    TO authenticated
    USING (
        organization_id IN (
            SELECT tm.team_id FROM public.team_members tm
            WHERE tm.member_user_id = (SELECT auth.uid())
            AND tm.role IN ('admin', 'owner')
        )
    );

-- Service role: Full access (scoped to service_role only)
CREATE POLICY compliance_audit_service ON public.compliance_audit_log
    FOR ALL
    TO service_role
    USING (true)
    WITH CHECK (true);

-- =============================================================================
-- VERIFICATION COMMENTS
-- =============================================================================

COMMENT ON FUNCTION public.update_consent_updated_at IS 'Trigger function with secure search_path';
COMMENT ON FUNCTION public.update_tombstone_timestamp IS 'Trigger function with secure search_path';
COMMENT ON FUNCTION public.cleanup_expired_tombstones IS 'Cleanup function with secure search_path - use fully qualified table names';
COMMENT ON FUNCTION public.is_document_tombstoned IS 'Check if document is tombstoned - secure search_path';
COMMENT ON FUNCTION public.get_tombstoned_document_ids IS 'Get tombstoned document IDs - secure search_path';
COMMENT ON FUNCTION public.generate_gdpr_compliance_report IS 'Generate GDPR report - secure search_path';
COMMENT ON FUNCTION public.get_pending_compliance_requests IS 'Get pending requests - secure search_path';
COMMENT ON FUNCTION public.verify_compliance_timeline IS 'Verify timeline - secure search_path';

-- =============================================================================
-- SECURITY AUDIT LOG ENTRY
-- =============================================================================

-- Log this security migration (if audit_logs table exists)
DO $$
BEGIN
    IF EXISTS (SELECT 1 FROM information_schema.tables WHERE table_name = 'audit_logs' AND table_schema = 'public') THEN
        INSERT INTO public.audit_logs (action, resource_type, details)
        VALUES (
            'security_migration',
            'database',
            jsonb_build_object(
                'migration', '20260203100000_fix_supabase_advisor_security',
                'fixes_applied', jsonb_build_array(
                    'P0: RLS Policy Always True - consent_audit_insert',
                    'P1: Function Search Path - 8 functions secured',
                    'P2: Auth RLS Initplan - 26 policies optimized'
                ),
                'applied_at', now()
            )
        );
    END IF;
EXCEPTION WHEN OTHERS THEN
    -- Ignore if audit_logs doesn't exist or has different schema
    NULL;
END $$;
