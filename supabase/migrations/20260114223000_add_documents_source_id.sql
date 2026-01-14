-- Add source_id column for stable deduplication
ALTER TABLE documents
ADD COLUMN IF NOT EXISTS source_id TEXT;

CREATE INDEX IF NOT EXISTS idx_documents_source_id
ON documents(user_id, source_id)
WHERE source_id IS NOT NULL;

-- Backfill from existing metadata where available
UPDATE documents
SET source_id = metadata->>'source_id'
WHERE source_id IS NULL
  AND metadata ? 'source_id';

-- Google Drive: use stored file_id
UPDATE documents
SET source_id = metadata->>'file_id'
WHERE source_id IS NULL
  AND source_type = 'google_drive'
  AND metadata ? 'file_id';

-- File uploads: use storage path (stable)
UPDATE documents
SET source_id = metadata->>'storage_path'
WHERE source_id IS NULL
  AND source_type = 'file_upload'
  AND metadata ? 'storage_path';

-- Web: use source_url when available
UPDATE documents
SET source_id = source_url
WHERE source_id IS NULL
  AND source_type = 'web'
  AND source_url IS NOT NULL;

COMMENT ON COLUMN documents.source_id IS
  'Stable identifier from source system for deduplication (Drive file_id, Web URL, Upload storage_path, etc).';
