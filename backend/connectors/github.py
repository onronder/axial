"""
GitHub Connector

Connects to GitHub API to fetch source code and documentation from repositories.
Implements strict content filtering to avoid ingesting build artifacts and binaries.

Features:
- OAuth authentication with token validation
- Recursive tree fetching (single API call per repo)
- Hybrid whitelist/blacklist content filtering
- Rate limit tracking with adaptive backoff
- Explicit repository selection (no auto-sync all)

API Reference:
- https://docs.github.com/en/rest/git/trees
- https://docs.github.com/en/rest/git/blobs
"""

from __future__ import annotations

import logging
import mimetypes
import time
from datetime import datetime, timezone
from typing import Any, Dict, Iterator, Optional, AsyncIterator, Set

import requests

from connectors.base import (
    BaseConnector,
    RemoteFile,
    ConnectorAuthError,
    ConnectorRateLimitError,
    ConnectorTransientError,
)
from connectors.enhanced import EnhancedConnector, SourceDocument, SourceType, ItemNotFoundError
from connectors.limits import connector_fetch_limit
from core.db import get_supabase
from core.config import settings
from services.oauth_token_manager import OAuthTokenManager, TokenRefreshError

logger = logging.getLogger(__name__)

# =============================================================================
# Constants
# =============================================================================

GITHUB_API_BASE = "https://api.github.com"
DEFAULT_TIMEOUT_SECONDS = 30
MAX_RETRIES = 3


# =============================================================================
# Content Filtering
# =============================================================================

