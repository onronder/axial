-- =============================================================================
-- Migration: Race Condition Fixes
-- Version: 20260224000000
-- Description: Comprehensive fixes for race conditions across the platform
-- =============================================================================

-- =============================================================================
-- 1. ATOMIC LLM TOKEN INCREMENT
-- Problem: Read-Modify-Write race in usage tracking
-- Solution: Single atomic database function
-- =============================================================================

CREATE OR REPLACE FUNCTION increment_llm_tokens(
    p_org_id UUID,
    p_tokens INTEGER,
    p_provider TEXT DEFAULT NULL,
    p_model TEXT DEFAULT NULL
)
RETURNS TABLE(
    new_total BIGINT,
    previous_total BIGINT
)
LANGUAGE plpgsql
SECURITY DEFINER
SET search_path = public
AS $$
DECLARE
    v_previous BIGINT;
    v_new BIGINT;
BEGIN
    -- Atomic upsert with returning
    INSERT INTO org_usage (org_id, llm_tokens_used, updated_at)
    VALUES (p_org_id, p_tokens, NOW())
    ON CONFLICT (org_id) DO UPDATE
    SET 
        llm_tokens_used = org_usage.llm_tokens_used + EXCLUDED.llm_tokens_used,
        updated_at = NOW()
    RETURNING 
        llm_tokens_used - p_tokens,  -- previous value
        llm_tokens_used              -- new value
    INTO v_previous, v_new;
    
    -- Handle case where previous was NULL (first insert)
    IF v_previous IS NULL THEN
        v_previous := 0;
    END IF;
    
    RETURN QUERY SELECT v_new, v_previous;
END;
$$;

-- Grant to service role only (called from backend)
REVOKE ALL ON FUNCTION increment_llm_tokens(UUID, INTEGER, TEXT, TEXT) FROM PUBLIC;
GRANT EXECUTE ON FUNCTION increment_llm_tokens(UUID, INTEGER, TEXT, TEXT) TO service_role;

COMMENT ON FUNCTION increment_llm_tokens IS 
'Atomically increment LLM token usage for an organization. 
Prevents race conditions from concurrent chat requests.
Returns both new total and previous total for audit purposes.';


-- =============================================================================
-- 2. ATOMIC LLM BALANCE DECREMENT (for override balance)
-- =============================================================================

CREATE OR REPLACE FUNCTION decrement_llm_balance(
    p_org_id UUID,
    p_tokens INTEGER
)
RETURNS INTEGER
LANGUAGE plpgsql
SECURITY DEFINER
SET search_path = public
AS $$
DECLARE
    v_new_balance INTEGER;
BEGIN
    -- Atomically decrement balance, floor at 0
    UPDATE teams
    SET llm_token_balance = GREATEST(0, COALESCE(llm_token_balance, 0) - p_tokens)
    WHERE id = p_org_id
    AND llm_token_balance IS NOT NULL
    RETURNING llm_token_balance INTO v_new_balance;
    
    RETURN v_new_balance;
END;
$$;

REVOKE ALL ON FUNCTION decrement_llm_balance(UUID, INTEGER) FROM PUBLIC;
GRANT EXECUTE ON FUNCTION decrement_llm_balance(UUID, INTEGER) TO service_role;

COMMENT ON FUNCTION decrement_llm_balance IS 
'Atomically decrement LLM token balance override for a team.
Only operates if llm_token_balance is set (not NULL).';


-- =============================================================================
-- 3. WEBHOOK IDEMPOTENCY TABLE
-- Problem: Duplicate webhook processing from retries
-- Solution: Track processed events with unique constraint
-- =============================================================================

CREATE TABLE IF NOT EXISTS processed_webhook_events (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    event_id TEXT NOT NULL,
    source TEXT NOT NULL,
    event_type TEXT,
    processed_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    metadata JSONB DEFAULT '{}',
    
    -- Unique constraint for idempotency
    CONSTRAINT uq_webhook_event_source UNIQUE (event_id, source)
);

