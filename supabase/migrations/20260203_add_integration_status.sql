-- Add status tracking to user_integrations
-- This allows tracking integration health and prompting users to reconnect when tokens expire

ALTER TABLE user_integrations
ADD COLUMN IF NOT EXISTS status TEXT DEFAULT 'active',
ADD COLUMN IF NOT EXISTS status_message TEXT;

-- Add index for status queries (only for non-active statuses)
CREATE INDEX IF NOT EXISTS idx_user_integrations_status
ON user_integrations(status) WHERE status != 'active';

-- Add comments for documentation
COMMENT ON COLUMN user_integrations.status IS 'Integration health status: active, reconnection_required, error';
COMMENT ON COLUMN user_integrations.status_message IS 'Human-readable status message for UI display';
