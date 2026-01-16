-- ============================================================
-- ARTIFACT 4: "Nuclear" Cleanup Script
-- ============================================================
-- Purpose: Remove ALL test data for a specific user
-- Usage: Run in Supabase SQL Editor (with service role)
--
-- IMPORTANT: Replace 'admin@axial-test.com' with your actual test user email
-- 
-- CASCADE behavior will automatically delete:
--   - documents (via team_id FK)
--   - document_chunks (via document_id FK)
--   - ingestion_jobs (via user_id FK)
--   - conversations (via user_id FK)
--   - messages (via conversation_id FK)
--   - scope_identities (via organization_id FK)
--   - subscriptions (via team_id FK)
--   - team_members (via team_id FK)
-- ============================================================

DO $$
DECLARE
    v_user_email TEXT := 'o.onder@fittechs.com';  -- <<< CHANGE THIS
    v_user_id UUID;
    v_team_id UUID;
    v_doc_count INT;
    v_chunk_count INT;
    v_job_count INT;
    v_conv_count INT;
    v_scope_count INT;
BEGIN
    -- Step 1: Get user_id
    SELECT id INTO v_user_id
    FROM auth.users
    WHERE email = v_user_email;
    
    IF v_user_id IS NULL THEN
        RAISE NOTICE '⚠️ User not found: %. Nothing to clean up.', v_user_email;
        RETURN;
    END IF;
    
    RAISE NOTICE 'Found user: % (ID: %)', v_user_email, v_user_id;
    
    -- Step 2: Get team_id
    SELECT id INTO v_team_id
    FROM public.teams
    WHERE owner_id = v_user_id;
    
    IF v_team_id IS NULL THEN
        RAISE NOTICE '⚠️ Team not found for user. Skipping team-related cleanup.';
    ELSE
        RAISE NOTICE 'Found team: %', v_team_id;
    END IF;
    
    -- Step 3: Count existing data for reporting
    SELECT COUNT(*) INTO v_doc_count
    FROM public.documents
    WHERE user_id = v_user_id OR organization_id = v_team_id;
    
    SELECT COUNT(*) INTO v_chunk_count
    FROM public.document_chunks dc
    JOIN public.documents d ON dc.document_id = d.id
    WHERE d.user_id = v_user_id OR d.organization_id = v_team_id;
    
    SELECT COUNT(*) INTO v_job_count
    FROM public.ingestion_jobs
    WHERE user_id = v_user_id OR organization_id = v_team_id;
    
    SELECT COUNT(*) INTO v_conv_count
    FROM public.conversations
    WHERE user_id = v_user_id OR organization_id = v_team_id;
    
    SELECT COUNT(*) INTO v_scope_count
    FROM public.scope_identities
    WHERE organization_id = v_team_id OR user_id = v_user_id;
    
    RAISE NOTICE '';
    RAISE NOTICE '📊 Data to be deleted:';
    RAISE NOTICE '   Documents: %', v_doc_count;
    RAISE NOTICE '   Chunks: %', v_chunk_count;
    RAISE NOTICE '   Ingestion Jobs: %', v_job_count;
    RAISE NOTICE '   Conversations: %', v_conv_count;
    RAISE NOTICE '   Scope Identities: %', v_scope_count;
    RAISE NOTICE '';
    
    -- Step 4: Delete scope_identities first (no FK to cascade from)
    DELETE FROM public.scope_identities
    WHERE organization_id = v_team_id OR user_id = v_user_id;
    RAISE NOTICE '🗑️ Deleted scope_identities';
    
    -- Step 5: Delete ingestion_file_status
    DELETE FROM public.ingestion_file_status
    WHERE user_id = v_user_id;
    RAISE NOTICE '🗑️ Deleted ingestion_file_status';
    
    -- Step 6: Delete notifications
    DELETE FROM public.notifications
    WHERE user_id = v_user_id;
    RAISE NOTICE '🗑️ Deleted notifications';
    
    -- Step 7: Delete messages (via conversations)
    DELETE FROM public.messages
    WHERE conversation_id IN (
        SELECT id FROM public.conversations
        WHERE user_id = v_user_id OR organization_id = v_team_id
    );
    RAISE NOTICE '🗑️ Deleted messages';
    
    -- Step 8: Delete conversations
    DELETE FROM public.conversations
    WHERE user_id = v_user_id OR organization_id = v_team_id;
    RAISE NOTICE '🗑️ Deleted conversations';
    
    -- Step 9: Delete document_chunks (via documents)
    DELETE FROM public.document_chunks
    WHERE document_id IN (
        SELECT id FROM public.documents
        WHERE user_id = v_user_id OR organization_id = v_team_id
    );
    RAISE NOTICE '🗑️ Deleted document_chunks';
    
    -- Step 10: Delete documents
    DELETE FROM public.documents
    WHERE user_id = v_user_id OR organization_id = v_team_id;
    RAISE NOTICE '🗑️ Deleted documents';
    
    -- Step 11: Delete ingestion_jobs
    DELETE FROM public.ingestion_jobs
    WHERE user_id = v_user_id OR organization_id = v_team_id;
    RAISE NOTICE '🗑️ Deleted ingestion_jobs';
    
    -- Step 12: Delete web_crawl_configs
    DELETE FROM public.web_crawl_configs
    WHERE user_id = v_user_id;
    RAISE NOTICE '🗑️ Deleted web_crawl_configs';
    
    -- Step 13: Delete user_integrations
    DELETE FROM public.user_integrations
    WHERE user_id = v_user_id;
    RAISE NOTICE '🗑️ Deleted user_integrations';
    
    -- Step 14: Delete subscriptions (if team exists)
    IF v_team_id IS NOT NULL THEN
        DELETE FROM public.subscriptions
        WHERE team_id = v_team_id;
        RAISE NOTICE '🗑️ Deleted subscriptions';
    END IF;
    
    -- Step 15: Delete team_members
    DELETE FROM public.team_members
    WHERE team_id = v_team_id OR member_user_id = v_user_id;
    RAISE NOTICE '🗑️ Deleted team_members';
    
    -- Step 16: Delete team (if exists)
    IF v_team_id IS NOT NULL THEN
        DELETE FROM public.teams
        WHERE id = v_team_id;
        RAISE NOTICE '🗑️ Deleted team';
    END IF;
    
    -- Step 17: Delete user_profiles
    DELETE FROM public.user_profiles
    WHERE user_id = v_user_id;
    RAISE NOTICE '🗑️ Deleted user_profiles';
    
    -- Step 18: Delete audit_logs
    DELETE FROM public.audit_logs
    WHERE user_id = v_user_id;
    RAISE NOTICE '🗑️ Deleted audit_logs';
    
    RAISE NOTICE '';
    RAISE NOTICE '✅ CLEANUP COMPLETE for user: %', v_user_email;
    RAISE NOTICE '';
    RAISE NOTICE '⚠️ NOTE: The auth.users record was NOT deleted.';
    RAISE NOTICE '   To fully remove the user, run:';
    RAISE NOTICE '   DELETE FROM auth.users WHERE id = ''%'';', v_user_id;
