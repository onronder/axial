-- =============================================================================
-- Migration: Fix file status column name in update_file_status_if_changed
-- Version: 20260224000001
-- Description: Corrects 'message' to 'status_message' column name
-- =============================================================================

-- The original migration used 'message' but the actual column is 'status_message'

CREATE OR REPLACE FUNCTION update_file_status_if_changed(
    p_file_status_id UUID,
    p_new_status TEXT,
    p_progress INTEGER DEFAULT NULL,
    p_message TEXT DEFAULT NULL,
    p_error_message TEXT DEFAULT NULL,
    p_document_id UUID DEFAULT NULL,
    p_chunks_processed INTEGER DEFAULT NULL
)
RETURNS BOOLEAN
LANGUAGE plpgsql
SECURITY DEFINER
SET search_path = public
AS $$
DECLARE
    v_current_status TEXT;
    v_current_progress INTEGER;
    v_updated BOOLEAN := FALSE;
BEGIN
    -- Get current state
    SELECT status, progress INTO v_current_status, v_current_progress
    FROM ingestion_file_status
    WHERE id = p_file_status_id;
    
    -- Only update if status or progress changed
    IF v_current_status IS DISTINCT FROM p_new_status 
       OR (p_progress IS NOT NULL AND v_current_progress IS DISTINCT FROM p_progress)
       OR p_document_id IS NOT NULL  -- Always update if setting document_id
    THEN
        UPDATE ingestion_file_status
        SET 
            status = COALESCE(p_new_status, status),
            progress = COALESCE(p_progress, progress),
            status_message = COALESCE(p_message, status_message),  -- Fixed: was 'message'
            error_message = COALESCE(p_error_message, error_message),
            document_id = COALESCE(p_document_id, document_id),
            chunks_processed = COALESCE(p_chunks_processed, chunks_processed),
            updated_at = NOW()
        WHERE id = p_file_status_id;
        
        v_updated := FOUND;
    END IF;
    
    RETURN v_updated;
END;
$$;

-- Ensure grants are still correct
REVOKE ALL ON FUNCTION update_file_status_if_changed(UUID, TEXT, INTEGER, TEXT, TEXT, UUID, INTEGER) FROM PUBLIC;
GRANT EXECUTE ON FUNCTION update_file_status_if_changed(UUID, TEXT, INTEGER, TEXT, TEXT, UUID, INTEGER) TO service_role;

COMMENT ON FUNCTION update_file_status_if_changed IS 
'Idempotent file status update. Only writes to database if state actually changed.
Reduces redundant writes during task retries. (Fixed: uses status_message column)';
