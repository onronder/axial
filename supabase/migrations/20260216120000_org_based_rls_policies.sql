-- Migration: Organization-Based RLS Policies
--
-- This migration standardizes all RLS policies to use organization_id
-- instead of individual user_id ownership. This is critical for:
--
-- 1. Multi-tenant isolation: Data belongs to organizations, not individuals
-- 2. Team access: All team members can access organization data
-- 3. Security: Removed members lose access immediately (no stale user_id refs)
--
-- Access Model:
--   - A user has access if they are a CURRENT member of the organization
--   - Organization membership is checked via team_members table
--   - Team owners have implicit access (tracked in teams table)
--   - REMOVED members are explicitly excluded (status = 'removed')

BEGIN;

-- ==========================================================================
-- Helper Function: Check if user is a member of an organization
-- ==========================================================================
-- This function is the single source of truth for organization membership.
-- It's used by all RLS policies for consistent access control.

CREATE OR REPLACE FUNCTION public.is_org_member(
    org_id UUID,
    user_uuid UUID
) RETURNS BOOLEAN AS $$
BEGIN
    -- Check 1: Is user the team/org owner?
    IF EXISTS (
        SELECT 1 FROM teams 
        WHERE id = org_id 
        AND owner_id = user_uuid
    ) THEN
        RETURN TRUE;
    END IF;
    
    -- Check 2: Is user an active team member?
    IF EXISTS (
        SELECT 1 FROM team_members 
        WHERE team_id = org_id 
        AND member_user_id = user_uuid
        AND status != 'removed'
    ) THEN
        RETURN TRUE;
    END IF;
    
    RETURN FALSE;
END;
$$ LANGUAGE plpgsql SECURITY DEFINER STABLE;

-- ==========================================================================
-- Documents RLS: Organization-Based Access
-- ==========================================================================

DROP POLICY IF EXISTS "Users can view own or team documents" ON public.documents;
DROP POLICY IF EXISTS "documents_org_select" ON public.documents;
DROP POLICY IF EXISTS "documents_org_insert" ON public.documents;
DROP POLICY IF EXISTS "documents_org_update" ON public.documents;
DROP POLICY IF EXISTS "documents_org_delete" ON public.documents;

-- SELECT: Users can view documents belonging to their organization
CREATE POLICY "documents_org_select" ON public.documents
    FOR SELECT
    USING (
        public.is_org_member(organization_id, (SELECT auth.uid()))
    );

-- INSERT: Users can insert documents into their organization
CREATE POLICY "documents_org_insert" ON public.documents
    FOR INSERT
    WITH CHECK (
        public.is_org_member(organization_id, (SELECT auth.uid()))
    );

-- UPDATE: Users can update documents in their organization
CREATE POLICY "documents_org_update" ON public.documents
    FOR UPDATE
    USING (
        public.is_org_member(organization_id, (SELECT auth.uid()))
    );

-- DELETE: Users can delete documents in their organization
CREATE POLICY "documents_org_delete" ON public.documents
    FOR DELETE
    USING (
        public.is_org_member(organization_id, (SELECT auth.uid()))
    );

-- ==========================================================================
-- Document Chunks RLS: Inherit from Documents
-- ==========================================================================

DROP POLICY IF EXISTS "Users can view chunks of allowed documents" ON public.document_chunks;
DROP POLICY IF EXISTS "chunks_org_select" ON public.document_chunks;

-- SELECT: Users can view chunks if they can view the parent document
CREATE POLICY "chunks_org_select" ON public.document_chunks
    FOR SELECT
    USING (
        EXISTS (
            SELECT 1 FROM public.documents d
            WHERE d.id = document_chunks.document_id
            AND public.is_org_member(d.organization_id, (SELECT auth.uid()))
        )
    );

-- ==========================================================================
-- Scope Identities RLS: Organization-Based Access (Fix existing)
-- ==========================================================================
-- NOTE: These were partially fixed in 20260118000000 but still have
-- user_id fallback. We remove that fallback now.

DROP POLICY IF EXISTS "scope_identities_select_org" ON scope_identities;
DROP POLICY IF EXISTS "scope_identities_insert_org" ON scope_identities;
DROP POLICY IF EXISTS "scope_identities_update_org" ON scope_identities;
DROP POLICY IF EXISTS "scope_identities_delete_org" ON scope_identities;

CREATE POLICY "scope_identities_select_org" ON scope_identities
    FOR SELECT
    USING (
        public.is_org_member(organization_id, (SELECT auth.uid()))
    );

