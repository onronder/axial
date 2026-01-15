-- Migration: Add scope_identities table and scope_id on documents

-- 1) Create scope_identities table
CREATE TABLE IF NOT EXISTS scope_identities (
    id TEXT PRIMARY KEY, -- Canonical URI (e.g., github://org/repo@main)
    user_id UUID NOT NULL REFERENCES auth.users(id) ON DELETE CASCADE,
    type TEXT NOT NULL,
    attributes JSONB NOT NULL DEFAULT '{}'::jsonb,
    summary TEXT,
    file_tree TEXT,
    last_ingested_at TIMESTAMPTZ,
    created_at TIMESTAMPTZ NOT NULL DEFAULT timezone('utc'::text, now()),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT timezone('utc'::text, now())
);

-- 2) Enable RLS and policies
ALTER TABLE scope_identities ENABLE ROW LEVEL SECURITY;

CREATE POLICY "scope_identities_select_own"
ON scope_identities FOR SELECT
USING (user_id = auth.uid());

CREATE POLICY "scope_identities_insert_own"
ON scope_identities FOR INSERT
WITH CHECK (user_id = auth.uid());

CREATE POLICY "scope_identities_update_own"
ON scope_identities FOR UPDATE
USING (user_id = auth.uid());

CREATE POLICY "scope_identities_delete_own"
ON scope_identities FOR DELETE
USING (user_id = auth.uid());

-- 3) Add scope_id to documents with FK + index
ALTER TABLE documents ADD COLUMN IF NOT EXISTS scope_id TEXT;

DO $$
BEGIN
    IF NOT EXISTS (
        SELECT 1
        FROM pg_constraint
        WHERE conname = 'documents_scope_id_fkey'
    ) THEN
        ALTER TABLE documents
            ADD CONSTRAINT documents_scope_id_fkey
            FOREIGN KEY (scope_id)
            REFERENCES scope_identities(id)
            ON DELETE CASCADE;
    END IF;
END $$;

CREATE INDEX IF NOT EXISTS idx_documents_scope_id ON documents(scope_id);
