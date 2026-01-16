-- Migration: Security Hardening - Fix SECURITY DEFINER Functions
--
-- This migration adds SET search_path = public to all SECURITY DEFINER
-- functions that were missing it. This prevents search_path hijacking
-- attacks where an attacker could create objects in other schemas.
--
-- Without a fixed search_path, a SECURITY DEFINER function could be
-- tricked into calling malicious functions in an attacker-controlled schema.

BEGIN;

-- ==========================================================================
-- Fix: get_effective_plan
-- ==========================================================================

CREATE OR REPLACE FUNCTION public.get_effective_plan(target_user_id UUID)
RETURNS TEXT
LANGUAGE plpgsql
SECURITY DEFINER
STABLE
SET search_path = public
AS $$
DECLARE
    v_team_id UUID;
    v_sub_status TEXT;
    v_owner_plan TEXT;
    v_own_plan TEXT;
BEGIN
    -- Check user's own subscription first (for team owners)
    SELECT subscription_status, plan INTO v_sub_status, v_own_plan
    FROM public.user_profiles
    WHERE user_id = target_user_id;
    
    -- If user has an active subscription, use their plan
    IF v_sub_status IN ('active', 'trialing') AND v_own_plan IS NOT NULL THEN
        RETURN v_own_plan;
    END IF;
    
    -- Check if user is a team member (inherit from owner)
    SELECT tm.team_id INTO v_team_id
    FROM public.team_members tm
    WHERE tm.member_user_id = target_user_id
      AND tm.status != 'removed'
    LIMIT 1;
    
    IF v_team_id IS NOT NULL THEN
        -- Get owner's plan
        SELECT up.plan INTO v_owner_plan
        FROM public.teams t
        JOIN public.user_profiles up ON up.user_id = t.owner_id
        WHERE t.id = v_team_id
          AND up.subscription_status IN ('active', 'trialing');
        
        IF v_owner_plan IS NOT NULL THEN
            RETURN v_owner_plan;
        END IF;
    END IF;
    
    -- Default to free if no valid subscription found
    RETURN COALESCE(v_own_plan, 'free');
END;
$$;

-- ==========================================================================
-- Fix: get_user_team_data
-- ==========================================================================

-- Drop first since return type may differ
DROP FUNCTION IF EXISTS public.get_user_team_data(UUID);

CREATE OR REPLACE FUNCTION public.get_user_team_data(p_user_id UUID)
RETURNS JSONB
LANGUAGE plpgsql
STABLE
SECURITY DEFINER
SET search_path = public
AS $$
DECLARE
    result JSONB;
BEGIN
    SELECT jsonb_build_object(
        'team_id', t.id,
        'team_name', t.name,
        'team_slug', t.slug,
        'team_plan', t.plan,
        'is_owner', (t.owner_id = p_user_id),
        'user_role', tm.role,
        'member_count', (SELECT COUNT(*) FROM public.team_members WHERE team_id = t.id AND status != 'removed')
    )
    INTO result
    FROM public.teams t
    LEFT JOIN public.team_members tm ON tm.team_id = t.id AND tm.member_user_id = p_user_id
    WHERE t.owner_id = p_user_id OR tm.member_user_id = p_user_id
    AND tm.status != 'removed'
    LIMIT 1;
    
    RETURN result;
END;
$$;

-- ==========================================================================
-- Fix: recalculate_user_usage
-- ==========================================================================

CREATE OR REPLACE FUNCTION public.recalculate_user_usage(target_user_id UUID)
RETURNS VOID
LANGUAGE plpgsql
SECURITY DEFINER
SET search_path = public
AS $$
DECLARE
    calc_file_count INTEGER;
    calc_storage_bytes BIGINT;
BEGIN
    -- Calculate actual values from documents
    SELECT 
        COUNT(*),
        COALESCE(SUM(file_size_bytes), 0)
    INTO calc_file_count, calc_storage_bytes
    FROM public.documents 
    WHERE user_id = target_user_id;
    
    -- Update user_usage table
    INSERT INTO public.user_usage (user_id, file_count, storage_bytes, updated_at)
    VALUES (target_user_id, calc_file_count, calc_storage_bytes, NOW())
    ON CONFLICT (user_id) 
    DO UPDATE SET 
        file_count = EXCLUDED.file_count,
        storage_bytes = EXCLUDED.storage_bytes,
        updated_at = NOW();
END;
$$;

-- ==========================================================================
-- Fix: upsert_scope_identity_document
-- ==========================================================================

CREATE OR REPLACE FUNCTION public.upsert_scope_identity_document(
    p_scope_id TEXT,
    p_organization_id UUID,
    p_user_id UUID,
    p_type TEXT,
    p_summary TEXT,
    p_file_tree TEXT,
    p_attributes JSONB,
    p_last_ingested_at TIMESTAMPTZ
) RETURNS UUID
LANGUAGE plpgsql
SECURITY DEFINER
SET search_path = public
AS $$
DECLARE
    v_doc_id UUID;
