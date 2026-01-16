-- Migration: Atomic Scope Quota Check
--
-- This migration adds a PostgreSQL function that atomically:
-- 1. Counts existing scopes for an organization
-- 2. Checks against the quota limit
-- 3. Creates a placeholder scope identity if within quota
--
-- This prevents the TOCTOU (Time-Of-Check-Time-Of-Use) race condition
-- where multiple concurrent workers could all pass the quota check
-- before any of them create their placeholder.
--
-- The function uses row-level locking to ensure serialized access
-- to the scope quota check + placeholder creation.

BEGIN;

-- ==========================================================================
-- Function: try_create_scope_placeholder
-- ==========================================================================
-- Returns:
--   'created'      - New placeholder was created
--   'exists'       - Scope already exists (no action needed)
--   'quota_exceeded' - Would exceed max_scopes limit
--   'no_subscription' - max_scopes is 0 (no active subscription)
--
-- Uses FOR UPDATE SKIP LOCKED to handle concurrent requests
-- without blocking for long periods.

CREATE OR REPLACE FUNCTION public.try_create_scope_placeholder(
    p_organization_id UUID,
    p_user_id UUID,
    p_scope_id TEXT,
    p_source_type TEXT,
    p_max_scopes INTEGER
) RETURNS TEXT AS $$
DECLARE
    v_current_count INTEGER;
    v_existing RECORD;
BEGIN
    -- HARD ZERO RULE: No subscription = No scopes
    IF p_max_scopes <= 0 THEN
        RETURN 'no_subscription';
    END IF;
    
    -- Check if scope already exists (don't count against quota)
    SELECT id, status INTO v_existing
    FROM scope_identities
    WHERE organization_id = p_organization_id
    AND id = p_scope_id
    FOR UPDATE SKIP LOCKED;  -- Lock the row if it exists
    
    IF FOUND THEN
        -- Scope exists, no quota check needed
        RETURN 'exists';
    END IF;
    
    -- Acquire advisory lock for this organization to serialize quota checks
    -- This prevents race conditions where multiple workers check quota simultaneously
    PERFORM pg_advisory_xact_lock(
        hashtext('scope_quota'::text),
        hashtext(p_organization_id::text)
    );
    
    -- Count existing scopes (now guaranteed exclusive)
    SELECT COUNT(*) INTO v_current_count
    FROM scope_identities
    WHERE organization_id = p_organization_id;
    
    -- Check quota
    IF v_current_count >= p_max_scopes THEN
        RETURN 'quota_exceeded';
    END IF;
    
    -- Create placeholder within quota (this is now atomic with the check)
    INSERT INTO scope_identities (
        id,
        organization_id,
        user_id,
        type,
        status,
        summary,
        attributes,
        created_at,
        updated_at
    ) VALUES (
        p_scope_id,
        p_organization_id,
        p_user_id,
        COALESCE(p_source_type, 'unknown'),
        'placeholder',
        'Generating identity...',
        jsonb_build_object('is_placeholder', true),
        NOW(),
        NOW()
    )
    ON CONFLICT (organization_id, id) DO NOTHING;  -- Handle race with another worker
    
    -- Check if we actually inserted
    IF NOT FOUND THEN
        -- Another worker inserted first, but that's OK
        RETURN 'exists';
    END IF;
    
    RETURN 'created';
END;
$$ LANGUAGE plpgsql;

-- ==========================================================================
-- Grant access to the function
-- ==========================================================================

GRANT EXECUTE ON FUNCTION public.try_create_scope_placeholder(UUID, UUID, TEXT, TEXT, INTEGER)
    TO service_role, authenticated;

COMMIT;
