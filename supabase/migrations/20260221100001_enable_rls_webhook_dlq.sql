-- =============================================================================
-- Migration: Enable RLS on webhook_dlq table
-- Created: 2026-01-17
-- Purpose: Secure webhook_dlq table - only accessible via service_role (backend)
-- =============================================================================

BEGIN;

-- Enable RLS on the table
ALTER TABLE public.webhook_dlq ENABLE ROW LEVEL SECURITY;

-- Force RLS even for table owners (security best practice)
ALTER TABLE public.webhook_dlq FORCE ROW LEVEL SECURITY;

-- No policies for authenticated users - only service_role can access
-- service_role bypasses RLS by default, so no explicit policy needed

COMMENT ON TABLE public.webhook_dlq IS 
'Dead Letter Queue for webhook events. RLS enabled - only accessible via service_role (backend).';

COMMIT;
