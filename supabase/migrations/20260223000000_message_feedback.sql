-- ============================================================================
-- Message Feedback System
-- Enables user ratings (thumbs up/down) on AI chat responses for quality analytics
-- ============================================================================
--
-- Purpose:
--   1. Collect user feedback on AI response quality
--   2. Enable team admins to identify problematic source documents
--   3. Enable platform admins to analyze feedback across all organizations
--
-- Related Files:
--   - backend/api/v1/feedback.py (API endpoints)
--   - backend/services/feedback_service.py (business logic)
--   - frontend-new/components/chat/FeedbackButtons.tsx (UI)
--
-- GDPR Compliance:
--   - Feedback deleted on user account deletion (CASCADE)
--   - 2-year retention policy via cleanup_old_feedback()
--   - Minimal data stored (truncated answer preview)
--
-- ============================================================================

BEGIN;

-- ============================================================================
-- 1. MESSAGE FEEDBACK TABLE
-- ============================================================================
-- Stores user ratings on AI chat responses
-- One rating per user per message (can update existing)

CREATE TABLE IF NOT EXISTS public.message_feedback (
    -- Primary key
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    
    -- Core relationships (all required)
    message_id UUID NOT NULL REFERENCES public.messages(id) ON DELETE CASCADE,
    user_id UUID NOT NULL REFERENCES auth.users(id) ON DELETE CASCADE,
    organization_id UUID NOT NULL,
    conversation_id UUID NOT NULL,
    
    -- Feedback data
    rating TEXT NOT NULL CHECK (rating IN ('positive', 'negative')),
    feedback_text TEXT CHECK (feedback_text IS NULL OR char_length(feedback_text) <= 100),
    
    -- Denormalized snapshot for analytics (avoids joins, preserves context)
    query_text TEXT NOT NULL,              -- The user's question
    answer_preview TEXT NOT NULL,          -- First 500 chars of AI response
    sources_snapshot JSONB NOT NULL DEFAULT '[]'::jsonb,  -- Copy of sources at feedback time
    
    -- Timestamps
    created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    
    -- One rating per user per message (upsert supported)
    CONSTRAINT message_feedback_unique_user_message UNIQUE (message_id, user_id)
);

-- ============================================================================
-- 2. PERFORMANCE INDEXES
-- ============================================================================

-- Primary lookup by message
CREATE INDEX IF NOT EXISTS idx_message_feedback_message_id 
    ON message_feedback(message_id);

-- User's feedback history
CREATE INDEX IF NOT EXISTS idx_message_feedback_user_id 
    ON message_feedback(user_id);

-- Organization analytics
CREATE INDEX IF NOT EXISTS idx_message_feedback_org_id 
    ON message_feedback(organization_id);

-- Filter by rating type
CREATE INDEX IF NOT EXISTS idx_message_feedback_rating 
    ON message_feedback(rating);

-- Time-based queries (recent feedback)
CREATE INDEX IF NOT EXISTS idx_message_feedback_created_at 
    ON message_feedback(created_at DESC);

-- Composite index for team analytics (org + rating + time)
CREATE INDEX IF NOT EXISTS idx_message_feedback_org_rating_created 
    ON message_feedback(organization_id, rating, created_at DESC);

-- ============================================================================
-- 3. MATERIALIZED VIEW: SOURCE QUALITY METRICS
-- ============================================================================
-- Aggregates feedback by source document for identifying problematic sources
-- Refreshed periodically (after bulk feedback or via scheduled job)

CREATE MATERIALIZED VIEW IF NOT EXISTS source_feedback_metrics AS
SELECT 
    organization_id,
    source_elem->>'label' AS source_label,
    source_elem->>'type' AS source_type,
    source_elem->>'url' AS source_url,
    COUNT(*) FILTER (WHERE rating = 'positive') AS positive_count,
    COUNT(*) FILTER (WHERE rating = 'negative') AS negative_count,
    COUNT(*) AS total_feedback,
    ROUND(
        COUNT(*) FILTER (WHERE rating = 'negative')::numeric / 
        NULLIF(COUNT(*), 0) * 100, 2
    ) AS negative_rate_pct,
    MAX(created_at) AS last_feedback_at
