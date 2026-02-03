-- KVKK 2026 Consent Management Tables
-- Granular consent controls for AI learning and external agent access

-- =============================================================================
-- Organization Consents (Default settings for entire organization)
-- =============================================================================

CREATE TABLE IF NOT EXISTS organization_consents (
    organization_id UUID PRIMARY KEY REFERENCES teams(id) ON DELETE CASCADE,

    -- AI Learning consent
    allow_ai_learning BOOLEAN NOT NULL DEFAULT false,
    ai_learning_consent_at TIMESTAMPTZ,
    ai_learning_consented_by UUID,

    -- External Agents consent (MCP access)
    allow_external_agents BOOLEAN NOT NULL DEFAULT false,
    external_agents_consent_at TIMESTAMPTZ,
    external_agents_consented_by UUID,

    -- Retention policy
    retention_policy TEXT DEFAULT 'default',

    -- Timestamps
    created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT now()
);

-- =============================================================================
-- Scope Consents (Override settings for specific scopes)
-- =============================================================================

CREATE TABLE IF NOT EXISTS scope_consents (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    scope_id TEXT NOT NULL,
    organization_id UUID NOT NULL REFERENCES teams(id) ON DELETE CASCADE,

    -- Inheritance
    inherit_org_consent BOOLEAN NOT NULL DEFAULT true,

    -- Consent overrides (NULL = inherit from org)
    allow_ai_learning BOOLEAN,
    allow_external_agents BOOLEAN,

    -- Agent-specific controls
    allowed_agent_ids TEXT[] DEFAULT ARRAY[]::TEXT[],
    blocked_agent_ids TEXT[] DEFAULT ARRAY[]::TEXT[],

    -- Audit
    consented_by UUID,
    consented_at TIMESTAMPTZ,

    -- Timestamps
    created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT now(),

    -- Unique constraint
    UNIQUE(scope_id, organization_id)
);

-- =============================================================================
-- Document Consents (Override settings for specific documents)
-- =============================================================================

CREATE TABLE IF NOT EXISTS document_consents (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    document_id UUID NOT NULL REFERENCES documents(id) ON DELETE CASCADE,
    organization_id UUID NOT NULL REFERENCES teams(id) ON DELETE CASCADE,

    -- Inheritance
    inherit_scope_consent BOOLEAN NOT NULL DEFAULT true,

    -- Consent overrides (NULL = inherit from scope/org)
    allow_ai_learning BOOLEAN,
    allow_external_agents BOOLEAN,

    -- Agent-specific controls
    allowed_agent_ids TEXT[] DEFAULT ARRAY[]::TEXT[],
    blocked_agent_ids TEXT[] DEFAULT ARRAY[]::TEXT[],

    -- Timestamps
    created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT now(),

    -- Unique constraint
    UNIQUE(document_id, organization_id)
);

-- =============================================================================
-- Consent Audit Log
-- =============================================================================

CREATE TABLE IF NOT EXISTS consent_audit_log (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    organization_id UUID NOT NULL,
    consent_level TEXT NOT NULL,  -- 'organization' | 'scope' | 'document'
    resource_id TEXT NOT NULL,
    field_changed TEXT NOT NULL,
    old_value JSONB,
    new_value JSONB,
    changed_by UUID NOT NULL,
    changed_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    ip_address INET,
    user_agent TEXT,

    -- Constraint
    CONSTRAINT consent_audit_log_level_valid CHECK (
        consent_level IN ('organization', 'scope', 'document')
    )
);

-- =============================================================================
-- Indexes
-- =============================================================================

-- Organization consents
CREATE INDEX IF NOT EXISTS idx_org_consents_org ON organization_consents(organization_id);

-- Scope consents
CREATE INDEX IF NOT EXISTS idx_scope_consents_org ON scope_consents(organization_id);
CREATE INDEX IF NOT EXISTS idx_scope_consents_scope ON scope_consents(scope_id, organization_id);

-- Document consents
CREATE INDEX IF NOT EXISTS idx_doc_consents_org ON document_consents(organization_id);
CREATE INDEX IF NOT EXISTS idx_doc_consents_doc ON document_consents(document_id, organization_id);

-- Audit log
CREATE INDEX IF NOT EXISTS idx_consent_audit_org ON consent_audit_log(organization_id, changed_at DESC);
CREATE INDEX IF NOT EXISTS idx_consent_audit_resource ON consent_audit_log(resource_id, changed_at DESC);

-- =============================================================================
-- RLS Policies
-- =============================================================================

ALTER TABLE organization_consents ENABLE ROW LEVEL SECURITY;
ALTER TABLE scope_consents ENABLE ROW LEVEL SECURITY;
ALTER TABLE document_consents ENABLE ROW LEVEL SECURITY;
ALTER TABLE consent_audit_log ENABLE ROW LEVEL SECURITY;

