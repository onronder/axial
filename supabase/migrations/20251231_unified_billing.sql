-- Migration: Unified Billing (Subscriptions on Teams)
-- Timestamp: 20251231000000

-- 1. Remove subscription_status from user_profiles (if exists)
DO $$ 
BEGIN
    IF EXISTS (SELECT 1 FROM information_schema.columns WHERE table_name = 'user_profiles' AND column_name = 'subscription_status') THEN
        ALTER TABLE user_profiles DROP COLUMN subscription_status;
    END IF;
END $$;

-- 2. Create subscriptions table
-- Drop old table if exists to ensure new schema (Team-based)
DROP TABLE IF EXISTS subscriptions CASCADE;

CREATE TABLE subscriptions (
    id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
    team_id uuid NOT NULL,
    polar_id text NOT NULL, -- Subscription ID from Polar
    status text NOT NULL CHECK (status IN ('active', 'past_due', 'canceled', 'incomplete', 'trialing')),
    plan_type text NOT NULL CHECK (plan_type IN ('starter', 'pro', 'enterprise')),
    seats integer DEFAULT 1, -- For Pro/Enterprise seat management
    current_period_end timestamptz,
    cancel_at_period_end boolean DEFAULT false,
    created_at timestamptz DEFAULT now(),
    updated_at timestamptz DEFAULT now(),
    
    -- Constraints
    CONSTRAINT fk_team FOREIGN KEY (team_id) REFERENCES teams(id) ON DELETE CASCADE,
    CONSTRAINT uq_subscriptions_team_id UNIQUE (team_id), -- One active subscription per team
    CONSTRAINT uq_subscriptions_polar_id UNIQUE (polar_id)
);

-- 3. Enable RLS
ALTER TABLE subscriptions ENABLE ROW LEVEL SECURITY;

-- 4. RLS Policies

-- Policy: Authenticated users can view subscription if they belong to the team
CREATE POLICY "Users can view team subscription"
    ON subscriptions FOR SELECT
    USING (
        EXISTS (
            SELECT 1 FROM team_members
            WHERE team_members.team_id = subscriptions.team_id
            AND team_members.member_user_id = auth.uid()
        )
    );

-- Policy: Service role has full access (for webhooks/admin)
-- Note: 'postgres' and 'service_role' bypass RLS by default in Supabase, 
-- but explicit policy is good practice if using local roles.
-- Since we rely on service_role for webhooks, no extra policy needed for writes 
-- as long as we use the service key. But for completeness:
-- (Supabase default is deny all for roles not listed)

-- 5. Add index for performance
CREATE INDEX IF NOT EXISTS idx_subscriptions_team_id ON subscriptions(team_id);
CREATE INDEX IF NOT EXISTS idx_subscriptions_polar_id ON subscriptions(polar_id);
