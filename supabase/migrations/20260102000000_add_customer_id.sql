-- Migration: Add customer_id to subscriptions
-- Required for Polar Customer Portal sessions API
-- Created: 2026-01-02

-- Add customer_id column to subscriptions table
ALTER TABLE subscriptions 
ADD COLUMN IF NOT EXISTS customer_id TEXT;

-- Index for faster lookups
CREATE INDEX IF NOT EXISTS idx_subscriptions_customer_id 
ON subscriptions(customer_id);

-- Comment
COMMENT ON COLUMN subscriptions.customer_id IS 'Polar customer ID for Customer Portal API';

-- Notify PostgREST to reload schema
NOTIFY pgrst, 'reload config';
