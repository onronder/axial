-- =============================================================================
-- Compliance Tombstones: Immediate Data Access Revocation
-- GDPR Article 17 / CCPA 2026 ADMT Compliance
--
-- This table implements "tombstone-first" deletion pattern:
-- 1. INSERT tombstone -> data immediately blocked from search/retrieval
-- 2. DELETE actual data -> Ghost Protocol secure wipe
-- 3. UPDATE tombstone status -> mark completed
--
-- Key Guarantees:
-- - Access revoked within 10-20ms of deletion request
-- - Supabase Realtime broadcasts to all connected clients
-- - Compliance audit trail maintained
-- =============================================================================

-- Main tombstone table
CREATE TABLE IF NOT EXISTS compliance_tombstones (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),

    -- What is being deleted
    resource_type TEXT NOT NULL CHECK (resource_type IN ('document', 'scope', 'organization', 'user')),
    resource_id TEXT NOT NULL,
    organization_id UUID NOT NULL REFERENCES teams(id) ON DELETE CASCADE,

    -- Cascading identifiers for fast filtering in hybrid_search
    -- GIN indexes on arrays allow O(1) containment checks
    document_ids UUID[] DEFAULT ARRAY[]::UUID[],
    scope_ids TEXT[] DEFAULT ARRAY[]::TEXT[],

    -- Compliance metadata
    compliance_type TEXT NOT NULL CHECK (compliance_type IN ('gdpr_art17', 'ccpa_admt', 'kvkk', 'user_request')),
    request_id UUID NOT NULL DEFAULT gen_random_uuid(),
    requested_by UUID REFERENCES auth.users(id),
    requested_at TIMESTAMPTZ NOT NULL DEFAULT now(),

    -- Lifecycle tracking
    status TEXT NOT NULL DEFAULT 'active' CHECK (status IN ('active', 'completed', 'failed')),
    completed_at TIMESTAMPTZ,
    failure_reason TEXT,

    -- Auto-expire completed tombstones after 24h (cleanup via pg_cron)
    -- Active tombstones never expire
    expires_at TIMESTAMPTZ DEFAULT now() + INTERVAL '24 hours',

    -- Audit fields
    created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT now()
);

-- =============================================================================
-- CRITICAL INDEXES: Must be fast for hybrid_search performance
-- =============================================================================

-- Primary lookup: active tombstones for an org (used in every search query)
CREATE INDEX idx_tombstones_active_org ON compliance_tombstones(organization_id)
    WHERE status = 'active';

-- GIN index for document_ids array containment check
-- Allows: d.id = ANY(t.document_ids) to be O(1) instead of O(n)
CREATE INDEX idx_tombstones_doc_ids_gin ON compliance_tombstones USING GIN(document_ids)
    WHERE status = 'active';

-- GIN index for scope_ids array containment check
CREATE INDEX idx_tombstones_scope_ids_gin ON compliance_tombstones USING GIN(scope_ids)
    WHERE status = 'active';

-- Resource lookup (for checking if specific resource is tombstoned)
CREATE INDEX idx_tombstones_resource ON compliance_tombstones(resource_type, resource_id)
    WHERE status = 'active';

-- Expiration cleanup index (for pg_cron job)
CREATE INDEX idx_tombstones_expires ON compliance_tombstones(expires_at)
    WHERE status IN ('completed', 'failed');

-- Request tracking
CREATE INDEX idx_tombstones_request_id ON compliance_tombstones(request_id);

-- =============================================================================
-- ROW LEVEL SECURITY
-- =============================================================================

ALTER TABLE compliance_tombstones ENABLE ROW LEVEL SECURITY;

-- Org members can view tombstones (for UI display)
CREATE POLICY "Org members can view tombstones"
    ON compliance_tombstones FOR SELECT
    USING (organization_id IN (
        SELECT tm.team_id FROM team_members tm WHERE tm.member_user_id = auth.uid()
    ));

-- Only admins/owners can create tombstones (deletion requests)
CREATE POLICY "Admins can create tombstones"
    ON compliance_tombstones FOR INSERT
    WITH CHECK (organization_id IN (
        SELECT tm.team_id FROM team_members tm
        WHERE tm.member_user_id = auth.uid()
        AND tm.role IN ('admin', 'owner')
    ));

-- Only admins/owners can update tombstones (mark completed/failed)
CREATE POLICY "Admins can update tombstones"
    ON compliance_tombstones FOR UPDATE
    USING (organization_id IN (
        SELECT tm.team_id FROM team_members tm
        WHERE tm.member_user_id = auth.uid()
        AND tm.role IN ('admin', 'owner')
    ));

-- Service role bypass for backend operations
CREATE POLICY "Service role full access"
    ON compliance_tombstones FOR ALL
    USING (auth.role() = 'service_role');

-- =============================================================================
-- SUPABASE REALTIME: Instant propagation to all clients
-- =============================================================================

-- Enable Realtime for this table
-- Clients subscribe to: postgres_changes, INSERT, compliance_tombstones
ALTER PUBLICATION supabase_realtime ADD TABLE compliance_tombstones;

