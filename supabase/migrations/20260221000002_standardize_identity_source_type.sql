-- =============================================================================
-- Migration: Standardize Identity Document source_type (ISSUE-003)
-- =============================================================================
--
-- PROBLEM:
-- Historical migrations created identity documents with inconsistent source_type:
-- - 20260201000000: Used 'scope_identity'
-- - 20260217120000: Used 'identity'
--
-- While hybrid_search excludes both values, the data inconsistency can cause:
-- - Confusion when debugging
-- - Potential issues with future filters
-- - Inconsistent UI display
--
-- SOLUTION:
-- Standardize ALL identity documents to use 'identity' as source_type.
-- This matches the latest migration convention.
-- =============================================================================

BEGIN;

-- ==========================================================================
-- Step 1: Count affected records (for logging)
-- ==========================================================================

DO $$
DECLARE
    v_scope_identity_count INTEGER;
    v_identity_count INTEGER;
BEGIN
    SELECT COUNT(*) INTO v_scope_identity_count
    FROM public.documents
    WHERE source_type = 'scope_identity';
    
    SELECT COUNT(*) INTO v_identity_count
    FROM public.documents
    WHERE source_type = 'identity';
    
    RAISE NOTICE '📊 Before migration:';
    RAISE NOTICE '   - Documents with source_type=scope_identity: %', v_scope_identity_count;
    RAISE NOTICE '   - Documents with source_type=identity: %', v_identity_count;
END $$;

-- ==========================================================================
-- Step 2: Standardize all 'scope_identity' to 'identity'
-- ==========================================================================

UPDATE public.documents 
SET source_type = 'identity',
    updated_at = NOW()
WHERE source_type = 'scope_identity';

-- ==========================================================================
-- Step 3: Verify standardization
-- ==========================================================================

DO $$
DECLARE
    v_remaining INTEGER;
    v_total_identity INTEGER;
BEGIN
    SELECT COUNT(*) INTO v_remaining
    FROM public.documents
    WHERE source_type = 'scope_identity';
    
    SELECT COUNT(*) INTO v_total_identity
    FROM public.documents
    WHERE source_type = 'identity';
    
    IF v_remaining > 0 THEN
        RAISE EXCEPTION 'ASSERTION FAILED: % documents still have scope_identity', v_remaining;
    END IF;
    
    RAISE NOTICE '✅ After migration:';
    RAISE NOTICE '   - Documents with source_type=scope_identity: 0';
    RAISE NOTICE '   - Documents with source_type=identity: %', v_total_identity;
END $$;

-- ==========================================================================
-- Step 4: Update upsert_scope_identity_document to always use 'identity'
-- ==========================================================================
-- This ensures future identity documents also use the standardized value.

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
            'identity',  -- STANDARDIZED: Always use 'identity', never 'scope_identity'
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
            source_type = 'identity',  -- STANDARDIZED: Always use 'identity'
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

-- Grant permissions
GRANT EXECUTE ON FUNCTION public.upsert_scope_identity_document(
    TEXT, UUID, UUID, TEXT, TEXT, TEXT, JSONB, TIMESTAMPTZ,
    TEXT, TEXT, JSONB, INT, TEXT, TEXT
) TO authenticated;

GRANT EXECUTE ON FUNCTION public.upsert_scope_identity_document(
    TEXT, UUID, UUID, TEXT, TEXT, TEXT, JSONB, TIMESTAMPTZ,
    TEXT, TEXT, JSONB, INT, TEXT, TEXT
) TO service_role;

-- ==========================================================================
-- Step 5: Add check constraint to prevent future inconsistencies (optional)
-- ==========================================================================
-- Note: This is commented out because it might break existing code that
-- uses other source_type values. Uncomment if you want strict enforcement.

-- ALTER TABLE public.documents
-- ADD CONSTRAINT check_identity_source_type
-- CHECK (
--     source_type NOT IN ('scope_identity')
--     OR source_type IS NULL
-- );

COMMENT ON FUNCTION public.upsert_scope_identity_document(
    TEXT, UUID, UUID, TEXT, TEXT, TEXT, JSONB, TIMESTAMPTZ,
    TEXT, TEXT, JSONB, INT, TEXT, TEXT
) IS 
'Upsert a scope identity and its corresponding identity document.

STANDARDIZED: Always uses source_type=''identity'' (never ''scope_identity'').
Fixed in 20260221000002 for data consistency.';

COMMIT;
