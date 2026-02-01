-- =============================================================================
-- Ghost Data Prevention: Add index for source_id based deduplication
-- =============================================================================
-- 
-- Problem: "Ghost Data" vulnerability where renamed/modified files create
--          duplicate documents instead of updating existing ones.
-- 
-- Solution: Primary deduplication by source_id (unique identifier from source)
--           with fallback to content_hash for legacy compatibility.
--
-- This index dramatically speeds up the duplicate check query:
--   SELECT id, content_hash FROM documents 
--   WHERE organization_id = ? AND source_id = ?
--
-- Expected Performance:
--   - Without index: Full table scan O(n)
--   - With index: B-tree lookup O(log n)
--   - For 100k documents: ~100ms → ~1ms
-- =============================================================================

-- Create composite index for source_id based deduplication
-- Includes content_hash as a covering index to avoid table lookup
CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_documents_org_source_id_dedup
ON documents (organization_id, source_id)
INCLUDE (content_hash)
WHERE source_id IS NOT NULL;

-- Add comment explaining the index purpose
COMMENT ON INDEX idx_documents_org_source_id_dedup IS 
    'Ghost Data Prevention: Speeds up duplicate detection by source_id within organization scope';

-- Also create an index for the fallback content_hash based deduplication
-- This is used when source_id is not available (legacy behavior)
CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_documents_org_content_hash_dedup
ON documents (organization_id, content_hash)
WHERE content_hash IS NOT NULL;

COMMENT ON INDEX idx_documents_org_content_hash_dedup IS 
    'Legacy deduplication: Speeds up duplicate detection by content_hash within organization scope';
