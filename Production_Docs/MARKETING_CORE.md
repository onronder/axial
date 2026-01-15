# Marketing Core Feature Sheet

## Positioning
Axial delivers organization-wide intelligence from your data sources with strong scope isolation and reliable LLM orchestration.

## Customer Value Themes (Code-Backed)

### Your Knowledge, Unified
- Connect GitHub, S3, Box, Google Drive, Notion, Dropbox, OneDrive, SharePoint, SFTP, Web, and direct uploads.
- Unified parsing pipeline for PDFs, docs, spreadsheets, and code with consistent chunking and embeddings.

### Zero Context Collision
- Scope Dominance Guard blocks ambiguous answers and requests clarification when context is fragmented.
- Explicit scope selection and search-all flows prevent cross-source confusion.

### Enterprise-Grade Privacy
- Organization-aware data isolation with composite keys and RLS policies.
- Org-scoped retrieval and identity summaries prevent cross-tenant leakage.

### Uninterrupted Intelligence
- Multi-provider failover (OpenAI to Grok/Groq) with circuit breaker protection.
- Token budgeting and quota enforcement keep usage predictable and safe.

## Proof Points (Implementation Anchors)
- Scope guard: `backend/services/scope_analysis.py`
- Clarification flow: `backend/api/v1/chat.py` and `frontend-new/components/chat/ClarificationCard.tsx`
- Org isolation: `supabase/migrations/20260118000000_add_organization_id_scopes.sql`
- Failover + circuit breaker: `backend/api/v1/chat.py`, `backend/core/resilience.py`
