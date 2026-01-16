-- Migration: Add status to scope_identities for placeholder tracking
-- 
-- Status values:
--   'placeholder' - Created during ingestion before documents are inserted (for FK compliance)
--   'completed'   - Full identity synthesized after ingestion finishes
--
-- The placeholder status allows:
-- 1. FK constraint satisfaction before document insertion
-- 2. Filtering incomplete identities from chat/UI
-- 3. Cleanup of orphan placeholders from failed ingestions

BEGIN;

-- Add status column with default 'placeholder'
-- New rows from placeholder creation will have 'placeholder'
-- Rows created by synthesize_and_save_identity will have 'completed'
ALTER TABLE scope_identities
    ADD COLUMN IF NOT EXISTS status TEXT NOT NULL DEFAULT 'placeholder';

-- Backfill existing rows: if they have a real summary, they're completed
UPDATE scope_identities
SET status = 'completed'
WHERE status = 'placeholder'
  AND summary IS NOT NULL
  AND summary != 'Generating identity...';

-- Also check the attributes.is_placeholder flag for defense in depth
UPDATE scope_identities
SET status = 'completed'
WHERE status = 'placeholder'
  AND (attributes->>'is_placeholder')::boolean IS FALSE;

-- Index for efficient cleanup queries and status filtering
CREATE INDEX IF NOT EXISTS idx_scope_identities_status 
    ON scope_identities(status) 
    WHERE status = 'placeholder';

-- Index for cleanup task: find old placeholders efficiently
CREATE INDEX IF NOT EXISTS idx_scope_identities_placeholder_updated
    ON scope_identities(updated_at)
    WHERE status = 'placeholder';

COMMIT;
