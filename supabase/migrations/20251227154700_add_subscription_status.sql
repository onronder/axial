-- Migration: Add subscription_status to user_profiles
-- Enables Polar.sh subscription integration
--
-- Note: 'plan' column already exists in user_profiles (free, pro, enterprise)
-- subscription_status tracks the payment status independently

ALTER TABLE user_profiles
ADD COLUMN IF NOT EXISTS subscription_status TEXT DEFAULT 'active';

-- Expected values:
-- 'active'     - Subscription is current and paid
-- 'trialing'   - User is in trial period
-- 'past_due'   - Payment failed, grace period
-- 'canceled'   - User canceled subscription
-- 'incomplete' - Initial payment pending

-- Create index for fast access checks (subscription-gated features)
CREATE INDEX IF NOT EXISTS idx_user_profiles_sub_status 
ON user_profiles(subscription_status);

-- Notify PostgREST
NOTIFY pgrst, 'reload config';
