-- Migration: Add Box connector definition
-- Box: Enterprise cloud storage with OAuth 2.0 (rotating refresh tokens)

-- Insert Box connector definition
INSERT INTO connector_definitions (
    type,
    name,
    description,
    icon_path,
    category,
    is_active,
    created_at
) VALUES (
    'box',
    'Box',
    'Connect to Box cloud storage for enterprise file management. Supports both personal and enterprise/business accounts with secure OAuth authentication.',
    '/icons/box.svg',
    'Cloud Storage',
    true,
    NOW()
) ON CONFLICT (type) DO UPDATE SET
    name = EXCLUDED.name,
    description = EXCLUDED.description,
    icon_path = EXCLUDED.icon_path,
    category = EXCLUDED.category,
    is_active = EXCLUDED.is_active;
