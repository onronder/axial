-- Migration: Fix scope identity upsert signature + org purge guardrails

BEGIN;

-- ==========================================================================
-- Align upsert_scope_identity_document signature with backend
-- ==========================================================================

CREATE OR REPLACE FUNCTION public.upsert_scope_identity_document(
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
) RETURNS UUID
LANGUAGE plpgsql
SECURITY DEFINER
SET search_path = public
AS $$
DECLARE
    v_doc_id UUID;
    v_chunk_count INTEGER;
BEGIN
    -- Ensure a row exists so SELECT FOR UPDATE can lock it
    INSERT INTO public.scope_identities (
        organization_id,
        id,
        user_id,
        type,
        summary,
        file_tree,
        attributes,
        last_ingested_at,
        status,
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
        'completed',
        NOW(),
        NOW()
    )
    ON CONFLICT (organization_id, id) DO NOTHING;

    -- Row-level lock to serialize identity writes
    PERFORM 1
    FROM public.scope_identities
    WHERE organization_id = p_organization_id
      AND id = p_scope_id
    FOR UPDATE;

    -- Update with freshest identity data
    UPDATE public.scope_identities
    SET user_id = p_user_id,
        type = p_type,
        summary = p_summary,
        file_tree = p_file_tree,
        attributes = p_attributes,
        last_ingested_at = p_last_ingested_at,
        status = 'completed',
        updated_at = NOW()
    WHERE organization_id = p_organization_id
      AND id = p_scope_id;

    -- Upsert the identity document (lock existing row if present)
    SELECT id INTO v_doc_id
    FROM public.documents
    WHERE organization_id = p_organization_id
      AND source_id = p_source_id
    FOR UPDATE;

    IF v_doc_id IS NULL THEN
        INSERT INTO public.documents (
            user_id,
            organization_id,
            team_id,
            title,
            source_type,
            source_url,
            metadata,
            source_id,
            file_size_bytes,
            content_hash,
            created_at,
            updated_at,
            scope_id
        ) VALUES (
            p_user_id,
            p_organization_id,
            p_organization_id,
            p_doc_title,
            'identity',
            NULL,
            p_metadata,
            p_source_id,
            COALESCE(p_file_size_bytes, 0),
            md5(p_summary),
            NOW(),
            NOW(),
            p_scope_id
        )
        RETURNING id INTO v_doc_id;
    ELSE
        UPDATE public.documents
        SET user_id = p_user_id,
            organization_id = p_organization_id,
            team_id = p_organization_id,
            title = p_doc_title,
            source_type = 'identity',
            source_url = NULL,
            metadata = p_metadata,
            file_size_bytes = COALESCE(p_file_size_bytes, 0),
            content_hash = md5(p_summary),
            updated_at = NOW(),
            scope_id = p_scope_id
        WHERE id = v_doc_id;

        DELETE FROM public.document_chunks WHERE document_id = v_doc_id;
    END IF;

    -- Insert identity chunk
    INSERT INTO public.document_chunks (
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
$$;

GRANT EXECUTE ON FUNCTION public.upsert_scope_identity_document(
    TEXT, UUID, UUID, TEXT, TEXT, TEXT, JSONB, TIMESTAMPTZ,
    TEXT, TEXT, JSONB, INT, TEXT, TEXT
) TO authenticated;

GRANT EXECUTE ON FUNCTION public.upsert_scope_identity_document(
    TEXT, UUID, UUID, TEXT, TEXT, TEXT, JSONB, TIMESTAMPTZ,
    TEXT, TEXT, JSONB, INT, TEXT, TEXT
) TO service_role;

-- ==========================================================================
-- Fix: purge_organization (org-wide active job guard)
-- ==========================================================================

CREATE OR REPLACE FUNCTION public.purge_organization(p_organization_id UUID, p_owner_id UUID)
RETURNS JSONB
LANGUAGE plpgsql
SECURITY DEFINER
SET search_path = public
AS $$
DECLARE
    v_is_owner BOOLEAN;
    v_has_active_jobs BOOLEAN;
    v_deleted_chunks INTEGER;
    v_deleted_docs INTEGER;
    v_deleted_scopes INTEGER;
    v_deleted_jobs INTEGER;
BEGIN
    -- Verify ownership
    SELECT EXISTS (
        SELECT 1 FROM public.teams WHERE id = p_organization_id AND owner_id = p_owner_id
    ) INTO v_is_owner;

    IF NOT v_is_owner THEN
        RAISE EXCEPTION 'User is not the organization owner';
    END IF;

    -- Check for active ingestion jobs across the org
    SELECT EXISTS (
        SELECT 1 FROM public.ingestion_jobs
        WHERE organization_id = p_organization_id
          AND status IN ('pending', 'processing')
    ) INTO v_has_active_jobs;

    IF v_has_active_jobs THEN
        RAISE EXCEPTION 'active_ingestion_jobs';
    END IF;

    -- Delete in order (respecting FK constraints)
    DELETE FROM public.document_chunks
    WHERE document_id IN (
        SELECT id FROM public.documents WHERE organization_id = p_organization_id
    );
    GET DIAGNOSTICS v_deleted_chunks = ROW_COUNT;

    DELETE FROM public.documents WHERE organization_id = p_organization_id;
    GET DIAGNOSTICS v_deleted_docs = ROW_COUNT;

    DELETE FROM public.scope_identities WHERE organization_id = p_organization_id;
    GET DIAGNOSTICS v_deleted_scopes = ROW_COUNT;

    DELETE FROM public.ingestion_jobs WHERE organization_id = p_organization_id;
    GET DIAGNOSTICS v_deleted_jobs = ROW_COUNT;

    RETURN jsonb_build_object(
        'deleted_chunks', v_deleted_chunks,
        'deleted_documents', v_deleted_docs,
        'deleted_scopes', v_deleted_scopes,
        'deleted_jobs', v_deleted_jobs
    );
END;
$$;

GRANT EXECUTE ON FUNCTION public.purge_organization(UUID, UUID) TO service_role;

COMMIT;
