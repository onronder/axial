-- MCP API Keys Table
-- Stores API keys for MCP (Model Context Protocol) agent access

CREATE TABLE IF NOT EXISTS mcp_api_keys (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    organization_id UUID NOT NULL REFERENCES teams(id) ON DELETE CASCADE,
    key_hash TEXT NOT NULL UNIQUE,  -- SHA-256 hash of the actual key
    agent_name TEXT NOT NULL,
    scopes TEXT[] DEFAULT ARRAY['*']::TEXT[],  -- Allowed scope patterns
    created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    expires_at TIMESTAMPTZ,
    revoked_at TIMESTAMPTZ,

    -- Constraints
    CONSTRAINT mcp_api_keys_agent_name_not_empty CHECK (agent_name <> '')
);

-- Indexes for efficient lookups
CREATE INDEX idx_mcp_api_keys_org ON mcp_api_keys(organization_id);
CREATE INDEX idx_mcp_api_keys_key_hash ON mcp_api_keys(key_hash) WHERE revoked_at IS NULL;
CREATE INDEX idx_mcp_api_keys_active ON mcp_api_keys(organization_id, created_at DESC)
    WHERE revoked_at IS NULL;

-- RLS Policies
ALTER TABLE mcp_api_keys ENABLE ROW LEVEL SECURITY;

-- Organization members can view their org's API keys
CREATE POLICY mcp_api_keys_select ON mcp_api_keys
    FOR SELECT
    USING (
        organization_id IN (
            SELECT id FROM teams WHERE owner_id = auth.uid()
            UNION
            SELECT team_id FROM team_members WHERE member_user_id = auth.uid()
        )
    );

-- Only team owners can create/update/delete API keys
CREATE POLICY mcp_api_keys_insert ON mcp_api_keys
    FOR INSERT
    WITH CHECK (
        organization_id IN (
            SELECT id FROM teams WHERE owner_id = auth.uid()
        )
    );

CREATE POLICY mcp_api_keys_update ON mcp_api_keys
    FOR UPDATE
    USING (
        organization_id IN (
            SELECT id FROM teams WHERE owner_id = auth.uid()
        )
    );

CREATE POLICY mcp_api_keys_delete ON mcp_api_keys
    FOR DELETE
    USING (
        organization_id IN (
            SELECT id FROM teams WHERE owner_id = auth.uid()
        )
    );

-- Service role bypass for backend operations
CREATE POLICY mcp_api_keys_service ON mcp_api_keys
    FOR ALL
    USING (auth.jwt() ->> 'role' = 'service_role');

-- Comments
COMMENT ON TABLE mcp_api_keys IS 'API keys for MCP (Model Context Protocol) agent access';
COMMENT ON COLUMN mcp_api_keys.key_hash IS 'SHA-256 hash of the API key (never store plaintext)';
COMMENT ON COLUMN mcp_api_keys.scopes IS 'Array of scope patterns this key can access (e.g., ["*"], ["gdrive:*"])';
COMMENT ON COLUMN mcp_api_keys.revoked_at IS 'When the key was revoked (NULL = active)';
