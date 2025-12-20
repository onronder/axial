-- =============================================================================
-- Sync State Table for Incremental Sync
-- =============================================================================
-- Tracks the last sync time and cursor for each integration to enable
-- incremental syncing instead of full re-sync.
-- =============================================================================

-- Create sync_state table
CREATE TABLE IF NOT EXISTS sync_state (
    id UUID DEFAULT gen_random_uuid() PRIMARY KEY,
    user_id UUID NOT NULL REFERENCES auth.users(id) ON DELETE CASCADE,
    provider TEXT NOT NULL,  -- 'google_drive', 'notion', etc.
    folder_id TEXT,          -- Optional: specific folder being synced
    
    -- Sync tracking
    last_sync_at TIMESTAMPTZ,
    next_page_token TEXT,    -- For Google Drive pagination
    last_cursor TEXT,        -- For Notion/other APIs
    
    -- Sync metadata
    items_synced INTEGER DEFAULT 0,
    sync_status TEXT DEFAULT 'idle',  -- 'idle', 'in_progress', 'completed', 'failed'
    error_message TEXT,
    
    -- Timestamps
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW(),
    
    -- Unique constraint per user/provider/folder
    UNIQUE(user_id, provider, folder_id)
);

-- Create index for efficient lookups
CREATE INDEX IF NOT EXISTS idx_sync_state_user_provider 
ON sync_state(user_id, provider);

-- RLS Policies
ALTER TABLE sync_state ENABLE ROW LEVEL SECURITY;

-- Users can only see their own sync state
CREATE POLICY "Users can view own sync state" ON sync_state
    FOR SELECT USING (auth.uid() = user_id);

CREATE POLICY "Users can insert own sync state" ON sync_state
    FOR INSERT WITH CHECK (auth.uid() = user_id);

CREATE POLICY "Users can update own sync state" ON sync_state
    FOR UPDATE USING (auth.uid() = user_id);

-- Service role can manage all sync states
CREATE POLICY "Service role full access to sync_state" ON sync_state
    FOR ALL USING (auth.jwt() ->> 'role' = 'service_role');

-- Function to update the updated_at timestamp
CREATE OR REPLACE FUNCTION update_sync_state_timestamp()
RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_at = NOW();
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

-- Trigger for automatic timestamp update
DROP TRIGGER IF EXISTS sync_state_updated_at ON sync_state;
CREATE TRIGGER sync_state_updated_at
    BEFORE UPDATE ON sync_state
    FOR EACH ROW
    EXECUTE FUNCTION update_sync_state_timestamp();

-- Grant permissions
GRANT SELECT, INSERT, UPDATE ON sync_state TO authenticated;
GRANT ALL ON sync_state TO service_role;
