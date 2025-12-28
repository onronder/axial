-- Migration: Team Schema for Multi-User Teams
-- Phase 3.8 Step 4/7 - Team Data Architecture
-- Created: 2025-12-28
--
-- This migration creates the team infrastructure for:
-- 1. Teams table (organization/workspace container)
-- 2. Refactored team_members with proper FKs
-- 3. Auto-team creation trigger for new users
-- 4. RLS policies for team data access

-- ============================================================
-- TEAMS TABLE
-- ============================================================
-- Each user can own exactly one team (for MVP simplicity)
-- Team members inherit the owner's plan for feature access

CREATE TABLE IF NOT EXISTS teams (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    name TEXT NOT NULL,
    slug TEXT UNIQUE,  -- For future URLs like app.axiohub.com/acme-corp
    owner_id UUID NOT NULL REFERENCES auth.users(id) ON DELETE CASCADE,
    created_at TIMESTAMPTZ DEFAULT now(),
    updated_at TIMESTAMPTZ DEFAULT now(),
    
    -- Each user can own only one team (MVP constraint)
    CONSTRAINT unique_team_owner UNIQUE (owner_id)
);

-- Indexes for fast lookups
CREATE INDEX IF NOT EXISTS idx_teams_owner_id ON teams(owner_id);
CREATE INDEX IF NOT EXISTS idx_teams_slug ON teams(slug);

-- ============================================================
-- REFACTOR TEAM_MEMBERS TABLE
-- ============================================================
-- Add team_id FK and member_user_id for actual Supabase user linking

-- Add team_id column (links to teams table)
ALTER TABLE team_members 
ADD COLUMN IF NOT EXISTS team_id UUID REFERENCES teams(id) ON DELETE CASCADE;

-- Add member_user_id (links to auth.users when they accept invite)
ALTER TABLE team_members 
ADD COLUMN IF NOT EXISTS member_user_id UUID REFERENCES auth.users(id) ON DELETE SET NULL;

-- Add joined_at timestamp
ALTER TABLE team_members 
ADD COLUMN IF NOT EXISTS joined_at TIMESTAMPTZ;

-- Ensure role column has proper constraint
-- (may already exist, so use DO block)
DO $$ 
BEGIN
    -- Check if role check constraint exists
    IF NOT EXISTS (
        SELECT 1 FROM pg_constraint 
        WHERE conname = 'team_members_role_check'
    ) THEN
        ALTER TABLE team_members 
        ADD CONSTRAINT team_members_role_check 
        CHECK (role IN ('admin', 'editor', 'viewer'));
    END IF;
END $$;

-- Create index on team_id for efficient team queries
CREATE INDEX IF NOT EXISTS idx_team_members_team_id ON team_members(team_id);
CREATE INDEX IF NOT EXISTS idx_team_members_member_user_id ON team_members(member_user_id);

-- ============================================================
-- AUTO-TEAM CREATION TRIGGER
-- ============================================================
-- When a new user signs up, automatically create a personal team

CREATE OR REPLACE FUNCTION create_personal_team()
RETURNS TRIGGER
LANGUAGE plpgsql
SECURITY DEFINER
SET search_path = public
AS $$
DECLARE
    new_team_id UUID;
    user_email TEXT;
    team_name TEXT;
