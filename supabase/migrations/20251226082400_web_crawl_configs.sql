-- Migration: Create web_crawl_configs table for advanced web crawling
-- Created: 2025-12-26
-- Purpose: Track web crawl job configurations and progress

CREATE TABLE IF NOT EXISTS web_crawl_configs (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id UUID NOT NULL REFERENCES auth.users(id) ON DELETE CASCADE,
    
    -- Crawl Configuration
    root_url TEXT NOT NULL,
    crawl_type TEXT NOT NULL DEFAULT 'single' CHECK (crawl_type IN ('single', 'recursive', 'sitemap')),
    max_depth INTEGER NOT NULL DEFAULT 1 CHECK (max_depth >= 1 AND max_depth <= 10),
    respect_robots_txt BOOLEAN NOT NULL DEFAULT TRUE,
    
    -- Progress Tracking
    status TEXT NOT NULL DEFAULT 'pending' CHECK (status IN ('pending', 'discovering', 'processing', 'completed', 'failed', 'cancelled')),
    total_pages_found INTEGER NOT NULL DEFAULT 0,
    pages_ingested INTEGER NOT NULL DEFAULT 0,
    pages_failed INTEGER NOT NULL DEFAULT 0,
    
    -- Error Handling
    error_message TEXT,
    
    -- Timestamps
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW(),
    completed_at TIMESTAMPTZ,
    
    -- Task Reference
    celery_task_id TEXT
);

-- Create index for user lookups
CREATE INDEX IF NOT EXISTS idx_web_crawl_configs_user_id ON web_crawl_configs(user_id);
CREATE INDEX IF NOT EXISTS idx_web_crawl_configs_status ON web_crawl_configs(status);

-- Enable RLS
ALTER TABLE web_crawl_configs ENABLE ROW LEVEL SECURITY;

-- RLS Policies: Users can only access their own crawl configs
CREATE POLICY "Users can view their own crawl configs"
    ON web_crawl_configs FOR SELECT
    USING (auth.uid() = user_id);

CREATE POLICY "Users can create their own crawl configs"
    ON web_crawl_configs FOR INSERT
    WITH CHECK (auth.uid() = user_id);

CREATE POLICY "Users can update their own crawl configs"
    ON web_crawl_configs FOR UPDATE
    USING (auth.uid() = user_id);

CREATE POLICY "Users can delete their own crawl configs"
    ON web_crawl_configs FOR DELETE
    USING (auth.uid() = user_id);

-- Service role policy for backend operations
CREATE POLICY "Service role has full access to crawl configs"
    ON web_crawl_configs FOR ALL
    USING (auth.role() = 'service_role');

-- Refresh Supabase Schema Cache
NOTIFY pgrst, 'reload config';
