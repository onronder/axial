-- Migration: Organization-Scoped Conversations & Messages
--
-- This migration:
-- 1. Adds organization_id to conversations table
-- 2. Backfills organization_id from user's team membership
-- 3. Updates RLS policies to allow org-wide access to conversations
--
-- This enables teams to share conversation history for collaborative AI work.

BEGIN;

-- ==========================================================================
-- Step 1: Add organization_id column to conversations
-- ==========================================================================

ALTER TABLE conversations 
ADD COLUMN IF NOT EXISTS organization_id UUID;

-- Create index for org-based queries
CREATE INDEX IF NOT EXISTS idx_conversations_org_id 
ON conversations(organization_id);

-- ==========================================================================
-- Step 2: Backfill organization_id from user's team membership
-- ==========================================================================
-- For existing conversations, inherit org_id from user's team

UPDATE conversations c
SET organization_id = (
    SELECT COALESCE(
        (SELECT team_id FROM team_members WHERE member_user_id = c.user_id LIMIT 1),
        (SELECT id FROM teams WHERE owner_id = c.user_id LIMIT 1),
        c.user_id::uuid  -- Fallback: use user_id as org_id for solo users
    )
)
WHERE organization_id IS NULL;

-- Set default for new conversations
ALTER TABLE conversations 
ALTER COLUMN organization_id SET DEFAULT auth.uid();

-- ==========================================================================
-- Step 3: Update Conversations RLS to Organization-Based Access
-- ==========================================================================

-- Drop old user-based policies
DROP POLICY IF EXISTS "Users can view own conversations" ON conversations;
DROP POLICY IF EXISTS "Users can insert own conversations" ON conversations;
DROP POLICY IF EXISTS "Users can update own conversations" ON conversations;
DROP POLICY IF EXISTS "Users can delete own conversations" ON conversations;

-- Drop any existing org-based policies (in case of re-run)
DROP POLICY IF EXISTS "conversations_org_select" ON conversations;
DROP POLICY IF EXISTS "conversations_org_insert" ON conversations;
DROP POLICY IF EXISTS "conversations_org_update" ON conversations;
DROP POLICY IF EXISTS "conversations_org_delete" ON conversations;

-- New org-based SELECT: View conversations in your organization
CREATE POLICY "conversations_org_select" ON conversations
    FOR SELECT
    USING (
        public.is_org_member(organization_id, (SELECT auth.uid()))
    );

-- New org-based INSERT: Create conversations in your organization
CREATE POLICY "conversations_org_insert" ON conversations
    FOR INSERT
    WITH CHECK (
        public.is_org_member(organization_id, (SELECT auth.uid()))
    );

-- New org-based UPDATE: Update conversations in your organization
-- (Could restrict to creator or admin if needed)
CREATE POLICY "conversations_org_update" ON conversations
    FOR UPDATE
    USING (
        public.is_org_member(organization_id, (SELECT auth.uid()))
    );

-- New org-based DELETE: Delete conversations in your organization
-- (Could restrict to creator or admin if needed)
CREATE POLICY "conversations_org_delete" ON conversations
    FOR DELETE
    USING (
        public.is_org_member(organization_id, (SELECT auth.uid()))
    );

-- ==========================================================================
-- Step 4: Update Messages RLS to Organization-Based Access
-- ==========================================================================

-- Drop old user-based policies
DROP POLICY IF EXISTS "Users can view messages in own conversations" ON messages;
DROP POLICY IF EXISTS "Users can insert messages in own conversations" ON messages;
DROP POLICY IF EXISTS "Users can delete messages in own conversations" ON messages;

-- Drop any existing org-based policies (in case of re-run)
DROP POLICY IF EXISTS "messages_org_select" ON messages;
DROP POLICY IF EXISTS "messages_org_insert" ON messages;
DROP POLICY IF EXISTS "messages_org_delete" ON messages;

-- New org-based SELECT: View messages in org's conversations
CREATE POLICY "messages_org_select" ON messages
    FOR SELECT
    USING (
        EXISTS (
            SELECT 1 FROM conversations c
            WHERE c.id = messages.conversation_id
            AND public.is_org_member(c.organization_id, (SELECT auth.uid()))
        )
    );

-- New org-based INSERT: Add messages to org's conversations
CREATE POLICY "messages_org_insert" ON messages
    FOR INSERT
    WITH CHECK (
        EXISTS (
            SELECT 1 FROM conversations c
            WHERE c.id = messages.conversation_id
            AND public.is_org_member(c.organization_id, (SELECT auth.uid()))
        )
    );

-- New org-based DELETE: Delete messages in org's conversations
CREATE POLICY "messages_org_delete" ON messages
    FOR DELETE
    USING (
        EXISTS (
            SELECT 1 FROM conversations c
            WHERE c.id = messages.conversation_id
            AND public.is_org_member(c.organization_id, (SELECT auth.uid()))
        )
    );

NOTIFY pgrst, 'reload config';

COMMIT;
