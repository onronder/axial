# CODEX Wave 2 Connector Design Lock

## Purpose
This document locks the Wave 2 connector scope before implementation. The goal is to remove ambiguity from:

1. Google Drive incremental sync
2. Google Drive shared drive support
3. GitHub incremental sync
4. OAuth token revocation for Dropbox, GitHub, and Box

Wave 2 is no longer a "small fixes" package. It now includes one medium-complexity provider feature set (Google Drive) and one design-sensitive provider feature set (GitHub). Codex should implement this document, not reinterpret product semantics during the build.

## Current Verified State

### Already done in Wave 1
- SFTP now explicitly advertises incremental support: [sftp.py](/Users/onuronder/axial/backend/connectors/sftp.py)
- Notion no longer claims unsupported incremental sync in the registry: [registry.py](/Users/onuronder/axial/backend/connectors/registry.py)

### Verified current gaps
- Google Drive `list_files()` accepts `since` but ignores it: [drive.py](/Users/onuronder/axial/backend/connectors/drive.py)
- Google Drive does not currently pass `supportsAllDrives` / `includeItemsFromAllDrives`: [drive.py](/Users/onuronder/axial/backend/connectors/drive.py)
- GitHub advertises incremental sync but flat listing does not use `since`, and emitted files have `modified_at=None`: [github.py](/Users/onuronder/axial/backend/connectors/github.py)
- Disconnect flow only revokes Google; Notion is explicit no-op; Dropbox/GitHub/Box revoke is missing: [integrations.py](/Users/onuronder/axial/backend/api/v1/integrations.py)

## Locked Scope

### Category A: Google Drive Incremental Sync

#### Decision A1
Google Drive incremental sync will be fully implemented in Wave 2.

#### Decision A2
The semantic definition of Google Drive incremental sync is:

- `since` means "only items whose `modifiedTime` is strictly newer than the supplied timestamp"
- this applies to sync/ingestion listing behavior
- `modified_at` must be populated on emitted `RemoteFile` objects

#### Decision A3
Implementation must use Google Drive API query filtering, not client-side post-filtering where avoidable.

#### Locked implementation requirements
- Update `DriveConnector.list_files()` to pass `since` into the sync implementation
- Update `_list_files_sync()` to include `modifiedTime` in requested fields
- Extend the Drive `q` expression with:
  - existing parent filter
  - `trashed=false`
  - `modifiedTime > '{since_iso}'`
- Parse and populate `RemoteFile.modified_at`
- Preserve existing browsing semantics when `since is None`

#### Notes
- The current API returns folder listings for explorer use and recursive expansion for ingestion use. Wave 2 only changes filtering behavior when `since` is explicitly provided.
- No UI change is required for incremental sync itself.

---

### Category B: Google Drive Shared Drives

#### Decision B1
Shared drive support will be implemented in Wave 2 at the connector/API level. No dedicated shared-drive picker UI is required in Wave 2.

#### Decision B2
Wave 2 shared drive support means:

- files and folders visible to the authenticated user in shared drives can be listed
- shared drive items can be fetched and ingested
- existing explorer/list flows should work without a separate shared-drive selection UI

#### Decision B3
Wave 2 does **not** include a new discovery endpoint or productized "select a shared drive" UX. If a later UX enhancement is needed, it is a separate wave.

#### Locked implementation requirements
- Apply `supportsAllDrives=true` and `includeItemsFromAllDrives=true` to all relevant Drive list/get calls
- Ensure recursive folder traversal uses the same flags
- Ensure metadata fetches for ingestion also use the same flags
- Include `modifiedTime` in relevant fields where incremental logic depends on it
- Do not regress My Drive behavior

#### Affected code paths
- `_drive_list()`: [drive.py](/Users/onuronder/axial/backend/connectors/drive.py)
- `_drive_get()`: [drive.py](/Users/onuronder/axial/backend/connectors/drive.py)
- `_get_all_files_recursive()`: [drive.py](/Users/onuronder/axial/backend/connectors/drive.py)
- `list_files()`: [drive.py](/Users/onuronder/axial/backend/connectors/drive.py)
- `fetch_documents_sync()`: [drive.py](/Users/onuronder/axial/backend/connectors/drive.py)

---

### Category C: GitHub Incremental Sync

#### Decision C1
GitHub incremental sync will be implemented in Wave 2. Capability claim will remain enabled only if implementation is completed and tested in this wave.

