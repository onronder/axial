-- =========================================================================
-- Migration: Add Microsoft OneDrive + SharePoint connector definitions
-- Date: 2026-01-12
-- =========================================================================

INSERT INTO public.connector_definitions (type, name, description, icon_path, category, is_active)
VALUES
    ('onedrive', 'OneDrive', 'Connect Microsoft OneDrive (personal or work) via Graph API', NULL, 'cloud', true),
    ('sharepoint', 'SharePoint', 'Connect Microsoft SharePoint sites via Graph API', NULL, 'cloud', true)
ON CONFLICT (type) DO NOTHING;

NOTIFY pgrst, 'reload config';
