-- Migration: Restrict Document INSERT to service_role Only
-- =============================================================================
-- 
-- SECURITY FIX:
-- Prevents authenticated users from inserting documents directly via Supabase
-- client, forcing all inserts through the backend API where:
-- - Malware scanning (ClamAV) is enforced
-- - Quota limits are checked
-- - Ghost Protocol encryption is applied
-- - File processing pipeline is run
--
-- After this migration:
-- - SELECT: Org members can read
-- - INSERT: Only service_role (backend) can insert
-- - UPDATE: Org members can update
-- - DELETE: Org members can delete
-- =============================================================================

BEGIN;

-- Drop existing INSERT policy
DROP POLICY IF EXISTS "documents_org_insert" ON public.documents;

-- Create service_role-only INSERT policy
CREATE POLICY "documents_service_role_insert" ON public.documents
    FOR INSERT
    TO service_role
    WITH CHECK (true);

-- Add comment explaining the security model
COMMENT ON POLICY "documents_service_role_insert" ON public.documents IS 
'Security: Only the backend (service_role) can insert documents.
This ensures all documents go through the ingestion pipeline with:
- Malware scanning (ClamAV)
- Quota enforcement
- Ghost Protocol encryption
- Proper file processing

Authenticated users must use the /api/v1/uploads endpoint.';

NOTIFY pgrst, 'reload config';

COMMIT;
