-- Migration: Scope identity composite key for multi-tenant isolation

BEGIN;

ALTER TABLE documents DROP CONSTRAINT IF EXISTS documents_scope_id_fkey;

ALTER TABLE scope_identities DROP CONSTRAINT IF EXISTS scope_identities_pkey;

ALTER TABLE scope_identities
    ADD CONSTRAINT scope_identities_pkey PRIMARY KEY (user_id, id);

ALTER TABLE documents
    ADD CONSTRAINT documents_scope_id_fkey
    FOREIGN KEY (user_id, scope_id)
    REFERENCES scope_identities(user_id, id)
    ON DELETE CASCADE;

CREATE INDEX IF NOT EXISTS idx_documents_user_scope_id ON documents(user_id, scope_id);

COMMIT;
