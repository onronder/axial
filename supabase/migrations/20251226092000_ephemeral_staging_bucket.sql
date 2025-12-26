-- Migration: Create ephemeral-staging bucket for zero-copy file processing
-- Created: 2025-12-26
-- Purpose: Secure temporary storage for uploaded files

-- Create the ephemeral staging bucket
INSERT INTO storage.buckets (id, name, public, file_size_limit, allowed_mime_types)
VALUES (
    'ephemeral-staging',
    'ephemeral-staging',
    false,  -- Private bucket
    52428800,  -- 50MB limit
    ARRAY['application/pdf', 'application/vnd.openxmlformats-officedocument.wordprocessingml.document', 'text/plain', 'text/markdown', 'text/html', 'application/octet-stream']
) ON CONFLICT (id) DO NOTHING;

-- RLS Policies for ephemeral-staging bucket

-- Allow authenticated users to upload to their own folder
CREATE POLICY "Users can upload to their folder"
ON storage.objects FOR INSERT
TO authenticated
WITH CHECK (
    bucket_id = 'ephemeral-staging' AND
    (storage.foldername(name))[1] = auth.uid()::text
);

-- Allow authenticated users to read their own files
CREATE POLICY "Users can read their own files"
ON storage.objects FOR SELECT
TO authenticated
USING (
    bucket_id = 'ephemeral-staging' AND
    (storage.foldername(name))[1] = auth.uid()::text
);

-- Allow service role full access (for worker cleanup)
CREATE POLICY "Service role full access to staging"
ON storage.objects FOR ALL
TO service_role
USING (bucket_id = 'ephemeral-staging')
WITH CHECK (bucket_id = 'ephemeral-staging');

-- Refresh schema cache
NOTIFY pgrst, 'reload config';
