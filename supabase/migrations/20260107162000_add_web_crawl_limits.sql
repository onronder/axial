-- Migration: Add crawl limits and subdomain flags to web_crawl_configs
-- Created: 2026-01-07
-- Purpose: Enforce safe crawl budgets and domain scoping

ALTER TABLE web_crawl_configs
    ADD COLUMN IF NOT EXISTS max_pages INTEGER NOT NULL DEFAULT 500 CHECK (max_pages >= 1 AND max_pages <= 10000),
    ADD COLUMN IF NOT EXISTS allow_subdomains BOOLEAN NOT NULL DEFAULT FALSE;

-- Refresh Supabase Schema Cache
NOTIFY pgrst, 'reload config';
