-- Migration: Add GitHub connector definition
-- GitHub: Code repository integration with strict content filtering

-- Insert GitHub connector definition
INSERT INTO connector_definitions (
    type,
    name,
    description,
    icon_path,
    category,
    is_active,
    created_at
) VALUES (
    'github',
    'GitHub',
    'Connect to GitHub repositories to sync source code and documentation. Intelligent filtering excludes node_modules, build artifacts, and binaries.',
    '/icons/github.svg',
    'Development',
    true,
    NOW()
) ON CONFLICT (type) DO UPDATE SET
    name = EXCLUDED.name,
    description = EXCLUDED.description,
    icon_path = EXCLUDED.icon_path,
    category = EXCLUDED.category,
    is_active = EXCLUDED.is_active;
