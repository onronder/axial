-- ============================================================
-- Migration: Add Cancel/Retry Support to Ingestion
-- Created: 2026-01-04
-- Description: Adds fields for job cancellation and file retry
-- ============================================================

-- Add cancellation support to ingestion_jobs
ALTER TABLE ingestion_jobs 
ADD COLUMN IF NOT EXISTS cancelled_at TIMESTAMPTZ,
ADD COLUMN IF NOT EXISTS cancelled_by UUID REFERENCES auth.users(id);

-- Add 'cancelled' as valid status
-- Note: If status is a CHECK constraint, we need to update it
-- First, let's add the metadata column for storing celery task ID
ALTER TABLE ingestion_jobs 
ADD COLUMN IF NOT EXISTS celery_task_id TEXT;

-- Add retry support to file status
ALTER TABLE ingestion_file_status 
ADD COLUMN IF NOT EXISTS retry_count INTEGER DEFAULT 0,
ADD COLUMN IF NOT EXISTS can_retry BOOLEAN DEFAULT true;

-- Add 'cancelled' status to the check constraint
-- Drop old constraint if exists and recreate with cancelled status
DO $$ 
BEGIN
    -- Try to drop existing constraint
    ALTER TABLE ingestion_file_status DROP CONSTRAINT IF EXISTS ingestion_file_status_status_check;
EXCEPTION
    WHEN others THEN NULL;
END $$;

ALTER TABLE ingestion_file_status 
ADD CONSTRAINT ingestion_file_status_status_check 
CHECK (status IN ('pending', 'uploading', 'processing', 'embedding', 'indexing', 'completed', 'failed', 'cancelled'));

-- Index for faster retry queries
CREATE INDEX IF NOT EXISTS idx_ingestion_file_status_retry 
ON ingestion_file_status(status, can_retry) 
WHERE status = 'failed' AND can_retry = true;

-- Add comments
COMMENT ON COLUMN ingestion_jobs.cancelled_at IS 'Timestamp when job was cancelled';
COMMENT ON COLUMN ingestion_jobs.cancelled_by IS 'User who cancelled the job';
COMMENT ON COLUMN ingestion_jobs.celery_task_id IS 'Celery task ID for revocation';
COMMENT ON COLUMN ingestion_file_status.retry_count IS 'Number of retry attempts (max 3)';
COMMENT ON COLUMN ingestion_file_status.can_retry IS 'Whether this file can be retried';
