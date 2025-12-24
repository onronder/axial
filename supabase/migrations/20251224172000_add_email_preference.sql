-- Migration: Add email preference to user_settings
-- Allows users to opt-out of email notifications

-- First ensure user_settings table exists (should be in settings_schema migration)
-- Add the email_on_ingestion_complete column if it doesn't exist
ALTER TABLE user_settings 
ADD COLUMN IF NOT EXISTS email_on_ingestion_complete BOOLEAN DEFAULT TRUE;

-- Add comment for documentation
COMMENT ON COLUMN user_settings.email_on_ingestion_complete 
IS 'Whether to send email notifications when document ingestion completes';
