-- ============================================================
-- Migration: Add Ingestion Progress Tracking Columns
-- Created: 2026-01-04
-- Description: Adds progress and status_message columns to ingestion_jobs
--              for real-time granular progress tracking
-- ============================================================

-- Add progress column (0-100 percentage)
ALTER TABLE ingestion_jobs 
ADD COLUMN IF NOT EXISTS progress INTEGER DEFAULT 0;

-- Add status_message column (e.g., "Indexing chunk 45/200...")
ALTER TABLE ingestion_jobs 
ADD COLUMN IF NOT EXISTS status_message TEXT;

-- Add index for faster status queries
CREATE INDEX IF NOT EXISTS idx_ingestion_jobs_user_status 
ON ingestion_jobs(user_id, status);

-- Verify the columns exist
COMMENT ON COLUMN ingestion_jobs.progress IS 'Progress percentage (0-100) updated during vectorization';
COMMENT ON COLUMN ingestion_jobs.status_message IS 'Human-readable status message for UI display';