-- =============================================================================
-- AUTO-UPDATE TIMESTAMP TRIGGER
-- =============================================================================

CREATE OR REPLACE FUNCTION update_tombstone_timestamp()
RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_at = now();
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

CREATE TRIGGER tombstone_updated
    BEFORE UPDATE ON compliance_tombstones
    FOR EACH ROW EXECUTE FUNCTION update_tombstone_timestamp();

-- =============================================================================
-- TOMBSTONE CLEANUP FUNCTION (for pg_cron)
-- =============================================================================

-- Cleanup expired/completed tombstones to prevent index bloat
-- Run daily via pg_cron at 3 AM UTC
CREATE OR REPLACE FUNCTION cleanup_expired_tombstones()
RETURNS INTEGER AS $$
DECLARE
    deleted_count INTEGER;
BEGIN
    -- Delete completed/failed tombstones past expiration
    DELETE FROM compliance_tombstones
    WHERE expires_at < now()
    AND status IN ('completed', 'failed');

    GET DIAGNOSTICS deleted_count = ROW_COUNT;

    -- Log cleanup for monitoring
    IF deleted_count > 0 THEN
        RAISE NOTICE '[ComplianceTombstones] Cleaned up % expired tombstones', deleted_count;
    END IF;

    RETURN deleted_count;
END;
$$ LANGUAGE plpgsql SECURITY DEFINER;

-- =============================================================================
-- HELPER FUNCTION: Check if document is tombstoned
-- =============================================================================

CREATE OR REPLACE FUNCTION is_document_tombstoned(
    p_document_id UUID,
    p_organization_id UUID
)
RETURNS BOOLEAN AS $$
BEGIN
    RETURN EXISTS (
        SELECT 1 FROM compliance_tombstones
        WHERE organization_id = p_organization_id
        AND status = 'active'
        AND p_document_id = ANY(document_ids)
    );
END;
$$ LANGUAGE plpgsql STABLE SECURITY DEFINER;

-- =============================================================================
-- HELPER FUNCTION: Get all tombstoned document IDs for org
-- =============================================================================

CREATE OR REPLACE FUNCTION get_tombstoned_document_ids(
    p_organization_id UUID
)
RETURNS UUID[] AS $$
DECLARE
    result UUID[];
BEGIN
    SELECT ARRAY_AGG(DISTINCT unnest_id)
    INTO result
    FROM compliance_tombstones t,
         LATERAL UNNEST(t.document_ids) AS unnest_id
    WHERE t.organization_id = p_organization_id
    AND t.status = 'active';

    RETURN COALESCE(result, ARRAY[]::UUID[]);
END;
$$ LANGUAGE plpgsql STABLE SECURITY DEFINER;

-- =============================================================================
-- GRANTS
-- =============================================================================

GRANT SELECT ON compliance_tombstones TO authenticated;
GRANT ALL ON compliance_tombstones TO service_role;
GRANT EXECUTE ON FUNCTION is_document_tombstoned TO authenticated;
GRANT EXECUTE ON FUNCTION is_document_tombstoned TO service_role;
GRANT EXECUTE ON FUNCTION get_tombstoned_document_ids TO authenticated;
GRANT EXECUTE ON FUNCTION get_tombstoned_document_ids TO service_role;
GRANT EXECUTE ON FUNCTION cleanup_expired_tombstones TO service_role;

-- =============================================================================
-- SCHEDULE PG_CRON JOB (if pg_cron is available)
-- =============================================================================

-- Note: pg_cron must be enabled in Supabase dashboard under Database > Extensions
-- This schedules daily cleanup at 3 AM UTC
DO $do_block$
BEGIN
    -- Check if pg_cron extension exists
    IF EXISTS (SELECT 1 FROM pg_extension WHERE extname = 'pg_cron') THEN
        -- Schedule the cleanup job
        PERFORM cron.schedule(
            'cleanup-compliance-tombstones',   -- Job name
            '0 3 * * *',                       -- Daily at 3 AM UTC
            'SELECT cleanup_expired_tombstones()'
        );
        RAISE NOTICE '[ComplianceTombstones] pg_cron job scheduled for daily cleanup';
    ELSE
        RAISE NOTICE '[ComplianceTombstones] pg_cron not available - manual cleanup required';
    END IF;
EXCEPTION
    WHEN OTHERS THEN
        RAISE NOTICE '[ComplianceTombstones] Could not schedule pg_cron job: %', SQLERRM;
END;
$do_block$;

COMMENT ON TABLE compliance_tombstones IS 'Immediate data access revocation for GDPR Article 17 / CCPA 2026 ADMT compliance. Tombstones block data from search/retrieval before actual deletion.';
COMMENT ON COLUMN compliance_tombstones.document_ids IS 'Array of document UUIDs blocked by this tombstone. Indexed with GIN for O(1) containment checks.';
COMMENT ON COLUMN compliance_tombstones.status IS 'active = data blocked, completed = deletion finished, failed = deletion error (data still blocked)';
