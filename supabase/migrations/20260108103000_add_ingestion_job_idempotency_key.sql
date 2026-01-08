-- Add idempotency key support for ingestion jobs

ALTER TABLE IF EXISTS ingestion_jobs
ADD COLUMN IF NOT EXISTS idempotency_key TEXT;

CREATE UNIQUE INDEX IF NOT EXISTS ingestion_jobs_user_provider_idempotency_key_idx
ON ingestion_jobs (user_id, provider, idempotency_key)
WHERE idempotency_key IS NOT NULL;