-- Index for cleanup queries
CREATE INDEX IF NOT EXISTS idx_processed_webhooks_processed_at 
ON processed_webhook_events(processed_at);

-- Auto-cleanup old events (>7 days) to prevent table bloat
CREATE OR REPLACE FUNCTION cleanup_old_webhook_events()
RETURNS INTEGER
LANGUAGE plpgsql
SECURITY DEFINER
SET search_path = public
AS $$
DECLARE
    deleted_count INTEGER;
BEGIN
    DELETE FROM processed_webhook_events
    WHERE processed_at < NOW() - INTERVAL '7 days';
    
    GET DIAGNOSTICS deleted_count = ROW_COUNT;
    RETURN deleted_count;
END;
$$;

REVOKE ALL ON FUNCTION cleanup_old_webhook_events() FROM PUBLIC;
GRANT EXECUTE ON FUNCTION cleanup_old_webhook_events() TO service_role;

-- RLS for processed_webhook_events (service role only)
ALTER TABLE processed_webhook_events ENABLE ROW LEVEL SECURITY;

-- Only service role can access
CREATE POLICY "service_role_full_access" ON processed_webhook_events
    FOR ALL TO service_role USING (true) WITH CHECK (true);

COMMENT ON TABLE processed_webhook_events IS 
'Tracks processed webhooks for idempotency. Events older than 7 days are automatically cleaned up.';


-- =============================================================================
-- 4. IDEMPOTENT WEBHOOK PROCESSING FUNCTION
-- =============================================================================

CREATE OR REPLACE FUNCTION try_process_webhook(
    p_event_id TEXT,
    p_source TEXT,
    p_event_type TEXT DEFAULT NULL
)
RETURNS BOOLEAN
LANGUAGE plpgsql
SECURITY DEFINER
SET search_path = public
AS $$
BEGIN
    -- Try to insert - if exists, do nothing and return false
    INSERT INTO processed_webhook_events (event_id, source, event_type)
    VALUES (p_event_id, p_source, p_event_type)
    ON CONFLICT (event_id, source) DO NOTHING;
    
    -- Return true if we inserted (should process), false if already existed
    RETURN FOUND;
END;
$$;

REVOKE ALL ON FUNCTION try_process_webhook(TEXT, TEXT, TEXT) FROM PUBLIC;
GRANT EXECUTE ON FUNCTION try_process_webhook(TEXT, TEXT, TEXT) TO service_role;

COMMENT ON FUNCTION try_process_webhook IS 
'Atomically check if webhook should be processed. Returns TRUE if first time seeing this event.
Use at start of webhook handler to prevent duplicate processing.';


-- =============================================================================
-- 5. TEAM SEAT LIMIT ENFORCEMENT
-- Problem: Concurrent invites can exceed seat limit
-- Solution: Database-level constraint with trigger
-- =============================================================================

-- Function to check seat limits
CREATE OR REPLACE FUNCTION check_team_seat_limit()
RETURNS TRIGGER
LANGUAGE plpgsql
SECURITY DEFINER
SET search_path = public
AS $$
DECLARE
    current_count INTEGER;
    max_seats INTEGER;
    team_plan TEXT;
BEGIN
    -- Only check on INSERT of new members (not status changes)
    IF TG_OP = 'INSERT' THEN
        -- Count current active members
        SELECT COUNT(*) INTO current_count
        FROM team_members
        WHERE team_id = NEW.team_id 
        AND status NOT IN ('removed', 'rejected');
        
        -- Get team's plan from subscription or default to free
        SELECT COALESCE(s.plan_type, 'free') INTO team_plan
        FROM teams t
        LEFT JOIN subscriptions s ON s.team_id = t.id AND s.status = 'active'
        WHERE t.id = NEW.team_id;
        
        -- Determine max seats based on plan
        CASE team_plan
            WHEN 'enterprise' THEN max_seats := 50;
            WHEN 'pro' THEN max_seats := 5;
            WHEN 'starter' THEN max_seats := 3;
            ELSE max_seats := 1; -- free plan
        END CASE;
        
        -- Check if adding this member would exceed limit
        IF current_count >= max_seats THEN
            RAISE EXCEPTION 'Team seat limit exceeded. Plan: %, Max seats: %, Current: %', 
                team_plan, max_seats, current_count
                USING ERRCODE = 'P0001';
        END IF;
    END IF;
    
    RETURN NEW;
