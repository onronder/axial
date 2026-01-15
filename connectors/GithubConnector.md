# GitHub Connector: Design Specification

> **Status**: ✅ IMPLEMENTED  
> **Version**: 1.0  
> **Date**: 2026-01-15  
> **Author**: Principal Software Architect  
> **Based On**: Dropbox Connector V2 Architecture
> **Implementation**: Complete - All core functionality working

---

## Table of Contents

1. [Executive Summary](#1-executive-summary)
2. [Architectural Challenges & Decisions](#2-architectural-challenges--decisions)
3. [API Strategy Deep Dive](#3-api-strategy-deep-dive)
4. [Content Filtering Strategy](#4-content-filtering-strategy)
5. [Rate Limiting & Quota Management](#5-rate-limiting--quota-management)
6. [Repository Selection UX](#6-repository-selection-ux)
7. [Implementation Specification](#7-implementation-specification)
8. [OAuth Integration](#8-oauth-integration)
9. [Database Requirements](#9-database-requirements)
10. [Testing Strategy](#10-testing-strategy)
11. [Implementation Roadmap](#11-implementation-roadmap)

---

## 1. Executive Summary

### Objective
Design a GitHub connector that ingests **meaningful knowledge** (code + documentation) from repositories while aggressively filtering noise that would degrade vector database quality.

### Context
- **Existing Connectors**: Dropbox, Google Drive, OneDrive, SharePoint, Notion, SFTP, Web
- **Unique Challenge**: GitHub repositories contain mixed content—valuable source code alongside build artifacts, dependencies, and binaries
- **Target**: Enterprise-grade integration with intelligent content filtering

### Key Architectural Decisions

| Decision | Approach | Rationale |
|----------|----------|-----------|
| Tree Traversal | Git Trees API (recursive) | Single request for entire repo structure vs N requests |
| Content Filtering | Whitelist + Gitignore Respect | Binary exclusion + user-controlled focus |
| Deduplication | Git blob SHA (native) | GitHub already provides content hashes |
| Content Fetch | Raw media type (`application/vnd.github.v3.raw`) | Avoid Base64 decode overhead |
| Repo Selection | Explicit list (`["owner/repo-a", "org/repo-b"]`) | Prevent accidental full-org sync |

---

## 2. Architectural Challenges & Decisions

### Challenge A: The "Noise" Problem (Filtering Strategy)

**Risk**: Ingesting `node_modules/`, `target/`, `.git/`, `vendor/`, `dist/`, or binary assets (`.png`, `.exe`, `.woff`) ruins vector database quality and burns embedding tokens.

**Decision: Hybrid Whitelist + Blacklist Strategy**

```
┌─────────────────────────────────────────────────────────────┐
│                    CONTENT FILTER PIPELINE                   │
├─────────────────────────────────────────────────────────────┤
│  1. Path Blacklist (hard reject)                            │
│     └── node_modules/, .git/, __pycache__/, vendor/, etc.   │
│                                                              │
│  2. Extension Whitelist (allow only these)                  │
│     └── .py, .ts, .js, .tsx, .jsx, .go, .rs, .java, .md...  │
│                                                              │
│  3. Size Filter                                              │
│     └── Skip files > 1MB (binary detection)                 │
│                                                              │
│  4. Binary Detection                                         │
│     └── Check first 8KB for null bytes                      │
└─────────────────────────────────────────────────────────────┘
```

**Whitelist vs Blacklist Analysis**:

| Approach | Pros | Cons |
|----------|------|------|
| **Whitelist Only** | Precise control, zero noise | May miss valuable config files (.yaml, .toml) |
| **Blacklist Only** | Inclusive | Can't predict all junk directories |
| **Hybrid (Chosen)** | Best of both; blacklist paths, whitelist extensions | Requires tuning |

**Proposed `CodeFileFilter` Class**:

```python
class CodeFileFilter:
    """Filter for high-value source code files."""
    
    # Hard-reject paths (checked first)
    PATH_BLACKLIST = {
        "node_modules/", ".git/", "__pycache__/", ".pytest_cache/",
        "vendor/", "target/", "build/", "dist/", ".next/", ".nuxt/",
        ".venv/", "venv/", "env/", ".tox/", ".eggs/", "*.egg-info/",
        "coverage/", ".nyc_output/", ".cache/", ".parcel-cache/",
    }
    
    # Allowed extensions (code + documentation)
    EXTENSION_WHITELIST = {
        # Programming Languages
        ".py", ".pyi",          # Python
        ".ts", ".tsx", ".mts",  # TypeScript
        ".js", ".jsx", ".mjs",  # JavaScript
        ".go",                  # Go
        ".rs",                  # Rust
        ".java", ".kt", ".scala", # JVM
        ".rb",                  # Ruby
        ".php",                 # PHP
        ".cs",                  # C#
        ".cpp", ".cc", ".c", ".h", ".hpp",  # C/C++
        ".swift",              # Swift
        ".sql",                # SQL
        ".sh", ".bash", ".zsh", # Shell
        
        # Documentation
        ".md", ".mdx", ".rst", ".txt",
        ".adoc", ".asciidoc",
        
        # Configuration (valuable for understanding projects)
        ".yaml", ".yml", ".toml", ".json", ".xml",
        ".env.example", ".gitignore", ".dockerignore",
        "Dockerfile", "Makefile", "Rakefile",
        ".ini", ".cfg", ".conf",
        
        # Web
        ".html", ".css", ".scss", ".sass", ".less",
        ".vue", ".svelte",
        
        # Data/ML (text-based)
        ".ipynb",  # Jupyter notebooks (JSON-based)
    }
    
    # Maximum file size (bytes) - files larger are likely binaries/data
    MAX_FILE_SIZE = 1 * 1024 * 1024  # 1MB
    
    def should_include(self, path: str, size: int | None) -> bool:
        """Determine if file should be ingested."""
        # 1. Path blacklist check
        for blocked in self.PATH_BLACKLIST:
            if blocked in path or path.startswith(blocked.rstrip("/")):
                return False
        
        # 2. Size check
        if size and size > self.MAX_FILE_SIZE:
            return False
        
        # 3. Extension whitelist check
        ext = self._get_extension(path)
        if ext not in self.EXTENSION_WHITELIST:
            # Special case: extensionless files like Dockerfile, Makefile
            filename = path.rsplit("/", 1)[-1]
            if filename not in self.EXTENSION_WHITELIST:
                return False
        
        return True
    
    def _get_extension(self, path: str) -> str:
        """Extract file extension (lowercase)."""
        if "." not in path.rsplit("/", 1)[-1]:
            return ""
        return "." + path.rsplit(".", 1)[-1].lower()
```

---

### Challenge B: API Strategy (Tree Traversal)

**Options Analyzed**:

| Endpoint | Requests | Latency | Limitations |
|----------|----------|---------|-------------|
| `GET /repos/{owner}/{repo}/contents/{path}` | N (per directory) | High | 1 request/folder, very slow |
| `GET /repos/{owner}/{repo}/git/trees/{sha}?recursive=1` | 1 | Low | Truncated at 100k items, 7MB response |

**Decision: Git Trees API with Truncation Handling**

```
┌──────────────────────────────────────────────────────────────┐
│               TREE TRAVERSAL STRATEGY                         │
├──────────────────────────────────────────────────────────────┤
│  1. Fetch default branch SHA                                 │
│     GET /repos/{owner}/{repo}/branches/{default_branch}      │
│                                                               │
│  2. Fetch full tree (single request)                         │
│     GET /repos/{owner}/{repo}/git/trees/{sha}?recursive=1    │
│                                                               │
│  3. Check `truncated` flag                                   │
│     └── If true: Fall back to non-recursive + manual DFS     │
│     └── If false: Process tree entries directly              │
│                                                               │
│  4. Filter entries (type=blob, extension match, path check)  │
│                                                               │
│  5. Fetch content for filtered blobs only                    │
└──────────────────────────────────────────────────────────────┘
```

**Truncation Handling Strategy**:

For repositories exceeding 100k items (rare but possible in monorepos):

```python
def _fetch_tree(self, config: dict, sha: str) -> Iterator[dict]:
    """Fetch tree with truncation fallback."""
    url = f"{GITHUB_API_BASE}/repos/{config['repo']}/git/trees/{sha}"
    
    # Try recursive first
    result = self._request(config, url, params={"recursive": "1"})
    
    if not result.get("truncated"):
        # Happy path: full tree in one request
        yield from result.get("tree", [])
        return
    
    # Fallback: non-recursive traversal
    logger.warning(f"⚠️ [GitHub] Tree truncated, using DFS fallback for {config['repo']}")
    yield from self._fetch_tree_dfs(config, sha)

def _fetch_tree_dfs(self, config: dict, sha: str, path: str = "") -> Iterator[dict]:
    """Depth-first traversal for large repos."""
    url = f"{GITHUB_API_BASE}/repos/{config['repo']}/git/trees/{sha}"
    result = self._request(config, url)  # non-recursive
    
    for entry in result.get("tree", []):
        entry_path = f"{path}/{entry['path']}" if path else entry["path"]
        
        if entry["type"] == "blob":
            yield {**entry, "path": entry_path}
        elif entry["type"] == "tree":
            # Skip blacklisted directories early (save API calls)
            if not self._filter.is_path_blacklisted(entry_path + "/"):
                yield from self._fetch_tree_dfs(config, entry["sha"], entry_path)
```

---

### Challenge C: Content Fetching (Raw vs JSON/Base64)

**Options**:

| Method | Response | Overhead | Limit |
|--------|----------|----------|-------|
| Contents API (JSON) | Base64 encoded | Decode required + 33% larger | 1MB |
| Blobs API (JSON) | Base64 encoded | Decode required | 100MB |
| Raw Media Type | Raw bytes | Zero overhead | 100MB |

**Decision: Raw Media Type via Blobs API**

```python
def fetch_blob_raw(self, config: dict, sha: str) -> bytes:
    """Fetch blob content as raw bytes (no Base64)."""
    url = f"{GITHUB_API_BASE}/repos/{config['repo']}/git/blobs/{sha}"
    headers = self._get_headers(config)
    headers["Accept"] = "application/vnd.github.v3.raw"
    
    with connector_fetch_limit("github"):
        response = self._request_with_retry(
            "GET", url, headers=headers, stream=True
        )
    
    if response.status_code == 404:
        raise ItemNotFoundError(f"Blob {sha} not found")
    
    response.raise_for_status()
    return response.content
```

**Alternative for Content Inspection** (when we need metadata too):

```python
def fetch_blob_with_metadata(self, config: dict, sha: str) -> tuple[bytes, dict]:
    """Fetch blob with metadata (for logging/audit)."""
    url = f"{GITHUB_API_BASE}/repos/{config['repo']}/git/blobs/{sha}"
    headers = self._get_headers(config)
    headers["Accept"] = "application/vnd.github.v3+json"
    
    result = self._request(config, url)
    
    # Decode Base64 content
    import base64
    content = base64.b64decode(result["content"])
    
    return content, {
        "sha": result["sha"],
        "size": result["size"],
        "encoding": result["encoding"],
    }
```

---

### Challenge D: Rate Limiting (Strict Management)

**GitHub Rate Limits**:

| Tier | Limit | Reset |
|------|-------|-------|
| Unauthenticated | 60 req/hour | Rolling |
| Authenticated (OAuth) | 5,000 req/hour | Rolling |
| GitHub App Installation | 5,000 req/hour/installation | Rolling |
| Secondary Rate Limits | Variable | Retry-After header |

**Large Repo Cost Analysis**:

| Operation | Requests | Example (10k files, 500 pass filter) |
|-----------|----------|-------------------------------------|
| Get branch | 1 | 1 |
| Get tree (recursive) | 1 | 1 |
| Fetch blobs | N (filtered) | 500 |
| **Total** | | **502 requests** |

A single large repo sync consumes ~10% of hourly quota. For 10 repos, we risk exhaustion.

**Decision: Aggressive Rate Management with Partial Sync**

```python
class GitHubRateLimiter:
    """Track and manage GitHub API rate limits."""
    
    RESERVE_THRESHOLD = 500  # Stop syncing if fewer than 500 requests remain
    AGGRESSIVE_BACKOFF = True
    
    def __init__(self):
        self.remaining = 5000
        self.reset_at = None
    
    def update_from_headers(self, response: requests.Response):
        """Update limits from response headers."""
        self.remaining = int(response.headers.get("X-RateLimit-Remaining", self.remaining))
        reset_ts = response.headers.get("X-RateLimit-Reset")
        if reset_ts:
            self.reset_at = datetime.fromtimestamp(int(reset_ts), tz=timezone.utc)
    
    def should_pause(self) -> bool:
        """Check if we should pause to preserve quota."""
        return self.remaining < self.RESERVE_THRESHOLD
    
    def get_wait_time(self) -> float:
        """Calculate wait time until reset."""
        if not self.reset_at:
            return 60.0
        delta = (self.reset_at - datetime.now(timezone.utc)).total_seconds()
        return max(0, delta)
    
    def handle_secondary_limit(self, response: requests.Response) -> float:
        """Handle secondary rate limits (abuse detection)."""
        retry_after = response.headers.get("Retry-After")
        if retry_after:
            return float(retry_after)
        
        # GitHub recommends exponential backoff
        return 60.0  # Default to 1 minute
```

**Partial Sync Strategy**:

```python
def list_files(self, config: dict, since: datetime | None = None) -> Iterator[RemoteFile]:
    """List files with quota-aware partial sync."""
    
    for repo_spec in config.get("repositories", []):
        if self._rate_limiter.should_pause():
            logger.warning(
                f"⏸️ [GitHub] Pausing sync - {self._rate_limiter.remaining} requests remaining. "
                f"Resuming after {self._rate_limiter.reset_at}"
            )
            # Yield a "partial" marker for the job system
            yield RemoteFile(
                id="__PARTIAL_SYNC__",
                name=f"Sync paused: {repo_spec}",
                mime_type="application/x-partial-sync",
                size=None,
                modified_at=datetime.now(timezone.utc),
            )
            break
        
        yield from self._list_repo_files(config, repo_spec, since)
```

---

### Challenge E: Repository Selection UX

**Problem**: A user may have access to hundreds of repositories (personal + organization). We cannot sync all by default.

**Decision: Explicit Repository Selection**

**Configuration Schema**:

```python
@dataclass
class GitHubConnectorConfig:
    """Configuration for GitHub connector."""
    
    # OAuth credentials (resolved from integration)
    access_token: str
    
    # Repository selection (REQUIRED - no default)
    repositories: list[str]  # ["owner/repo", "org/repo"]
    
    # Optional branch override (default: repo's default branch)
    branch_overrides: dict[str, str] = field(default_factory=dict)
    # Example: {"owner/repo": "develop"}
    
    # Optional path filters (narrow scope within repos)
    include_paths: dict[str, list[str]] = field(default_factory=dict)
    # Example: {"owner/repo": ["src/", "docs/"]}
    
    # Feature flags
    include_forks: bool = False
    include_archived: bool = False
```

**Repository Discovery Endpoint** (for UI):

```python
@router.get("/github/repositories")
async def list_available_repos(
    user_id: str = Depends(require_editor)
) -> list[dict]:
    """
    List repositories user has access to for selection.
    
    Returns:
        List of {owner, name, full_name, description, is_fork, is_archived, visibility}
    """
    connector = GitHubConnector()
    config = connector._resolve_config({"user_id": user_id})
    
    repos = []
    # Fetch user's own repos
    for repo in connector._fetch_user_repos(config):
        repos.append({
            "owner": repo["owner"]["login"],
            "name": repo["name"],
            "full_name": repo["full_name"],
            "description": repo.get("description"),
            "is_fork": repo.get("fork", False),
            "is_archived": repo.get("archived", False),
            "visibility": repo.get("visibility", "private"),
            "default_branch": repo.get("default_branch", "main"),
        })
    
    # Fetch org repos (if user has org memberships)
    for org in connector._fetch_user_orgs(config):
        for repo in connector._fetch_org_repos(config, org["login"]):
            repos.append({...})
    
    return repos
```

**Frontend Flow**:

```
┌─────────────────────────────────────────────────────────────┐
│               GITHUB CONNECTOR SETUP FLOW                    │
├─────────────────────────────────────────────────────────────┤
│  1. User clicks "Connect GitHub"                            │
│  2. OAuth redirect → authorization                          │
│  3. Callback → store tokens                                 │
│  4. Show Repository Selection Modal:                        │
│     ┌─────────────────────────────────────────────┐         │
│     │ Select repositories to sync:                │         │
│     │ ┌─────────────────────────────────────────┐ │         │
│     │ │ ☑ myuser/project-a          [private]  │ │         │
│     │ │ ☑ myuser/project-b          [public]   │ │         │
│     │ │ ☐ myuser/dotfiles           [private]  │ │         │
│     │ │ ── Organization: acme-corp ──          │ │         │
│     │ │ ☑ acme-corp/platform        [private]  │ │         │
│     │ │ ☐ acme-corp/legacy-app (archived)      │ │         │
│     │ └─────────────────────────────────────────┘ │         │
│     │                    [Save Selection]         │         │
│     └─────────────────────────────────────────────┘         │
│  5. Store selected repos in integration credentials         │
│  6. Trigger initial sync job                                │
└─────────────────────────────────────────────────────────────┘
```

---

## 3. API Strategy Deep Dive

### API Endpoints Used

| Endpoint | Method | Purpose | Rate Cost |
|----------|--------|---------|-----------|
| `GET /user` | GET | Validate token, get user info | 1 |
| `GET /user/repos` | GET | List user's repositories | 1/page |
| `GET /user/orgs` | GET | List user's organizations | 1 |
| `GET /orgs/{org}/repos` | GET | List org repositories | 1/page |
| `GET /repos/{owner}/{repo}` | GET | Get repo metadata | 1 |
| `GET /repos/{owner}/{repo}/branches/{branch}` | GET | Get branch SHA | 1 |
| `GET /repos/{owner}/{repo}/git/trees/{sha}` | GET | List repo tree | 1 |
| `GET /repos/{owner}/{repo}/git/blobs/{sha}` | GET | Fetch file content | 1 |
| `GET /repos/{owner}/{repo}/commits` | GET | Get commit history (for since filter) | 1/page |

### Sync Flow Diagram

```
┌─────────────────────────────────────────────────────────────┐
│                    GITHUB SYNC FLOW                          │
├─────────────────────────────────────────────────────────────┤
│                                                              │
│  FOR EACH selected repository:                              │
│  │                                                           │
│  ├─► 1. Get default branch SHA                              │
│  │      GET /repos/{owner}/{repo}/branches/{branch}         │
│  │                                                           │
│  ├─► 2. Fetch recursive tree (single request)              │
│  │      GET /repos/{owner}/{repo}/git/trees/{sha}?recursive=1│
│  │                                                           │
│  ├─► 3. For each tree entry (type=blob):                   │
│  │   │                                                       │
│  │   ├─► 3a. Apply CodeFileFilter                          │
│  │   │       - Path blacklist?  → SKIP                      │
│  │   │       - Extension whitelist? → PASS                  │
│  │   │       - Size > 1MB? → SKIP                           │
│  │   │                                                       │
│  │   ├─► 3b. Check SHA against DB (dedup)                  │
│  │   │       - SHA exists in documents.content_hash? → SKIP │
│  │   │                                                       │
│  │   └─► 3c. Yield RemoteFile for ingestion                │
│  │                                                           │
│  └─► 4. Fetch content for yielded files                    │
│          GET /repos/{owner}/{repo}/git/blobs/{sha}          │
│          Accept: application/vnd.github.v3.raw              │
│                                                              │
└─────────────────────────────────────────────────────────────┘
```

---

## 4. Content Filtering Strategy

### Filter Configuration (User-Customizable)

```python
# Default filter settings (stored in integration credentials)
DEFAULT_FILTER_CONFIG = {
    # Extension whitelist (can be customized per integration)
    "allowed_extensions": [
        # Code
        ".py", ".ts", ".js", ".tsx", ".jsx", ".go", ".rs", ".java",
        ".rb", ".php", ".cs", ".cpp", ".c", ".h", ".swift", ".kt",
        ".scala", ".sql", ".sh", ".bash",
        # Docs
        ".md", ".mdx", ".rst", ".txt", ".adoc",
        # Config
        ".yaml", ".yml", ".toml", ".json", ".xml", ".ini",
        ".dockerfile", ".gitignore", ".env.example",
        # Web
        ".html", ".css", ".scss", ".vue", ".svelte",
    ],
    
    # Path blacklist (always excluded)
    "blocked_paths": [
        "node_modules/", ".git/", "__pycache__/", "vendor/",
        "target/", "build/", "dist/", ".next/", ".nuxt/",
        ".venv/", "venv/", ".tox/", "coverage/", ".cache/",
        "*.min.js", "*.min.css",  # Minified assets
    ],
    
    # Size limits
    "max_file_size_bytes": 1_000_000,  # 1MB
    
    # Binary detection
    "skip_binary_files": True,
}
```

### Binary Detection

```python
def is_likely_binary(content_sample: bytes) -> bool:
    """
    Detect binary files by checking for null bytes.
    
    GitHub API returns Base64 for all files, but we can decode
    first 8KB and check for binary indicators.
    """
    if not content_sample:
        return False
    
    # Check first 8KB for null bytes
    sample = content_sample[:8192]
    
    # Null bytes are a strong binary indicator
    if b'\x00' in sample:
        return True
    
    # High ratio of non-printable chars suggests binary
    non_printable = sum(1 for b in sample if b < 32 and b not in (9, 10, 13))
    if len(sample) > 0 and (non_printable / len(sample)) > 0.3:
        return True
    
    return False
```

---

## 5. Rate Limiting & Quota Management

### Request Budget Calculator

```python
def estimate_sync_cost(repositories: list[str], file_counts: dict[str, int]) -> dict:
    """
    Estimate API request cost for a sync operation.
    
    Args:
        repositories: List of repos to sync
        file_counts: Estimated file counts per repo (from previous syncs)
    
    Returns:
        {
            "estimated_requests": int,
            "percentage_of_hourly_quota": float,
            "recommended_batch_size": int,
        }
    """
    base_cost = len(repositories) * 2  # branch + tree per repo
    
    # Assume 10% of files pass filter (conservative)
    content_cost = sum(
        int(count * 0.1) 
        for repo, count in file_counts.items() 
        if repo in repositories
    )
    
    total = base_cost + content_cost
    
    return {
        "estimated_requests": total,
        "percentage_of_hourly_quota": (total / 5000) * 100,
        "recommended_batch_size": max(1, 5000 // (total or 1)),
        "safe_to_proceed": total < 4500,  # Keep 500 buffer
    }
```

### Adaptive Rate Limiting

```python
class AdaptiveRateLimiter:
    """
    Adaptive rate limiter that slows down as quota depletes.
    """
    
    def __init__(self):
        self.remaining = 5000
        self.reset_at = None
        self.request_count = 0
        self.last_request = None
    
    def get_delay(self) -> float:
        """Calculate delay before next request."""
        if self.remaining > 2500:
            return 0.0  # Full speed
        elif self.remaining > 1000:
            return 0.1  # Slight throttle
        elif self.remaining > 500:
            return 0.5  # Moderate throttle
        else:
            # Aggressive throttle - spread remaining requests
            if self.reset_at:
                time_to_reset = (self.reset_at - datetime.now(timezone.utc)).total_seconds()
                return max(0, time_to_reset / (self.remaining or 1))
            return 2.0
    
    async def wait_if_needed(self):
        """Async wait based on rate limit status."""
        delay = self.get_delay()
        if delay > 0:
            await asyncio.sleep(delay)
```

---

## 6. Repository Selection UX

### Integration Credentials Schema

```json
{
    "type": "object",
    "properties": {
        "selected_repositories": {
            "type": "array",
            "items": {
                "type": "object",
                "properties": {
                    "full_name": {"type": "string"},
                    "branch": {"type": "string"},
                    "include_paths": {"type": "array", "items": {"type": "string"}},
                    "enabled": {"type": "boolean"}
                },
                "required": ["full_name", "enabled"]
            }
        },
        "filter_config": {
            "type": "object",
            "properties": {
                "allowed_extensions": {"type": "array"},
                "blocked_paths": {"type": "array"},
                "max_file_size_bytes": {"type": "integer"}
            }
        },
        "last_sync": {
            "type": "object",
            "properties": {
                "timestamp": {"type": "string", "format": "date-time"},
                "commit_shas": {"type": "object"}
            }
        }
    }
}
```

### Example Integration Record

```json
{
    "id": "uuid-123",
    "user_id": "user-456",
    "connector_definition_id": "github-def-id",
    "access_token": "encrypted:...",
    "refresh_token": "encrypted:...",
    "expires_at": "2026-01-15T12:00:00Z",
    "credentials": {
        "selected_repositories": [
            {
                "full_name": "acme-corp/platform",
                "branch": "main",
                "include_paths": ["src/", "docs/"],
                "enabled": true
            },
            {
                "full_name": "user/personal-project",
                "branch": "develop",
                "include_paths": [],
                "enabled": true
            }
        ],
        "filter_config": {
            "allowed_extensions": [".py", ".ts", ".md", ".yaml"],
            "blocked_paths": ["node_modules/", "tests/fixtures/"],
            "max_file_size_bytes": 500000
        },
        "last_sync": {
            "timestamp": "2026-01-14T10:00:00Z",
            "commit_shas": {
                "acme-corp/platform": "abc123...",
                "user/personal-project": "def456..."
            }
        }
    }
}
```

---

## 7. Implementation Specification

### Module Structure

**File**: `backend/connectors/github.py`

```
GitHubConnector (EnhancedConnector, BaseConnector)
│
├── Properties
│   ├── connector_type → SourceType.GITHUB
│   ├── supports_incremental_sync → True
│   └── supports_batch_fetch → True
│
├── Configuration & Auth
│   ├── validate_config(config: dict) → bool
│   ├── _verify_token(access_token: str) → dict
│   ├── _resolve_config(config: dict) → dict
│   └── _load_integration(config: dict) → dict
│
├── HTTP Layer (Private)
│   ├── _request(config, url, **kwargs) → dict | bytes
│   ├── _request_with_retry(method, url, **kwargs) → Response
│   ├── _get_headers(config) → dict
│   ├── _handle_rate_limit(response) → None
│   └── _parse_link_header(header) → dict
│
├── Repository Discovery
│   ├── list_available_repositories(config) → list[dict]
│   ├── _fetch_user_repos(config) → Iterator[dict]
│   ├── _fetch_user_orgs(config) → Iterator[dict]
│   └── _fetch_org_repos(config, org) → Iterator[dict]
│
├── Tree Traversal
│   ├── _get_branch_sha(config, repo, branch) → str
│   ├── _fetch_tree(config, repo, sha) → Iterator[dict]
│   └── _fetch_tree_dfs(config, repo, sha, path) → Iterator[dict]
│
├── Content Filtering
│   ├── _filter: CodeFileFilter
│   └── _should_include_entry(entry) → bool
│
├── File Discovery (BaseConnector)
│   ├── list_files(config, since) → Iterator[RemoteFile]
│   └── _entry_to_remote_file(entry, repo) → RemoteFile
│
├── Content Fetching (BaseConnector + EnhancedConnector)
│   ├── fetch_file_content(file_id, config) → bytes
│   ├── fetch_blob_raw(config, repo, sha) → bytes
│   ├── fetch_documents(item_ids, credentials, **kwargs) → AsyncIterator[SourceDocument]
│   ├── fetch_documents_sync(item_ids, credentials, **kwargs) → Iterator[SourceDocument]
│   └── _build_source_document(config, entry, content) → SourceDocument
│
├── Incremental Sync
│   ├── _get_commits_since(config, repo, since) → list[dict]
│   └── _get_changed_files(config, repo, since) → set[str]
│
└── Rate Limiting
    ├── _rate_limiter: GitHubRateLimiter
    └── _check_quota() → bool
```

### RemoteFile ID Schema

To uniquely identify files across repositories:

```
{repo_full_name}:{blob_sha}:{path}
```

Example:
```
acme-corp/platform:abc123def456:src/main.py
```

Parsed as:
```python
@dataclass
class GitHubFileId:
    repo: str
    sha: str
    path: str
    
    @classmethod
    def from_string(cls, id_str: str) -> "GitHubFileId":
        parts = id_str.split(":", 2)
        return cls(repo=parts[0], sha=parts[1], path=parts[2])
    
    def __str__(self) -> str:
        return f"{self.repo}:{self.sha}:{self.path}"
```

### Duplicate Detection (Native SHA)

GitHub provides blob SHAs that are content-addressable (like our SHA-256):

```python
def _is_duplicate(self, supabase, blob_sha: str, repo: str, path: str) -> bool:
    """
    Check if blob already ingested.
    
    Note: Git blob SHA is SHA-1 of "blob {size}\0{content}", not raw SHA-256.
    We store both for compatibility.
    """
    # Primary check: exact blob SHA
    result = supabase.table("documents").select("id").eq(
        "metadata->>git_blob_sha", blob_sha
    ).limit(1).execute()
    
    if result.data:
        logger.debug(f"♻️ [GitHub] Duplicate blob {blob_sha[:8]}... ({path})")
        return True
    
    return False
```

---

## 8. OAuth Integration

### Authorization URL

```
https://github.com/login/oauth/authorize
  ?client_id={GITHUB_CLIENT_ID}
  &redirect_uri={GITHUB_REDIRECT_URI}
  &scope=repo%20read:org
  &state={state_token}
```

### Token Exchange

```http
POST https://github.com/login/oauth/access_token
Accept: application/json
Content-Type: application/x-www-form-urlencoded

client_id={CLIENT_ID}
&client_secret={CLIENT_SECRET}
&code={AUTH_CODE}
&redirect_uri={REDIRECT_URI}
```

**Response**:
```json
{
    "access_token": "gho_xxxxxxxxxxxx",
    "token_type": "bearer",
    "scope": "repo,read:org"
}
```

### OAuth Scopes

| Scope | Access | Required |
|-------|--------|----------|
| `repo` | Full access to private repos | For private repos |
| `public_repo` | Access to public repos only | Minimum |
| `read:org` | Read org membership | For org repos |
| `read:user` | Read user profile | Optional |

**Recommended**: `repo` + `read:org` for full functionality

### Token Refresh

**Important**: GitHub OAuth tokens do NOT expire by default. However, GitHub Apps use expiring tokens.

For OAuth Apps (our case):
```python
def refresh_github_token(...) -> tuple[str, Optional[str]]:
    """
    GitHub OAuth tokens don't expire.
    This method validates the token is still active.
    """
    # GitHub tokens don't expire, but can be revoked
    # We just verify the token is still valid
    response = requests.get(
        "https://api.github.com/user",
        headers={"Authorization": f"Bearer {access_token}"},
        timeout=10
    )
    
    if response.status_code == 401:
        raise TokenRefreshError("GitHub token revoked or invalid")
    
    return access_token, None  # No expiry
```

---

## 9. Database Requirements

### Connector Definition Migration

```sql
-- Add GitHub connector definition
INSERT INTO connector_definitions (
    type,
    name,
    oauth_required,
    config_schema,
    created_at
) VALUES (
    'github',
    'GitHub',
    true,
    '{
        "type": "object",
        "properties": {
            "selected_repositories": {
                "type": "array",
                "description": "List of repositories to sync"
            },
            "filter_config": {
                "type": "object",
                "description": "File filtering configuration"
            }
        },
        "required": ["selected_repositories"]
    }',
    NOW()
) ON CONFLICT (type) DO NOTHING;
```

### Document Metadata Schema

For GitHub-sourced documents, store:

```sql
-- Example metadata stored in documents.metadata
{
    "source": "github",
    "repository": "acme-corp/platform",
    "branch": "main",
    "path": "src/core/auth.py",
    "git_blob_sha": "abc123def456...",
    "commit_sha": "789xyz...",
    "commit_date": "2026-01-14T10:00:00Z",
    "author": "developer@acme.com",
    "language": "python"
}
```

### Registry Entry

```python
# backend/connectors/registry.py

CONNECTOR_REGISTRY = {
    # ... existing entries ...
    
    "github": {
        "id": "github",
        "name": "GitHub",
        "capabilities": ["incremental_sync", "text_content", "code_aware"],
        "rate_limit_rpm": 83,  # 5000/hour = 83/minute
    },
}
```

### Config Settings

```python
# backend/core/config.py

# GitHub OAuth
GITHUB_CLIENT_ID: Optional[str] = None
GITHUB_CLIENT_SECRET: Optional[str] = None
GITHUB_REDIRECT_URI: Optional[str] = None

# Connector Concurrency
CONNECTOR_CONCURRENCY_GITHUB: int = 2
```

### Concurrency Limits

```python
# backend/connectors/limits.py

def _get_limit(connector_type: str) -> int:
    # ... existing code ...
    if normalized == "github":
        return settings.CONNECTOR_CONCURRENCY_GITHUB
```

---

## 10. Testing Strategy

### Unit Tests

| Test Case | Description |
|-----------|-------------|
| `test_validate_config_with_token` | Valid token passes validation |
| `test_validate_config_missing_repos` | Reject config without selected_repositories |
| `test_code_filter_extension_whitelist` | Only allowed extensions pass |
| `test_code_filter_path_blacklist` | Blocked paths rejected |
| `test_code_filter_size_limit` | Large files rejected |
| `test_binary_detection` | Binary files detected and skipped |
| `test_tree_fetch_recursive` | Full tree fetched in one request |
| `test_tree_fetch_truncated_fallback` | DFS fallback on truncation |
| `test_blob_fetch_raw` | Raw content without Base64 |
| `test_rate_limit_tracking` | Headers properly parsed |
| `test_rate_limit_pause` | Sync pauses at threshold |
| `test_incremental_sync_by_sha` | Only changed files synced |
| `test_file_id_encoding` | repo:sha:path format |

### Integration Tests

| Test Scenario | Description |
|---------------|-------------|
| OAuth Flow | Full connect → callback → store flow |
| Repository Discovery | List user + org repos |
| Small Repo Sync | < 1000 files, full sync |
| Large Repo Sync | 10k+ files, verify filtering |
| Rate Limit Recovery | Trigger pause, verify resume |
| Incremental Sync | Second sync only fetches changes |

### Mock Fixtures

```python
@pytest.fixture
def mock_github_api():
    """Mock GitHub API responses."""
    with responses.RequestsMock() as rsps:
        # GET /user
        rsps.add(
            responses.GET,
            "https://api.github.com/user",
            json={"login": "testuser", "id": 12345},
            status=200,
            headers={
                "X-RateLimit-Remaining": "4999",
                "X-RateLimit-Reset": str(int(time.time()) + 3600),
            }
        )
        
        # GET /repos/{owner}/{repo}/git/trees/{sha}
        rsps.add(
            responses.GET,
            re.compile(r"https://api\.github\.com/repos/.+/git/trees/.+"),
            json={
                "sha": "abc123",
                "tree": [
                    {"path": "src/main.py", "type": "blob", "sha": "def456", "size": 1000},
                    {"path": "node_modules/.bin", "type": "tree", "sha": "xyz789"},
                    {"path": "README.md", "type": "blob", "sha": "ghi012", "size": 500},
                ],
                "truncated": False,
            },
            status=200,
        )
        
        # GET /repos/{owner}/{repo}/git/blobs/{sha}
        rsps.add(
            responses.GET,
            re.compile(r"https://api\.github\.com/repos/.+/git/blobs/.+"),
            body=b"# Hello World\nprint('test')",
            status=200,
            content_type="application/vnd.github.v3.raw",
        )
        
        yield rsps
```

---

## 11. Implementation Roadmap

### Phase 1: Foundation (Day 1)

| Task | File | Effort |
|------|------|--------|
| Add GitHub config settings | `backend/core/config.py` | 15 min |
| Add registry entry | `backend/connectors/registry.py` | 5 min |
| Add concurrency limit | `backend/connectors/limits.py` | 5 min |
| Add SourceType.GITHUB | `backend/connectors/enhanced.py` | 5 min |
| Database migration | `supabase/migrations/XXX_github.sql` | 10 min |

### Phase 2: Core Connector (Day 1-2)

| Task | Effort |
|------|--------|
| Create `github.py` module structure | 30 min |
| Implement `CodeFileFilter` class | 1 hr |
| Implement HTTP layer (`_request`, rate limit tracking) | 1 hr |
| Implement `validate_config` | 30 min |
| Implement tree traversal (recursive + DFS fallback) | 1.5 hr |
| Implement `list_files` with filtering | 1 hr |
| Implement `fetch_file_content` / `fetch_blob_raw` | 30 min |
| Implement `fetch_documents_sync` | 1 hr |

### Phase 3: OAuth & API Integration (Day 2-3)

| Task | Effort |
|------|--------|
| Add OAuth callback endpoint | 1 hr |
| Add repository discovery endpoint | 1 hr |
| Add token validation to `OAuthTokenManager` | 30 min |
| Add disconnect endpoint | 15 min |
| Implement incremental sync (commit-based) | 1.5 hr |

### Phase 4: Testing (Day 3-4)

| Task | Effort |
|------|--------|
| Unit tests | 2.5 hrs |
| Integration tests | 1.5 hr |
| Manual E2E testing | 1 hr |

### Phase 5: Frontend (Day 4-5)

| Task | Effort |
|------|--------|
| Add GitHub to ConnectorsList | 30 min |
| Repository selection modal | 2 hrs |
| GitHub icon/branding | 15 min |
| Connect button integration | 30 min |

### Total Estimated Effort: 18-22 hours

---

## Appendix A: GitHub API Reference

### Useful Documentation Links

- [REST API Reference](https://docs.github.com/en/rest)
- [Git Trees API](https://docs.github.com/en/rest/git/trees)
- [Git Blobs API](https://docs.github.com/en/rest/git/blobs)
- [OAuth Apps](https://docs.github.com/en/apps/oauth-apps)
- [Rate Limits](https://docs.github.com/en/rest/rate-limit)

### Response Examples

**GET /repos/{owner}/{repo}/git/trees/{sha}?recursive=1**:
```json
{
    "sha": "abc123def456789",
    "url": "https://api.github.com/repos/owner/repo/git/trees/abc123",
    "tree": [
        {
            "path": "src/main.py",
            "mode": "100644",
            "type": "blob",
            "sha": "def456789abc123",
            "size": 2048,
            "url": "https://api.github.com/repos/owner/repo/git/blobs/def456"
        },
        {
            "path": "src/utils",
            "mode": "040000",
            "type": "tree",
            "sha": "789xyz123abc456",
            "url": "https://api.github.com/repos/owner/repo/git/trees/789xyz"
        },
        {
            "path": "README.md",
            "mode": "100644",
            "type": "blob",
            "sha": "123abc456def789",
            "size": 512,
            "url": "https://api.github.com/repos/owner/repo/git/blobs/123abc"
        }
    ],
    "truncated": false
}
```

**Rate Limit Headers**:
```
X-RateLimit-Limit: 5000
X-RateLimit-Remaining: 4999
X-RateLimit-Reset: 1704067200
X-RateLimit-Used: 1
X-RateLimit-Resource: core
```

---

## Appendix B: Decision Summary

| Challenge | Decision | Alternatives Considered |
|-----------|----------|------------------------|
| Content Filtering | Hybrid whitelist + blacklist | Whitelist-only, blacklist-only |
| Tree Traversal | Git Trees API (recursive) | Contents API (per-directory) |
| Content Fetch | Raw media type | Base64 + decode |
| Deduplication | Git blob SHA | Content SHA-256 |
| Rate Limiting | Adaptive with pause threshold | Fixed delays, no quota tracking |
| Repo Selection | Explicit list (mandatory) | Auto-sync all, regex patterns |
| OAuth Scope | `repo` + `read:org` | `public_repo` only |

---

## Appendix C: Risk Mitigation

| Risk | Mitigation |
|------|------------|
| Quota exhaustion mid-sync | Partial sync markers, job resume capability |
| Monorepo with 100k+ files | Tree truncation fallback, aggressive filtering |
| Private repo access denied | Clear error messaging, scope verification |
| Stale tokens | Token validation on sync start |
| Binary files slipping through | Size filter + null byte detection |
| Language detection errors | Use file extension, not content sniffing |

---

## Appendix D: Comparison with Existing Connectors

### Feature Parity Matrix

| Feature | Dropbox | GitHub | Notes |
|---------|---------|--------|-------|
| OAuth Authentication | ✅ | ✅ | GitHub tokens don't expire |
| Token Refresh | ✅ | N/A | GitHub uses long-lived tokens |
| Incremental Sync | ✅ (timestamp) | ✅ (commit SHA) | Different strategies |
| Team/Org Support | ✅ (namespace) | ✅ (org repos) | |
| Content Filtering | Basic (MIME) | Advanced (whitelist+blacklist) | Code-specific |
| Rate Limiting | Retry-After | X-RateLimit headers | |
| Concurrency Control | ✅ | ✅ | |
| Binary Detection | ❌ | ✅ | Required for code repos |
| Folder Selection | Root path | Repository list | |

### Unique GitHub Requirements

1. **Code-Aware Filtering**: Must understand programming file types
2. **Repository Selection**: User MUST choose repos (no "sync all")
3. **Tree API**: Efficient single-request file listing
4. **Blob SHA Dedup**: Use native Git hashes for deduplication
5. **Rate Budget**: 5000 req/hr requires careful management

---

## Appendix E: Implementation Summary (COMPLETED)

### Files Created/Modified

| File | Status | Description |
|------|--------|-------------|
| `backend/core/config.py` | ✅ Modified | Added `GITHUB_CLIENT_ID`, `GITHUB_CLIENT_SECRET`, `GITHUB_REDIRECT_URI`, `CONNECTOR_CONCURRENCY_GITHUB` |
| `backend/connectors/registry.py` | ✅ Modified | Added `github` entry with capabilities `["code_aware", "incremental_sync", "text_content"]` |
| `backend/connectors/limits.py` | ✅ Modified | Added GitHub concurrency limit |
| `backend/connectors/enhanced.py` | ✅ Modified | Added `SourceType.GITHUB` enum value |
| `backend/connectors/github.py` | ✅ Created | Full connector with `CodeFileFilter` and `GitHubRateLimiter` (~700 lines) |
| `backend/connectors/__init__.py` | ✅ Modified | Registered `GitHubConnector` in `CONNECTORS` dict |
| `backend/services/oauth_token_manager.py` | ✅ Modified | Added `validate_github_token()` method |
| `backend/api/v1/integrations.py` | ✅ Modified | Added OAuth exchange, repo listing, and repo selection endpoints |
| `supabase/migrations/20260115000000_add_github_connector.sql` | ✅ Created | Connector definition migration |

### Key Features Implemented

1. **Content Filtering (`CodeFileFilter`)**
   - Path blacklist: `node_modules/`, `.git/`, `__pycache__/`, `vendor/`, `dist/`, etc.
   - Extension whitelist: `.py`, `.ts`, `.js`, `.go`, `.rs`, `.md`, `.yaml`, etc.
   - Filename whitelist: `Dockerfile`, `Makefile`, `package.json`, etc.
   - Size limit: 1MB max file size
   - Binary detection via null byte check

2. **Rate Limiting (`GitHubRateLimiter`)**
   - Tracks `X-RateLimit-Remaining` header
   - Pauses sync at 500 requests remaining
   - Handles 429 and 403 rate limit responses
   - Exponential backoff with `Retry-After` header

3. **Repository Selection**
   - `GET /integrations/github/repos` - List available repos
   - `POST /integrations/github/repos/select` - Save selected repos
   - Stores selection in `credentials.selected_repositories`

4. **Tree Traversal**
   - Uses recursive Git Trees API (single request per repo)
   - Falls back to DFS for truncated trees (>100k items)
   - Early blacklist filtering during traversal

5. **Content Fetching**
   - Uses raw media type (`application/vnd.github.v3.raw`)
   - Avoids Base64 decode overhead
   - Streaming downloads

### API Endpoints Added

| Endpoint | Method | Purpose |
|----------|--------|---------|
| `/integrations/github/exchange` | POST | OAuth code → token exchange |
| `/integrations/github/repos` | GET | List user's available repositories |
| `/integrations/github/repos/select` | POST | Save repository selection |

### Environment Variables Required

```bash
GITHUB_CLIENT_ID=your_oauth_app_client_id
GITHUB_CLIENT_SECRET=your_oauth_app_client_secret
GITHUB_REDIRECT_URI=https://app.axiohub.io/api/v1/integrations/github/callback
```

### Testing

```bash
# Run the database migration
cd supabase && supabase db push

# Test the connector
cd backend
python -c "from connectors.github import GitHubConnector; print('✅ Import OK')"
```

### Remaining Tasks (Frontend)

- [ ] Add GitHub to ConnectorsList component
- [ ] Add GitHub icon/branding (`/assets/connectors/github.svg`)
- [ ] Create repository selection modal component
- [ ] Add GitHub connect button with OAuth redirect
- [ ] Handle callback URL in frontend routing

---

*Document Version: 1.0 | Created: 2026-01-15 | Implementation Complete: 2026-01-15*