class CodeFileFilter:
    """
    Filter for high-value source code files.
    
    Implements a hybrid whitelist/blacklist strategy:
    1. Path blacklist: Hard-reject known junk directories
    2. Extension whitelist: Only allow code/documentation files
    3. Size limit: Skip files likely to be binaries
    """
    
    # Hard-reject paths (checked first)
    PATH_BLACKLIST: Set[str] = {
        "node_modules/", ".git/", "__pycache__/", ".pytest_cache/",
        "vendor/", "target/", "build/", "dist/", ".next/", ".nuxt/",
        ".venv/", "venv/", "env/", ".tox/", ".eggs/",
        "coverage/", ".nyc_output/", ".cache/", ".parcel-cache/",
        ".idea/", ".vscode/", ".DS_Store", "Thumbs.db",
        "*.egg-info/", "site-packages/", "bower_components/",
        ".gradle/", ".mvn/", "bin/", "obj/",
    }
    
    # Allowed extensions (code + documentation)
    EXTENSION_WHITELIST: Set[str] = {
        # Programming Languages
        ".py", ".pyi", ".pyx",
        ".ts", ".tsx", ".mts", ".cts",
        ".js", ".jsx", ".mjs", ".cjs",
        ".go", ".mod", ".sum",
        ".rs", ".toml",
        ".java", ".kt", ".kts", ".scala", ".clj",
        ".rb", ".erb", ".rake",
        ".php", ".phtml",
        ".cs", ".fs", ".vb",
        ".cpp", ".cc", ".c", ".h", ".hpp", ".hh",
        ".swift", ".m", ".mm",
        ".sql", ".psql",
        ".sh", ".bash", ".zsh", ".fish",
        ".ps1", ".psm1",
        ".r", ".R",
        ".lua",
        ".pl", ".pm",
        ".ex", ".exs",
        ".hs", ".lhs",
        ".ml", ".mli",
        ".elm",
        ".v", ".sv",
        ".proto",
        ".graphql", ".gql",
        # Documentation
        ".md", ".mdx", ".markdown",
        ".rst", ".txt",
        ".adoc", ".asciidoc",
        # Configuration (valuable for understanding projects)
        ".yaml", ".yml",
        ".json",
        ".xml",
        ".ini", ".cfg", ".conf",
        ".env.example", ".env.sample",
        ".gitignore", ".gitattributes",
        ".dockerignore", ".editorconfig",
        # Web
        ".html", ".htm",
        ".css", ".scss", ".sass", ".less", ".styl",
        ".vue", ".svelte",
        # Data/ML (text-based)
        ".ipynb",
    }
    
    # Files without extension that are valuable
    FILENAME_WHITELIST: Set[str] = {
        "Dockerfile", "Containerfile",
        "Makefile", "GNUmakefile",
        "Rakefile", "Gemfile", "Brewfile",
        "Procfile", "Vagrantfile",
        "CMakeLists.txt", "BUILD", "WORKSPACE",
        "requirements.txt", "setup.py", "setup.cfg",
        "package.json", "package-lock.json",
        "tsconfig.json", "jsconfig.json",
        "composer.json", "Cargo.toml",
        "go.mod", "go.sum",
        "pom.xml", "build.gradle", "build.gradle.kts",
        ".eslintrc", ".prettierrc", ".babelrc",
        "LICENSE", "README", "CHANGELOG", "CONTRIBUTING",
    }
    
    # Maximum file size (bytes) - larger files are likely binaries/data
    MAX_FILE_SIZE = 1 * 1024 * 1024  # 1MB
    
    def should_include(self, path: str, size: Optional[int] = None) -> bool:
        """Determine if file should be ingested."""
        # 1. Path blacklist check
        path_lower = path.lower()
        for blocked in self.PATH_BLACKLIST:
            blocked_lower = blocked.lower().rstrip("/")
            if blocked_lower in path_lower or path_lower.startswith(blocked_lower):
                return False
        
        # 2. Size check (if provided)
        if size is not None and size > self.MAX_FILE_SIZE:
            return False
        
        # 3. Extract filename
        filename = path.rsplit("/", 1)[-1] if "/" in path else path
        
        # 4. Check filename whitelist (extensionless files)
        if filename in self.FILENAME_WHITELIST:
            return True
        
        # Also check case-insensitive for common files
        if filename.upper() in {f.upper() for f in self.FILENAME_WHITELIST}:
            return True
        
        # 5. Extension whitelist check
        ext = self._get_extension(filename)
        if ext and ext in self.EXTENSION_WHITELIST:
            return True
        
        return False
    
    def is_path_blacklisted(self, path: str) -> bool:
        """Check if path is in blacklist (for early directory skipping)."""
        path_lower = path.lower()
        for blocked in self.PATH_BLACKLIST:
            blocked_lower = blocked.lower().rstrip("/")
            if blocked_lower in path_lower:
                return True
        return False
    
    @staticmethod
    def _get_extension(filename: str) -> str:
        """Extract file extension (lowercase, including dot)."""
        if "." not in filename:
            return ""
        return "." + filename.rsplit(".", 1)[-1].lower()


# =============================================================================
# Rate Limiter
# =============================================================================

class GitHubRateLimiter:
    """Track and manage GitHub API rate limits."""
    
    RESERVE_THRESHOLD = 500  # Pause if fewer than 500 requests remain
    
    def __init__(self):
        self.remaining = 5000
        self.limit = 5000
        self.reset_at: Optional[datetime] = None
        self.used = 0
    
    def update_from_headers(self, response: requests.Response):
        """Update limits from response headers."""
        try:
            self.remaining = int(response.headers.get("X-RateLimit-Remaining", self.remaining))
            self.limit = int(response.headers.get("X-RateLimit-Limit", self.limit))
            self.used = int(response.headers.get("X-RateLimit-Used", self.used))
            
            reset_ts = response.headers.get("X-RateLimit-Reset")
            if reset_ts:
                self.reset_at = datetime.fromtimestamp(int(reset_ts), tz=timezone.utc)
        except (ValueError, TypeError):
            pass
    
    def should_pause(self) -> bool:
        """Check if we should pause to preserve quota."""
        return self.remaining < self.RESERVE_THRESHOLD
    
    def get_wait_time(self) -> float:
        """Calculate wait time until reset."""
        if not self.reset_at:
            return 60.0
        delta = (self.reset_at - datetime.now(timezone.utc)).total_seconds()
        return max(0, delta)


