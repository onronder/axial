-- Migration: Add indexing_status to documents
-- Timestamp: 20251230220000

-- Create enum type if not exists
DO $$ BEGIN
    CREATE TYPE indexing_status_enum AS ENUM ('pending', 'processing', 'completed', 'failed');
EXCEPTION
    WHEN duplicate_object THEN null;
END $$;

-- Add column to documents table
ALTER TABLE documents 
ADD COLUMN IF NOT EXISTS indexing_status indexing_status_enum DEFAULT 'pending';

-- Add index for status filtering
CREATE INDEX IF NOT EXISTS idx_documents_indexing_status ON documents(indexing_status);
