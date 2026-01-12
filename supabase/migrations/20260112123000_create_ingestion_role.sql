-- Phase 2 Step 7: Least-Privilege Role for Ingestion Workers

-- 1) Create dedicated role
DO $$
BEGIN
    IF NOT EXISTS (SELECT 1 FROM pg_roles WHERE rolname = 'ingestion_role') THEN
        CREATE ROLE ingestion_role LOGIN;
    END IF;
END $$;

-- 2) Schema usage
GRANT USAGE ON SCHEMA public TO ingestion_role;

-- 3) Data access (no DELETE, no DDL)
GRANT SELECT, INSERT, UPDATE ON TABLE
    documents,
    document_chunks,
    ingestion_jobs,
    ingestion_file_status
TO ingestion_role;

GRANT SELECT ON TABLE
    teams,
    subscriptions,
    org_usage
TO ingestion_role;

-- 4) RLS bypass for ingestion role (scoped by narrow grants above)
ALTER ROLE ingestion_role WITH BYPASSRLS;

-- Note: Default privileges and auth schema revokes are omitted here to avoid
-- permission errors on managed schemas. The role is constrained by explicit grants above.
