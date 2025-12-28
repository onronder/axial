-- Migration: Enforce Strict Paywall (Plan = 'none')
-- Overwrites the handle_new_user trigger function to ensure all new users start inactive.

CREATE OR REPLACE FUNCTION public.handle_new_user()
RETURNS trigger
LANGUAGE plpgsql
SECURITY DEFINER SET search_path = public
AS $$
BEGIN
  INSERT INTO public.user_profiles (
    user_id,
    email,
    first_name,
    last_name,
    plan,                 -- <== FORCED TO 'none'
    subscription_status   -- <== FORCED TO 'inactive'
  )
  VALUES (
    new.id,
    new.email,
    new.raw_user_meta_data->>'first_name',
    new.raw_user_meta_data->>'last_name',
    'none',
    'inactive'
  );
  RETURN new;
END;
$$;
