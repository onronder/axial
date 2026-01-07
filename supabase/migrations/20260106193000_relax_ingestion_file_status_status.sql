-- ============================================================
-- Migration: Relax ingestion_file_status.status to allow flexible values
-- Created: 2026-01-06
-- Description: Remove strict CHECK constraint to support dynamic status stages
-- ============================================================

ALTER TABLE ingestion_file_status
DROP CONSTRAINT IF EXISTS ingestion_file_status_status_check;

COMMENT ON COLUMN ingestion_file_status.status IS
'Processing state (flexible, defined in application)';
