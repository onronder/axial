-- Migration: Add message column to ingestion_jobs
-- Fixes: "Could not find the 'message' column of 'ingestion_jobs' in the schema cache"
-- Date: 2026-01-06

ALTER TABLE public.ingestion_jobs
ADD COLUMN IF NOT EXISTS message TEXT;

COMMENT ON COLUMN public.ingestion_jobs.message IS 'Current status message for progress display';
