-- Migration: Add Failed Tasks Table for Dead Letter Queue
-- Date: 2026-01-05
-- Purpose: Track failed Celery tasks for retry and debugging

CREATE TABLE IF NOT EXISTS failed_tasks (
    id UUID DEFAULT gen_random_uuid() PRIMARY KEY,
    task_id TEXT NOT NULL UNIQUE,
    task_name TEXT NOT NULL,
    user_id UUID,
    job_id UUID,
    
    -- Task details
    args JSONB,
    kwargs JSONB,
    
    -- Failure details
    exception_type TEXT,
    exception_message TEXT,
    traceback TEXT,
    
    -- Retry info
    attempt_count INTEGER DEFAULT 1,
    max_retries INTEGER DEFAULT 3,
    next_retry_at TIMESTAMPTZ,
    
    -- Status tracking
    status TEXT DEFAULT 'failed' CHECK (status IN ('failed', 'pending_retry', 'retrying', 'permanently_failed', 'resolved')),
    
    -- Timestamps
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW(),
    resolved_at TIMESTAMPTZ,
    
    -- Foreign key
    CONSTRAINT fk_user FOREIGN KEY (user_id) REFERENCES auth.users(id) ON DELETE CASCADE
);

-- Indexes for performance
CREATE INDEX IF NOT EXISTS idx_failed_tasks_status ON failed_tasks(status);
CREATE INDEX IF NOT EXISTS idx_failed_tasks_user ON failed_tasks(user_id);
CREATE INDEX IF NOT EXISTS idx_failed_tasks_next_retry ON failed_tasks(next_retry_at) WHERE status = 'pending_retry';
CREATE INDEX IF NOT EXISTS idx_failed_tasks_created ON failed_tasks(created_at DESC);

-- Updated timestamp trigger
CREATE OR REPLACE FUNCTION update_failed_tasks_updated_at()
RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_at = NOW();
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

CREATE TRIGGER trigger_failed_tasks_updated_at
    BEFORE UPDATE ON failed_tasks
    FOR EACH ROW
    EXECUTE FUNCTION update_failed_tasks_updated_at();

-- Comments
COMMENT ON TABLE failed_tasks IS 'Dead letter queue for failed Celery tasks';
COMMENT ON COLUMN failed_tasks.status IS 'Task status: failed, pending_retry, retrying, permanently_failed, resolved';
COMMENT ON COLUMN failed_tasks.attempt_count IS 'Number of retry attempts made';
COMMENT ON COLUMN failed_tasks.next_retry_at IS 'When to retry this task (NULL if not retrying)';
