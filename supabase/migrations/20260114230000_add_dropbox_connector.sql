-- Migration: Add Dropbox connector definition
-- Supports both Personal and Business/Team accounts via Path Root header

-- Insert Dropbox connector definition
INSERT INTO connector_definitions (
    type,
    name,
    description,
    icon_path,
    category,
    is_active,
    created_at
) VALUES (
    'dropbox',
    'Dropbox',
    'Connect to Dropbox to sync files and folders. Supports Personal and Business/Team accounts.',
    '/icons/dropbox.svg',
    'Cloud Storage',
    true,
    NOW()
) ON CONFLICT (type) DO UPDATE SET
    name = EXCLUDED.name,
    description = EXCLUDED.description,
    icon_path = EXCLUDED.icon_path,
    category = EXCLUDED.category,
    is_active = EXCLUDED.is_active;
