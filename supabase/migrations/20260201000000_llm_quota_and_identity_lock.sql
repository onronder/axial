-- Migration: LLM quota tracking + scope identity locking + transactional org purge

-- 1) Add LLM quota tracking fields
ALTER TABLE public.org_usage
    ADD COLUMN IF NOT EXISTS llm_tokens_used BIGINT NOT NULL DEFAULT 0;

ALTER TABLE public.teams
    ADD COLUMN IF NOT EXISTS llm_token_balance BIGINT;

COMMENT ON COLUMN public.org_usage.llm_tokens_used IS
    'Total LLM tokens consumed by the org (all providers)';

COMMENT ON COLUMN public.teams.llm_token_balance IS
    'Optional prepaid LLM token balance for the org (overrides plan limit when set)';

-- 2) Locked upsert for scope identity + identity document (prevents duplicate writes)
CREATE OR REPLACE FUNCTION upsert_scope_identity_document(
    p_scope_id TEXT,
    p_organization_id UUID,
    p_user_id UUID,
    p_type TEXT,
    p_summary TEXT,
    p_file_tree TEXT,
    p_attributes JSONB,
    p_last_ingested_at TIMESTAMPTZ,
    p_doc_title TEXT,
    p_source_id TEXT,
    p_metadata JSONB,
    p_file_size_bytes INT,
    p_chunk_content TEXT,
    p_chunk_embedding TEXT
) RETURNS UUID AS $$
DECLARE
    v_doc_id UUID;
BEGIN
    -- Ensure a row exists so SELECT FOR UPDATE can lock it
    INSERT INTO scope_identities (
        organization_id,
        id,
        user_id,
        type,
        summary,
        file_tree,
        attributes,
        last_ingested_at,
        created_at,
        updated_at
    ) VALUES (
        p_organization_id,
        p_scope_id,
        p_user_id,
        p_type,
        p_summary,
        p_file_tree,
        p_attributes,
        p_last_ingested_at,
        NOW(),
        NOW()
    )
    ON CONFLICT (organization_id, id) DO NOTHING;

    -- Row-level lock to serialize identity writes
    PERFORM 1
    FROM scope_identities
    WHERE organization_id = p_organization_id
      AND id = p_scope_id
    FOR UPDATE;

    -- Update with freshest identity data
    UPDATE scope_identities
    SET user_id = p_user_id,
        type = p_type,
        summary = p_summary,
        file_tree = p_file_tree,
        attributes = p_attributes,
        last_ingested_at = p_last_ingested_at,
        updated_at = NOW()
    WHERE organization_id = p_organization_id
      AND id = p_scope_id;

    -- Upsert the identity document (lock existing row if present)
    SELECT id INTO v_doc_id
    FROM documents
    WHERE organization_id = p_organization_id
      AND source_id = p_source_id
    FOR UPDATE;

    IF v_doc_id IS NULL THEN
        INSERT INTO documents (
            user_id,
            organization_id,
            team_id,
            title,
            source_type,
            source_url,
            metadata,
            source_id,
            file_size_bytes,
            created_at,
            updated_at,
            scope_id
        ) VALUES (
            p_user_id,
            p_organization_id,
            p_organization_id,
            p_doc_title,
            'scope_identity',
            NULL,
            p_metadata,
            p_source_id,
            p_file_size_bytes,
            NOW(),
            NOW(),
            p_scope_id
        )
        RETURNING id INTO v_doc_id;
    ELSE
        UPDATE documents
        SET user_id = p_user_id,
            team_id = p_organization_id,
            title = p_doc_title,
            source_type = 'scope_identity',
            source_url = NULL,
            metadata = p_metadata,
            file_size_bytes = p_file_size_bytes,
            updated_at = NOW(),
            scope_id = p_scope_id
        WHERE id = v_doc_id;

        DELETE FROM document_chunks WHERE document_id = v_doc_id;
    END IF;

    -- Insert identity chunk
    INSERT INTO document_chunks (
        document_id,
        content,
        embedding,
        chunk_index,
        created_at
    ) VALUES (
        v_doc_id,
        p_chunk_content,
        CASE
            WHEN p_chunk_embedding IS NULL OR length(p_chunk_embedding) = 0 THEN NULL
            ELSE p_chunk_embedding::vector
        END,
        0,
        NOW()
    );

    RETURN v_doc_id;
END;
$$ LANGUAGE plpgsql SECURITY DEFINER;

GRANT EXECUTE ON FUNCTION upsert_scope_identity_document TO authenticated;
GRANT EXECUTE ON FUNCTION upsert_scope_identity_document TO service_role;

-- 3) Transactional org purge with ingestion guardrail
CREATE OR REPLACE FUNCTION purge_organization(
    p_org_id UUID
) RETURNS JSONB AS $$
DECLARE
    v_active_jobs INT := 0;
    v_deleted_chunks INT := 0;
    v_deleted_docs INT := 0;
    v_deleted_scopes INT := 0;
    v_deleted_jobs INT := 0;
BEGIN
    SELECT COUNT(*)
    INTO v_active_jobs
    FROM ingestion_jobs
    WHERE organization_id = p_org_id
      AND status IN ('pending', 'processing');

    IF v_active_jobs > 0 THEN
        RAISE EXCEPTION 'active_ingestion_jobs' USING ERRCODE = 'P0001';
    END IF;

    DELETE FROM document_chunks dc
    USING documents d
    WHERE dc.document_id = d.id
      AND d.organization_id = p_org_id;
    GET DIAGNOSTICS v_deleted_chunks = ROW_COUNT;

    DELETE FROM documents
    WHERE organization_id = p_org_id;
    GET DIAGNOSTICS v_deleted_docs = ROW_COUNT;

    DELETE FROM scope_identities
    WHERE organization_id = p_org_id;
    GET DIAGNOSTICS v_deleted_scopes = ROW_COUNT;

    DELETE FROM ingestion_jobs
    WHERE organization_id = p_org_id;
    GET DIAGNOSTICS v_deleted_jobs = ROW_COUNT;

    DELETE FROM org_usage
    WHERE org_id = p_org_id;

    RETURN jsonb_build_object(
        'organization_id', p_org_id,
        'deleted_chunks', v_deleted_chunks,
        'deleted_documents', v_deleted_docs,
        'deleted_scopes', v_deleted_scopes,
        'deleted_jobs', v_deleted_jobs
    );
END;
$$ LANGUAGE plpgsql SECURITY DEFINER;

GRANT EXECUTE ON FUNCTION purge_organization TO authenticated;
GRANT EXECUTE ON FUNCTION purge_organization TO service_role;