FROM message_feedback,
LATERAL jsonb_array_elements(sources_snapshot) AS source_elem
WHERE jsonb_array_length(sources_snapshot) > 0
GROUP BY 
    organization_id, 
    source_elem->>'label',
    source_elem->>'type',
    source_elem->>'url';

-- Indexes on materialized view for efficient queries
CREATE INDEX IF NOT EXISTS idx_source_metrics_org 
    ON source_feedback_metrics(organization_id);

CREATE INDEX IF NOT EXISTS idx_source_metrics_negative_rate 
    ON source_feedback_metrics(negative_rate_pct DESC);

CREATE INDEX IF NOT EXISTS idx_source_metrics_total 
    ON source_feedback_metrics(total_feedback DESC);

-- ============================================================================
-- 4. ROW LEVEL SECURITY
-- ============================================================================

ALTER TABLE message_feedback ENABLE ROW LEVEL SECURITY;

-- Drop existing policies if re-running migration
DROP POLICY IF EXISTS "message_feedback_insert" ON message_feedback;
DROP POLICY IF EXISTS "message_feedback_update" ON message_feedback;
DROP POLICY IF EXISTS "message_feedback_select" ON message_feedback;
DROP POLICY IF EXISTS "message_feedback_delete" ON message_feedback;

-- INSERT: Users can submit feedback for messages in their org's conversations
CREATE POLICY "message_feedback_insert" ON message_feedback
    FOR INSERT
    WITH CHECK (
        -- User must be the one submitting (user_id matches auth.uid())
        user_id = (SELECT auth.uid())
        AND
        -- User must be a member of the organization
        public.is_org_member(organization_id, (SELECT auth.uid()))
        AND
        -- Message must exist in a conversation the user can access
        EXISTS (
            SELECT 1 FROM messages m
            JOIN conversations c ON c.id = m.conversation_id
            WHERE m.id = message_feedback.message_id
            AND public.is_org_member(c.organization_id, (SELECT auth.uid()))
        )
    );

-- UPDATE: Users can update their own feedback only
CREATE POLICY "message_feedback_update" ON message_feedback
    FOR UPDATE
    USING (user_id = (SELECT auth.uid()))
    WITH CHECK (user_id = (SELECT auth.uid()));

-- SELECT: Users can view their own feedback, org members can view for analytics
CREATE POLICY "message_feedback_select" ON message_feedback
    FOR SELECT
    USING (
        -- User can always see their own feedback
        user_id = (SELECT auth.uid())
        OR
        -- Org members can view feedback for analytics (admin check at API level)
        public.is_org_member(organization_id, (SELECT auth.uid()))
    );

-- DELETE: Users can delete their own feedback only
CREATE POLICY "message_feedback_delete" ON message_feedback
    FOR DELETE
    USING (user_id = (SELECT auth.uid()));

-- ============================================================================
-- 5. UPDATED_AT TRIGGER
-- ============================================================================

-- Function to auto-update updated_at timestamp
CREATE OR REPLACE FUNCTION update_message_feedback_updated_at()
RETURNS TRIGGER
LANGUAGE plpgsql
SECURITY DEFINER
SET search_path = public
AS $$
BEGIN
    NEW.updated_at = now();
    RETURN NEW;
END;
$$;

-- Trigger to call function on updates
DROP TRIGGER IF EXISTS trigger_message_feedback_updated_at ON message_feedback;
CREATE TRIGGER trigger_message_feedback_updated_at
    BEFORE UPDATE ON message_feedback
    FOR EACH ROW
    EXECUTE FUNCTION update_message_feedback_updated_at();

