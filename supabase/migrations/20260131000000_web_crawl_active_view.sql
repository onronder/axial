-- Migration: Add active crawls view and performance optimizations
-- Created: 2026-01-31
-- Purpose: Enable frontend to query active crawls for state restoration

-- =============================================================================
-- PERFORMANCE INDEXES
-- =============================================================================

-- Composite index for efficient active crawl lookups by user
CREATE INDEX IF NOT EXISTS idx_web_crawl_configs_user_active 
ON web_crawl_configs(user_id, status) 
WHERE status IN ('pending', 'discovering', 'processing');

-- Index for recent crawls (last 30 days)
CREATE INDEX IF NOT EXISTS idx_web_crawl_configs_created_at 
ON web_crawl_configs(created_at DESC);

-- =============================================================================
-- SECURE VIEW FOR ACTIVE CRAWLS
-- =============================================================================

-- Drop existing view if exists (for idempotency)
DROP VIEW IF EXISTS active_web_crawls;

-- Create secure view that inherits RLS from base table
-- This view shows only active crawls (pending, discovering, processing)
CREATE VIEW active_web_crawls
WITH (security_invoker = true)  -- Inherits RLS from base table
AS
SELECT 
    id,
    user_id,
    root_url,
    crawl_type,
    max_depth,
    max_pages,
    allow_subdomains,
    respect_robots_txt,
    status,
    total_pages_found,
    pages_ingested,
    pages_failed,
    error_message,
    celery_task_id,
    created_at,
    updated_at
FROM web_crawl_configs
WHERE status IN ('pending', 'discovering', 'processing');

-- Grant SELECT on view to authenticated users
GRANT SELECT ON active_web_crawls TO authenticated;

-- =============================================================================
-- RECENT CRAWLS VIEW (for history display)
-- =============================================================================

-- Drop existing view if exists
DROP VIEW IF EXISTS recent_web_crawls;

-- Create secure view for recent crawls (last 30 days, any status)
CREATE VIEW recent_web_crawls
WITH (security_invoker = true)
AS
SELECT 
    id,
    user_id,
    root_url,
    crawl_type,
    max_depth,
    max_pages,
    status,
    total_pages_found,
    pages_ingested,
    pages_failed,
    error_message,
    refresh_interval,
    next_crawl_at,
    last_crawl_at,
    created_at,
    updated_at,
    completed_at
FROM web_crawl_configs
WHERE created_at > NOW() - INTERVAL '30 days'
ORDER BY created_at DESC;

-- Grant SELECT on view to authenticated users
GRANT SELECT ON recent_web_crawls TO authenticated;

-- =============================================================================
-- COMMENTS FOR DOCUMENTATION
-- =============================================================================

COMMENT ON VIEW active_web_crawls IS 
    'Active web crawls (pending/discovering/processing) with RLS inherited from web_crawl_configs';

COMMENT ON VIEW recent_web_crawls IS 
    'Recent web crawls from last 30 days with RLS inherited from web_crawl_configs';

-- Refresh Supabase Schema Cache
NOTIFY pgrst, 'reload config';
