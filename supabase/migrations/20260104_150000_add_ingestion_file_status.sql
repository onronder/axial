-- ============================================================
-- Migration: Add Per-File Ingestion Status Tracking
-- Created: 2026-01-04
-- Description: Enables granular per-file progress tracking for ingestion jobs
-- ============================================================

-- First, ensure the parent table has the progress columns
ALTER TABLE ingestion_jobs 
ADD COLUMN IF NOT EXISTS progress INTEGER DEFAULT 0;

ALTER TABLE ingestion_jobs 
ADD COLUMN IF NOT EXISTS status_message TEXT;

-- Create the per-file status tracking table
CREATE TABLE IF NOT EXISTS ingestion_file_status (
    id UUID DEFAULT gen_random_uuid() PRIMARY KEY,
    job_id UUID NOT NULL REFERENCES ingestion_jobs(id) ON DELETE CASCADE,
    user_id UUID NOT NULL,
    
    -- File Info
    filename TEXT NOT NULL,
    file_size_bytes BIGINT DEFAULT 0,
    
    -- Status (granular states for UX)
    status TEXT DEFAULT 'pending' CHECK (status IN (
        'pending',      -- Waiting to start
        'uploading',    -- Downloading/uploading file
        'processing',   -- Parsing/extracting content
        'embedding',    -- Generating embeddings
        'indexing',     -- Saving to database
        'completed',    -- Successfully done
        'failed'        -- Error occurred
    )),
    progress INTEGER DEFAULT 0 CHECK (progress >= 0 AND progress <= 100),
    status_message TEXT,
    error_message TEXT,
    
    -- Processing metadata
    chunks_total INTEGER DEFAULT 0,
    chunks_processed INTEGER DEFAULT 0,
    document_id UUID,  -- Populated after successful ingestion
    
    -- Timestamps
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW()
);

-- Indexes for fast lookups
CREATE INDEX IF NOT EXISTS idx_ingestion_file_status_job 
ON ingestion_file_status(job_id);

CREATE INDEX IF NOT EXISTS idx_ingestion_file_status_user 
ON ingestion_file_status(user_id, status);

CREATE INDEX IF NOT EXISTS idx_ingestion_file_status_updated 
ON ingestion_file_status(updated_at DESC);

-- Enable Row Level Security
ALTER TABLE ingestion_file_status ENABLE ROW LEVEL SECURITY;

-- RLS Policy: Users can view their own file status
DROP POLICY IF EXISTS "Users can view own file status" ON ingestion_file_status;
CREATE POLICY "Users can view own file status" ON ingestion_file_status
    FOR SELECT USING (auth.uid() = user_id);

-- RLS Policy: Service role has full access
DROP POLICY IF EXISTS "Service role full access" ON ingestion_file_status;
CREATE POLICY "Service role full access" ON ingestion_file_status
    FOR ALL USING (auth.role() = 'service_role');

-- Enable Realtime for this table
ALTER PUBLICATION supabase_realtime ADD TABLE ingestion_file_status;

-- Add comments for documentation
COMMENT ON TABLE ingestion_file_status IS 'Per-file progress tracking for ingestion jobs';
COMMENT ON COLUMN ingestion_file_status.status IS 'Current processing state: pending, uploading, processing, embedding, indexing, completed, failed';
COMMENT ON COLUMN ingestion_file_status.progress IS 'Progress percentage (0-100) for this specific file';
COMMENT ON COLUMN ingestion_file_status.chunks_total IS 'Total number of chunks for this file';
COMMENT ON COLUMN ingestion_file_status.chunks_processed IS 'Number of chunks processed so far';
