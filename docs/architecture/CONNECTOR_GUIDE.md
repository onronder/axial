# Connector Implementation Guide (Enterprise Grade)

This guide defines the required contract and best practices for adding new ingestion connectors. Follow it for every new connector (we expect 10+ new providers).

## Core Contract
- Implement `BaseConnector` (`backend/connectors/base.py`):
  - `validate_config(config: dict) -> bool`: verify tokens/ids/scopes up front.
  - `list_files(config: dict, since: datetime | None) -> Iterator[RemoteFile]`: discovery.
  - `fetch_file_content(file_id: str, config: dict) -> bytes`: download bytes.
- Use standard exceptions:
  - `ConnectorAuthError` for auth/permission failures (no retry).
  - `ConnectorRateLimitError` for 429/limit responses (callers back off).
  - `ConnectorTransientError` for 5xx/timeouts (callers may retry).
- Yield `RemoteFile` with populated metadata when available:
  - `id`, `name`, `mime_type`, `size`, `modified_at`, optional `parent_id`, `web_view_url`.

## Registry and Metadata
- Add an entry to `backend/connectors/registry.py`:
  - `id`, `name`, `capabilities` (e.g., `["incremental_sync"]`, `["binary_content"]`, `["crawl"]`).
  - `rate_limit_rpm` default to inform throttling.
- Ensure the API layer uses the registry to validate connector type (no hardcoded if/else).

## Security Requirements
- **SSRF**: Any HTTP-based connector must block private/loopback/link-local targets. Reuse the Web connector’s `is_safe_url` pattern.
- **Auth Hygiene**: Never log secrets; mask tokens. Validate scopes in `validate_config`.
- **Input Sanitization**: Sanitize paths/ids used in URLs or filenames.
- **Dedup Awareness**: Populate `RemoteFile.size/modified_at` to assist dedup + incremental logic.

## Performance and Resilience
- Respect provider rate limits; surface them via `ConnectorRateLimitError`.
- Use incremental sync where possible: honor the `since` cursor to avoid full crawls.
- Stream downloads; avoid loading massive files in memory if provider SDK allows.
- Provide MIME types when known; otherwise leave `mime_type=None` so downstream detectors can run.

## Integration Steps (Checklist)
1) Add registry entry in `backend/connectors/registry.py`.
2) Implement connector class in `backend/connectors/<provider>.py` inheriting `BaseConnector`.
3) Implement `validate_config` (token presence, scope, URL safety).
4) Implement `list_files`:
   - Accept `config` dict; include auth tokens, root/folder, optional `since`.
   - Yield `RemoteFile` items; avoid raising on single-file errors—log and continue when safe.
   - Apply provider pagination/backoff; map 401/403 -> `ConnectorAuthError`, 429 -> `ConnectorRateLimitError`, 5xx -> `ConnectorTransientError`.
5) Implement `fetch_file_content`:
   - Use the same `config`; fetch bytes; raise the standard exceptions as above.
   - For HTTP sources, re-run SSRF safety on resolved URLs.
6) Register in any factory/loader (API or worker) that instantiates connectors via the registry.
7) Add unit tests (or a helper script) to verify `validate_config`, `list_files` (first page), and one `fetch_file_content`.
8) Add audit log events for connect/disconnect and ingestion/sync flows.

## Template (Skeleton)
```python
from connectors.base import BaseConnector, RemoteFile, ConnectorAuthError, ConnectorRateLimitError, ConnectorTransientError

class FooConnector(BaseConnector):
    def validate_config(self, config: dict) -> bool:
        token = config.get("token")
        if not token:
            return False
        # Optionally: perform a lightweight /me call and return True/False
        return True

    def list_files(self, config: dict, since=None):
        try:
            # call provider API with pagination; honor `since`
            for item in self._list_items(config, since):
                yield RemoteFile(
                    id=item["id"],
                    name=item["name"],
                    mime_type=item.get("mime_type"),
                    size=item.get("size"),
                    modified_at=item.get("modified_at"),
                    parent_id=item.get("parent_id"),
                    web_view_url=item.get("url"),
                )
        except AuthError as e:
            raise ConnectorAuthError(str(e))
        except RateLimitError as e:
            raise ConnectorRateLimitError(str(e))
        except TransientError as e:
            raise ConnectorTransientError(str(e))

    def fetch_file_content(self, file_id: str, config: dict) -> bytes:
        try:
            return self._download_bytes(file_id, config)
        except AuthError as e:
            raise ConnectorAuthError(str(e))
        except RateLimitError as e:
            raise ConnectorRateLimitError(str(e))
        except TransientError as e:
            raise ConnectorTransientError(str(e))
```

## Logging and Observability
- Keep connector logs concise; include `provider`, `file_id`, and `user_id/team_id` when available (no secrets).
- For repeated transient failures, log once per page/batch, not per item.
- Emit audit logs for high-value actions:
  - `connector.connect`, `connector.disconnect`
  - `connector.sync_start`, `connector.sync_success`, `connector.sync_fail`
  - `ingest.queued` for user-triggered ingestion

## Helper Scripts (Recommended)
- Provide a minimal helper under `backend/scripts/<provider>_helper.py` for manual validation.
- The helper should use env-driven config (`<PROVIDER>_HOST`, `<PROVIDER>_USERNAME`, etc.) and avoid logging secrets.

## Error Handling Rules
- Authentication/permission issues: raise `ConnectorAuthError`.
- Rate limits: raise `ConnectorRateLimitError` to trigger backoff.
- Transient network/5xx: raise `ConnectorTransientError`.
- Malformed items: skip with a warning; do not abort full sync unless data integrity is at risk.

## When Adding 10+ Connectors
- Share common utilities (rate limiting, HTTP client, SSRF checks).
- Keep registry metadata up to date (capabilities, rpm).
- Validate configs uniformly (dict-driven; no bespoke signatures).
- Ensure each connector is idempotent and safe to retry on transient errors.
