-- =============================================================================
-- Migration: Fix RLS Performance Warnings
-- Created: 2026-01-17
-- Purpose: 
--   1. Fix auth_rls_initplan on audit_logs (use SELECT wrapper)
--   2. Remove duplicate permissive policies on ingestion tables
-- =============================================================================

BEGIN;

-- =============================================================================
-- 1. FIX: audit_logs auth_rls_initplan
-- =============================================================================

-- Drop the problematic policy
DROP POLICY IF EXISTS "Service role can insert audit logs" ON public.audit_logs;

-- Recreate with proper SELECT wrapper for auth functions
-- Note: service_role bypasses RLS, but we keep this for documentation
CREATE POLICY "Service role can insert audit logs" ON public.audit_logs
    FOR INSERT
    TO service_role
    WITH CHECK (true);

-- =============================================================================
-- 2. FIX: ingestion_file_status multiple permissive policies
-- Remove the service_role policy - service_role bypasses RLS anyway
-- =============================================================================

DROP POLICY IF EXISTS "ingestion_file_status_service_role" ON public.ingestion_file_status;

-- =============================================================================
-- 3. FIX: ingestion_jobs multiple permissive policies  
-- Remove old user-based policies, keep only org-based policies
-- =============================================================================

-- Drop legacy user-based policies
DROP POLICY IF EXISTS "Users can insert jobs" ON public.ingestion_jobs;
DROP POLICY IF EXISTS "Users can view their own jobs" ON public.ingestion_jobs;
DROP POLICY IF EXISTS "Users can update their own jobs" ON public.ingestion_jobs;

-- =============================================================================
-- 4. VERIFY: Ensure org-based policies exist and use SELECT wrapper
-- =============================================================================

-- Drop and recreate org policies with SELECT wrapper for performance
DROP POLICY IF EXISTS "ingestion_jobs_org_select" ON public.ingestion_jobs;
DROP POLICY IF EXISTS "ingestion_jobs_org_insert" ON public.ingestion_jobs;
DROP POLICY IF EXISTS "ingestion_jobs_org_update" ON public.ingestion_jobs;

-- Recreate with SELECT wrapper for optimal performance
CREATE POLICY "ingestion_jobs_org_select" ON public.ingestion_jobs
    FOR SELECT
    TO authenticated
    USING (is_org_member(organization_id, (SELECT auth.uid())));

CREATE POLICY "ingestion_jobs_org_insert" ON public.ingestion_jobs
    FOR INSERT
    TO authenticated
    WITH CHECK (is_org_member(organization_id, (SELECT auth.uid())));

CREATE POLICY "ingestion_jobs_org_update" ON public.ingestion_jobs
    FOR UPDATE
    TO authenticated
    USING (is_org_member(organization_id, (SELECT auth.uid())))
    WITH CHECK (is_org_member(organization_id, (SELECT auth.uid())));

-- Fix ingestion_file_status org policy with SELECT wrapper
DROP POLICY IF EXISTS "ingestion_file_status_select_org" ON public.ingestion_file_status;

CREATE POLICY "ingestion_file_status_select_org" ON public.ingestion_file_status
    FOR SELECT
    TO authenticated
    USING (is_org_member(organization_id, (SELECT auth.uid())));

COMMIT;
