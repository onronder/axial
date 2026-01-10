-- =============================================================================
-- Normalize legacy provider/source_type values to canonical forms
-- =============================================================================
-- Replaces deprecated values (file, drive, upload) with canonical names.
-- =============================================================================

BEGIN;

-- Documents: source_type normalization
UPDATE documents
SET source_type = 'file_upload'
WHERE source_type IN ('file', 'upload', 'file-upload');

UPDATE documents
SET source_type = 'google_drive'
WHERE source_type IN ('drive', 'google-drive', 'gdrive');

ALTER TABLE documents
    ALTER COLUMN source_type SET DEFAULT 'file_upload';

-- Ingestion jobs: provider normalization
UPDATE ingestion_jobs
SET provider = 'file_upload'
WHERE provider IN ('file', 'upload', 'file-upload');

UPDATE ingestion_jobs
SET provider = 'google_drive'
WHERE provider IN ('drive', 'google-drive', 'gdrive');

-- Sync state: provider normalization
UPDATE sync_state
SET provider = 'file_upload'
WHERE provider IN ('file', 'upload', 'file-upload');

UPDATE sync_state
SET provider = 'google_drive'
WHERE provider IN ('drive', 'google-drive', 'gdrive');

COMMIT;

-- Notify PostgREST to reload schema cache
NOTIFY pgrst, 'reload config';
