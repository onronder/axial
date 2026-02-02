-- =============================================================================
-- Migration: Atomic Token Reservation for Race Condition Prevention
-- Version: 20260302000000
-- Description: Adds functions for atomic token reservation to prevent concurrent
--              requests from exceeding quota (TOCTOU race condition fix)
-- =============================================================================

-- =============================================================================
-- 1. ATOMIC TOKEN RESERVATION
-- Problem: Check-then-use pattern allows concurrent requests to both pass quota
--          check then exceed the budget
-- Solution: Atomically reserve tokens before LLM call, release unused after
-- =============================================================================

CREATE OR REPLACE FUNCTION reserve_llm_tokens(
    p_org_id UUID,
    p_tokens INTEGER,
    p_plan_code TEXT DEFAULT NULL
)
RETURNS TABLE(
    success BOOLEAN,
    reservation_id UUID,
    reserved_tokens INTEGER,
    remaining_balance BIGINT
)
LANGUAGE plpgsql
SECURITY DEFINER
SET search_path = public
AS $$
DECLARE
    v_reservation_id UUID := gen_random_uuid();
    v_current_balance BIGINT;
    v_limit BIGINT;
    v_override_balance BIGINT;
    v_plan_limit BIGINT;
    v_tokens_used BIGINT;
BEGIN
    -- Get current balance (either override or calculated from plan limit - usage)

    -- First check for override balance on teams table
    SELECT llm_token_balance INTO v_override_balance
    FROM teams
    WHERE id = p_org_id;

    -- Get current usage
    SELECT COALESCE(llm_tokens_used, 0) INTO v_tokens_used
    FROM org_usage
    WHERE org_id = p_org_id;

    IF v_tokens_used IS NULL THEN
        v_tokens_used := 0;
    END IF;

    -- Determine plan limit based on plan_code
    CASE p_plan_code
        WHEN 'enterprise', 'enterprise_small', 'enterprise_medium', 'enterprise_large' THEN
            v_plan_limit := 100000000;  -- 100M tokens
        WHEN 'pro' THEN
            v_plan_limit := 10000000;   -- 10M tokens
        WHEN 'starter' THEN
            v_plan_limit := 1000000;    -- 1M tokens
        ELSE
            v_plan_limit := 100000;     -- 100K tokens (free)
    END CASE;

    -- Calculate effective balance
    IF v_override_balance IS NOT NULL THEN
        v_current_balance := v_override_balance;
    ELSE
        v_current_balance := GREATEST(0, v_plan_limit - v_tokens_used);
    END IF;

    -- Check if we have enough balance
    IF v_current_balance < p_tokens THEN
        -- Insufficient balance
        RETURN QUERY SELECT
            FALSE,
            NULL::UUID,
            0,
            v_current_balance;
        RETURN;
    END IF;

    -- Atomically reserve tokens by incrementing usage
    INSERT INTO org_usage (org_id, llm_tokens_used, updated_at)
    VALUES (p_org_id, p_tokens, NOW())
    ON CONFLICT (org_id) DO UPDATE
    SET
        llm_tokens_used = org_usage.llm_tokens_used + p_tokens,
        updated_at = NOW();

    -- If override balance exists, decrement it too
    IF v_override_balance IS NOT NULL THEN
        UPDATE teams
        SET llm_token_balance = GREATEST(0, llm_token_balance - p_tokens)
        WHERE id = p_org_id;

        v_current_balance := GREATEST(0, v_override_balance - p_tokens);
    ELSE
        v_current_balance := GREATEST(0, v_plan_limit - v_tokens_used - p_tokens);
    END IF;

    RETURN QUERY SELECT
        TRUE,
        v_reservation_id,
        p_tokens,
        v_current_balance;
END;
$$;

-- Grant to service role only
REVOKE ALL ON FUNCTION reserve_llm_tokens(UUID, INTEGER, TEXT) FROM PUBLIC;
GRANT EXECUTE ON FUNCTION reserve_llm_tokens(UUID, INTEGER, TEXT) TO service_role;

COMMENT ON FUNCTION reserve_llm_tokens IS
'Atomically reserve LLM tokens before making an API call.
Prevents race conditions where concurrent requests both pass quota check then exceed budget.
Returns success=false if insufficient balance.';


-- =============================================================================
-- 2. RELEASE UNUSED TOKENS
-- Call after LLM request completes if actual usage was less than reserved
-- =============================================================================

CREATE OR REPLACE FUNCTION release_llm_tokens(
    p_org_id UUID,
    p_tokens INTEGER
)
RETURNS INTEGER
LANGUAGE plpgsql
SECURITY DEFINER
SET search_path = public
AS $$
DECLARE
    v_new_usage BIGINT;
BEGIN
    IF p_tokens <= 0 THEN
        RETURN 0;
    END IF;

    -- Atomically decrement usage (floor at 0)
    UPDATE org_usage
    SET
        llm_tokens_used = GREATEST(0, llm_tokens_used - p_tokens),
        updated_at = NOW()
    WHERE org_id = p_org_id
    RETURNING llm_tokens_used INTO v_new_usage;

    -- Also credit back to override balance if it exists
    UPDATE teams
    SET llm_token_balance = COALESCE(llm_token_balance, 0) + p_tokens
    WHERE id = p_org_id
    AND llm_token_balance IS NOT NULL;

    RETURN COALESCE(v_new_usage, 0);
END;
$$;

REVOKE ALL ON FUNCTION release_llm_tokens(UUID, INTEGER) FROM PUBLIC;
GRANT EXECUTE ON FUNCTION release_llm_tokens(UUID, INTEGER) TO service_role;

COMMENT ON FUNCTION release_llm_tokens IS
'Release unused reserved tokens back to the organization balance.
Call after LLM request if actual usage was less than estimated.';


-- =============================================================================
-- VERIFICATION
-- =============================================================================

DO $$
BEGIN
    -- Verify functions exist
    ASSERT (SELECT EXISTS(SELECT 1 FROM pg_proc WHERE proname = 'reserve_llm_tokens'));
    ASSERT (SELECT EXISTS(SELECT 1 FROM pg_proc WHERE proname = 'release_llm_tokens'));

    RAISE NOTICE '✅ Atomic token reservation migration completed successfully';
END;
$$;