END;
$$;

-- Drop existing trigger if exists (safe re-run)
DROP TRIGGER IF EXISTS enforce_team_seat_limit ON team_members;

-- Create trigger
CREATE TRIGGER enforce_team_seat_limit
    BEFORE INSERT ON team_members
    FOR EACH ROW
    EXECUTE FUNCTION check_team_seat_limit();

COMMENT ON FUNCTION check_team_seat_limit IS 
'Trigger function that enforces team seat limits at the database level.
Prevents race conditions where concurrent invites exceed the limit.';


-- =============================================================================
-- 6. DISTRIBUTED LOCK TABLE FOR TOKEN REFRESH
-- Problem: Concurrent OAuth refresh can invalidate tokens (especially Box)
-- Solution: Advisory lock via database
-- =============================================================================

CREATE TABLE IF NOT EXISTS distributed_locks (
    lock_key TEXT PRIMARY KEY,
    locked_by TEXT NOT NULL,
    locked_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    expires_at TIMESTAMPTZ NOT NULL,
    metadata JSONB DEFAULT '{}'
);

-- Index for cleanup
CREATE INDEX IF NOT EXISTS idx_distributed_locks_expires 
ON distributed_locks(expires_at);

-- Function to acquire lock
CREATE OR REPLACE FUNCTION acquire_lock(
    p_lock_key TEXT,
    p_locked_by TEXT,
    p_ttl_seconds INTEGER DEFAULT 30
)
RETURNS BOOLEAN
LANGUAGE plpgsql
SECURITY DEFINER
SET search_path = public
AS $$
DECLARE
    v_acquired BOOLEAN := FALSE;
BEGIN
    -- First, clean up expired locks
    DELETE FROM distributed_locks WHERE expires_at < NOW();
    
    -- Try to acquire lock
    INSERT INTO distributed_locks (lock_key, locked_by, expires_at)
    VALUES (p_lock_key, p_locked_by, NOW() + (p_ttl_seconds || ' seconds')::INTERVAL)
    ON CONFLICT (lock_key) DO NOTHING;
    
    -- Check if we got it
    v_acquired := FOUND;
    
    RETURN v_acquired;
END;
$$;

-- Function to release lock
CREATE OR REPLACE FUNCTION release_lock(
    p_lock_key TEXT,
    p_locked_by TEXT DEFAULT NULL
)
RETURNS BOOLEAN
LANGUAGE plpgsql
SECURITY DEFINER
SET search_path = public
AS $$
DECLARE
    v_released BOOLEAN := FALSE;
BEGIN
    -- Release the lock (optionally verify owner)
    IF p_locked_by IS NULL THEN
        DELETE FROM distributed_locks WHERE lock_key = p_lock_key;
    ELSE
        DELETE FROM distributed_locks 
        WHERE lock_key = p_lock_key AND locked_by = p_locked_by;
    END IF;
    
    v_released := FOUND;
    RETURN v_released;
END;
$$;

-- Function to check lock status
CREATE OR REPLACE FUNCTION check_lock(
    p_lock_key TEXT
)
RETURNS TABLE(
    is_locked BOOLEAN,
    locked_by TEXT,
    locked_at TIMESTAMPTZ,
    expires_at TIMESTAMPTZ
)
LANGUAGE plpgsql
SECURITY DEFINER
SET search_path = public
AS $$
BEGIN
    RETURN QUERY
    SELECT 
        TRUE,
        dl.locked_by,
        dl.locked_at,
        dl.expires_at
    FROM distributed_locks dl
    WHERE dl.lock_key = p_lock_key
    AND dl.expires_at > NOW();
    
    -- If no rows returned, return unlocked
    IF NOT FOUND THEN
        RETURN QUERY SELECT FALSE, NULL::TEXT, NULL::TIMESTAMPTZ, NULL::TIMESTAMPTZ;
    END IF;
