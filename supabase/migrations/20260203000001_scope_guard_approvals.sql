-- Scope Guard Action Approvals Table
-- Human-in-the-loop approval workflow for destructive actions

-- Create approval status enum
DO $$
BEGIN
    IF NOT EXISTS (SELECT 1 FROM pg_type WHERE typname = 'approval_status') THEN
        CREATE TYPE approval_status AS ENUM (
            'pending',
            'approved',
            'rejected',
            'expired',
            'executed'
        );
    END IF;
END$$;

-- Create action approvals table
CREATE TABLE IF NOT EXISTS action_approvals (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    organization_id UUID NOT NULL REFERENCES teams(id) ON DELETE CASCADE,

    -- Action details
    action_type TEXT NOT NULL,
    resource_type TEXT NOT NULL,
    resource_id TEXT NOT NULL,

    -- State
    status approval_status NOT NULL DEFAULT 'pending',

    -- Cryptographic mandate
    mandate_nonce TEXT NOT NULL UNIQUE,
    mandate_signature TEXT NOT NULL,

    -- Participants
    requested_by UUID NOT NULL,
    approved_by UUID,

    -- Timing
    requested_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    expires_at TIMESTAMPTZ NOT NULL,
    approved_at TIMESTAMPTZ,
    executed_at TIMESTAMPTZ,

    -- Context & Results
    request_context JSONB DEFAULT '{}',
    execution_result JSONB DEFAULT '{}',

    -- Constraints
    CONSTRAINT action_approvals_action_type_not_empty CHECK (action_type <> ''),
    CONSTRAINT action_approvals_resource_type_not_empty CHECK (resource_type <> ''),
    CONSTRAINT action_approvals_resource_id_not_empty CHECK (resource_id <> '')
);

-- Indexes for efficient queries
CREATE INDEX IF NOT EXISTS idx_action_approvals_org_pending
    ON action_approvals(organization_id, status)
    WHERE status = 'pending';

CREATE INDEX IF NOT EXISTS idx_action_approvals_org_status
    ON action_approvals(organization_id, status, requested_at DESC);

CREATE INDEX IF NOT EXISTS idx_action_approvals_mandate_nonce
    ON action_approvals(mandate_nonce);

CREATE INDEX IF NOT EXISTS idx_action_approvals_expires
    ON action_approvals(expires_at)
    WHERE status = 'pending';

-- RLS Policies
ALTER TABLE action_approvals ENABLE ROW LEVEL SECURITY;

-- Organization members can view their org's approvals
CREATE POLICY action_approvals_select ON action_approvals
    FOR SELECT
    USING (
        organization_id IN (
            SELECT id FROM teams WHERE owner_id = auth.uid()
            UNION
            SELECT team_id FROM team_members WHERE member_user_id = auth.uid()
        )
    );

-- Only team members can create approval requests
CREATE POLICY action_approvals_insert ON action_approvals
    FOR INSERT
    WITH CHECK (
        organization_id IN (
            SELECT id FROM teams WHERE owner_id = auth.uid()
            UNION
            SELECT team_id FROM team_members WHERE member_user_id = auth.uid()
        )
    );

-- Only team owners/admins can update approvals (approve/reject/execute)
CREATE POLICY action_approvals_update ON action_approvals
    FOR UPDATE
    USING (
        organization_id IN (
            SELECT id FROM teams WHERE owner_id = auth.uid()
        )
        OR
        organization_id IN (
            SELECT team_id FROM team_members
            WHERE member_user_id = auth.uid()
            AND role IN ('admin')
        )
    );

-- Service role bypass for backend operations
CREATE POLICY action_approvals_service ON action_approvals
    FOR ALL
    USING (auth.jwt() ->> 'role' = 'service_role');

-- Comments
COMMENT ON TABLE action_approvals IS 'Human-in-the-loop approval workflow for destructive actions';
COMMENT ON COLUMN action_approvals.mandate_nonce IS 'Unique nonce for preventing replay attacks';
COMMENT ON COLUMN action_approvals.mandate_signature IS 'HMAC-SHA256 signature for mandate verification';
COMMENT ON COLUMN action_approvals.request_context IS 'Additional context for the approval (e.g., document IDs for bulk delete)';
COMMENT ON COLUMN action_approvals.execution_result IS 'Result of the executed action';
