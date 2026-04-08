-- =============================================================================
-- Post-backfill maintenance for document_chunks.content_search
-- Created: 2026-04-07
--
-- IMPORTANT:
-- - This is an operational SQL file, not a migration.
-- - REINDEX INDEX CONCURRENTLY cannot run inside a transaction block.
-- - The GIN index remains logically correct during backfill because
--   document_chunks.content_search is a stored TSVECTOR column and row updates
--   maintain the index automatically.
-- - Run this only after the content_search backfill completes if you want to
--   compact post-update GIN bloat and refresh planner statistics.
-- =============================================================================

REINDEX INDEX CONCURRENTLY public.idx_document_chunks_content_search;
ANALYZE public.document_chunks;
