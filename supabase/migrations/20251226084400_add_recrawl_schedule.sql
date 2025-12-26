-- Migration: Add scheduled re-crawling fields to web_crawl_configs
-- Created: 2025-12-26
-- Purpose: Enable "Living Knowledge" with automatic re-crawling

-- Add refresh interval and scheduling fields
ALTER TABLE web_crawl_configs 
ADD COLUMN IF NOT EXISTS refresh_interval TEXT NOT NULL DEFAULT 'never' 
    CHECK (refresh_interval IN ('never', 'daily', 'weekly', 'monthly'));

ALTER TABLE web_crawl_configs 
ADD COLUMN IF NOT EXISTS next_crawl_at TIMESTAMPTZ;

ALTER TABLE web_crawl_configs 
ADD COLUMN IF NOT EXISTS last_crawl_at TIMESTAMPTZ;

-- Create index for scheduled crawl lookups
CREATE INDEX IF NOT EXISTS idx_web_crawl_configs_next_crawl 
ON web_crawl_configs(next_crawl_at) 
WHERE status = 'completed' AND refresh_interval != 'never';

-- Refresh Supabase Schema Cache
NOTIFY pgrst, 'reload config';