#### Decision C2
The semantic definition of GitHub incremental sync is:

- `since` means "only files changed on the selected branch after the supplied timestamp"
- the result set is path-based and de-duplicated
- deleted files are not emitted by the connector listing; they are handled by existing reconciliation/deletion flows
- `modified_at` on emitted `RemoteFile` equals the most recent commit timestamp affecting that path after branch filtering

#### Decision C3
GitHub incremental sync is **not** defined as "compare two full trees and diff everything" for Wave 2. It is defined as a branch commit-history based changed-file listing.

#### Locked implementation approach
- For each enabled repository:
  - determine target branch
  - query commits on that branch since the supplied timestamp
  - collect changed file paths from commit details
  - de-duplicate paths
  - filter paths through existing include/exclude logic
  - emit `RemoteFile` entries only for paths that still exist on the target branch
  - set `modified_at` to latest matching commit date for that path

#### Implementation constraint
- The implementation must use the existing GitHub rate-limiting layer
- commit-history traversal must be pagination-aware
- repositories with high commit volume must be handled without assuming a small fixed commit count
- commit detail fetches should be batched/constrained through the existing limiter rather than naive unbounded fan-out

#### Why this is locked
- Tree API alone does not give file modification timestamps
- the current connector emits `modified_at=None`, so "incremental by tree walk" is underspecified
- commit-history semantics are consistent with user expectations for repository sync

#### Important constraint
- This implementation only applies to sync/full-ingestion listing behavior
- hierarchical browse (`list_files()` folder explorer UX) stays as-is and does not need incremental semantics

---

### Category D: OAuth Token Revocation

#### Decision D1
Wave 2 will add provider-side revoke for:

- Dropbox
- GitHub
- Box

#### Decision D2
Revocation is best-effort and non-blocking.

This means:
- provider revoke failure must not block disconnect
- DB cleanup remains the source of truth
- revoke attempts are logged with warning level on failure

#### Locked provider targets
- Dropbox: `POST https://api.dropboxapi.com/2/auth/token/revoke`
- GitHub: `DELETE https://api.github.com/applications/{client_id}/token` using Basic auth with `client_id:client_secret`
- Box: `POST https://api.box.com/oauth2/revoke`

#### Decision D3
If provider-side revoke requires app credentials and those credentials are not configured, disconnect must continue with warning logging rather than fail closed.

---

## Out of Scope

The following are explicitly **not** Wave 2:

- Microsoft redirect allowlist / SSRF fix
- Web crawler request-time IP pinning
- Google Drive shared-drive picker UX
- GitHub delete reconciliation redesign
- Notion incremental implementation
- Dropbox team-space UX changes

Those remain in later waves.

## Recommended Implementation Order

### Step 1: Low-risk cleanup
- Dropbox revoke
- Box revoke
- GitHub revoke

### Step 2: Google Drive
- incremental sync
- shared drive flags
- modifiedTime propagation

### Step 3: GitHub
- branch commit history query
- changed-file path extraction
- `modified_at` population
- capability stays only if tests pass

### Step 4: Contract and regression tests
- registry assertions
- connector unit tests
- disconnect/revoke tests
- provider-specific incremental sync tests

## Required Tests

### Google Drive
- `since=None` preserves current listing behavior
- `since=timestamp` filters by modified time
- `RemoteFile.modified_at` is populated
- shared drive files are visible in list/get flows
- My Drive behavior is unchanged

### GitHub
- `since=None` preserves current behavior
- incremental path listing only returns changed files on selected branch
- deleted files are not emitted
- `modified_at` is populated from commit metadata
- include/exclude filters still apply

### Revoke
- disconnect attempts provider revoke when access token exists
- revoke failures do not block DB cleanup
- warning logging occurs on revoke failure
- provider-specific HTTP call shape is covered by unit tests/mocks

## Acceptance Criteria

Wave 2 is complete only when all of the following are true:

1. Google Drive incremental sync works with populated `modified_at`
2. Google Drive shared drive items can be listed and fetched without regressions
3. GitHub incremental sync is implemented with branch commit-history semantics
4. Dropbox, GitHub, and Box revoke paths exist and are covered by tests
5. Registry/property capability claims match actual behavior after implementation

## Delivery Rule

Codex should not split this into independent interpretations. The semantics above are locked. If implementation friction reveals a missing dependency or provider constraint, Codex should surface that as a scoped blocker against this document rather than silently changing behavior.
