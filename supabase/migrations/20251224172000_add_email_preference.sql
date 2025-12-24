-- Migration: Add email_on_ingestion_complete to user_notification_settings
-- Allows users to opt-out of email notifications for ingestion completions
-- This uses the existing key-value notification settings pattern

-- Insert default setting for existing users (will be inserted per-user on first load)
-- The worker will check for this key in user_notification_settings table

-- Just add a comment explaining the expected setting format:
-- setting_key: 'email_on_ingestion_complete'
-- setting_label: 'Ingestion Complete'
-- setting_description: 'Receive email notifications when document ingestion completes'
-- category: 'email'
-- enabled: true (default)

-- Note: This migration is informational - the actual setting row is created
-- dynamically by the application when the user first accesses notification settings
-- The worker checks for: user_notification_settings WHERE setting_key = 'email_on_ingestion_complete'

-- No schema changes needed - using existing key-value pattern
SELECT 1;
