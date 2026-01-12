-- Migration: Add composite index for deduplication by team/content hash
-- Scope: documents table

CREATE INDEX IF NOT EXISTS documents_team_content_hash_idx
ON documents (team_id, content_hash);

-- Fallback for solo users already covered by existing user/title/hash index.
