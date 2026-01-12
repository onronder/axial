# Axial Refactoring v2.0 - "The Enterprise Backbone"

## Key Features Delivered
- **Smart Quotas:** Tier-based concurrency, storage, and daily job limits with admission control.
- **Traffic Control:** Split Celery queues isolating Parsing (CPU) vs. Embedding (IO) workloads.
- **Unified Connectors:** Standardized `BaseConnector` across Drive, Notion, Web, and Uploads for plug-and-play integrations.
- **Cost Efficiency:** SHA-256 deduplication prevents redundant parsing/embedding and AI spend.
- **Security:** RLS enforcement plus rate limiting to guard against abuse.

## Known Operational Notes
- Chat endpoints can return 502 on very long LLM responses; timeout tuning is a future item.
- `ingestion_role` infrastructure is present but dormant; reserved for a future least-privilege worker DB path.
