-- Add user_id and source columns
ALTER TABLE documents 
ADD COLUMN IF NOT EXISTS user_id uuid,
ADD COLUMN IF NOT EXISTS source_type text DEFAULT 'file';

-- Index for performance
CREATE INDEX IF NOT EXISTS idx_documents_user_id ON documents(user_id);

-- Enable Row Level Security (RLS)
ALTER TABLE documents ENABLE ROW LEVEL SECURITY;

-- Policy: Users can only select their own data
CREATE POLICY "Users can select own documents" ON documents
FOR SELECT USING (auth.uid() = user_id);

-- Policy: Users can insert their own data
CREATE POLICY "Users can insert own documents" ON documents
FOR INSERT WITH CHECK (auth.uid() = user_id);
