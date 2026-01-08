-- Add content_hash for idempotent ingestion matching
ALTER TABLE IF EXISTS documents
ADD COLUMN IF NOT EXISTS content_hash TEXT;

-- Index to speed duplicate detection by user/title/hash
CREATE INDEX IF NOT EXISTS documents_user_title_hash_idx
ON documents (user_id, title, content_hash);
