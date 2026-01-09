-- Fix RLS recursion between teams and team_members policies
-- Use SECURITY DEFINER helper functions to avoid policy cross-dependency

CREATE OR REPLACE FUNCTION public.is_team_owner(p_team_id uuid, p_user_id uuid)
RETURNS boolean
LANGUAGE sql
SECURITY DEFINER
SET search_path = public
AS $$
    SELECT EXISTS (
        SELECT 1 FROM public.teams t
        WHERE t.id = p_team_id
        AND t.owner_id = p_user_id
    );
$$;

CREATE OR REPLACE FUNCTION public.is_team_member(p_team_id uuid, p_user_id uuid)
RETURNS boolean
LANGUAGE sql
SECURITY DEFINER
SET search_path = public
AS $$
    SELECT EXISTS (
        SELECT 1 FROM public.team_members tm
        WHERE tm.team_id = p_team_id
        AND tm.member_user_id = p_user_id
    );
$$;

CREATE OR REPLACE FUNCTION public.is_team_member_of_owner(p_owner_id uuid, p_member_user_id uuid)
RETURNS boolean
LANGUAGE sql
SECURITY DEFINER
SET search_path = public
AS $$
    SELECT EXISTS (
        SELECT 1
        FROM public.teams t
        JOIN public.team_members tm ON tm.team_id = t.id
        WHERE t.owner_id = p_owner_id
        AND tm.member_user_id = p_member_user_id
    );
$$;

GRANT EXECUTE ON FUNCTION public.is_team_owner(uuid, uuid) TO authenticated;
GRANT EXECUTE ON FUNCTION public.is_team_owner(uuid, uuid) TO service_role;

GRANT EXECUTE ON FUNCTION public.is_team_member(uuid, uuid) TO authenticated;
GRANT EXECUTE ON FUNCTION public.is_team_member(uuid, uuid) TO service_role;

GRANT EXECUTE ON FUNCTION public.is_team_member_of_owner(uuid, uuid) TO authenticated;
GRANT EXECUTE ON FUNCTION public.is_team_member_of_owner(uuid, uuid) TO service_role;

-- Teams policy: owners or members can view team
DROP POLICY IF EXISTS "Team access for owners and members" ON public.teams;
CREATE POLICY "Team access for owners and members"
ON public.teams FOR SELECT
USING (
    owner_id = (SELECT auth.uid())
    OR public.is_team_member(teams.id, (SELECT auth.uid()))
);

-- Team members policies: owner or member access without recursion
DROP POLICY IF EXISTS "Team members visibility" ON public.team_members;
CREATE POLICY "Team members visibility"
ON public.team_members FOR SELECT
USING (
    team_members.member_user_id = (SELECT auth.uid())
    OR public.is_team_owner(team_members.team_id, (SELECT auth.uid()))
);

DROP POLICY IF EXISTS "Owners can insert team members" ON public.team_members;
CREATE POLICY "Owners can insert team members"
ON public.team_members FOR INSERT
WITH CHECK (
    public.is_team_owner(team_members.team_id, (SELECT auth.uid()))
);

DROP POLICY IF EXISTS "Owners can update team members" ON public.team_members;
CREATE POLICY "Owners can update team members"
ON public.team_members FOR UPDATE
USING (
    public.is_team_owner(team_members.team_id, (SELECT auth.uid()))
);

DROP POLICY IF EXISTS "Owners can delete team members" ON public.team_members;
CREATE POLICY "Owners can delete team members"
ON public.team_members FOR DELETE
USING (
    public.is_team_owner(team_members.team_id, (SELECT auth.uid()))
);

-- Documents policy: allow owner or team member of owner
DROP POLICY IF EXISTS "Users can view own or team documents" ON public.documents;
CREATE POLICY "Users can view own or team documents"
ON public.documents FOR SELECT
USING (
    user_id = (SELECT auth.uid())
    OR public.is_team_member_of_owner(documents.user_id, (SELECT auth.uid()))
);

-- Document chunks policy: inherit document access without recursion
DROP POLICY IF EXISTS "Users can view chunks of allowed documents" ON public.document_chunks;
CREATE POLICY "Users can view chunks of allowed documents"
ON public.document_chunks FOR SELECT
USING (
    EXISTS (
        SELECT 1 FROM public.documents d
        WHERE d.id = document_chunks.document_id
        AND (
            d.user_id = (SELECT auth.uid())
            OR public.is_team_member_of_owner(d.user_id, (SELECT auth.uid()))
        )
    )
);

NOTIFY pgrst, 'reload config';