-- ============================================================================
-- 6. GDPR: RETENTION POLICY CLEANUP FUNCTION
-- ============================================================================
-- Deletes feedback older than 2 years
-- Should be called by a scheduled job (pg_cron or Celery Beat)

CREATE OR REPLACE FUNCTION cleanup_old_feedback()
RETURNS INTEGER
LANGUAGE plpgsql
SECURITY DEFINER
SET search_path = public
AS $$
DECLARE
    deleted_count INTEGER;
BEGIN
    -- Delete feedback older than 2 years
    DELETE FROM message_feedback
    WHERE created_at < NOW() - INTERVAL '2 years';
    
    GET DIAGNOSTICS deleted_count = ROW_COUNT;
    
    -- Refresh materialized view if any rows were deleted
    IF deleted_count > 0 THEN
        REFRESH MATERIALIZED VIEW CONCURRENTLY source_feedback_metrics;
    END IF;
    
    RETURN deleted_count;
END;
$$;

COMMENT ON FUNCTION cleanup_old_feedback IS 
    'GDPR retention policy: Deletes message feedback older than 2 years. '
    'Returns the number of deleted rows. Should be called weekly.';

-- ============================================================================
-- 7. HELPER FUNCTION: REFRESH SOURCE METRICS
-- ============================================================================
-- Call after bulk feedback submissions or on a schedule

CREATE OR REPLACE FUNCTION refresh_source_feedback_metrics()
RETURNS VOID
LANGUAGE plpgsql
SECURITY DEFINER
SET search_path = public
AS $$
BEGIN
    REFRESH MATERIALIZED VIEW CONCURRENTLY source_feedback_metrics;
END;
$$;

COMMENT ON FUNCTION refresh_source_feedback_metrics IS
    'Refreshes the source_feedback_metrics materialized view. '
    'Call after bulk feedback operations or on a schedule (e.g., hourly).';

-- ============================================================================
-- 8. SERVICE ROLE GRANTS
-- ============================================================================
-- Service role needs full access for backend operations and platform admin

GRANT ALL ON message_feedback TO service_role;
GRANT ALL ON source_feedback_metrics TO service_role;
GRANT EXECUTE ON FUNCTION cleanup_old_feedback() TO service_role;
GRANT EXECUTE ON FUNCTION refresh_source_feedback_metrics() TO service_role;

-- ============================================================================
-- 9. TABLE COMMENTS (Documentation)
-- ============================================================================

COMMENT ON TABLE message_feedback IS 
    'Stores user ratings (thumbs up/down) on AI chat responses for quality analytics. '
    'One rating per user per message. Includes denormalized data for efficient analytics.';

COMMENT ON COLUMN message_feedback.message_id IS 
    'FK to messages table - the AI response being rated';

COMMENT ON COLUMN message_feedback.organization_id IS 
    'Organization ID for multi-tenant analytics and RLS';

COMMENT ON COLUMN message_feedback.rating IS 
    'User rating: positive (helpful) or negative (not helpful)';

COMMENT ON COLUMN message_feedback.feedback_text IS 
    'Optional comment from user, max 100 characters (GDPR data minimization)';

COMMENT ON COLUMN message_feedback.query_text IS 
    'The user question that prompted this AI response (for context in analytics)';

COMMENT ON COLUMN message_feedback.answer_preview IS 
    'First 500 chars of AI response (truncated for GDPR data minimization)';

COMMENT ON COLUMN message_feedback.sources_snapshot IS 
    'JSONB copy of sources at feedback time (enables source quality analysis)';

COMMENT ON MATERIALIZED VIEW source_feedback_metrics IS 
    'Aggregated feedback metrics per source document. '
    'Use for identifying documents that frequently appear in negative feedback. '
    'Refresh with refresh_source_feedback_metrics() or REFRESH MATERIALIZED VIEW.';

-- ============================================================================
-- 10. NOTIFY POSTGREST
-- ============================================================================

NOTIFY pgrst, 'reload config';

COMMIT;
