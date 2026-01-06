-- ============================================================
-- Migration: Fix Supabase Advisor Security & Performance Issues
-- Date: 2026-01-06
-- 
-- Fixes:
-- 1. ERROR: Enable RLS on failed_tasks table
-- 2. WARN: Fix function search_path for 5 functions
-- 3. WARN: Optimize RLS policies (auth.uid() -> (SELECT auth.uid()))
-- 4. WARN: Remove duplicate indexes
-- ============================================================

-- ============================================================
-- 1. CRITICAL: Enable RLS on failed_tasks
-- ============================================================
ALTER TABLE IF EXISTS public.failed_tasks ENABLE ROW LEVEL SECURITY;

-- Allow users to see their own failed tasks
DROP POLICY IF EXISTS "Users can view own failed tasks" ON public.failed_tasks;
CREATE POLICY "Users can view own failed tasks"
ON public.failed_tasks FOR SELECT
USING (user_id = (SELECT auth.uid()));

-- Allow users to update their own failed tasks (for retry/resolve)
DROP POLICY IF EXISTS "Users can update own failed tasks" ON public.failed_tasks;
CREATE POLICY "Users can update own failed tasks"
ON public.failed_tasks FOR UPDATE
USING (user_id = (SELECT auth.uid()));

-- Service role has full access (for backend operations)
DROP POLICY IF EXISTS "Service role full access to failed_tasks" ON public.failed_tasks;
CREATE POLICY "Service role full access to failed_tasks"
ON public.failed_tasks FOR ALL
USING (auth.role() = 'service_role');


-- ============================================================
-- 2. Fix Function Search Paths (Security)
-- ============================================================
DO $$
BEGIN
    ALTER FUNCTION public.get_effective_plan SET search_path = public;
EXCEPTION WHEN undefined_function THEN NULL;
END $$;

DO $$
BEGIN
    ALTER FUNCTION public.get_user_team_data SET search_path = public;
EXCEPTION WHEN undefined_function THEN NULL;
END $$;

DO $$
BEGIN
    ALTER FUNCTION public.recalculate_user_usage SET search_path = public;
EXCEPTION WHEN undefined_function THEN NULL;
END $$;

DO $$
BEGIN
    ALTER FUNCTION public.handle_new_user SET search_path = public;
EXCEPTION WHEN undefined_function THEN NULL;
END $$;

DO $$
BEGIN
    ALTER FUNCTION public.update_failed_tasks_updated_at SET search_path = public;
EXCEPTION WHEN undefined_function THEN NULL;
END $$;


-- ============================================================
-- 3. Remove Duplicate Indexes (Performance)
-- ============================================================

-- document_chunks: Keep document_chunks_document_id_idx
DROP INDEX IF EXISTS public.idx_document_chunks_doc_id;
DROP INDEX IF EXISTS public.idx_document_chunks_document_id;

-- documents: Keep documents_user_id_idx
DROP INDEX IF EXISTS public.idx_documents_user_id;

-- ingestion_file_status: Keep idx_file_status_job_id
DROP INDEX IF EXISTS public.idx_ingestion_file_status_job;

-- ingestion_jobs: Keep idx_ingestion_jobs_status
DROP INDEX IF EXISTS public.idx_ingestion_jobs_user_status;

-- team_members: Keep idx_team_members_member_user
DROP INDEX IF EXISTS public.idx_team_members_member_user_id;


-- ============================================================
-- 4. Optimize RLS Policies (Performance)
-- Replace auth.uid() with (SELECT auth.uid()) to prevent per-row re-evaluation
-- ============================================================

-- user_integrations policies
DROP POLICY IF EXISTS "Users can view own integrations" ON public.user_integrations;
CREATE POLICY "Users can view own integrations"
ON public.user_integrations FOR SELECT
USING (user_id = (SELECT auth.uid()));

DROP POLICY IF EXISTS "Users can insert own integrations" ON public.user_integrations;
CREATE POLICY "Users can insert own integrations"
ON public.user_integrations FOR INSERT
WITH CHECK (user_id = (SELECT auth.uid()));

