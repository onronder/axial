-- Performance optimization: Single query for user team data
-- Replaces 4 sequential queries with 1 RPC call

CREATE OR REPLACE FUNCTION get_user_team_data(target_user_id UUID)
RETURNS JSON AS $$
DECLARE
    result JSON;
BEGIN
    SELECT json_build_object(
        'team', row_to_json(t.*),
        'subscription', row_to_json(s.*),
        'profile', row_to_json(p.*),
        'member', row_to_json(tm.*)
    ) INTO result
    FROM team_members tm
    JOIN teams t ON t.id = tm.team_id
    LEFT JOIN subscriptions s ON s.team_id = t.id
    LEFT JOIN user_profiles p ON p.user_id = tm.member_user_id
    WHERE tm.member_user_id = target_user_id
    AND tm.status != 'removed'
    LIMIT 1;
    
    RETURN result;
END;
$$ LANGUAGE plpgsql STABLE SECURITY DEFINER;

-- Grant execute permission
GRANT EXECUTE ON FUNCTION get_user_team_data(UUID) TO authenticated;

COMMENT ON FUNCTION get_user_team_data IS 'Performance optimization: Get user team data in single query instead of N+1';
