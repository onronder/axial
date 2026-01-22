# Chat Feedback & Quality Analytics System

## Implementation Specification Document

**Version:** 1.0.0  
**Created:** 2026-01-22  
**Status:** Implementation Ready

---

## Table of Contents

1. [Overview](#1-overview)
2. [Requirements](#2-requirements)
3. [Database Design](#3-database-design)
4. [Backend API Design](#4-backend-api-design)
5. [Frontend Design](#5-frontend-design)
6. [Security & Access Control](#6-security--access-control)
7. [GDPR Compliance](#7-gdpr-compliance)
8. [Implementation Checklist](#8-implementation-checklist)

---

## 1. Overview

### 1.1 Purpose

This system enables users to provide feedback (thumbs up/down) on AI chat responses. The collected data serves two purposes:

1. **Team Quality Insights**: Team admins can identify which source documents produce poor answers
2. **Platform Quality Assurance**: Axio platform admins can analyze feedback across all organizations to improve the RAG system

### 1.2 Key Decisions

| Aspect | Decision | Rationale |
|--------|----------|-----------|
| **Anonymity** | Not anonymous - track user who gave feedback | Enables accountability and pattern analysis |
| **Comment** | Optional, max 100 characters | Reduces friction while allowing context |
| **Visibility** | Team admins + Axio platform admins | Serves both customer and platform needs |
| **UI Display** | Don't show feedback counts on messages | Prevents social bias in feedback |
| **GDPR** | 2-year retention, cascading delete | Standard compliance practices |

### 1.3 Architecture Overview

```
┌─────────────────────────────────────────────────────────────────────────┐
│                              Frontend                                    │
│  ┌─────────────────────────────────────────────────────────────────────┐│
│  │  MessageBubble                                                       ││
│  │  ┌─────────────────────────────────────────────────────────────────┐││
│  │  │  AI Response content...                                         │││
│  │  │  [Source Pills]                                                 │││
│  │  │  ┌─────────────────────────────────────────────────────────────┐│││
│  │  │  │  👍 Helpful   👎 Not Helpful                                ││││
│  │  │  └─────────────────────────────────────────────────────────────┘│││
│  │  └─────────────────────────────────────────────────────────────────┘││
│  └─────────────────────────────────────────────────────────────────────┘│
└─────────────────────────────────────────────────────────────────────────┘
                                    │
                                    ▼
┌─────────────────────────────────────────────────────────────────────────┐
│                              Backend API                                 │
│  POST /api/v1/chat/feedback                                             │
│  GET  /api/v1/analytics/feedback (Team Admin)                           │
│  GET  /api/v1/admin/feedback/platform (Platform Admin)                  │
└─────────────────────────────────────────────────────────────────────────┘
                                    │
                                    ▼
┌─────────────────────────────────────────────────────────────────────────┐
│                              Database                                    │
│  message_feedback (table)                                               │
│  source_feedback_metrics (materialized view)                            │
└─────────────────────────────────────────────────────────────────────────┘
```

---

## 2. Requirements

### 2.1 Functional Requirements

| ID | Requirement | Priority |
|----|-------------|----------|
| FR-01 | Users can rate assistant messages as positive or negative | P0 |
| FR-02 | Users can optionally add a comment (max 100 chars) on negative feedback | P0 |
| FR-03 | One rating per user per message (can update existing) | P0 |
| FR-04 | Team admins can view feedback analytics for their organization | P0 |
| FR-05 | Platform admins can view feedback across all organizations | P0 |
| FR-06 | Analytics shows which source documents appear in negative feedback | P0 |
| FR-07 | Feedback deleted when user account is deleted (GDPR) | P0 |
| FR-08 | Feedback deleted after 2-year retention period | P1 |

### 2.2 Non-Functional Requirements

| ID | Requirement | Target |
|----|-------------|--------|
| NFR-01 | Feedback submission response time | < 500ms |
| NFR-02 | Analytics query response time | < 2s for 10,000 records |
| NFR-03 | Support concurrent feedback from 100 users | No data loss |

---

## 3. Database Design

### 3.1 Table: message_feedback

**File:** `supabase/migrations/20260122000000_message_feedback.sql`

```sql
-- ============================================================================
-- Message Feedback Table
-- Stores user ratings on AI chat responses for quality analytics
-- ============================================================================

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
    
    -- Denormalized snapshot (for analytics without joins)
    query_text TEXT NOT NULL,           -- The user's question
    answer_preview TEXT NOT NULL,       -- First 500 chars of AI response
    sources_snapshot JSONB NOT NULL,    -- Copy of sources at feedback time
    
    -- Metadata
    created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    
    -- Constraints
    CONSTRAINT message_feedback_one_per_user UNIQUE (message_id, user_id)
);
```

### 3.2 Indexes

```sql
-- Performance indexes for common queries
CREATE INDEX idx_message_feedback_org_id ON message_feedback(organization_id);
CREATE INDEX idx_message_feedback_rating ON message_feedback(rating);
CREATE INDEX idx_message_feedback_created_at ON message_feedback(created_at DESC);
CREATE INDEX idx_message_feedback_message_id ON message_feedback(message_id);
CREATE INDEX idx_message_feedback_user_id ON message_feedback(user_id);

-- Composite index for analytics queries
CREATE INDEX idx_message_feedback_org_rating_created 
    ON message_feedback(organization_id, rating, created_at DESC);
```

### 3.3 Materialized View: source_feedback_metrics

```sql
-- Aggregate metrics by source document for identifying problematic sources
CREATE MATERIALIZED VIEW source_feedback_metrics AS
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
GROUP BY 
    organization_id, 
    source_elem->>'label',
    source_elem->>'type',
    source_elem->>'url';

-- Index on materialized view
CREATE INDEX idx_source_metrics_org ON source_feedback_metrics(organization_id);
CREATE INDEX idx_source_metrics_negative_rate ON source_feedback_metrics(negative_rate_pct DESC);
```

### 3.4 Row Level Security

```sql
-- Enable RLS
ALTER TABLE message_feedback ENABLE ROW LEVEL SECURITY;

-- Policy: Users can insert feedback for messages in their organization's conversations
CREATE POLICY "message_feedback_insert" ON message_feedback
    FOR INSERT
    WITH CHECK (
        -- User must be org member
        public.is_org_member(organization_id, auth.uid())
        AND
        -- Message must belong to a conversation in user's org
        EXISTS (
            SELECT 1 FROM messages m
            JOIN conversations c ON c.id = m.conversation_id
            WHERE m.id = message_feedback.message_id
            AND public.is_org_member(c.organization_id, auth.uid())
        )
    );

-- Policy: Users can update their own feedback
CREATE POLICY "message_feedback_update" ON message_feedback
    FOR UPDATE
    USING (user_id = auth.uid())
    WITH CHECK (user_id = auth.uid());

-- Policy: Users can view feedback in their organization (for their own messages)
CREATE POLICY "message_feedback_select" ON message_feedback
    FOR SELECT
    USING (
        user_id = auth.uid()
        OR
        -- Team admins can view all org feedback (checked at API level)
        public.is_org_member(organization_id, auth.uid())
    );

-- Policy: Users can delete their own feedback
CREATE POLICY "message_feedback_delete" ON message_feedback
    FOR DELETE
    USING (user_id = auth.uid());

-- Service role has full access (for platform admin endpoints)
-- This is implicit as service_role bypasses RLS
```

### 3.5 GDPR: Retention Policy Function

```sql
-- Function to delete old feedback (called by scheduled job)
CREATE OR REPLACE FUNCTION cleanup_old_feedback()
RETURNS INTEGER
LANGUAGE plpgsql
SECURITY DEFINER
SET search_path = public
AS $$
DECLARE
    deleted_count INTEGER;
BEGIN
    DELETE FROM message_feedback
    WHERE created_at < NOW() - INTERVAL '2 years';
    
    GET DIAGNOSTICS deleted_count = ROW_COUNT;
    
    -- Refresh materialized view after cleanup
    REFRESH MATERIALIZED VIEW CONCURRENTLY source_feedback_metrics;
    
    RETURN deleted_count;
END;
$$;

COMMENT ON FUNCTION cleanup_old_feedback IS 
    'GDPR retention policy: Deletes feedback older than 2 years';
```

---

## 4. Backend API Design

### 4.1 File Structure

```
backend/api/v1/
├── feedback.py          # New file: Feedback endpoints
└── ... (existing files)

backend/services/
├── feedback_service.py  # New file: Business logic
└── ... (existing files)
```

### 4.2 Endpoint: Submit Feedback

**File:** `backend/api/v1/feedback.py`

```python
POST /api/v1/chat/feedback

Request Body:
{
    "message_id": "uuid",
    "rating": "positive" | "negative",
    "feedback_text": "optional comment, max 100 chars"
}

Response (201 Created):
{
    "id": "uuid",
    "message_id": "uuid",
    "rating": "positive" | "negative",
    "created_at": "ISO timestamp"
}

Response (200 OK - Updated existing):
{
    "id": "uuid",
    "message_id": "uuid", 
    "rating": "positive" | "negative",
    "updated_at": "ISO timestamp"
}

Errors:
- 400: Invalid rating value or feedback_text too long
- 404: Message not found or not accessible
- 403: User not authorized (message not in their org)
```

### 4.3 Endpoint: Get Team Feedback Analytics

```python
GET /api/v1/analytics/feedback

Query Parameters:
- limit: int (default 50, max 100)
- offset: int (default 0)
- rating: "positive" | "negative" | null (filter by rating)
- from_date: ISO date string
- to_date: ISO date string
- source_label: string (filter by source document)

Response:
{
    "items": [
        {
            "id": "uuid",
            "rating": "negative",
            "feedback_text": "Answer was outdated",
            "query_text": "What is our refund policy?",
            "answer_preview": "Our refund policy states...",
            "sources": [...],
            "user_email": "john@company.com",
            "created_at": "2026-01-22T10:30:00Z"
        }
    ],
    "total": 150,
    "has_more": true,
    "summary": {
        "positive_count": 120,
        "negative_count": 30,
        "negative_rate_pct": 20.0
    }
}

Access: Team owners and admins only
```

### 4.4 Endpoint: Get Source Quality Metrics

```python
GET /api/v1/analytics/feedback/sources

Query Parameters:
- min_feedback_count: int (default 5, exclude sources with few ratings)
- sort_by: "negative_rate_pct" | "total_feedback" | "negative_count"
- sort_order: "asc" | "desc" (default "desc")
- limit: int (default 20, max 50)

Response:
{
    "items": [
        {
            "source_label": "Outdated-Policy.pdf",
            "source_type": "File",
            "source_url": null,
            "positive_count": 5,
            "negative_count": 15,
            "total_feedback": 20,
            "negative_rate_pct": 75.0,
            "last_feedback_at": "2026-01-22T10:30:00Z"
        }
    ],
    "total": 25
}

Access: Team owners and admins only
```

### 4.5 Endpoint: Platform Admin Analytics

```python
GET /api/v1/admin/feedback/platform

Query Parameters:
- limit, offset, rating, from_date, to_date (same as team endpoint)
- organization_id: UUID (filter by specific org)

Response: Same structure as team endpoint but across all organizations

Access: Axio platform admins only (requires is_platform_admin check)
```

### 4.6 Service Layer

**File:** `backend/services/feedback_service.py`

```python
class FeedbackService:
    """
    Business logic for chat feedback operations.
    
    All methods are stateless and use the provided Supabase client.
    Organization scoping is enforced at this layer.
    """
    
    async def submit_feedback(
        self,
        supabase,
        user_id: str,
        organization_id: str,
        message_id: str,
        rating: str,
        feedback_text: Optional[str] = None
    ) -> dict:
        """Submit or update feedback for a message."""
        
    async def get_team_feedback(
        self,
        supabase,
        organization_id: str,
        limit: int,
        offset: int,
        filters: dict
    ) -> dict:
        """Get feedback analytics for a team."""
        
    async def get_source_metrics(
        self,
        supabase,
        organization_id: str,
        min_feedback_count: int,
        sort_by: str,
        sort_order: str,
        limit: int
    ) -> dict:
        """Get aggregated source quality metrics."""
        
    async def get_platform_feedback(
        self,
        supabase,
        limit: int,
        offset: int,
        filters: dict
    ) -> dict:
        """Get feedback across all organizations (platform admin only)."""
```

---

## 5. Frontend Design

### 5.1 File Structure

```
frontend-new/
├── components/
│   └── chat/
│       ├── MessageBubble.tsx       # Modified: Add FeedbackButtons
│       ├── FeedbackButtons.tsx     # New: 👍 👎 buttons
│       └── FeedbackCommentModal.tsx # New: Optional comment dialog
├── hooks/
│   └── useFeedback.ts              # New: Feedback submission hook
└── app/
    └── dashboard/
        └── admin/
            └── feedback/
                └── page.tsx         # New: Admin analytics dashboard
```

### 5.2 Component: FeedbackButtons

**File:** `frontend-new/components/chat/FeedbackButtons.tsx`

```typescript
interface FeedbackButtonsProps {
    messageId: string;
    sources: SourceMetadata[];
    queryText: string;      // The user's question (from previous message)
    answerPreview: string;  // First 500 chars of this message
    disabled?: boolean;     // Disable during streaming
}

/**
 * Feedback buttons for AI responses.
 * 
 * States:
 * - default: Both buttons shown, neither selected
 * - positive: Thumbs up highlighted, thumbs down faded
 * - negative: Thumbs down highlighted, thumbs up faded + shows comment modal
 * - submitted: Shows "Thanks for feedback" briefly, then returns to selected state
 */
export function FeedbackButtons({
    messageId,
    sources,
    queryText,
    answerPreview,
    disabled = false
}: FeedbackButtonsProps)
```

### 5.3 Hook: useFeedback

**File:** `frontend-new/hooks/useFeedback.ts`

```typescript
interface UseFeedbackReturn {
    submitFeedback: (
        messageId: string,
        rating: 'positive' | 'negative',
        sources: SourceMetadata[],
        queryText: string,
        answerPreview: string,
        feedbackText?: string
    ) => Promise<void>;
    isSubmitting: boolean;
    error: string | null;
    // Track which messages have feedback
    feedbackState: Record<string, 'positive' | 'negative'>;
}

export function useFeedback(): UseFeedbackReturn
```

### 5.4 Integration with MessageBubble

**Modified:** `frontend-new/components/chat/MessageBubble.tsx`

```typescript
// Add to MessageBubbleProps
interface MessageBubbleProps {
    message: MockMessage & { sources?: SourceMetadata[] | Source[] };
    isStreaming?: boolean;
    previousMessage?: MockMessage;  // NEW: To get the user's query
}

// Add below source pills (only for assistant messages)
{!isUser && !isStreaming && (
    <FeedbackButtons
        messageId={message.id}
        sources={normalizedSources}
        queryText={previousMessage?.content || ''}
        answerPreview={message.content.slice(0, 500)}
    />
)}
```

---

## 6. Security & Access Control

### 6.1 Authentication

All endpoints require valid JWT authentication via `Depends(get_current_user)`.

### 6.2 Authorization Matrix

| Endpoint | Free Users | Paid Users | Team Admin | Team Owner | Platform Admin |
|----------|------------|------------|------------|------------|----------------|
| POST /chat/feedback | ✅ | ✅ | ✅ | ✅ | ✅ |
| GET /analytics/feedback | ❌ | ❌ | ✅ | ✅ | ✅ |
| GET /analytics/feedback/sources | ❌ | ❌ | ✅ | ✅ | ✅ |
| GET /admin/feedback/platform | ❌ | ❌ | ❌ | ❌ | ✅ |

### 6.3 Platform Admin Check

```python
# In dependencies.py
async def require_platform_admin(user_id: str = Depends(get_current_user)):
    """
    Verify user is a platform admin.
    Platform admins are identified by:
    - Email domain (e.g., @axiohub.io)
    - Or explicit flag in user_profiles table
    """
    supabase = get_supabase()
    
    # Check user email
    user = supabase.auth.admin.get_user_by_id(user_id)
    if user and user.user.email.endswith('@axiohub.io'):
        return user_id
    
    # Check platform_admin flag
    profile = supabase.table("user_profiles")\
        .select("is_platform_admin")\
        .eq("user_id", user_id)\
        .single()\
        .execute()
    
    if profile.data and profile.data.get("is_platform_admin"):
        return user_id
    
    raise HTTPException(status_code=403, detail="Platform admin access required")
```

---

## 7. GDPR Compliance

### 7.1 Data Subject Rights

| Right | Implementation |
|-------|----------------|
| **Right to Access** | User can view their own feedback via API |
| **Right to Rectification** | User can update feedback (PUT endpoint) |
| **Right to Erasure** | Feedback deleted on user account deletion (CASCADE) |
| **Right to Restrict Processing** | Not applicable (feedback is voluntary) |
| **Right to Data Portability** | Included in data export (existing export endpoint) |

### 7.2 Retention Policy

- **Active Data**: Retained for 2 years from creation
- **Deleted Users**: Feedback deleted immediately (CASCADE constraint)
- **Cleanup**: Scheduled job runs weekly to delete old feedback

### 7.3 Data Minimization

- `feedback_text` is optional and limited to 100 characters
- `answer_preview` is truncated to 500 characters
- Full message content is NOT stored (only preview)

---

## 8. Implementation Checklist

### Phase 1: Database (Day 1)

- [ ] Create migration file `20260122000000_message_feedback.sql`
- [ ] Create table `message_feedback`
- [ ] Create indexes
- [ ] Create materialized view `source_feedback_metrics`
- [ ] Create RLS policies
- [ ] Create retention cleanup function
- [ ] Test migration locally
- [ ] Deploy migration to production

### Phase 2: Backend API (Day 2)

- [ ] Create `backend/services/feedback_service.py`
- [ ] Create `backend/api/v1/feedback.py`
- [ ] Register router in `backend/main.py`
- [ ] Add `is_platform_admin` column to user_profiles (if needed)
- [ ] Add `require_platform_admin` dependency
- [ ] Write unit tests for feedback service
- [ ] Write integration tests for feedback endpoints

### Phase 3: Frontend (Day 3-4)

- [ ] Create `frontend-new/hooks/useFeedback.ts`
- [ ] Create `frontend-new/components/chat/FeedbackButtons.tsx`
- [ ] Create `frontend-new/components/chat/FeedbackCommentModal.tsx`
- [ ] Modify `MessageBubble.tsx` to include FeedbackButtons
- [ ] Update chat page to pass previous message for query context
- [ ] Write component tests

### Phase 4: Admin Dashboard (Day 5)

- [ ] Create `frontend-new/app/dashboard/admin/feedback/page.tsx`
- [ ] Create feedback analytics table component
- [ ] Create source quality metrics component
- [ ] Add navigation link in admin sidebar

### Phase 5: Testing & Deployment (Day 6)

- [ ] End-to-end testing
- [ ] Performance testing (analytics queries)
- [ ] Security review
- [ ] Deploy to staging
- [ ] Deploy to production

---

## Appendix A: Related Files Reference

### Existing Files to Reference

| File | Purpose |
|------|---------|
| `supabase/migrations/20251226213700_audit_logs.sql` | Migration pattern example |
| `supabase/migrations/20260216120000_org_based_rls_policies.sql` | RLS pattern with is_org_member |
| `backend/api/v1/admin.py` | Admin endpoint pattern |
| `backend/api/v1/chat.py` | Message/sources structure |
| `backend/services/audit.py` | Service layer pattern |
| `frontend-new/components/chat/MessageBubble.tsx` | Component to modify |
| `frontend-new/hooks/useChatHistory.tsx` | Hook pattern example |

### New Files to Create

| File | Type |
|------|------|
| `supabase/migrations/20260122000000_message_feedback.sql` | Database migration |
| `backend/api/v1/feedback.py` | API endpoints |
| `backend/services/feedback_service.py` | Business logic |
| `frontend-new/hooks/useFeedback.ts` | React hook |
| `frontend-new/components/chat/FeedbackButtons.tsx` | UI component |
| `frontend-new/components/chat/FeedbackCommentModal.tsx` | UI component |
| `frontend-new/app/dashboard/admin/feedback/page.tsx` | Admin page |

---

**Document Status:** ✅ IMPLEMENTED  
**Implementation Date:** 2026-01-22

---

## Implementation Summary

All components have been implemented and verified:

### Files Created

| File | Type | Description |
|------|------|-------------|
| `supabase/migrations/20260122000000_message_feedback.sql` | Database | Table, indexes, RLS policies, materialized view, cleanup function |
| `backend/services/feedback_service.py` | Backend | Business logic for feedback operations |
| `backend/api/v1/feedback.py` | Backend | REST API endpoints for feedback |
| `frontend-new/hooks/useFeedback.ts` | Frontend | React hook for feedback state management |
| `frontend-new/components/chat/FeedbackButtons.tsx` | Frontend | UI component for thumbs up/down buttons |
| `frontend-new/app/dashboard/settings/analytics/page.tsx` | Frontend | Admin dashboard for feedback analytics |

### Files Modified

| File | Change |
|------|--------|
| `backend/main.py` | Registered feedback_router |
| `frontend-new/components/chat/MessageBubble.tsx` | Added FeedbackButtons integration |
| `frontend-new/components/chat/ChatArea.tsx` | Added feedback hook and props passing |
| `frontend-new/app/dashboard/chat/[chatId]/page.tsx` | Added conversationId prop |
| `frontend-new/app/dashboard/settings/layout.tsx` | Added Analytics nav item |

### Deployment Steps

1. Run database migration:
   ```bash
   supabase db push
   # Or deploy to production via your CI/CD pipeline
   ```

2. Deploy backend (Railway will auto-detect new files)

3. Deploy frontend (Vercel will auto-detect new files)

4. Verify:
   - Open a chat and respond to see feedback buttons
   - Click thumbs down to test the comment modal
   - Visit Settings > Analytics to see the dashboard (admin only)
