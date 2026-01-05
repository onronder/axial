-- Migration: Fix ingestion_file_status schema
-- Add missing file_size column
-- Created: 2026-01-05

-- Add missing file_size column
ALTER TABLE ingestion_file_status 
ADD COLUMN IF NOT EXISTS file_size BIGINT DEFAULT 0;

-- Add index for performance
CREATE INDEX IF NOT EXISTS idx_ingestion_file_status_job_id 
ON ingestion_file_status(job_id);

CREATE INDEX IF NOT EXISTS idx_ingestion_file_status_user_id 
ON ingestion_file_status(user_id);

-- Notify PostgREST to reload schema cache
NOTIFY pgrst, 'reload schema';