DROP POLICY IF EXISTS "Users can update own integrations" ON public.user_integrations;
CREATE POLICY "Users can update own integrations"
ON public.user_integrations FOR UPDATE
USING (user_id = (SELECT auth.uid()));


-- conversations policies
DROP POLICY IF EXISTS "Users can view own conversations" ON public.conversations;
CREATE POLICY "Users can view own conversations"
ON public.conversations FOR SELECT
USING (user_id = (SELECT auth.uid()));

DROP POLICY IF EXISTS "Users can insert own conversations" ON public.conversations;
CREATE POLICY "Users can insert own conversations"
ON public.conversations FOR INSERT
WITH CHECK (user_id = (SELECT auth.uid()));

DROP POLICY IF EXISTS "Users can update own conversations" ON public.conversations;
CREATE POLICY "Users can update own conversations"
ON public.conversations FOR UPDATE
USING (user_id = (SELECT auth.uid()));

DROP POLICY IF EXISTS "Users can delete own conversations" ON public.conversations;
CREATE POLICY "Users can delete own conversations"
ON public.conversations FOR DELETE
USING (user_id = (SELECT auth.uid()));


-- messages policies
DROP POLICY IF EXISTS "Users can view messages in own conversations" ON public.messages;
CREATE POLICY "Users can view messages in own conversations"
ON public.messages FOR SELECT
USING (
    EXISTS (
        SELECT 1 FROM public.conversations c
        WHERE c.id = messages.conversation_id
        AND c.user_id = (SELECT auth.uid())
    )
);

DROP POLICY IF EXISTS "Users can insert messages in own conversations" ON public.messages;
CREATE POLICY "Users can insert messages in own conversations"
ON public.messages FOR INSERT
WITH CHECK (
    EXISTS (
        SELECT 1 FROM public.conversations c
        WHERE c.id = messages.conversation_id
        AND c.user_id = (SELECT auth.uid())
    )
);

DROP POLICY IF EXISTS "Users can delete messages in own conversations" ON public.messages;
CREATE POLICY "Users can delete messages in own conversations"
ON public.messages FOR DELETE
USING (
    EXISTS (
        SELECT 1 FROM public.conversations c
        WHERE c.id = messages.conversation_id
        AND c.user_id = (SELECT auth.uid())
    )
);


-- user_profiles policies
DROP POLICY IF EXISTS "Users can view own profile" ON public.user_profiles;
CREATE POLICY "Users can view own profile"
ON public.user_profiles FOR SELECT
USING (id = (SELECT auth.uid()));

DROP POLICY IF EXISTS "Users can insert own profile" ON public.user_profiles;
CREATE POLICY "Users can insert own profile"
ON public.user_profiles FOR INSERT
WITH CHECK (id = (SELECT auth.uid()));


-- user_notification_settings policies
DROP POLICY IF EXISTS "Users can view own notifications" ON public.user_notification_settings;
CREATE POLICY "Users can view own notifications"
ON public.user_notification_settings FOR SELECT
USING (user_id = (SELECT auth.uid()));

DROP POLICY IF EXISTS "Users can insert own notifications" ON public.user_notification_settings;
CREATE POLICY "Users can insert own notifications"
ON public.user_notification_settings FOR INSERT
WITH CHECK (user_id = (SELECT auth.uid()));

DROP POLICY IF EXISTS "Users can update own notifications" ON public.user_notification_settings;
CREATE POLICY "Users can update own notifications"
ON public.user_notification_settings FOR UPDATE
USING (user_id = (SELECT auth.uid()));

DROP POLICY IF EXISTS "Users can delete own notifications" ON public.user_notification_settings;
CREATE POLICY "Users can delete own notifications"
ON public.user_notification_settings FOR DELETE
USING (user_id = (SELECT auth.uid()));


-- sync_state policies (consolidate and optimize)
DROP POLICY IF EXISTS "Users can view own sync state" ON public.sync_state;
DROP POLICY IF EXISTS "Users can insert own sync state" ON public.sync_state;
DROP POLICY IF EXISTS "Users can update own sync state" ON public.sync_state;
DROP POLICY IF EXISTS "Service role full access to sync_state" ON public.sync_state;

