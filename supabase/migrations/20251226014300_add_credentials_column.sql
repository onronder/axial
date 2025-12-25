-- Migration: Add credentials and settings columns for OAuth tokens
-- Created: 2025-12-26
-- Purpose: Store OAuth credentials and provider-specific settings

-- Add credentials column for storing OAuth tokens (access_token, refresh_token, etc.)
-- Add settings column for future provider-specific configuration
ALTER TABLE user_integrations 
ADD COLUMN IF NOT EXISTS credentials JSONB,
ADD COLUMN IF NOT EXISTS settings JSONB;

-- Add useful comment for documentation
COMMENT ON COLUMN user_integrations.credentials IS 'OAuth credentials including access_token, refresh_token, workspace_id, etc.';
COMMENT ON COLUMN user_integrations.settings IS 'Provider-specific settings and configuration';

-- Refresh Supabase Schema Cache to prevent PGRST204 error
-- This is crucial - without it, Supabase/PostgREST won't see the new columns
NOTIFY pgrst, 'reload config';
