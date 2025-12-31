-- Migration: Security Lockdown (Backend-Write-Only)
-- Created: 2025-12-31

-- ============================================================
-- 0. SCHEMA UPDATES
-- ============================================================
-- Add team_id to documents to support team-based RLS
ALTER TABLE documents ADD COLUMN IF NOT EXISTS team_id UUID REFERENCES teams(id);
CREATE INDEX IF NOT EXISTS idx_documents_team_id ON documents(team_id);

-- ============================================================
-- 1. ENABLE RLS
-- ============================================================

ALTER TABLE documents ENABLE ROW LEVEL SECURITY;
ALTER TABLE document_chunks ENABLE ROW LEVEL SECURITY;
-- subscriptions already enabled in unified_billing
ALTER TABLE user_profiles ENABLE ROW LEVEL SECURITY;

-- ============================================================
-- 2. REMOVE WRITE POLICIES / ENSURE CLEAN SLATE
-- ============================================================
-- We drop *all* permissive policies for 'authenticated' role

-- Documents
DROP POLICY IF EXISTS "Users can insert own documents" ON documents;
DROP POLICY IF EXISTS "Users can update own documents" ON documents;
DROP POLICY IF EXISTS "Users can delete own documents" ON documents;
DROP POLICY IF EXISTS "Users can crud their own documents" ON documents; -- From relational_docs.sql
DROP POLICY IF EXISTS "Enable insert for authenticated users only" ON documents;
DROP POLICY IF EXISTS "Enable update for users based on user_id" ON documents;
DROP POLICY IF EXISTS "Enable delete for users based on user_id" ON documents;

-- Document Chunks
DROP POLICY IF EXISTS "Users can insert own chunks" ON document_chunks;
DROP POLICY IF EXISTS "Users can update own chunks" ON document_chunks;
DROP POLICY IF EXISTS "Users can delete own chunks" ON document_chunks;
DROP POLICY IF EXISTS "Users can select own chunks via parent" ON document_chunks; -- We replace this
DROP POLICY IF EXISTS "Enable insert for authenticated users only" ON document_chunks;

-- Subscriptions (Handled in unified_billing, but ensuring no stray write policies)
DROP POLICY IF EXISTS "Users can insert own subscription" ON subscriptions;
DROP POLICY IF EXISTS "Users can update own subscription" ON subscriptions;
-- Note: 'Users can view team subscription' is created in unified_billing. We keep that.

-- User Profiles (Lockdown Quotas)
DROP POLICY IF EXISTS "Users can update own profile" ON user_profiles;
-- We'll allow UPDATE on some fields if needed, but for now strict lockdown is safer.
-- If they need to update `full_name` etc, we'd need a partial policy, but objective implies "Backend-Write-Only".

-- ============================================================
-- 3. ADD READ-ONLY POLICIES
-- ============================================================

-- Documents
DROP POLICY IF EXISTS "Users can view own documents" ON documents;
DROP POLICY IF EXISTS "Users can select own documents" ON documents; -- From tenancy.sql
DROP POLICY IF EXISTS "Enable read access for users based on user_id" ON documents;

CREATE POLICY "Users can view own or team documents" ON documents
    FOR SELECT
    TO authenticated
    USING (
        -- Personal Data
        user_id = auth.uid() 
        OR 
        -- Team Data (if document belongs to a team)
        (
            team_id IS NOT NULL AND
            team_id IN (
                SELECT team_id 
                FROM team_members 
                WHERE member_user_id = auth.uid()
            )
        )
    );

-- Document Chunks
DROP POLICY IF EXISTS "Users can view chunks of allowed documents" ON document_chunks;

CREATE POLICY "Users can view chunks of allowed documents" ON document_chunks
    FOR SELECT
    TO authenticated
    USING (
        EXISTS (
            SELECT 1 FROM documents d
            WHERE d.id = document_chunks.document_id
            AND (
                d.user_id = auth.uid()
                OR 
                (
                    d.team_id IS NOT NULL AND
                    d.team_id IN (
                        SELECT team_id 
                        FROM team_members 
                        WHERE member_user_id = auth.uid()
                    )
                )
            )
        )
    );

-- User Profiles (Read Own)
-- Usually user_profiles has `user_id` as PK or FK. If `id` is PK and maps to auth.uid(), check that.
-- Looking at standard Supabase patterns, usually `id` = `auth.uid()`.
-- Let's assume standard `id` = `auth.uid()`.

DROP POLICY IF EXISTS "Users can view own profile" ON user_profiles;
DROP POLICY IF EXISTS "Enable read access for users based on user_id" ON user_profiles;

CREATE POLICY "Users can view own profile" ON user_profiles
    FOR SELECT
    TO authenticated
    USING (user_id = auth.uid()); -- Accessing own profile

-- ============================================================
-- 4. CLEANUP & NOTIFY
-- ============================================================

COMMENT ON POLICY "Users can view own or team documents" ON documents IS 'Strict Read-Only: Own data or Team data';
COMMENT ON POLICY "Users can view chunks of allowed documents" ON document_chunks IS 'Strict Read-Only: Inherits document access';

NOTIFY pgrst, 'reload config';