CREATE POLICY "Users can view own sync state"
ON public.sync_state FOR SELECT
USING (user_id = (SELECT auth.uid()) OR (SELECT auth.role()) = 'service_role');

CREATE POLICY "Users can insert own sync state"
ON public.sync_state FOR INSERT
WITH CHECK (user_id = (SELECT auth.uid()) OR (SELECT auth.role()) = 'service_role');

CREATE POLICY "Users can update own sync state"
ON public.sync_state FOR UPDATE
USING (user_id = (SELECT auth.uid()) OR (SELECT auth.role()) = 'service_role');


-- ingestion_jobs policies
DROP POLICY IF EXISTS "Users can view their own jobs" ON public.ingestion_jobs;
CREATE POLICY "Users can view their own jobs"
ON public.ingestion_jobs FOR SELECT
USING (user_id = (SELECT auth.uid()));

DROP POLICY IF EXISTS "Users can update their own jobs" ON public.ingestion_jobs;
CREATE POLICY "Users can update their own jobs"
ON public.ingestion_jobs FOR UPDATE
USING (user_id = (SELECT auth.uid()));

DROP POLICY IF EXISTS "Users can insert jobs" ON public.ingestion_jobs;
CREATE POLICY "Users can insert jobs"
ON public.ingestion_jobs FOR INSERT
WITH CHECK (user_id = (SELECT auth.uid()));


-- notifications policies
DROP POLICY IF EXISTS "Users can view their own notifications" ON public.notifications;
CREATE POLICY "Users can view their own notifications"
ON public.notifications FOR SELECT
USING (user_id = (SELECT auth.uid()));

DROP POLICY IF EXISTS "Users can update their own notifications" ON public.notifications;
CREATE POLICY "Users can update their own notifications"
ON public.notifications FOR UPDATE
USING (user_id = (SELECT auth.uid()));

DROP POLICY IF EXISTS "Users can delete their own notifications" ON public.notifications;
CREATE POLICY "Users can delete their own notifications"
ON public.notifications FOR DELETE
USING (user_id = (SELECT auth.uid()));


-- web_crawl_configs policies (consolidate service role + user)
DROP POLICY IF EXISTS "Users can view their own crawl configs" ON public.web_crawl_configs;
DROP POLICY IF EXISTS "Users can create their own crawl configs" ON public.web_crawl_configs;
DROP POLICY IF EXISTS "Users can update their own crawl configs" ON public.web_crawl_configs;
DROP POLICY IF EXISTS "Users can delete their own crawl configs" ON public.web_crawl_configs;
DROP POLICY IF EXISTS "Service role has full access to crawl configs" ON public.web_crawl_configs;

CREATE POLICY "Users can view their own crawl configs"
ON public.web_crawl_configs FOR SELECT
USING (user_id = (SELECT auth.uid()) OR (SELECT auth.role()) = 'service_role');

CREATE POLICY "Users can create their own crawl configs"
ON public.web_crawl_configs FOR INSERT
WITH CHECK (user_id = (SELECT auth.uid()) OR (SELECT auth.role()) = 'service_role');

CREATE POLICY "Users can update their own crawl configs"
ON public.web_crawl_configs FOR UPDATE
USING (user_id = (SELECT auth.uid()) OR (SELECT auth.role()) = 'service_role');

CREATE POLICY "Users can delete their own crawl configs"
ON public.web_crawl_configs FOR DELETE
USING (user_id = (SELECT auth.uid()) OR (SELECT auth.role()) = 'service_role');


-- teams policies (consolidate owner + member)
DROP POLICY IF EXISTS "Owners can view own team" ON public.teams;
DROP POLICY IF EXISTS "Members can view team" ON public.teams;
DROP POLICY IF EXISTS "Owners can update own team" ON public.teams;

CREATE POLICY "Team access for owners and members"
ON public.teams FOR SELECT
USING (
    owner_id = (SELECT auth.uid())
    OR EXISTS (
        SELECT 1 FROM public.team_members tm
        WHERE tm.team_id = teams.id
        AND tm.member_user_id = (SELECT auth.uid())
    )
);

