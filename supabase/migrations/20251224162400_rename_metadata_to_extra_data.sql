-- Migration: Rename metadata to extra_data in notifications table
-- This fixes SQLModel compatibility issue where 'metadata' shadows a parent attribute
-- and Dict type has no direct SQLAlchemy mapping

-- Step 1: Add new column
ALTER TABLE notifications 
ADD COLUMN IF NOT EXISTS extra_data TEXT;

-- Step 2: Migrate existing data (convert JSONB to TEXT)
UPDATE notifications 
SET extra_data = metadata::text 
WHERE metadata IS NOT NULL AND extra_data IS NULL;

-- Step 3: Drop the old column
ALTER TABLE notifications 
DROP COLUMN IF EXISTS metadata;

-- Add comment explaining the change
COMMENT ON COLUMN notifications.extra_data IS 'JSON string containing additional notification metadata. Renamed from metadata to avoid SQLModel attribute shadowing.';
