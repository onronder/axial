# Pricing Plans and Feature Tiers

This document reflects the hard-coded plan limits in `backend/core/quotas.py` and `backend/core/config.py`. Plans are mapped to a model tier used by `backend/services/router.py` and `backend/services/llm_factory.py`.

## Plan Tiers (Product and Code)
Customer-facing plans are `starter`, `pro`, and `enterprise`. All defaults resolve to `starter` when a plan is missing or unknown.

### Starter
- Model tier: `standard` (fast model only)
- Max files: 50
- Max storage: 100 MB
- Max scopes: 5
- Max LLM tokens: 1,000,000
- Team seats: 1
- Web crawl: enabled

### Pro
- Model tier: `premium` (fast + smart models)
- Max files: 2,000
- Max storage: 10,240 MB (10 GB)
- Max scopes: 100
- Max LLM tokens: 10,000,000
- Team seats: 5
- Web crawl: enabled

### Enterprise
- Model tier: `premium` (fast + smart models)
- Max files: 100,000
- Max storage: 1 TB
- Max scopes: 1,000
- Max LLM tokens: 100,000,000
- Team seats: 100
- Web crawl: enabled

## Model Access by Tier
Routing logic in `backend/services/router.py`:
- Standard: always uses `gpt-4o-mini` (fast model).
- Pro/Enterprise: uses `gpt-4o` for complex requests and `gpt-4o-mini` for simple requests.
- Keyword override: prompts containing `refactor`, `architect`, or `optimize` force smart tier.

Failover models are used when configured:
- Grok (xAI): optional fallback when `GROK_API_KEY` and `GROK_MODEL_NAME` are set.
- Groq: fallback when `GROQ_API_KEY` is set.

## Feature Access Gating
The following gates are enforced in code:
- Team seats: `max_team_seats` from `backend/core/quotas.py`.
- Web crawl: `allow_web_crawl` from `backend/core/quotas.py`.
- Premium models: `model_tier` must be `premium` for smart model access.
- S3 connector: flagged as enterprise-only in `backend/connectors/registry.py`.

## Notes
- Token quota enforcement occurs at runtime via `backend/services/usage.py`.
- Identity synthesis enforces `max_scopes` per org in `backend/services/scope_identity.py`.
