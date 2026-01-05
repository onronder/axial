-- Migration: Add missing columns to ingestion_jobs and notifications
-- Fixes schema mismatches found in production

-- Add missing columns to ingestion_jobs
ALTER TABLE ingestion_jobs 
ADD COLUMN IF NOT EXISTS processed_files INTEGER DEFAULT 0,
ADD COLUMN IF NOT EXISTS failed_files INTEGER DEFAULT 0,
ADD COLUMN IF NOT EXISTS total_files INTEGER DEFAULT 0;

-- Add missing metadata column to notifications  
ALTER TABLE notifications
ADD COLUMN IF NOT EXISTS metadata JSONB DEFAULT '{}'::jsonb;

-- Add comments
COMMENT ON COLUMN ingestion_jobs.processed_files IS 'Number of successfully processed files';
COMMENT ON COLUMN ingestion_jobs.failed_files IS 'Number of failed files';
COMMENT ON COLUMN ingestion_jobs.total_files IS 'Total number of files to process';
COMMENT ON COLUMN notifications.metadata IS 'Additional notification metadata (job_id, etc.)';
