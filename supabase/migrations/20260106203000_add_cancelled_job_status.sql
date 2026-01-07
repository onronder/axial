-- ============================================================
-- Migration: Add cancelled to job_status enum
-- Created: 2026-01-06
-- Description: Allow ingestion_jobs.status = 'cancelled'
-- ============================================================

DO $$
BEGIN
    IF EXISTS (
        SELECT 1
        FROM pg_type
        WHERE typname = 'job_status'
    ) THEN
        ALTER TYPE job_status ADD VALUE IF NOT EXISTS 'cancelled';
    END IF;
END $$;
