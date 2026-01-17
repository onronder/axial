-- =============================================================================
-- Migration: Add Webhook Dead Letter Queue Table
-- Created: 2026-01-17
-- Purpose: Store failed webhook events for later retry
-- =============================================================================

BEGIN;

-- Create webhook_dlq table for storing failed webhook events
CREATE TABLE IF NOT EXISTS public.webhook_dlq (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    event_id TEXT NOT NULL,
    event_type TEXT NOT NULL,
    source TEXT NOT NULL DEFAULT 'polar',
    payload JSONB NOT NULL,
    error_message TEXT,
    retry_count INTEGER DEFAULT 0,
    status TEXT DEFAULT 'pending' CHECK (status IN ('pending', 'processed', 'failed')),
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW(),
    
    -- Unique constraint to prevent duplicate entries for same event
    CONSTRAINT webhook_dlq_unique_event UNIQUE (event_id, source)
);

-- Create indexes for efficient querying
CREATE INDEX IF NOT EXISTS idx_webhook_dlq_status ON public.webhook_dlq(status);
CREATE INDEX IF NOT EXISTS idx_webhook_dlq_created_at ON public.webhook_dlq(created_at);
CREATE INDEX IF NOT EXISTS idx_webhook_dlq_source ON public.webhook_dlq(source);

-- Add comment for documentation
COMMENT ON TABLE public.webhook_dlq IS 
'Dead Letter Queue for webhook events that fail processing. Enables automatic retry of failed events.';

COMMENT ON COLUMN public.webhook_dlq.event_id IS 'Unique webhook event ID from the source';
COMMENT ON COLUMN public.webhook_dlq.event_type IS 'Type of webhook event (e.g., subscription.created)';
COMMENT ON COLUMN public.webhook_dlq.source IS 'Source of the webhook (e.g., polar)';
COMMENT ON COLUMN public.webhook_dlq.payload IS 'Full JSON payload of the webhook event';
COMMENT ON COLUMN public.webhook_dlq.error_message IS 'Error message from the failed processing attempt';
COMMENT ON COLUMN public.webhook_dlq.retry_count IS 'Number of retry attempts (max 5)';
COMMENT ON COLUMN public.webhook_dlq.status IS 'Status: pending (needs retry), processed (success), failed (max retries exceeded)';

-- Grant permissions
GRANT SELECT, INSERT, UPDATE ON public.webhook_dlq TO service_role;

-- No RLS needed - this is a backend-only table accessed via service_role

NOTIFY pgrst, 'reload config';

COMMIT;
