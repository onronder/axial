-- Migration: Create ingestion_jobs table for tracking background task progress
-- Enables polling-based progress tracking for long-running ingestion tasks

-- Create enum for job status
DO $$ BEGIN
    CREATE TYPE job_status AS ENUM ('pending', 'processing', 'completed', 'failed');
EXCEPTION
    WHEN duplicate_object THEN null;
END $$;

-- Create ingestion_jobs table
CREATE TABLE IF NOT EXISTS ingestion_jobs (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id UUID NOT NULL,
    provider TEXT NOT NULL,
    total_files INT NOT NULL DEFAULT 0,
    processed_files INT NOT NULL DEFAULT 0,
    status job_status NOT NULL DEFAULT 'pending',
    error_message TEXT,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT timezone('utc'::text, now()) NOT NULL,
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT timezone('utc'::text, now()) NOT NULL
);

-- Create index for efficient polling queries
CREATE INDEX IF NOT EXISTS idx_ingestion_jobs_user_status 
ON ingestion_jobs(user_id, status);

-- Create index for cleanup of old jobs
CREATE INDEX IF NOT EXISTS idx_ingestion_jobs_created_at 
ON ingestion_jobs(created_at);

-- Add RLS policies
ALTER TABLE ingestion_jobs ENABLE ROW LEVEL SECURITY;

-- Users can only see their own jobs
CREATE POLICY "Users can view their own jobs"
ON ingestion_jobs FOR SELECT
USING (user_id = auth.uid());

-- Users can only update their own jobs (for status updates from worker)
CREATE POLICY "Users can update their own jobs"
ON ingestion_jobs FOR UPDATE
USING (user_id = auth.uid());

-- Allow insert for authenticated users
CREATE POLICY "Users can insert jobs"
ON ingestion_jobs FOR INSERT
WITH CHECK (user_id = auth.uid());

-- Service role can do everything (for worker)
CREATE POLICY "Service role has full access"
ON ingestion_jobs
TO service_role
USING (true)
WITH CHECK (true);
