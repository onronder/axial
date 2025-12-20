-- Migration: Settings Schema for User Profiles, Notifications, and Team Management
-- Created: 2025-12-20

-- ============================================================
-- USER PROFILES TABLE
-- ============================================================
CREATE TABLE IF NOT EXISTS user_profiles (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id UUID NOT NULL REFERENCES auth.users(id) ON DELETE CASCADE UNIQUE,
    first_name TEXT,
    last_name TEXT,
    plan TEXT DEFAULT 'free' CHECK (plan IN ('free', 'pro', 'enterprise')),
    theme TEXT DEFAULT 'system' CHECK (theme IN ('light', 'dark', 'system')),
    created_at TIMESTAMPTZ DEFAULT now(),
    updated_at TIMESTAMPTZ DEFAULT now()
);

-- Index for fast user lookups
CREATE INDEX IF NOT EXISTS idx_user_profiles_user_id ON user_profiles(user_id);

-- ============================================================
-- USER NOTIFICATION SETTINGS TABLE
-- ============================================================
CREATE TABLE IF NOT EXISTS user_notification_settings (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id UUID NOT NULL REFERENCES auth.users(id) ON DELETE CASCADE,
    setting_key TEXT NOT NULL,
    setting_label TEXT NOT NULL,
    setting_description TEXT,
    category TEXT DEFAULT 'email' CHECK (category IN ('email', 'system')),
    enabled BOOLEAN DEFAULT true,
    created_at TIMESTAMPTZ DEFAULT now(),
    updated_at TIMESTAMPTZ DEFAULT now(),
    UNIQUE(user_id, setting_key)
);

-- Index for fast user lookups
CREATE INDEX IF NOT EXISTS idx_user_notification_settings_user_id ON user_notification_settings(user_id);

-- ============================================================
-- TEAM MEMBERS TABLE
-- ============================================================
CREATE TABLE IF NOT EXISTS team_members (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    owner_user_id UUID NOT NULL REFERENCES auth.users(id) ON DELETE CASCADE,
    email TEXT NOT NULL,
    name TEXT,
    role TEXT DEFAULT 'viewer' CHECK (role IN ('admin', 'editor', 'viewer')),
    status TEXT DEFAULT 'pending' CHECK (status IN ('active', 'pending', 'suspended')),
    last_active TIMESTAMPTZ,
    created_at TIMESTAMPTZ DEFAULT now(),
    invited_at TIMESTAMPTZ DEFAULT now()
);

-- Indexes
CREATE INDEX IF NOT EXISTS idx_team_members_owner_user_id ON team_members(owner_user_id);
CREATE INDEX IF NOT EXISTS idx_team_members_email ON team_members(email);

-- ============================================================
-- ROW LEVEL SECURITY
-- ============================================================
ALTER TABLE user_profiles ENABLE ROW LEVEL SECURITY;
ALTER TABLE user_notification_settings ENABLE ROW LEVEL SECURITY;
ALTER TABLE team_members ENABLE ROW LEVEL SECURITY;

-- User Profiles: Users can only access their own profile
CREATE POLICY "Users can view own profile" ON user_profiles
    FOR SELECT USING (auth.uid() = user_id);

CREATE POLICY "Users can insert own profile" ON user_profiles
    FOR INSERT WITH CHECK (auth.uid() = user_id);

CREATE POLICY "Users can update own profile" ON user_profiles
    FOR UPDATE USING (auth.uid() = user_id);

-- Notification Settings: Users can only access their own settings
CREATE POLICY "Users can view own notifications" ON user_notification_settings
    FOR SELECT USING (auth.uid() = user_id);

CREATE POLICY "Users can insert own notifications" ON user_notification_settings
    FOR INSERT WITH CHECK (auth.uid() = user_id);

CREATE POLICY "Users can update own notifications" ON user_notification_settings
    FOR UPDATE USING (auth.uid() = user_id);

CREATE POLICY "Users can delete own notifications" ON user_notification_settings
    FOR DELETE USING (auth.uid() = user_id);

-- Team Members: Owners can manage their team
CREATE POLICY "Owners can view own team" ON team_members
    FOR SELECT USING (auth.uid() = owner_user_id);

CREATE POLICY "Owners can insert team members" ON team_members
    FOR INSERT WITH CHECK (auth.uid() = owner_user_id);

CREATE POLICY "Owners can update team members" ON team_members
    FOR UPDATE USING (auth.uid() = owner_user_id);

CREATE POLICY "Owners can delete team members" ON team_members
    FOR DELETE USING (auth.uid() = owner_user_id);

-- ============================================================
-- GRANT SERVICE ROLE ACCESS (for backend)
-- ============================================================
GRANT ALL ON user_profiles TO service_role;
GRANT ALL ON user_notification_settings TO service_role;
GRANT ALL ON team_members TO service_role;

-- Notify PostgREST to reload schema cache
NOTIFY pgrst, 'reload config';
