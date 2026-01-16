BEGIN;

UPDATE public.documents
SET source_type = 'identity',
    updated_at = NOW()
WHERE (
        metadata->>'type' = 'identity_card'
        OR title LIKE 'Scope Identity:%'
    )
  AND source_type IS DISTINCT FROM 'identity';

COMMIT;