BEGIN
    -- Upsert scope identity
    INSERT INTO public.scope_identities (
        id,
        organization_id,
        user_id,
        type,
        summary,
        file_tree,
        attributes,
        last_ingested_at,
        status,
        updated_at
    ) VALUES (
        p_scope_id,
        p_organization_id,
        p_user_id,
        p_type,
        p_summary,
        p_file_tree,
        p_attributes,
        p_last_ingested_at,
        'completed',
        NOW()
    )
    ON CONFLICT (organization_id, id) 
    DO UPDATE SET
        type = EXCLUDED.type,
        summary = EXCLUDED.summary,
        file_tree = EXCLUDED.file_tree,
        attributes = EXCLUDED.attributes,
        last_ingested_at = EXCLUDED.last_ingested_at,
        status = 'completed',
        updated_at = NOW();

    -- Upsert identity document
    INSERT INTO public.documents (
        id,
        user_id,
        organization_id,
        team_id,
        title,
        source_type,
        source_id,
        scope_id,
        content_hash,
        metadata,
        created_at,
        updated_at
    ) VALUES (
        gen_random_uuid(),
        p_user_id,
        p_organization_id,
        p_organization_id,
        'Scope Identity: ' || p_scope_id,
        'identity',
        'identity::' || p_scope_id,
        p_scope_id,
        md5(p_summary),
        jsonb_build_object(
            'scope_id', p_scope_id,
            'type', 'identity_card',
            'is_identity', true,
            'organization_id', p_organization_id
        ),
        NOW(),
        NOW()
    )
    ON CONFLICT (organization_id, source_id) 
    DO UPDATE SET
        title = EXCLUDED.title,
        content_hash = EXCLUDED.content_hash,
        metadata = EXCLUDED.metadata,
        updated_at = NOW()
    RETURNING id INTO v_doc_id;

    RETURN v_doc_id;
END;
$$;

-- ==========================================================================
-- Fix: purge_organization
-- ==========================================================================

CREATE OR REPLACE FUNCTION public.purge_organization(p_organization_id UUID, p_owner_id UUID)
RETURNS JSONB
LANGUAGE plpgsql
SECURITY DEFINER
SET search_path = public
AS $$
DECLARE
    v_is_owner BOOLEAN;
    v_has_active_jobs BOOLEAN;
    v_deleted_docs INTEGER;
    v_deleted_scopes INTEGER;
    v_deleted_jobs INTEGER;
BEGIN
    -- Verify ownership
    SELECT EXISTS (
        SELECT 1 FROM public.teams WHERE id = p_organization_id AND owner_id = p_owner_id
    ) INTO v_is_owner;
    
    IF NOT v_is_owner THEN
        RAISE EXCEPTION 'User is not the organization owner';
    END IF;
    
    -- Check for active ingestion jobs
    SELECT EXISTS (
        SELECT 1 FROM public.ingestion_jobs 
        WHERE user_id = p_owner_id 
        AND status IN ('pending', 'processing')
    ) INTO v_has_active_jobs;
    
    IF v_has_active_jobs THEN
        RAISE EXCEPTION 'Cannot purge while ingestion jobs are active';
    END IF;
    
    -- Delete in order (respecting FK constraints)
    DELETE FROM public.document_chunks 
    WHERE document_id IN (
        SELECT id FROM public.documents WHERE organization_id = p_organization_id
    );
    
    DELETE FROM public.documents WHERE organization_id = p_organization_id;
    GET DIAGNOSTICS v_deleted_docs = ROW_COUNT;
    
    DELETE FROM public.scope_identities WHERE organization_id = p_organization_id;
    GET DIAGNOSTICS v_deleted_scopes = ROW_COUNT;
    
    DELETE FROM public.ingestion_jobs WHERE user_id = p_owner_id;
    GET DIAGNOSTICS v_deleted_jobs = ROW_COUNT;
    
    RETURN jsonb_build_object(
        'deleted_documents', v_deleted_docs,
        'deleted_scopes', v_deleted_scopes,
        'deleted_jobs', v_deleted_jobs
    );
END;
$$;

-- ==========================================================================
-- Fix: search_similar_chunks (if exists)
-- ==========================================================================
-- Use ALTER FUNCTION to add search_path without changing signature

DO $$
BEGIN
    IF EXISTS (SELECT 1 FROM pg_proc WHERE proname = 'search_similar_chunks') THEN
        -- Just add search_path to existing function
        ALTER FUNCTION public.search_similar_chunks SET search_path = public;
    END IF;
EXCEPTION WHEN OTHERS THEN
    -- Ignore if function doesn't exist or can't be altered
    NULL;
END $$;

NOTIFY pgrst, 'reload config';

COMMIT;
