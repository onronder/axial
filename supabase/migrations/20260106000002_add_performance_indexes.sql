-- Performance Indexes Migration
-- Date: 2026-01-06
-- Purpose: Add indexes for VERIFIED query patterns from actual codebase
-- VERIFIED AGAINST: backend/*.py grep search results

-- =============================================================================
-- Team members queries (from team_service.py, team.py, usage.py)
-- =============================================================================
-- Pattern: .eq("member_user_id", user_id) - usage.py:113, team_service.py:151
CREATE INDEX IF NOT EXISTS idx_team_members_member_user
  ON public.team_members(member_user_id);

-- Pattern: .eq("team_id", team_id) - team.py:278, team_service.py:573
CREATE INDEX IF NOT EXISTS idx_team_members_team_id
  ON public.team_members(team_id);

-- =============================================================================
-- Notifications queries (from notifications.py)
-- =============================================================================
-- Pattern: .eq("user_id", user_id).eq("is_read", false)
CREATE INDEX IF NOT EXISTS idx_notifications_user_unread
  ON public.notifications(user_id)
  WHERE is_read = false;

-- Pattern: .eq("user_id", user_id).eq("type", type)
CREATE INDEX IF NOT EXISTS idx_notifications_user_type
  ON public.notifications(user_id, type);

-- =============================================================================
-- Ingestion file status queries (from jobs.py, tasks.py, ingestion_pipeline.py)
-- =============================================================================
-- Pattern: .eq("job_id", job_id) - jobs.py:268, tasks.py:197
CREATE INDEX IF NOT EXISTS idx_file_status_job_id
  ON public.ingestion_file_status(job_id);

-- Pattern: .eq("status", "processing"/"pending") for cleanup - periodic_tasks.py:101
CREATE INDEX IF NOT EXISTS idx_file_status_status
  ON public.ingestion_file_status(status);

-- =============================================================================
-- Documents queries (from documents.py)
-- =============================================================================
-- Pattern: .eq("user_id", user_id).order("created_at") 
CREATE INDEX IF NOT EXISTS idx_documents_user_created
  ON public.documents(user_id, created_at DESC);

-- Pattern: .eq("indexing_status", status) for filtering
CREATE INDEX IF NOT EXISTS idx_documents_indexing_status
  ON public.documents(indexing_status);

-- =============================================================================
-- Conversations and messages queries (from chat.py)
-- =============================================================================
CREATE INDEX IF NOT EXISTS idx_conversations_user_updated
  ON public.conversations(user_id, updated_at DESC);

CREATE INDEX IF NOT EXISTS idx_messages_conversation
  ON public.messages(conversation_id, created_at);

-- =============================================================================
-- Subscriptions queries (from billing.py, usage.py)
-- =============================================================================
-- Pattern: .eq("team_id", team_id).eq("status", "active")
CREATE INDEX IF NOT EXISTS idx_subscriptions_team_active
  ON public.subscriptions(team_id)
  WHERE status = 'active';

-- =============================================================================
-- Ingestion jobs queries (from jobs.py, integrations.py)
-- =============================================================================
-- Pattern: .eq("user_id", user_id).eq("status", status)
CREATE INDEX IF NOT EXISTS idx_ingestion_jobs_user_status
  ON public.ingestion_jobs(user_id, status);

-- Pattern: order by created_at DESC for listing
CREATE INDEX IF NOT EXISTS idx_ingestion_jobs_created
  ON public.ingestion_jobs(created_at DESC);

-- =============================================================================
-- User integrations queries (from integrations.py, connectors/*.py)
-- =============================================================================
-- Pattern: .eq("user_id", user_id).eq("connector_definition_id", def_id)
-- Verified: integrations.py:445, 567, 633; drive.py:216, 265
CREATE INDEX IF NOT EXISTS idx_user_integrations_user_connector
  ON public.user_integrations(user_id, connector_definition_id);

-- =============================================================================
-- Failed tasks (DLQ) queries (from dlq.py, dlq_worker.py)
-- =============================================================================
-- Pattern: .eq("status", "pending_retry").lte("next_retry_at", now) - dlq_worker.py:153-156
CREATE INDEX IF NOT EXISTS idx_failed_tasks_retry_ready
  ON public.failed_tasks(status, next_retry_at)
  WHERE status = 'pending_retry';

-- Pattern: .eq("job_id", job_id).eq("user_id", user_id) - dlq.py:113-117
CREATE INDEX IF NOT EXISTS idx_failed_tasks_job_user
  ON public.failed_tasks(job_id, user_id);

-- Pattern: .eq("user_id", user_id).order("created_at" DESC) - dlq.py:329-345
CREATE INDEX IF NOT EXISTS idx_failed_tasks_user_created
  ON public.failed_tasks(user_id, created_at DESC);
