-- Performance Optimization: Database Indexes
-- Run this migration in Supabase SQL Editor
-- Date: 2024-12-26

-- =============================================================================
-- 1. Documents: Listing documents by user, sorted by date (Dashboard default)
-- =============================================================================
CREATE INDEX IF NOT EXISTS idx_documents_user_created 
ON documents(user_id, created_at DESC);

-- =============================================================================
-- 2. Notifications: Quickly finding unread notifications for bell icon
-- =============================================================================
-- Partial index: only covers unread notifications (much smaller)
CREATE INDEX IF NOT EXISTS idx_notifications_user_unread 
ON notifications(user_id, created_at DESC) 
WHERE is_read = false;

-- =============================================================================
-- 3. Ingestion Jobs: Monitoring active jobs (progress bar queries)
-- =============================================================================
CREATE INDEX IF NOT EXISTS idx_ingestion_jobs_user_status 
ON ingestion_jobs(user_id, status);

-- =============================================================================
-- 4. Document Chunks: Faster cascade deletes when document is removed
-- =============================================================================
CREATE INDEX IF NOT EXISTS idx_document_chunks_doc_id 
ON document_chunks(document_id);

-- =============================================================================
-- 5. User Integrations: Quick lookups by user and connector type
-- =============================================================================
CREATE INDEX IF NOT EXISTS idx_user_integrations_user_type
ON user_integrations(user_id, connector_type);

-- =============================================================================
-- 6. Web Crawl Configs: Finding active crawls for user
-- =============================================================================
CREATE INDEX IF NOT EXISTS idx_web_crawl_configs_user_status
ON web_crawl_configs(user_id, status);

-- =============================================================================
-- Optional: Analyze tables to update query planner statistics
-- =============================================================================
-- ANALYZE documents;
-- ANALYZE notifications;
-- ANALYZE ingestion_jobs;
-- ANALYZE document_chunks;
