-- =============================================================================
-- Compliance Audit Log: Legal Proof of Compliance Timeline
-- GDPR Article 17 / CCPA 2026 ADMT Documentation
--
-- This table provides legally defensible evidence of compliance:
-- - Precise timestamps for access revocation and deletion
-- - GDPR 30-day deadline tracking with auto-calculated compliance status
-- - Full audit trail for regulatory inquiries
-- =============================================================================

CREATE TABLE IF NOT EXISTS compliance_audit_log (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),

    -- Link to tombstone (if applicable)
    tombstone_id UUID REFERENCES compliance_tombstones(id) ON DELETE SET NULL,
    request_id UUID NOT NULL,
    organization_id UUID NOT NULL REFERENCES teams(id) ON DELETE CASCADE,

    -- Compliance context
    regulation TEXT NOT NULL CHECK (regulation IN ('gdpr', 'ccpa', 'kvkk', 'internal')),
    article TEXT,                        -- 'art17', 'admt_optout', etc.
    request_type TEXT NOT NULL CHECK (request_type IN ('deletion', 'optout', 'rectification', 'access', 'portability')),

    -- Subject information (pseudonymized for privacy-by-design)
    -- We store hashes, not actual IDs, to protect subject identity in logs
    subject_type TEXT NOT NULL CHECK (subject_type IN ('user', 'organization', 'document', 'scope')),
    subject_id_hash TEXT NOT NULL,       -- SHA-256 of actual ID

    -- ==========================================================================
    -- TIMELINE: Critical for legal compliance proof
    -- ==========================================================================

    -- When we received the deletion request
    received_at TIMESTAMPTZ NOT NULL,

    -- When tombstone became active (data blocked from access)
    -- GDPR Article 17(2): "without undue delay" - we achieve <20ms
    access_revoked_at TIMESTAMPTZ NOT NULL,

    -- When actual deletion process started
    deletion_started_at TIMESTAMPTZ,

    -- When deletion was verified complete
    deletion_completed_at TIMESTAMPTZ,

    -- ==========================================================================
    -- DELETION DETAILS
    -- ==========================================================================

    -- What categories of data were deleted
    data_types_deleted TEXT[] DEFAULT ARRAY[]::TEXT[],
    -- e.g., ['document_chunks', 'embeddings', 'files', 'metadata']

    -- Counts of items deleted (for verification)
    items_deleted JSONB DEFAULT '{}'::JSONB,
    -- e.g., {"documents": 5, "chunks": 120, "files": 3}

    -- ==========================================================================
    -- VERIFICATION
    -- ==========================================================================

    -- How deletion was verified
    verification_method TEXT CHECK (verification_method IN ('cascade_confirm', 'manual_audit', 'automated_check', 'sampling')),

    -- Whether verification passed
    verification_passed BOOLEAN,

    -- Detailed verification results
    verification_details JSONB,
    -- e.g., {"storage_cleared": true, "vectors_deleted": 120, "cascade_complete": true}

    -- ==========================================================================
    -- REQUESTOR INFORMATION (for audit trail)
    -- ==========================================================================

    requestor_id UUID REFERENCES auth.users(id) ON DELETE SET NULL,
    requestor_ip INET,
    requestor_user_agent TEXT,

    -- ==========================================================================
    -- GDPR COMPLIANCE DEADLINE
    -- ==========================================================================

    -- GDPR Article 12(3): Response within one month, extendable to three months
    -- Default: 30 days from request
    deadline_at TIMESTAMPTZ DEFAULT now() + INTERVAL '30 days',

    -- Auto-calculated compliance status
    -- TRUE if deletion completed before deadline
    compliant BOOLEAN GENERATED ALWAYS AS (
        deletion_completed_at IS NOT NULL
        AND deletion_completed_at <= deadline_at
    ) STORED,

    -- ==========================================================================
    -- AUDIT METADATA
    -- ==========================================================================

    created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    notes TEXT  -- For manual annotations by compliance officers
);

-- =============================================================================
-- INDEXES
-- =============================================================================

-- Primary lookup: compliance logs for an organization
CREATE INDEX idx_compliance_audit_org ON compliance_audit_log(organization_id, received_at DESC);

-- Pending requests (not yet completed) - for monitoring dashboards
-- Also supports overdue queries: WHERE deadline_at < now() at query time
CREATE INDEX idx_compliance_audit_pending ON compliance_audit_log(deadline_at)
    WHERE deletion_completed_at IS NULL;

-- By regulation - for regulatory reporting
CREATE INDEX idx_compliance_audit_regulation ON compliance_audit_log(regulation, created_at DESC);

