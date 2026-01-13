-- ============================================================================
-- Migration: Add SFTP connector definition
-- Date: 2026-01-12
-- ============================================================================

INSERT INTO public.connector_definitions (type, name, description, icon_path, category, is_active)
VALUES (
    'sftp',
    'SFTP',
    'Connect an SFTP server to import files securely',
    NULL,
    'files',
    true
)
ON CONFLICT (type) DO NOTHING;

NOTIFY pgrst, 'reload config';