CREATE POLICY "scope_identities_insert_org" ON scope_identities
    FOR INSERT
    WITH CHECK (
        public.is_org_member(organization_id, (SELECT auth.uid()))
    );

CREATE POLICY "scope_identities_update_org" ON scope_identities
    FOR UPDATE
    USING (
        public.is_org_member(organization_id, (SELECT auth.uid()))
    );

CREATE POLICY "scope_identities_delete_org" ON scope_identities
    FOR DELETE
    USING (
        public.is_org_member(organization_id, (SELECT auth.uid()))
    );

-- ==========================================================================
-- Ingestion Jobs RLS: Organization-Based Access
-- ==========================================================================

DROP POLICY IF EXISTS "Users can view own ingestion jobs" ON public.ingestion_jobs;
DROP POLICY IF EXISTS "Users can insert own ingestion jobs" ON public.ingestion_jobs;
DROP POLICY IF EXISTS "Users can update own ingestion jobs" ON public.ingestion_jobs;
DROP POLICY IF EXISTS "ingestion_jobs_org_select" ON public.ingestion_jobs;
DROP POLICY IF EXISTS "ingestion_jobs_org_insert" ON public.ingestion_jobs;
DROP POLICY IF EXISTS "ingestion_jobs_org_update" ON public.ingestion_jobs;

-- Only create new policies if organization_id column exists
DO $$
BEGIN
    IF EXISTS (
        SELECT 1 FROM information_schema.columns 
        WHERE table_name = 'ingestion_jobs' 
        AND column_name = 'organization_id'
    ) THEN
        EXECUTE 'CREATE POLICY "ingestion_jobs_org_select" ON public.ingestion_jobs
            FOR SELECT
            USING (public.is_org_member(organization_id, (SELECT auth.uid())))';
        
        EXECUTE 'CREATE POLICY "ingestion_jobs_org_insert" ON public.ingestion_jobs
            FOR INSERT
            WITH CHECK (public.is_org_member(organization_id, (SELECT auth.uid())))';
        
        EXECUTE 'CREATE POLICY "ingestion_jobs_org_update" ON public.ingestion_jobs
            FOR UPDATE
            USING (public.is_org_member(organization_id, (SELECT auth.uid())))';
    END IF;
END $$;

-- ==========================================================================
-- Conversations RLS: Organization-Based Access
-- ==========================================================================

DROP POLICY IF EXISTS "Users can view own conversations" ON public.conversations;
DROP POLICY IF EXISTS "Users can insert own conversations" ON public.conversations;
DROP POLICY IF EXISTS "conversations_org_select" ON public.conversations;
DROP POLICY IF EXISTS "conversations_org_insert" ON public.conversations;

-- Only create if organization_id exists on conversations
DO $$
BEGIN
    IF EXISTS (
        SELECT 1 FROM information_schema.columns 
        WHERE table_name = 'conversations' 
        AND column_name = 'organization_id'
    ) THEN
        EXECUTE 'CREATE POLICY "conversations_org_select" ON public.conversations
            FOR SELECT
            USING (public.is_org_member(organization_id, (SELECT auth.uid())))';
        
        EXECUTE 'CREATE POLICY "conversations_org_insert" ON public.conversations
            FOR INSERT
            WITH CHECK (public.is_org_member(organization_id, (SELECT auth.uid())))';
    ELSE
        -- Fallback: Keep user_id based policies if organization_id doesn't exist
        EXECUTE 'CREATE POLICY "conversations_org_select" ON public.conversations
            FOR SELECT
            USING (user_id = (SELECT auth.uid()))';
        
        EXECUTE 'CREATE POLICY "conversations_org_insert" ON public.conversations
            FOR INSERT
            WITH CHECK (user_id = (SELECT auth.uid()))';
    END IF;
END $$;

-- ==========================================================================
-- User Integrations RLS: User-specific (these are individual OAuth tokens)
-- ==========================================================================
-- NOTE: User integrations remain user_id based because OAuth tokens
-- are tied to individual users, not organizations.

-- No changes needed for user_integrations - they're correctly user-scoped

-- ==========================================================================
-- Index for Performance: Organization membership lookups
-- ==========================================================================

CREATE INDEX IF NOT EXISTS idx_team_members_member_org_active
    ON team_members(member_user_id, team_id)
    WHERE status != 'removed';

CREATE INDEX IF NOT EXISTS idx_teams_owner_id
    ON teams(owner_id);

-- Notify PostgREST to reload configuration
NOTIFY pgrst, 'reload config';

COMMIT;
