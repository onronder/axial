-- =============================================================================
-- Add 'notion' to source_type_enum
-- =============================================================================
-- The connector_definitions table includes 'notion' but the enum only has
-- 'file', 'web', 'drive'. Adding 'notion' for future compatibility.
-- =============================================================================

-- Add 'notion' value to the enum type
ALTER TYPE source_type_enum ADD VALUE IF NOT EXISTS 'notion';
