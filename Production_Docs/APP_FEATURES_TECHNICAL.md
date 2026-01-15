# App Features Matrix (Technical)

This matrix maps technical capabilities to their code sources.

## Data Connectivity
- Multi-source ingestion via connectors: GitHub, S3, Box, Google Drive, Notion, Dropbox, OneDrive, SharePoint, SFTP, Web, File Upload. See `backend/connectors/` and `backend/connectors/registry.py`.
- OAuth-based connectors with incremental sync capabilities where supported (registry capabilities).
- S3 ingestion with IAM credentials (`backend/connectors/s3.py`).
- OCR and document parsing for PDFs/DOCX via LlamaParse and fallbacks (`backend/services/parsers.py`).
- Tabular parsing for CSV/XLSX with size limits (`backend/services/parsers.py`, `backend/core/config.py`).

## Intelligence
- Scope Dominance Guard (DOMINANT/CONTESTED/FRAGMENTED) to prevent context collisions (`backend/services/scope_analysis.py`).
- HTTP 300 Clarification flow with scope candidates (`backend/api/v1/chat.py`, frontend `frontend-new/lib/chat-utils.ts`).
- Scope identity cards (summary + tree) stored and embedded (`backend/services/scope_identity.py`).
- Intent detection, safety, and complexity classification using Groq (`backend/services/guardrails.py`).
- Query condensation for follow-ups (`backend/api/v1/chat.py`).

## Enterprise
- Organization-wide isolation using `organization_id` with composite keys (`supabase/migrations/20260118000000_add_organization_id_scopes.sql`).
- Team membership and plan inheritance (`backend/services/team_service.py`).
- CSV onboarding for team members (`backend/api/v1/team.py` -> `bulk_invite_team_members`).
- Atomic org deletion with active-ingestion guard (`backend/services/cleanup.py`, `supabase/migrations/20260201000000_llm_quota_and_identity_lock.sql`).
- RLS policies for documents and scope identities (`supabase/migrations/20260108125000_fix_rls_team_recursion.sql`, `supabase/migrations/20260118000000_add_organization_id_scopes.sql`).

## Resilience
- Multi-provider LLM failover with circuit breaker (`backend/api/v1/chat.py`, `backend/core/resilience.py`, `backend/services/router.py`).
- Token quota enforcement and usage tracking (`backend/services/usage.py`).
- Identity synthesis locking with SELECT FOR UPDATE in RPC (`supabase/migrations/20260201000000_llm_quota_and_identity_lock.sql`).
- Connector concurrency caps (`backend/connectors/limits.py`).
- Embedding throttling and retry with adaptive backoff (`backend/services/embeddings.py`).
- Celery task retries for critical paths (`backend/worker/tasks.py`).
