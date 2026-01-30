-- =============================================================================
-- Migration: Fix Function Search Path Mutable Warnings (V2)
-- Created: 2026-01-30
-- Purpose: Ensure all functions have immutable search_path to resolve
--          Supabase linter warnings for security compliance
-- 
-- WARNING ADDRESSED:
--   "Function has a role mutable search_path"
--   https://supabase.com/docs/guides/database/database-linter?lint=0011_function_search_path_mutable
-- 
-- SECURITY RATIONALE:
--   Without a fixed search_path, an attacker could:
--   1. Create a malicious schema with same-named functions
--   2. Manipulate the session search path
--   3. Execute malicious functions instead of intended ones
-- 
-- APPROACH:
--   Using ALTER FUNCTION ... SET search_path instead of CREATE OR REPLACE
--   to preserve existing function logic while only changing the security setting
-- =============================================================================

BEGIN;

-- =============================================================================
-- 1. FIX: hybrid_search
-- =============================================================================
-- Note: Using DO block with exception handling to skip if function doesn't exist

DO $$
BEGIN
    -- Try to alter the function
    EXECUTE 'ALTER FUNCTION public.hybrid_search(
        TEXT,           -- query_text
        VECTOR(1536),   -- query_embedding
        INT,            -- match_count
        UUID,           -- filter_org_id
        FLOAT,          -- vector_weight
        FLOAT,          -- keyword_weight
        FLOAT           -- similarity_threshold
    ) SET search_path = public, pg_catalog';
    
    RAISE NOTICE 'Fixed search_path for hybrid_search';
EXCEPTION
    WHEN undefined_function THEN
        RAISE NOTICE 'hybrid_search function not found, skipping';
    WHEN OTHERS THEN
        RAISE NOTICE 'Error altering hybrid_search: %', SQLERRM;
END;
$$;

-- =============================================================================
-- 2. FIX: hybrid_search_scoped
-- =============================================================================

DO $$
BEGIN
    EXECUTE 'ALTER FUNCTION public.hybrid_search_scoped(
        TEXT,           -- query_text
        VECTOR(1536),   -- query_embedding
        INT,            -- match_count
        UUID,           -- filter_org_id
        TEXT[],         -- filter_scope_ids
        FLOAT,          -- vector_weight
        FLOAT,          -- keyword_weight
        FLOAT           -- similarity_threshold
    ) SET search_path = public, pg_catalog';
    
    RAISE NOTICE 'Fixed search_path for hybrid_search_scoped';
EXCEPTION
    WHEN undefined_function THEN
        RAISE NOTICE 'hybrid_search_scoped function not found, skipping';
    WHEN OTHERS THEN
        RAISE NOTICE 'Error altering hybrid_search_scoped: %', SQLERRM;
END;
$$;

-- =============================================================================
-- 3. FIX: match_documents
-- =============================================================================

DO $$
BEGIN
    EXECUTE 'ALTER FUNCTION public.match_documents(
        VECTOR(1536),   -- query_embedding
        FLOAT,          -- match_threshold
        INT,            -- match_count
        UUID            -- filter_org_id
    ) SET search_path = public, pg_catalog';
    
    RAISE NOTICE 'Fixed search_path for match_documents';
EXCEPTION
    WHEN undefined_function THEN
        RAISE NOTICE 'match_documents function not found, skipping';
    WHEN OTHERS THEN
        RAISE NOTICE 'Error altering match_documents: %', SQLERRM;
END;
$$;

-- =============================================================================
-- 4. FIX: purge_organization (1-arg version)
-- =============================================================================

DO $$
BEGIN
    EXECUTE 'ALTER FUNCTION public.purge_organization(UUID) SET search_path = public, pg_catalog';
    
    RAISE NOTICE 'Fixed search_path for purge_organization(UUID)';
EXCEPTION
    WHEN undefined_function THEN
        RAISE NOTICE 'purge_organization(UUID) function not found, skipping';
    WHEN OTHERS THEN
        RAISE NOTICE 'Error altering purge_organization: %', SQLERRM;
END;
$$;

-- =============================================================================
-- 5. FIX: update_documents_updated_at trigger function
-- =============================================================================

DO $$
BEGIN
    EXECUTE 'ALTER FUNCTION public.update_documents_updated_at() SET search_path = public, pg_catalog';
    
    RAISE NOTICE 'Fixed search_path for update_documents_updated_at';
EXCEPTION
    WHEN undefined_function THEN
        RAISE NOTICE 'update_documents_updated_at function not found, skipping';
    WHEN OTHERS THEN
        RAISE NOTICE 'Error altering update_documents_updated_at: %', SQLERRM;
END;
$$;

-- =============================================================================
-- 6. FIX: handle_new_user trigger function
-- =============================================================================

DO $$
BEGIN
    EXECUTE 'ALTER FUNCTION public.handle_new_user() SET search_path = public, pg_catalog';
    
    RAISE NOTICE 'Fixed search_path for handle_new_user';
EXCEPTION
    WHEN undefined_function THEN
        RAISE NOTICE 'handle_new_user function not found, skipping';
    WHEN OTHERS THEN
        RAISE NOTICE 'Error altering handle_new_user: %', SQLERRM;
END;
$$;

-- =============================================================================
-- Verification Query (run after migration to confirm)
-- =============================================================================
-- SELECT proname, proconfig 
-- FROM pg_proc 
-- WHERE pronamespace = 'public'::regnamespace 
-- AND proname IN ('hybrid_search', 'hybrid_search_scoped', 'match_documents');
-- 
-- Expected: proconfig should contain 'search_path=public, pg_catalog' for each

COMMIT;