END $$;

-- ============================================================
-- VERIFICATION: Confirm all data is gone
-- ============================================================

-- Replace email below to match your test user
DO $$
DECLARE
    v_user_email TEXT := 'o.onder@fittechs.com';  -- <<< CHANGE THIS
    v_user_id UUID;
    v_team_id UUID;
    v_remaining_docs INT;
    v_remaining_chunks INT;
    v_remaining_jobs INT;
    v_remaining_convs INT;
    v_remaining_scopes INT;
BEGIN
    SELECT id INTO v_user_id FROM auth.users WHERE email = v_user_email;
    SELECT id INTO v_team_id FROM public.teams WHERE owner_id = v_user_id;
    
    SELECT COUNT(*) INTO v_remaining_docs
    FROM public.documents WHERE user_id = v_user_id OR organization_id = v_team_id;
    
    SELECT COUNT(*) INTO v_remaining_chunks
    FROM public.document_chunks dc
    JOIN public.documents d ON dc.document_id = d.id
    WHERE d.user_id = v_user_id;
    
    SELECT COUNT(*) INTO v_remaining_jobs
    FROM public.ingestion_jobs WHERE user_id = v_user_id;
    
    SELECT COUNT(*) INTO v_remaining_convs
    FROM public.conversations WHERE user_id = v_user_id;
    
    SELECT COUNT(*) INTO v_remaining_scopes
    FROM public.scope_identities WHERE user_id = v_user_id;
    
    RAISE NOTICE '';
    RAISE NOTICE '🔍 VERIFICATION RESULTS:';
    RAISE NOTICE '   Remaining Documents: % (should be 0)', COALESCE(v_remaining_docs, 0);
    RAISE NOTICE '   Remaining Chunks: % (should be 0)', COALESCE(v_remaining_chunks, 0);
    RAISE NOTICE '   Remaining Jobs: % (should be 0)', COALESCE(v_remaining_jobs, 0);
    RAISE NOTICE '   Remaining Conversations: % (should be 0)', COALESCE(v_remaining_convs, 0);
    RAISE NOTICE '   Remaining Scope Identities: % (should be 0)', COALESCE(v_remaining_scopes, 0);
    
    IF COALESCE(v_remaining_docs, 0) = 0 
       AND COALESCE(v_remaining_chunks, 0) = 0 
       AND COALESCE(v_remaining_jobs, 0) = 0 
       AND COALESCE(v_remaining_convs, 0) = 0 
       AND COALESCE(v_remaining_scopes, 0) = 0 THEN
        RAISE NOTICE '';
        RAISE NOTICE '✅ ALL DATA SUCCESSFULLY REMOVED!';
    ELSE
        RAISE NOTICE '';
        RAISE NOTICE '⚠️ WARNING: Some data may remain. Check the counts above.';
    END IF;
END $$;