CREATE POLICY "Owners can update own team"
ON public.teams FOR UPDATE
USING (owner_id = (SELECT auth.uid()));


-- team_members policies (consolidate)
DROP POLICY IF EXISTS "Owners can view own team" ON public.team_members;
DROP POLICY IF EXISTS "Members can view teammates" ON public.team_members;
DROP POLICY IF EXISTS "Owners can insert team members" ON public.team_members;
DROP POLICY IF EXISTS "Owners can update team members" ON public.team_members;
DROP POLICY IF EXISTS "Owners can delete team members" ON public.team_members;

CREATE POLICY "Team members visibility"
ON public.team_members FOR SELECT
USING (
    EXISTS (
        SELECT 1 FROM public.teams t
        WHERE t.id = team_members.team_id
        AND (t.owner_id = (SELECT auth.uid()) OR team_members.member_user_id = (SELECT auth.uid()))
    )
);

CREATE POLICY "Owners can insert team members"
ON public.team_members FOR INSERT
WITH CHECK (
    EXISTS (
        SELECT 1 FROM public.teams t
        WHERE t.id = team_members.team_id
        AND t.owner_id = (SELECT auth.uid())
    )
);

CREATE POLICY "Owners can update team members"
ON public.team_members FOR UPDATE
USING (
    EXISTS (
        SELECT 1 FROM public.teams t
        WHERE t.id = team_members.team_id
        AND t.owner_id = (SELECT auth.uid())
    )
);

CREATE POLICY "Owners can delete team members"
ON public.team_members FOR DELETE
USING (
    EXISTS (
        SELECT 1 FROM public.teams t
        WHERE t.id = team_members.team_id
        AND t.owner_id = (SELECT auth.uid())
    )
);


-- documents policies
DROP POLICY IF EXISTS "Users can view own or team documents" ON public.documents;
CREATE POLICY "Users can view own or team documents"
ON public.documents FOR SELECT
USING (
    user_id = (SELECT auth.uid())
    OR EXISTS (
        SELECT 1 FROM public.team_members tm
        JOIN public.teams t ON t.id = tm.team_id
        WHERE tm.member_user_id = (SELECT auth.uid())
        AND t.owner_id = documents.user_id
    )
);


-- document_chunks policies
DROP POLICY IF EXISTS "Users can view chunks of allowed documents" ON public.document_chunks;
CREATE POLICY "Users can view chunks of allowed documents"
ON public.document_chunks FOR SELECT
USING (
    EXISTS (
        SELECT 1 FROM public.documents d
        WHERE d.id = document_chunks.document_id
        AND (
            d.user_id = (SELECT auth.uid())
            OR EXISTS (
                SELECT 1 FROM public.team_members tm
                JOIN public.teams t ON t.id = tm.team_id
                WHERE tm.member_user_id = (SELECT auth.uid())
                AND t.owner_id = d.user_id
            )
        )
    )
);


-- subscriptions policies
DROP POLICY IF EXISTS "Users can view team subscription" ON public.subscriptions;
CREATE POLICY "Users can view team subscription"
ON public.subscriptions FOR SELECT
USING (
    EXISTS (
        SELECT 1 FROM public.teams t
        WHERE t.id = subscriptions.team_id
        AND (
            t.owner_id = (SELECT auth.uid())
            OR EXISTS (
                SELECT 1 FROM public.team_members tm
                WHERE tm.team_id = t.id
                AND tm.member_user_id = (SELECT auth.uid())
            )
        )
    )
);


-- ingestion_file_status policies (consolidate)
DROP POLICY IF EXISTS "Users can view own file status" ON public.ingestion_file_status;
DROP POLICY IF EXISTS "Service role full access" ON public.ingestion_file_status;

CREATE POLICY "Users can view own file status"
ON public.ingestion_file_status FOR SELECT
USING (user_id = (SELECT auth.uid()) OR (SELECT auth.role()) = 'service_role');

CREATE POLICY "Service role can manage file status"
ON public.ingestion_file_status FOR ALL
USING ((SELECT auth.role()) = 'service_role');


-- ============================================================
-- Done! Re-run Supabase Advisor to verify fixes
-- ============================================================