BEGIN
    -- Get user's email for team name
    user_email := NEW.email;
    team_name := COALESCE(
        split_part(user_email, '@', 1) || '''s Team',
        'Personal Team'
    );
    
    -- Create the team
    INSERT INTO teams (name, owner_id, created_at, updated_at)
    VALUES (team_name, NEW.id, now(), now())
    RETURNING id INTO new_team_id;
    
    -- Add user as admin member of their own team
    INSERT INTO team_members (
        team_id,
        owner_user_id,
        member_user_id,
        email,
        name,
        role,
        status,
        joined_at,
        created_at
    ) VALUES (
        new_team_id,
        NEW.id,  -- owner_user_id (backward compat)
        NEW.id,  -- member_user_id (actual user)
        user_email,
        split_part(user_email, '@', 1),
        'admin',
        'active',
        now(),
        now()
    );
    
    RETURN NEW;
END;
$$;

-- Create trigger on auth.users (only if not exists)
DROP TRIGGER IF EXISTS on_auth_user_created_create_team ON auth.users;

CREATE TRIGGER on_auth_user_created_create_team
    AFTER INSERT ON auth.users
    FOR EACH ROW
    EXECUTE FUNCTION create_personal_team();

-- ============================================================
-- ROW LEVEL SECURITY
-- ============================================================

ALTER TABLE teams ENABLE ROW LEVEL SECURITY;

-- Team owners can view/manage their team
CREATE POLICY "Owners can view own team" ON teams
    FOR SELECT USING (auth.uid() = owner_id);

CREATE POLICY "Owners can update own team" ON teams
    FOR UPDATE USING (auth.uid() = owner_id);

-- Team members can view their team (via team_members join)
CREATE POLICY "Members can view team" ON teams
    FOR SELECT USING (
        id IN (
            SELECT team_id FROM team_members 
            WHERE member_user_id = auth.uid()
        )
    );

-- Update team_members RLS to include team-based access
-- Members can view their teammates
DROP POLICY IF EXISTS "Members can view teammates" ON team_members;
CREATE POLICY "Members can view teammates" ON team_members
    FOR SELECT USING (
        team_id IN (
            SELECT team_id FROM team_members 
            WHERE member_user_id = auth.uid()
        )
    );

-- ============================================================
-- HELPER FUNCTION: Get effective plan for a user
-- ============================================================
-- Returns the team owner's plan (for inherited access)
-- Used as fallback when cache is cold

CREATE OR REPLACE FUNCTION get_effective_plan(target_user_id UUID)
RETURNS TEXT
LANGUAGE plpgsql
SECURITY DEFINER
STABLE
AS $$
DECLARE
    owner_plan TEXT;
    own_plan TEXT;
BEGIN
    -- Find the user's team and get the owner's plan
    SELECT up.plan INTO owner_plan
    FROM team_members tm
    JOIN teams t ON t.id = tm.team_id
    JOIN user_profiles up ON up.user_id = t.owner_id
    WHERE tm.member_user_id = target_user_id
    LIMIT 1;
    
    -- If found, return owner's plan
    IF owner_plan IS NOT NULL THEN
        RETURN owner_plan;
    END IF;
    
    -- Fallback: return user's own plan
    SELECT plan INTO own_plan
    FROM user_profiles
    WHERE user_id = target_user_id;
    
    RETURN COALESCE(own_plan, 'free');
END;
$$;

-- Grant execute to authenticated users and service role
GRANT EXECUTE ON FUNCTION get_effective_plan(UUID) TO authenticated;
GRANT EXECUTE ON FUNCTION get_effective_plan(UUID) TO service_role;

-- ============================================================
-- SERVICE ROLE GRANTS
-- ============================================================

GRANT ALL ON teams TO service_role;

-- ============================================================
-- MIGRATION FOR EXISTING USERS
-- ============================================================
-- Create teams for any existing users who don't have one

DO $$
DECLARE
    user_record RECORD;
    new_team_id UUID;
BEGIN
    -- Find users without teams
    FOR user_record IN 
        SELECT u.id, u.email 
        FROM auth.users u
        LEFT JOIN teams t ON t.owner_id = u.id
        WHERE t.id IS NULL
    LOOP
        -- Create team for this user
        INSERT INTO teams (name, owner_id, created_at, updated_at)
        VALUES (
            COALESCE(split_part(user_record.email, '@', 1) || '''s Team', 'Personal Team'),
            user_record.id,
            now(),
            now()
        )
        RETURNING id INTO new_team_id;
        
        -- Add as admin member
        INSERT INTO team_members (
            team_id, owner_user_id, member_user_id, 
            email, name, role, status, joined_at, created_at
        ) VALUES (
            new_team_id, user_record.id, user_record.id,
            user_record.email, split_part(user_record.email, '@', 1),
            'admin', 'active', now(), now()
        )
        ON CONFLICT DO NOTHING;  -- Skip if somehow already exists
    END LOOP;
END $$;

-- ============================================================
-- COMMENTS
-- ============================================================

COMMENT ON TABLE teams IS 'Organization/workspace container. Each user owns exactly one team.';
COMMENT ON COLUMN teams.slug IS 'URL-friendly identifier for future team URLs';
COMMENT ON COLUMN teams.owner_id IS 'User who owns this team - their plan determines team limits';
COMMENT ON COLUMN team_members.team_id IS 'FK to teams table';
COMMENT ON COLUMN team_members.member_user_id IS 'FK to auth.users when member accepts invite';
COMMENT ON FUNCTION create_personal_team IS 'Auto-creates personal team when user signs up';
COMMENT ON FUNCTION get_effective_plan IS 'Returns plan inherited from team owner';

-- Notify PostgREST to reload schema cache
NOTIFY pgrst, 'reload config';