-- By request ID - for tracking specific requests
CREATE INDEX idx_compliance_audit_request_id ON compliance_audit_log(request_id);

-- Tombstone linkage
CREATE INDEX idx_compliance_audit_tombstone ON compliance_audit_log(tombstone_id)
    WHERE tombstone_id IS NOT NULL;

-- Compliance status - for generating compliance reports
CREATE INDEX idx_compliance_audit_compliant ON compliance_audit_log(compliant, regulation)
    WHERE deletion_completed_at IS NOT NULL;

-- =============================================================================
-- ROW LEVEL SECURITY
-- =============================================================================

ALTER TABLE compliance_audit_log ENABLE ROW LEVEL SECURITY;

-- Only admins/owners can view compliance logs (sensitive data)
CREATE POLICY "Admins can view compliance logs"
    ON compliance_audit_log FOR SELECT
    USING (organization_id IN (
        SELECT tm.team_id FROM team_members tm
        WHERE tm.member_user_id = auth.uid()
        AND tm.role IN ('admin', 'owner')
    ));

-- Service role full access for backend operations
CREATE POLICY "Service role full access"
    ON compliance_audit_log FOR ALL
    USING (auth.role() = 'service_role');

-- =============================================================================
-- COMPLIANCE REPORTING FUNCTIONS
-- =============================================================================

-- Generate GDPR Article 17 compliance report for a time period
CREATE OR REPLACE FUNCTION generate_gdpr_compliance_report(
    p_organization_id UUID,
    p_start_date TIMESTAMPTZ,
    p_end_date TIMESTAMPTZ
)
RETURNS JSONB AS $$
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
                FROM compliance_audit_log
                WHERE organization_id = p_organization_id
                AND received_at BETWEEN p_start_date AND p_end_date
                AND regulation = 'gdpr'
                GROUP BY request_type
            ) sub
        ),
        'generated_at', now()
    )
    INTO result
    FROM compliance_audit_log
    WHERE organization_id = p_organization_id
    AND received_at BETWEEN p_start_date AND p_end_date
    AND regulation = 'gdpr';

    RETURN COALESCE(result, jsonb_build_object(
        'organization_id', p_organization_id,
        'total_requests', 0,
        'message', 'No GDPR requests in this period'
    ));
END;
$$ LANGUAGE plpgsql STABLE SECURITY DEFINER;

-- Get pending/overdue compliance requests for alerting
CREATE OR REPLACE FUNCTION get_pending_compliance_requests(
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
) AS $$
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
    FROM compliance_audit_log cal
    WHERE cal.deletion_completed_at IS NULL
    AND (p_organization_id IS NULL OR cal.organization_id = p_organization_id)
    ORDER BY cal.deadline_at ASC;
END;
$$ LANGUAGE plpgsql STABLE SECURITY DEFINER;

-- =============================================================================
-- TIMELINE VERIFICATION FUNCTION
-- =============================================================================

-- Verify that timeline entries are consistent (for data integrity)
CREATE OR REPLACE FUNCTION verify_compliance_timeline(
    p_audit_id UUID
)
RETURNS JSONB AS $$
DECLARE
    audit_record compliance_audit_log%ROWTYPE;
    issues TEXT[] := ARRAY[]::TEXT[];
BEGIN
    SELECT * INTO audit_record FROM compliance_audit_log WHERE id = p_audit_id;

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
$$ LANGUAGE plpgsql STABLE SECURITY DEFINER;

-- =============================================================================
-- GRANTS
-- =============================================================================

GRANT SELECT ON compliance_audit_log TO authenticated;
GRANT ALL ON compliance_audit_log TO service_role;
GRANT EXECUTE ON FUNCTION generate_gdpr_compliance_report TO authenticated;
GRANT EXECUTE ON FUNCTION generate_gdpr_compliance_report TO service_role;
GRANT EXECUTE ON FUNCTION get_pending_compliance_requests TO authenticated;
GRANT EXECUTE ON FUNCTION get_pending_compliance_requests TO service_role;
GRANT EXECUTE ON FUNCTION verify_compliance_timeline TO authenticated;
GRANT EXECUTE ON FUNCTION verify_compliance_timeline TO service_role;

COMMENT ON TABLE compliance_audit_log IS 'Legal compliance audit trail with precise timeline proof for GDPR/CCPA regulatory inquiries';
COMMENT ON COLUMN compliance_audit_log.compliant IS 'Auto-calculated: TRUE if deletion completed before GDPR 30-day deadline';
COMMENT ON COLUMN compliance_audit_log.subject_id_hash IS 'SHA-256 hash of subject ID for privacy-by-design - original ID not stored';
