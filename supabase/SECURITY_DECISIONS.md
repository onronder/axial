# Supabase Security Decisions

This document records security decisions and tradeoffs for the Axial database.

## Extensions in Public Schema

**Status:** Accepted Risk  
**Date:** 2026-01-31

### Issue
The Supabase Database Linter reports warnings about extensions installed in the `public` schema:
- `vector` extension
- `pg_trgm` extension

### Analysis

Moving extensions to a dedicated `extensions` schema is generally a security best practice because:
- Extensions in `public` are accessible to all authenticated users
- It reduces the attack surface

However, for our use case:

1. **Low Security Impact:**
   - `vector`: Read-only vector similarity search. No sensitive operations.
   - `pg_trgm`: Text trigram search. No sensitive operations.
   - Neither extension exposes sensitive data or allows privilege escalation.

2. **High Migration Risk:**
   - Moving `vector` requires rebuilding ALL vector indexes on `document_chunks`
   - With millions of chunks, this would take hours
   - Requires significant downtime
   - Risk of data loss if migration fails

3. **No User Benefit:**
   - Users cannot call these extensions directly (RLS protects the tables)
   - Extensions are only used by backend functions

### Decision

**Accept the warning.** The security risk is minimal compared to the migration complexity and downtime.

### Future Considerations

If migrating extensions becomes necessary:
1. Schedule a maintenance window (4-8 hours for large datasets)
2. Create new extensions schema
3. Recreate all dependent objects (indexes, functions)
4. Update all function search paths
5. Test thoroughly before cutover

---

## Webhook DLQ RLS

**Status:** Implemented  
**Date:** 2026-01-31

### Issue
The `webhook_dlq` table had RLS enabled but no policies.

### Solution
Added explicit `service_role` policy. While technically redundant (service_role bypasses RLS), this:
- Satisfies the database linter
- Documents the access intent explicitly
- Follows the principle of explicit > implicit

See migration: `20260131000001_fix_webhook_dlq_rls.sql`

---

## Unused Indexes

**Status:** Deferred (6 months)  
**Date:** 2026-01-31

### Issue
The database has 51 unused indexes reported by the linter.

### Analysis

Unused indexes are reported because they haven't been used since Postgres started tracking. For a new/low-traffic application, this is expected.

**Critical indexes to KEEP:**
- `idx_documents_*` - Document queries
- `idx_document_chunks_*` - Vector search
- `idx_conversations_*` - Chat history
- `idx_team_members_*` - Team features
- `idx_audit_logs_*` - Audit log queries

### Decision

**Defer review until 2026-07-31** after 6 months of production traffic. Indexes that remain unused after real-world usage patterns emerge can be safely removed.

---

## Review Schedule

| Decision | Review Date | Status |
|----------|-------------|--------|
| Extensions in public | 2026-07-31 | Monitor |
| Unused indexes | 2026-07-31 | Re-evaluate |
| webhook_dlq RLS | Complete | ✅ Done |