-- Organization consents - org members can read, admins can write
CREATE POLICY org_consents_select ON organization_consents
    FOR SELECT
    USING (
        organization_id IN (
            SELECT id FROM teams WHERE owner_id = auth.uid()
            UNION
            SELECT team_id FROM team_members WHERE member_user_id = auth.uid()
        )
    );

CREATE POLICY org_consents_insert ON organization_consents
    FOR INSERT
    WITH CHECK (
        organization_id IN (
            SELECT id FROM teams WHERE owner_id = auth.uid()
        )
    );

CREATE POLICY org_consents_update ON organization_consents
    FOR UPDATE
    USING (
        organization_id IN (
            SELECT id FROM teams WHERE owner_id = auth.uid()
        )
    );

-- Scope consents - same pattern
CREATE POLICY scope_consents_select ON scope_consents
    FOR SELECT
    USING (
        organization_id IN (
            SELECT id FROM teams WHERE owner_id = auth.uid()
            UNION
            SELECT team_id FROM team_members WHERE member_user_id = auth.uid()
        )
    );

CREATE POLICY scope_consents_all ON scope_consents
    FOR ALL
    USING (
        organization_id IN (
            SELECT id FROM teams WHERE owner_id = auth.uid()
        )
        OR
        organization_id IN (
            SELECT team_id FROM team_members
            WHERE member_user_id = auth.uid()
            AND role = 'admin'
        )
    );

-- Document consents - editors can modify
CREATE POLICY doc_consents_select ON document_consents
    FOR SELECT
    USING (
        organization_id IN (
            SELECT id FROM teams WHERE owner_id = auth.uid()
            UNION
            SELECT team_id FROM team_members WHERE member_user_id = auth.uid()
        )
    );

CREATE POLICY doc_consents_all ON document_consents
    FOR ALL
    USING (
        organization_id IN (
            SELECT id FROM teams WHERE owner_id = auth.uid()
        )
        OR
        organization_id IN (
            SELECT team_id FROM team_members
            WHERE member_user_id = auth.uid()
            AND role IN ('admin', 'editor')
        )
    );

-- Audit log - admins only
CREATE POLICY consent_audit_select ON consent_audit_log
    FOR SELECT
    USING (
        organization_id IN (
            SELECT id FROM teams WHERE owner_id = auth.uid()
        )
        OR
        organization_id IN (
            SELECT team_id FROM team_members
            WHERE member_user_id = auth.uid()
            AND role = 'admin'
        )
    );

CREATE POLICY consent_audit_insert ON consent_audit_log
    FOR INSERT
    WITH CHECK (true);  -- Backend can always insert

-- Service role bypass
CREATE POLICY org_consents_service ON organization_consents
    FOR ALL USING (auth.jwt() ->> 'role' = 'service_role');

CREATE POLICY scope_consents_service ON scope_consents
    FOR ALL USING (auth.jwt() ->> 'role' = 'service_role');

CREATE POLICY doc_consents_service ON document_consents
    FOR ALL USING (auth.jwt() ->> 'role' = 'service_role');

CREATE POLICY consent_audit_service ON consent_audit_log
    FOR ALL USING (auth.jwt() ->> 'role' = 'service_role');

-- =============================================================================
-- Triggers for updated_at
-- =============================================================================

CREATE OR REPLACE FUNCTION update_consent_updated_at()
RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_at = now();
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

DROP TRIGGER IF EXISTS org_consents_updated_at ON organization_consents;
CREATE TRIGGER org_consents_updated_at
    BEFORE UPDATE ON organization_consents
    FOR EACH ROW EXECUTE FUNCTION update_consent_updated_at();

DROP TRIGGER IF EXISTS scope_consents_updated_at ON scope_consents;
CREATE TRIGGER scope_consents_updated_at
    BEFORE UPDATE ON scope_consents
    FOR EACH ROW EXECUTE FUNCTION update_consent_updated_at();

DROP TRIGGER IF EXISTS doc_consents_updated_at ON document_consents;
CREATE TRIGGER doc_consents_updated_at
    BEFORE UPDATE ON document_consents
    FOR EACH ROW EXECUTE FUNCTION update_consent_updated_at();

-- =============================================================================
-- Comments
-- =============================================================================

COMMENT ON TABLE organization_consents IS 'Organization-level consent defaults for KVKK compliance';
COMMENT ON TABLE scope_consents IS 'Scope-level consent overrides (inherits from organization if not set)';
COMMENT ON TABLE document_consents IS 'Document-level consent overrides (inherits from scope/org if not set)';
COMMENT ON TABLE consent_audit_log IS 'Audit trail of all consent changes for compliance reporting';

COMMENT ON COLUMN organization_consents.allow_ai_learning IS 'Whether data can be used for AI model training';
COMMENT ON COLUMN organization_consents.allow_external_agents IS 'Whether external AI agents (MCP) can access data';
COMMENT ON COLUMN scope_consents.inherit_org_consent IS 'If true, uses organization-level consent settings';
COMMENT ON COLUMN document_consents.inherit_scope_consent IS 'If true, uses scope-level (or org-level) consent settings';
