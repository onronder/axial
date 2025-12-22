-- ============================================================================
-- Dynamic Connector Architecture Migration
-- Creates connector_definitions table and updates user_integrations
-- ============================================================================

-- 1. Create connector_definitions table
CREATE TABLE IF NOT EXISTS public.connector_definitions (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    type TEXT UNIQUE NOT NULL,
    name TEXT NOT NULL,
    description TEXT,
    icon_path TEXT,
    category TEXT,
    is_active BOOLEAN DEFAULT true,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT timezone('utc'::text, now()) NOT NULL
);

-- 2. Seed initial connector definitions
INSERT INTO public.connector_definitions (id, type, name, description, icon_path, category, is_active) VALUES
    ('a1b2c3d4-1111-4000-8000-000000000001', 'google_drive', 'Google Drive', 'Connect your Google Drive to import documents', '/icons/google-drive.svg', 'Cloud Storage', true),
    ('a1b2c3d4-2222-4000-8000-000000000002', 'notion', 'Notion', 'Import pages and databases from Notion', '/icons/notion.svg', 'Knowledge Base', true),
    ('a1b2c3d4-3333-4000-8000-000000000003', 'web', 'Web Scraper', 'Import content from any public URL', '/icons/web.svg', 'Web', true)
ON CONFLICT (type) DO NOTHING;

-- 3. Clear existing incompatible data from user_integrations
-- This is required because we're adding a NOT NULL FK
TRUNCATE TABLE public.user_integrations CASCADE;

-- 4. Add connector_definition_id column to user_integrations
ALTER TABLE public.user_integrations 
    ADD COLUMN IF NOT EXISTS connector_definition_id UUID;

-- 5. Add Foreign Key constraint
ALTER TABLE public.user_integrations
    DROP CONSTRAINT IF EXISTS fk_connector_definition;

ALTER TABLE public.user_integrations
    ADD CONSTRAINT fk_connector_definition 
    FOREIGN KEY (connector_definition_id) 
    REFERENCES public.connector_definitions(id) 
    ON DELETE CASCADE;

-- 6. Add unique constraint for upsert operations
-- This enables proper ON CONFLICT handling
ALTER TABLE public.user_integrations
    DROP CONSTRAINT IF EXISTS unique_user_connector;

ALTER TABLE public.user_integrations
    ADD CONSTRAINT unique_user_connector 
    UNIQUE (user_id, connector_definition_id);

-- 7. Drop old unique constraint that used provider text
ALTER TABLE public.user_integrations
    DROP CONSTRAINT IF EXISTS user_integrations_user_id_provider_key;

-- 8. Drop the old provider column (no longer needed)
ALTER TABLE public.user_integrations
    DROP COLUMN IF EXISTS provider;

-- 9. Make connector_definition_id NOT NULL after data cleanup
ALTER TABLE public.user_integrations
    ALTER COLUMN connector_definition_id SET NOT NULL;

-- 10. Add last_sync_at column if not exists
ALTER TABLE public.user_integrations
    ADD COLUMN IF NOT EXISTS last_sync_at TIMESTAMP WITH TIME ZONE;

-- 11. Enable RLS on connector_definitions (public read, admin write)
ALTER TABLE public.connector_definitions ENABLE ROW LEVEL SECURITY;

CREATE POLICY "Anyone can view active connectors" ON public.connector_definitions
    FOR SELECT USING (is_active = true);

-- 12. Create index for faster lookups
CREATE INDEX IF NOT EXISTS idx_connector_definitions_type 
    ON public.connector_definitions(type);

CREATE INDEX IF NOT EXISTS idx_user_integrations_connector_def 
    ON public.user_integrations(connector_definition_id);

-- Notify PostgREST to reload schema cache
NOTIFY pgrst, 'reload config';