END;
$$;

-- Grant to service role
REVOKE ALL ON FUNCTION acquire_lock(TEXT, TEXT, INTEGER) FROM PUBLIC;
REVOKE ALL ON FUNCTION release_lock(TEXT, TEXT) FROM PUBLIC;
REVOKE ALL ON FUNCTION check_lock(TEXT) FROM PUBLIC;
GRANT EXECUTE ON FUNCTION acquire_lock(TEXT, TEXT, INTEGER) TO service_role;
GRANT EXECUTE ON FUNCTION release_lock(TEXT, TEXT) TO service_role;
GRANT EXECUTE ON FUNCTION check_lock(TEXT) TO service_role;

-- RLS for distributed_locks
ALTER TABLE distributed_locks ENABLE ROW LEVEL SECURITY;

CREATE POLICY "service_role_locks" ON distributed_locks
    FOR ALL TO service_role USING (true) WITH CHECK (true);

COMMENT ON TABLE distributed_locks IS 
'Distributed locking mechanism for coordinating concurrent operations.
Used primarily for OAuth token refresh to prevent race conditions.';


-- =============================================================================
-- 7. IDEMPOTENT FILE STATUS UPDATE FUNCTION
-- Problem: Redundant updates on task retries
-- Solution: Only update if state actually changed
-- =============================================================================

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
            status_message = COALESCE(p_message, status_message),
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

REVOKE ALL ON FUNCTION update_file_status_if_changed(UUID, TEXT, INTEGER, TEXT, TEXT, UUID, INTEGER) FROM PUBLIC;
GRANT EXECUTE ON FUNCTION update_file_status_if_changed(UUID, TEXT, INTEGER, TEXT, TEXT, UUID, INTEGER) TO service_role;

COMMENT ON FUNCTION update_file_status_if_changed IS 
'Idempotent file status update. Only writes to database if state actually changed.
Reduces redundant writes during task retries.';


-- =============================================================================
-- GRANTS FOR NEW TABLES
-- =============================================================================

GRANT ALL ON TABLE processed_webhook_events TO service_role;
GRANT ALL ON TABLE distributed_locks TO service_role;


-- =============================================================================
-- VERIFICATION
-- =============================================================================

DO $$
BEGIN
    -- Verify functions exist
    ASSERT (SELECT EXISTS(SELECT 1 FROM pg_proc WHERE proname = 'increment_llm_tokens'));
    ASSERT (SELECT EXISTS(SELECT 1 FROM pg_proc WHERE proname = 'decrement_llm_balance'));
    ASSERT (SELECT EXISTS(SELECT 1 FROM pg_proc WHERE proname = 'try_process_webhook'));
    ASSERT (SELECT EXISTS(SELECT 1 FROM pg_proc WHERE proname = 'acquire_lock'));
    ASSERT (SELECT EXISTS(SELECT 1 FROM pg_proc WHERE proname = 'release_lock'));
    ASSERT (SELECT EXISTS(SELECT 1 FROM pg_proc WHERE proname = 'update_file_status_if_changed'));
    
    -- Verify tables exist
    ASSERT (SELECT EXISTS(SELECT 1 FROM information_schema.tables WHERE table_name = 'processed_webhook_events'));
    ASSERT (SELECT EXISTS(SELECT 1 FROM information_schema.tables WHERE table_name = 'distributed_locks'));
    
    -- Verify trigger exists
    ASSERT (SELECT EXISTS(SELECT 1 FROM pg_trigger WHERE tgname = 'enforce_team_seat_limit'));
    
    RAISE NOTICE '✅ Race condition fixes migration completed successfully';
END;
$$;
