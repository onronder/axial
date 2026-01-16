-- Migration: Fix Scope Quota RPC - Check Existing FIRST
--
-- CRITICAL FIX: The previous RPC checked max_scopes BEFORE checking if
-- the scope already exists. This caused paid orgs to get "no_subscription"
-- errors when max_scopes was passed as 0 (the default).
--
-- The fix: Check if scope EXISTS first, return 'exists' immediately.
-- Only check quota for NEW scopes.

BEGIN;

-- ==========================================================================
-- Function: try_create_scope_placeholder (FIXED)
-- ==========================================================================
-- CRITICAL CHANGE: Check existing scope BEFORE quota check
-- This ensures existing scopes always return 'exists' regardless of max_scopes

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
    -- ==========================================================================
    -- STEP 1: CHECK IF SCOPE ALREADY EXISTS (BEFORE quota check!)
    -- ==========================================================================
    -- This is the critical fix: existing scopes should ALWAYS return 'exists'
    -- regardless of max_scopes value. Only NEW scopes need quota checks.
    
    SELECT id, status INTO v_existing
    FROM scope_identities
    WHERE organization_id = p_organization_id
    AND id = p_scope_id;
    
    IF FOUND THEN
        -- Scope exists, no quota check needed - return immediately
        RETURN 'exists';
    END IF;
    
    -- ==========================================================================
    -- STEP 2: QUOTA CHECK (only for NEW scopes)
    -- ==========================================================================
    -- HARD ZERO RULE: No subscription = No NEW scopes
    -- But this only applies to NEW scopes, not existing ones
    
    IF p_max_scopes <= 0 THEN
        RETURN 'no_subscription';
    END IF;
    
    -- Acquire advisory lock for this organization to serialize quota checks
    -- This prevents race conditions where multiple workers check quota simultaneously
    PERFORM pg_advisory_xact_lock(
        hashtext('scope_quota'::text),
        hashtext(p_organization_id::text)
    );
    
    -- Re-check if scope was created while we were waiting for the lock
    SELECT id INTO v_existing
    FROM scope_identities
    WHERE organization_id = p_organization_id
    AND id = p_scope_id;
    
    IF FOUND THEN
        RETURN 'exists';
    END IF;
    
    -- Count existing scopes (now guaranteed exclusive)
    SELECT COUNT(*) INTO v_current_count
    FROM scope_identities
    WHERE organization_id = p_organization_id;
    
    -- Check quota
    IF v_current_count >= p_max_scopes THEN
        RETURN 'quota_exceeded';
    END IF;
    
    -- ==========================================================================
    -- STEP 3: CREATE PLACEHOLDER
    -- ==========================================================================
    
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
    ON CONFLICT (organization_id, id) DO NOTHING;
    
    -- Check if we actually inserted (race with another worker)
    IF NOT FOUND THEN
        RETURN 'exists';
    END IF;
    
    RETURN 'created';
END;
$$ LANGUAGE plpgsql
   SET search_path = public;  -- Security hardening

-- ==========================================================================
-- Fix is_org_member: Add search_path for security
-- ==========================================================================

CREATE OR REPLACE FUNCTION public.is_org_member(
    org_id UUID,
    user_uuid UUID
) RETURNS BOOLEAN AS $$
BEGIN
    -- Check 1: Is user the team/org owner?
    IF EXISTS (
        SELECT 1 FROM public.teams 
        WHERE id = org_id 
        AND owner_id = user_uuid
    ) THEN
        RETURN TRUE;
    END IF;
    
    -- Check 2: Is user an active team member?
    IF EXISTS (
        SELECT 1 FROM public.team_members 
        WHERE team_id = org_id 
        AND member_user_id = user_uuid
        AND status != 'removed'
    ) THEN
        RETURN TRUE;
    END IF;
    
    RETURN FALSE;
END;
$$ LANGUAGE plpgsql 
   SECURITY DEFINER
   SET search_path = public;  -- CRITICAL: Prevents search_path hijacking

COMMIT;
