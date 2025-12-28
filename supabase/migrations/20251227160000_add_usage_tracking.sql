-- Migration: Add Usage Tracking for Monetization
-- Supports quota enforcement by tracking file counts and storage per user
-- Created: 2025-12-27

-- ============================================================
-- UPDATE DOCUMENTS TABLE: Add file_size_bytes
-- ============================================================
-- Track individual file sizes for accurate storage calculation
ALTER TABLE documents
ADD COLUMN IF NOT EXISTS file_size_bytes BIGINT DEFAULT 0;

-- Index for efficient aggregation queries
CREATE INDEX IF NOT EXISTS idx_documents_file_size 
ON documents(user_id, file_size_bytes);

-- ============================================================
-- UPDATE USER_PROFILES TABLE: Add cached usage columns
-- ============================================================
-- These columns cache usage data to avoid expensive SUM() queries
-- Can be maintained via triggers or application logic

-- Total storage in bytes across all documents
ALTER TABLE user_profiles
ADD COLUMN IF NOT EXISTS total_storage_bytes BIGINT DEFAULT 0;

-- Total file count (documents owned by user)
ALTER TABLE user_profiles
ADD COLUMN IF NOT EXISTS file_count INTEGER DEFAULT 0;

-- ============================================================
-- UPDATE PLAN CHECK CONSTRAINT
-- ============================================================
-- Add 'starter' plan to the allowed values
-- First drop the existing constraint, then recreate with new values
ALTER TABLE user_profiles
DROP CONSTRAINT IF EXISTS user_profiles_plan_check;

ALTER TABLE user_profiles
ADD CONSTRAINT user_profiles_plan_check 
CHECK (plan IN ('free', 'starter', 'pro', 'enterprise'));

-- ============================================================
-- HELPER FUNCTION: Recalculate user usage
-- ============================================================
-- Can be called manually or via scheduled job to sync cached values
CREATE OR REPLACE FUNCTION recalculate_user_usage(target_user_id UUID)
RETURNS VOID
LANGUAGE plpgsql
SECURITY DEFINER
AS $$
DECLARE
    calc_file_count INTEGER;
    calc_storage_bytes BIGINT;
BEGIN
    -- Calculate current usage from documents table
    SELECT 
        COALESCE(COUNT(*), 0),
        COALESCE(SUM(file_size_bytes), 0)
    INTO calc_file_count, calc_storage_bytes
    FROM documents
    WHERE user_id = target_user_id;
    
    -- Update the cached values in user_profiles
    UPDATE user_profiles
    SET 
        file_count = calc_file_count,
        total_storage_bytes = calc_storage_bytes,
        updated_at = now()
    WHERE user_id = target_user_id;
END;
$$;

-- Grant execute to service_role for backend access
GRANT EXECUTE ON FUNCTION recalculate_user_usage(UUID) TO service_role;

-- ============================================================
-- COMMENT DOCUMENTATION
-- ============================================================
COMMENT ON COLUMN documents.file_size_bytes IS 'Size of the ingested file in bytes';
COMMENT ON COLUMN user_profiles.total_storage_bytes IS 'Cached total storage used by user in bytes';
COMMENT ON COLUMN user_profiles.file_count IS 'Cached count of documents owned by user';
COMMENT ON FUNCTION recalculate_user_usage IS 'Recalculates and syncs cached usage values from documents table';

-- Notify PostgREST to reload schema cache
NOTIFY pgrst, 'reload config';
