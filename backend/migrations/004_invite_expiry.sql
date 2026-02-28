ALTER TABLE team_members ADD COLUMN IF NOT EXISTS expires_at TIMESTAMPTZ;
ALTER TABLE team_members ADD COLUMN IF NOT EXISTS removed_at TIMESTAMPTZ;

-- Backfill: existing pending invites get 30-day grace period from now
UPDATE team_members
SET expires_at = NOW() + INTERVAL '30 days'
WHERE status = 'pending' AND expires_at IS NULL;