# =============================================================================
# GitHub Connector
# =============================================================================

class GitHubConnector(EnhancedConnector, BaseConnector):
    """
    GitHub connector for unified ingestion pipeline.
    
    Features:
    - OAuth token validation (GitHub tokens don't expire by default)
    - Recursive tree fetching (efficient single-call per repo)
    - Strict content filtering (code + docs only)
    - Rate limit tracking with pause capability
    - Explicit repository selection
    """
    
    def __init__(self):
        self._filter = CodeFileFilter()
        self._rate_limiter = GitHubRateLimiter()
    
    @property
    def connector_type(self) -> SourceType:
        return SourceType.GITHUB
    
    @property
    def supports_incremental_sync(self) -> bool:
        return True
    
    @property
    def supports_batch_fetch(self) -> bool:
        return True
    
    # =========================================================================
    # Configuration & Validation
    # =========================================================================
    
    def validate_config(self, config: dict) -> bool:
        """Validate GitHub configuration by checking /user endpoint."""
        if not isinstance(config, dict):
            return False
        
        access_token = config.get("access_token")
        integration_id = config.get("integration_id")
        user_id = config.get("user_id")
        
        if not access_token and not integration_id and not user_id:
            return False
        
        if access_token:
            try:
                self._verify_token(access_token)
                return True
            except ConnectorAuthError:
                return False
            except Exception:
                return True  # Network errors = config might be OK
        
        return True
    
    def _verify_token(self, access_token: str) -> dict:
        """Verify token by calling /user endpoint."""
        url = f"{GITHUB_API_BASE}/user"
        headers = {
            "Authorization": f"Bearer {access_token}",
            "Accept": "application/vnd.github.v3+json",
            "X-GitHub-Api-Version": "2022-11-28",
        }
        
        try:
            response = requests.get(url, headers=headers, timeout=10)
            self._rate_limiter.update_from_headers(response)
            
            if response.status_code == 401:
                raise ConnectorAuthError("GitHub token invalid or revoked")
            
            if response.status_code == 403:
                raise ConnectorAuthError("GitHub token lacks required permissions")
            
            if response.status_code != 200:
                raise ConnectorTransientError(f"GitHub API error: {response.text[:200]}")
            
            return response.json()
        except requests.RequestException as exc:
            raise ConnectorTransientError(f"GitHub connection error: {exc}") from exc
    
    # =========================================================================
    # HTTP Layer
    # =========================================================================
    
    def _get_headers(self, config: dict) -> dict:
        """Build request headers with authentication."""
        return {
            "Authorization": f"Bearer {config.get('access_token')}",
            "Accept": "application/vnd.github.v3+json",
            "X-GitHub-Api-Version": "2022-11-28",
        }
    
    def _request(
        self,
        config: dict,
        url: str,
        params: Optional[dict] = None,
    ) -> dict:
        """Make a GET request to GitHub API."""
        headers = self._get_headers(config)
        
        with connector_fetch_limit("github"):
            response = self._request_with_retry(
                "GET",
                url,
                headers=headers,
                params=params,
                timeout=DEFAULT_TIMEOUT_SECONDS,
            )
        
        if response.status_code == 404:
            raise ItemNotFoundError(f"GitHub resource not found: {url}")
        
        try:
            response.raise_for_status()
            return response.json()
        except requests.HTTPError as exc:
            raise ConnectorTransientError(f"GitHub API error: {exc}") from exc
    
    def _request_with_retry(
        self,
        method: str,
        url: str,
        headers: Optional[dict] = None,
        params: Optional[dict] = None,
        stream: bool = False,
        timeout: int = DEFAULT_TIMEOUT_SECONDS,
    ) -> requests.Response:
        """Execute HTTP request with retry logic."""
        headers = headers or {}
        attempt = 0
        
        while True:
            try:
                response = requests.request(
                    method,
                    url,
                    headers=headers,
                    params=params,
                    timeout=timeout,
                    stream=stream,
                )
            except requests.RequestException as exc:
                raise ConnectorTransientError(f"GitHub network error: {exc}") from exc
            
            # Update rate limit info
            self._rate_limiter.update_from_headers(response)
            
            # Handle rate limiting
            if response.status_code == 403 and "rate limit" in response.text.lower():
                if attempt >= MAX_RETRIES:
                    raise ConnectorRateLimitError("GitHub rate limit exceeded after retries")
                
                retry_after = response.headers.get("Retry-After")
                delay = int(retry_after) if retry_after else 60
                
                logger.warning(f"⏳ [GitHub] Rate limited, retrying in {delay}s")
                response.close()
                time.sleep(delay)
                attempt += 1
                continue
            
            if response.status_code == 429:
                if attempt >= MAX_RETRIES:
                    raise ConnectorRateLimitError("GitHub secondary rate limit exceeded")
                
                retry_after = response.headers.get("Retry-After", "60")
                delay = int(retry_after)
                
                logger.warning(f"⏳ [GitHub] Secondary rate limit, retrying in {delay}s")
                response.close()
                time.sleep(delay)
                attempt += 1
                continue
            
            if response.status_code == 401:
                response.close()
                raise ConnectorAuthError("GitHub token invalid or revoked")
            
            if response.status_code >= 500:
                detail = response.text[:500] if response.text else "No details"
                response.close()
                raise ConnectorTransientError(f"GitHub server error: {detail}")
            
            return response
    
    # =========================================================================
    # Repository Discovery (for frontend selection UI)
    # =========================================================================
    
    def get_available_repositories(self, access_token: str) -> list[dict]:
        """
        List repositories the user has access to.
        
        Used by frontend for repository selection UI.
        Returns both user's own repos and organization repos.
        """
        config = {"access_token": access_token}
        repos = []
        
        # Fetch user's own repos (includes private)
        page = 1
        while True:
            url = f"{GITHUB_API_BASE}/user/repos"
            params = {
                "per_page": 100,
                "page": page,
                "sort": "updated",
                "direction": "desc",
                "affiliation": "owner,collaborator,organization_member",
            }
            
            try:
                result = self._request(config, url, params)
            except Exception as e:
                logger.error(f"❌ [GitHub] Failed to fetch repos page {page}: {e}")
                break
            
            if not result:
                break
            
            for repo in result:
                repos.append({
                    "id": repo["id"],
                    "name": repo["name"],
                    "full_name": repo["full_name"],
                    "description": repo.get("description"),
                    "private": repo.get("private", False),
                    "fork": repo.get("fork", False),
                    "archived": repo.get("archived", False),
                    "default_branch": repo.get("default_branch", "main"),
                    "owner": repo["owner"]["login"],
                    "owner_type": repo["owner"]["type"],  # "User" or "Organization"
                    "updated_at": repo.get("updated_at"),
                    "language": repo.get("language"),
                    "stargazers_count": repo.get("stargazers_count", 0),
                })
            
            if len(result) < 100:
                break
            page += 1
            
            # Safety limit
            if page > 50:
                logger.warning("⚠️ [GitHub] Reached 50 pages of repos, stopping")
                break
        
        return repos
    
    # =========================================================================
    # Tree Traversal
    # =========================================================================
    
    def _get_branch_sha(self, config: dict, repo: str, branch: str) -> str:
        """Get the commit SHA for a branch."""
        url = f"{GITHUB_API_BASE}/repos/{repo}/branches/{branch}"
        result = self._request(config, url)
        return result["commit"]["sha"]
    
    def _fetch_tree(self, config: dict, repo: str, sha: str) -> Iterator[dict]:
        """
        Fetch repository tree with truncation handling.
        
        Uses recursive=1 for efficiency (single API call).
        Falls back to DFS if tree is truncated (>100k items).
        """
        url = f"{GITHUB_API_BASE}/repos/{repo}/git/trees/{sha}"
        params = {"recursive": "1"}
        
        result = self._request(config, url, params)
        
        if not result.get("truncated"):
            # Happy path: full tree in one request
            yield from result.get("tree", [])
            return
        
        # Fallback: DFS traversal for massive repos
        logger.warning(f"⚠️ [GitHub] Tree truncated for {repo}, using DFS fallback")
        yield from self._fetch_tree_dfs(config, repo, sha, "")
    
    def _fetch_tree_dfs(
        self,
        config: dict,
        repo: str,
        sha: str,
        path: str,
    ) -> Iterator[dict]:
        """Depth-first traversal for truncated trees."""
        url = f"{GITHUB_API_BASE}/repos/{repo}/git/trees/{sha}"
        result = self._request(config, url)  # non-recursive
        
        for entry in result.get("tree", []):
            entry_path = f"{path}/{entry['path']}" if path else entry["path"]
            
            if entry["type"] == "blob":
                yield {**entry, "path": entry_path}
            elif entry["type"] == "tree":
                # Skip blacklisted directories early
                if not self._filter.is_path_blacklisted(entry_path + "/"):
                    yield from self._fetch_tree_dfs(config, repo, entry["sha"], entry_path)
    
    # =========================================================================
    # File Discovery - list_files()
    # =========================================================================
    
    def list_files(
        self,
        config: dict,
        since: Optional[datetime] = None,
    ) -> Iterator[RemoteFile]:
        """
        List files from selected GitHub repositories.
        
        Requires config to contain 'selected_repositories' list in credentials.
        """
        resolved = self._resolve_config(config)
        
        # Get selected repositories from credentials
        credentials = resolved.get("credentials", {})
        selected_repos = credentials.get("selected_repositories", [])
        
        if not selected_repos:
            logger.warning("⚠️ [GitHub] No repositories selected")
            return
        
        for repo_config in selected_repos:
            if not repo_config.get("enabled", True):
                continue
            
            repo_name = repo_config.get("full_name")
            branch = repo_config.get("branch")
            
            if not repo_name:
                continue
            
            # Check rate limit before processing repo
            if self._rate_limiter.should_pause():
                logger.warning(
                    f"⏸️ [GitHub] Pausing sync - {self._rate_limiter.remaining} requests remaining"
                )
                break
            
            try:
                yield from self._list_repo_files(resolved, repo_name, branch, since)
            except Exception as e:
                logger.error(f"❌ [GitHub] Failed to list files from {repo_name}: {e}")
                continue
    
    def _list_repo_files(
        self,
        config: dict,
        repo: str,
        branch: Optional[str],
        since: Optional[datetime],
    ) -> Iterator[RemoteFile]:
        """List files from a single repository."""
        # Get default branch if not specified
        if not branch:
            url = f"{GITHUB_API_BASE}/repos/{repo}"
            repo_info = self._request(config, url)
            branch = repo_info.get("default_branch", "main")
        
        # Get branch SHA
        sha = self._get_branch_sha(config, repo, branch)
        
        logger.info(f"📂 [GitHub] Listing files from {repo} (branch: {branch})")
        
        file_count = 0
        filtered_count = 0
        
        # Fetch tree
        for entry in self._fetch_tree(config, repo, sha):
            if entry["type"] != "blob":
                continue
            
            file_count += 1
            
            # Apply content filter
            if not self._filter.should_include(entry["path"], entry.get("size")):
                filtered_count += 1
                continue
            
            yield RemoteFile(
                id=f"{repo}:{entry['sha']}:{entry['path']}",
                name=entry["path"].rsplit("/", 1)[-1],
                mime_type=self._guess_mime_type(entry["path"]),
                size=entry.get("size"),
                modified_at=None,  # Tree API doesn't provide timestamps
                parent_id=repo,
                web_view_url=f"https://github.com/{repo}/blob/{branch}/{entry['path']}",
            )
        
        logger.info(
            f"📊 [GitHub] {repo}: {file_count} total files, "
            f"{filtered_count} filtered, {file_count - filtered_count} to ingest"
        )
    
    # =========================================================================
    # Content Fetching
    # =========================================================================
    
    def fetch_file_content(self, file_id: str, config: dict) -> bytes:
        """Fetch raw file content from GitHub."""
        resolved = self._resolve_config(config)
        
        # Parse file_id: repo:sha:path
        parts = file_id.split(":", 2)
        if len(parts) != 3:
            raise ValueError(f"Invalid GitHub file ID format: {file_id}")
        
        repo, sha, path = parts
        return self._fetch_blob_raw(resolved, repo, sha)
    
    def _fetch_blob_raw(self, config: dict, repo: str, sha: str) -> bytes:
        """Fetch blob content as raw bytes (no Base64 overhead)."""
        url = f"{GITHUB_API_BASE}/repos/{repo}/git/blobs/{sha}"
        headers = self._get_headers(config)
        headers["Accept"] = "application/vnd.github.v3.raw"
        
        with connector_fetch_limit("github"):
            response = self._request_with_retry(
                "GET",
                url,
                headers=headers,
                stream=True,
                timeout=DEFAULT_TIMEOUT_SECONDS,
            )
        
        if response.status_code == 404:
            response.close()
            raise ItemNotFoundError(f"GitHub blob not found: {sha}")
        
        try:
            response.raise_for_status()
        except requests.HTTPError as exc:
            response.close()
            raise ConnectorTransientError(f"GitHub download error: {exc}") from exc
        
        content = response.content
        response.close()
        return content
    
    async def fetch_documents(
        self,
        item_ids: list[str],
        credentials: Optional[Dict[str, Any]] = None,
        **kwargs,
    ) -> AsyncIterator[SourceDocument]:
        """Async wrapper for fetch_documents_sync."""
        for doc in self.fetch_documents_sync(item_ids, credentials, **kwargs):
            yield doc
    
    def fetch_documents_sync(
        self,
        item_ids: list[str],
        credentials: Optional[Dict[str, Any]] = None,
        **kwargs,
    ) -> Iterator[SourceDocument]:
        """Fetch documents from GitHub for ingestion pipeline."""
        if not item_ids:
            return
        
        resolved = self._resolve_config(credentials or {})
        
        logger.info(f"📥 [GitHubConnector] Fetching {len(item_ids)} item(s)")
        
        for item_id in item_ids:
            try:
                # Parse file_id: repo:sha:path
                parts = item_id.split(":", 2)
                if len(parts) != 3:
                    logger.warning(f"⚠️ [GitHub] Invalid file ID: {item_id}")
                    continue
                
                repo, sha, path = parts
                
                # Fetch raw content
                content = self._fetch_blob_raw(resolved, repo, sha)
                
                # Binary detection
                if self._is_binary(content):
                    logger.debug(f"⏭️ [GitHub] Skipping binary file: {path}")
                    continue
                
                filename = path.rsplit("/", 1)[-1]
                
                yield SourceDocument(
                    content=content,
                    metadata={
                        "source": "github",
                        "repository": repo,
                        "path": path,
                        "git_blob_sha": sha,
                    },
                    source_type=SourceType.GITHUB,
                    source_id=item_id,
                    filename=filename,
                    mime_type=self._guess_mime_type(filename),
                    size_bytes=len(content),
                    parent_id=repo,
                )
                
            except ItemNotFoundError:
                logger.warning(f"⚠️ [GitHub] Not found: {item_id}")
                continue
            except Exception as e:
                logger.error(f"❌ [GitHub] Failed to fetch {item_id}: {e}")
                continue
        
        logger.info("📥 [GitHubConnector] Fetch stream ended")
    
    # =========================================================================
    # Configuration Resolution
    # =========================================================================
    
    def _resolve_config(self, config: dict) -> dict:
        """Resolve configuration, fetching tokens from database if needed."""
        resolved = dict(config or {})
        
        if resolved.get("access_token"):
            return resolved
        
        integration = self._load_integration(resolved)
        
        try:
            creds = OAuthTokenManager.get_valid_credentials(integration, "github")
        except TokenRefreshError as exc:
            raise ConnectorAuthError("GitHub integration requires reconnection") from exc
        
        resolved["access_token"] = creds.get("access_token")
        resolved["integration_id"] = creds.get("integration_id") or integration.get("id")
        resolved["credentials"] = integration.get("credentials") or {}
        
        return resolved
    
    def _load_integration(self, config: dict) -> Dict[str, Any]:
        """Load integration record from database."""
        supabase = get_supabase()
        integration_id = config.get("integration_id")
        user_id = config.get("user_id")
        
        if integration_id:
            result = supabase.table("user_integrations").select("*").eq(
                "id", integration_id
            ).single().execute()
            if result.data:
                return result.data
            raise ConnectorAuthError(f"Integration {integration_id} not found")
        
        if not user_id:
            raise ConnectorAuthError("GitHub requires user_id or integration_id")
        
        def_result = supabase.table("connector_definitions").select("id").eq(
            "type", "github"
        ).single().execute()
        if not def_result.data:
            raise ConnectorAuthError("GitHub connector not registered")
        
        int_result = supabase.table("user_integrations").select("*").eq(
            "user_id", user_id
        ).eq("connector_definition_id", def_result.data["id"]).single().execute()
        if not int_result.data:
            raise ConnectorAuthError("GitHub not connected for this user")
        
        return int_result.data
    
    # =========================================================================
    # Helpers
    # =========================================================================
    
    @staticmethod
    def _is_binary(content: bytes) -> bool:
        """Detect binary files by checking for null bytes."""
        if not content:
            return False
        
        # Check first 8KB
        sample = content[:8192]
        
        # Null bytes = binary
        if b'\x00' in sample:
            return True
        
        return False
    
    @staticmethod
    def _guess_mime_type(filename: Optional[str]) -> str:
        """Guess MIME type from filename."""
        if not filename:
            return "text/plain"
        
        # Common code MIME types
        ext = filename.rsplit(".", 1)[-1].lower() if "." in filename else ""
        
        code_mimes = {
            "py": "text/x-python",
            "js": "text/javascript",
            "ts": "text/typescript",
            "tsx": "text/typescript-jsx",
            "jsx": "text/javascript-jsx",
            "go": "text/x-go",
            "rs": "text/x-rust",
            "java": "text/x-java",
            "rb": "text/x-ruby",
            "php": "text/x-php",
            "c": "text/x-c",
            "cpp": "text/x-c++",
            "h": "text/x-c",
            "cs": "text/x-csharp",
            "swift": "text/x-swift",
            "kt": "text/x-kotlin",
            "scala": "text/x-scala",
            "sql": "text/x-sql",
            "sh": "text/x-shellscript",
            "bash": "text/x-shellscript",
            "md": "text/markdown",
            "yaml": "text/yaml",
            "yml": "text/yaml",
            "json": "application/json",
            "xml": "application/xml",
            "html": "text/html",
            "css": "text/css",
            "scss": "text/x-scss",
            "vue": "text/x-vue",
            "svelte": "text/x-svelte",
        }
        
        if ext in code_mimes:
            return code_mimes[ext]
        
        guessed, _ = mimetypes.guess_type(filename)
        return guessed or "text/plain"


# =============================================================================
# Module-level Connector Instance
# =============================================================================

def get_github_connector() -> GitHubConnector:
    """Factory function to get a GitHubConnector instance."""
    return GitHubConnector()

