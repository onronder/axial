-- =============================================================================
-- Migration: Fix Function Search Path Mutable Warnings
-- Created: 2026-01-17
-- Purpose: Add SET search_path = public to all affected functions
-- =============================================================================

BEGIN;

-- =============================================================================
-- 1. FIX: update_documents_updated_at
-- =============================================================================

CREATE OR REPLACE FUNCTION public.update_documents_updated_at()
RETURNS TRIGGER
LANGUAGE plpgsql
SECURITY DEFINER
SET search_path = public
AS $$
BEGIN
    NEW.updated_at = NOW();
    RETURN NEW;
END;
$$;

-- =============================================================================
-- 2. FIX: hybrid_search_scoped
-- Signature: (TEXT, VECTOR(1536), INT, UUID, TEXT[], FLOAT, FLOAT, FLOAT)
-- =============================================================================

ALTER FUNCTION public.hybrid_search_scoped(
    TEXT,           -- query_text
    VECTOR(1536),   -- query_embedding
    INT,            -- match_count
    UUID,           -- filter_org_id
    TEXT[],         -- filter_scope_ids
    FLOAT,          -- vector_weight
    FLOAT,          -- keyword_weight
    FLOAT           -- similarity_threshold
) SET search_path = public;

-- =============================================================================
-- 3. FIX: purge_organization - 1-arg version (2-arg already has it)
-- =============================================================================

ALTER FUNCTION public.purge_organization(UUID) SET search_path = public;

-- =============================================================================
-- 4. FIX: hybrid_search
-- Signature: (TEXT, VECTOR(1536), INT, UUID, FLOAT, FLOAT, FLOAT)
-- =============================================================================

ALTER FUNCTION public.hybrid_search(
    TEXT,           -- query_text
    VECTOR(1536),   -- query_embedding
    INT,            -- match_count
    UUID,           -- filter_org_id
    FLOAT,          -- vector_weight
    FLOAT,          -- keyword_weight
    FLOAT           -- similarity_threshold
) SET search_path = public;

-- =============================================================================
-- 5. FIX: match_documents
-- Signature: (VECTOR(1536), FLOAT, INT, UUID)
-- =============================================================================

ALTER FUNCTION public.match_documents(
    VECTOR(1536),   -- query_embedding
    FLOAT,          -- match_threshold
    INT,            -- match_count
    UUID            -- filter_org_id
) SET search_path = public;

COMMIT;
