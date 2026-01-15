-- Migration: Add organization_id for org-scoped access

BEGIN;

ALTER TABLE scope_identities ADD COLUMN IF NOT EXISTS organization_id UUID;
ALTER TABLE documents ADD COLUMN IF NOT EXISTS organization_id UUID;
ALTER TABLE ingestion_jobs ADD COLUMN IF NOT EXISTS organization_id UUID;

-- Backfill organization_id from team memberships
UPDATE scope_identities s
SET organization_id = tm.team_id
FROM team_members tm
WHERE tm.member_user_id = s.user_id
  AND s.organization_id IS NULL;

UPDATE documents d
SET organization_id = tm.team_id
FROM team_members tm
WHERE tm.member_user_id = d.user_id
  AND d.organization_id IS NULL;

-- Fallback for owners without membership rows
UPDATE scope_identities s
SET organization_id = t.id
FROM teams t
WHERE t.owner_id = s.user_id
  AND s.organization_id IS NULL;

UPDATE documents d
SET organization_id = t.id
FROM teams t
WHERE t.owner_id = d.user_id
  AND d.organization_id IS NULL;

-- Final fallback to avoid NULLs
UPDATE scope_identities SET organization_id = user_id WHERE organization_id IS NULL;
UPDATE documents SET organization_id = user_id WHERE organization_id IS NULL;

-- Align team_id for existing documents (team access RLS)
UPDATE documents SET team_id = organization_id WHERE team_id IS NULL;

ALTER TABLE scope_identities ALTER COLUMN organization_id SET NOT NULL;
ALTER TABLE documents ALTER COLUMN organization_id SET NOT NULL;

-- Optional: enforce user_id not null when safe
DO $$
BEGIN
    IF NOT EXISTS (SELECT 1 FROM documents WHERE user_id IS NULL) THEN
        ALTER TABLE documents ALTER COLUMN user_id SET NOT NULL;
    END IF;
END $$;

ALTER TABLE documents DROP CONSTRAINT IF EXISTS documents_scope_id_fkey;
ALTER TABLE scope_identities DROP CONSTRAINT IF EXISTS scope_identities_pkey;

ALTER TABLE scope_identities
    ADD CONSTRAINT scope_identities_pkey PRIMARY KEY (organization_id, id);

ALTER TABLE documents
    ADD CONSTRAINT documents_scope_id_fkey
    FOREIGN KEY (organization_id, scope_id)
    REFERENCES scope_identities(organization_id, id)
    ON DELETE CASCADE;

CREATE INDEX IF NOT EXISTS idx_documents_org_scope_id ON documents(organization_id, scope_id);

-- Update scope_identities RLS to org-aware policies
DROP POLICY IF EXISTS "scope_identities_select_own" ON scope_identities;
DROP POLICY IF EXISTS "scope_identities_insert_own" ON scope_identities;
DROP POLICY IF EXISTS "scope_identities_update_own" ON scope_identities;
DROP POLICY IF EXISTS "scope_identities_delete_own" ON scope_identities;

CREATE POLICY "scope_identities_select_org" ON scope_identities
    FOR SELECT
    USING (
        organization_id IN (
            SELECT team_id FROM team_members WHERE member_user_id = auth.uid()
        )
        OR user_id = auth.uid()
    );

CREATE POLICY "scope_identities_insert_org" ON scope_identities
    FOR INSERT
    WITH CHECK (
        organization_id IN (
            SELECT team_id FROM team_members WHERE member_user_id = auth.uid()
        )
        OR user_id = auth.uid()
    );

CREATE POLICY "scope_identities_update_org" ON scope_identities
    FOR UPDATE
    USING (
        organization_id IN (
            SELECT team_id FROM team_members WHERE member_user_id = auth.uid()
        )
        OR user_id = auth.uid()
    );

CREATE POLICY "scope_identities_delete_org" ON scope_identities
    FOR DELETE
    USING (
        organization_id IN (
            SELECT team_id FROM team_members WHERE member_user_id = auth.uid()
        )
        OR user_id = auth.uid()
    );

COMMIT;
