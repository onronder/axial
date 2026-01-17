-- =============================================================================
-- Migration: Add Index on scope_identities.user_id Foreign Key
-- Created: 2026-01-17
-- Purpose: Fix unindexed foreign key warning for better JOIN performance
-- =============================================================================

-- Use CONCURRENTLY to avoid locking the table during index creation
-- This is safe for production and won't block reads/writes
CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_scope_identities_user_id 
ON public.scope_identities(user_id);
