-- ============================================================================
-- Audit Logging System
-- Tracks critical user actions for compliance and debugging
-- ============================================================================

-- 1. Create audit_logs table
CREATE TABLE IF NOT EXISTS public.audit_logs (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    
    -- Actor (nullable for system actions)
    user_id UUID REFERENCES auth.users(id) ON DELETE SET NULL,
    
    -- Action metadata
    action TEXT NOT NULL,  -- e.g., 'document.delete', 'auth.login_fail'
    resource_type TEXT,    -- e.g., 'document', 'chat', 'user', 'connector'
    resource_id TEXT,      -- ID of the affected object
    
    -- Details (flexible JSON for old/new values, context)
    details JSONB DEFAULT '{}'::jsonb,
    
    -- Request context
    ip_address INET,
    user_agent TEXT,
    
    -- Timestamps
    created_at TIMESTAMP WITH TIME ZONE DEFAULT timezone('utc'::text, now()) NOT NULL
);

-- ============================================================================
-- 2. Performance Indexes
-- ============================================================================

-- Find all actions by a specific user
CREATE INDEX IF NOT EXISTS idx_audit_logs_user_id 
ON audit_logs(user_id);

-- Filter by action type (e.g., all deletes)
CREATE INDEX IF NOT EXISTS idx_audit_logs_action 
ON audit_logs(action);

-- Time-based queries (recent activity, date ranges)
CREATE INDEX IF NOT EXISTS idx_audit_logs_created_at 
ON audit_logs(created_at DESC);

-- Find actions on a specific resource
CREATE INDEX IF NOT EXISTS idx_audit_logs_resource 
ON audit_logs(resource_type, resource_id);

-- ============================================================================
-- 3. Row Level Security
-- ============================================================================

ALTER TABLE public.audit_logs ENABLE ROW LEVEL SECURITY;

-- Admins can read all logs (future: role-based access)
-- For now, no SELECT policy = only service_role can read
-- This is intentional for security

-- Service role can insert (used by backend)
CREATE POLICY "Service role can insert audit logs" ON public.audit_logs
    FOR INSERT
    WITH CHECK (true);

-- ============================================================================
-- 4. Data Retention (optional: auto-delete old logs)
-- ============================================================================

-- Comment: Consider adding a cron job or Celery Beat task to delete
-- logs older than N days for GDPR compliance:
-- DELETE FROM audit_logs WHERE created_at < NOW() - INTERVAL '90 days';

-- ============================================================================
-- 5. Notify PostgREST
-- ============================================================================

NOTIFY pgrst, 'reload config';
