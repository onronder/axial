-- Migration: Strict Paywall - Default new users to inactive
-- Purpose: New users must complete Polar checkout before accessing app
-- Date: 2025-12-28

-- Update the handle_new_user function to set default plan to 'none' and status to 'inactive'
CREATE OR REPLACE FUNCTION public.handle_new_user()
RETURNS TRIGGER AS $$
BEGIN
    INSERT INTO public.user_profiles (
        user_id,
        email,
        first_name,
        last_name,
        plan,
        subscription_status,
        created_at,
        updated_at
    )
    VALUES (
        NEW.id,
        NEW.email,
        COALESCE(NEW.raw_user_meta_data->>'first_name', ''),
        COALESCE(NEW.raw_user_meta_data->>'last_name', ''),
        'none',  -- No plan by default - user must subscribe
        'inactive',  -- Inactive until Polar confirms subscription/trial
        NOW(),
        NOW()
    );
    RETURN NEW;
END;
$$ LANGUAGE plpgsql SECURITY DEFINER;

-- Note: Existing users are NOT affected by this change.
-- Only new sign-ups will have plan='none' and status='inactive'.
-- Polar webhook will update these to actual plan and 'active'/'trialing' status.

COMMENT ON FUNCTION public.handle_new_user() IS 
'Creates user profile on signup with default plan=none, status=inactive. 
User must complete Polar checkout to activate account.';
