# Quotas & Limits (High-Perception Strategy)

## Philosophy
- **Generous concurrency for perception:** Starter/Pro users get high parallelism (5–10 jobs) so the product feels fast.
- **TPM as the safety valve:** OpenAI cost is governed by `max_tpm` per plan; concurrency is not throttled unless TPM would be exceeded.
- **Enterprise sizing:** Clear T-shirt tiers map to contract value and capacity.

## Plan Matrix (exact values)
```
starter:           concurrent=5   storage_mb=100      daily_jobs=10     max_tpm=20000
pro:               concurrent=10  storage_mb=2000     daily_jobs=100    max_tpm=50000
enterprise_small:  concurrent=15  storage_mb=50000    daily_jobs=1000   max_tpm=100000   (~$500/mo)
enterprise_medium: concurrent=25  storage_mb=200000   daily_jobs=5000   max_tpm=250000   (~$2000/mo)
enterprise_large:  concurrent=50  storage_mb=1000000  daily_jobs=10000  max_tpm=500000   (~$5000+/mo)
```

## Enforcement Model
- **Admission control (API/dispatcher):** Uses `org_usage` + active job counts per org. Blocks when concurrency, storage, or daily job caps are hit.
- **TPM throttling (embedding):** Per-plan token-per-minute regulator sleeps batches to honor `max_tpm`. Concurrency remains high; embedding pace is the governor.
- **Tracking:** `org_usage` holds storage/job counters; active jobs are derived from `ingestion_jobs` per org membership (team owner + members).

## Operator Notes
- Keep `QUOTA_LIMITS` in `backend/core/config.py` as the single source of truth.
- Adjust TPM first to control cost spikes; keep concurrency generous unless CPU/RAM pressure is observed.
- For new enterprise tiers, extend `QUOTA_LIMITS` and update plan lookup logic alongside contract terms.
