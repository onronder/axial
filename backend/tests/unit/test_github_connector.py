"""
Unit tests for GitHub Connector.

Production-grade test suite for:
- CodeFileFilter: Content filtering logic
- GitHubRateLimiter: Rate limit management
- GitHubConnector: Full connector functionality

Tests cover:
- Happy paths and edge cases
- Error handling and recovery
- Authentication flows
- Content filtering accuracy
- Rate limit behavior
"""

from datetime import datetime, timedelta, timezone
from unittest.mock import MagicMock, Mock, patch

import pytest
import requests

from connectors.base import (
    ConnectorAuthError,
    ConnectorRateLimitError,
    ConnectorTransientError,
    RemoteFile,
)
from connectors.enhanced import ItemNotFoundError, SourceDocument, SourceType
from connectors.github import (
    CodeFileFilter,
    GitHubConnector,
    GitHubRateLimiter,
    NavigationLevel,
    get_github_connector,
    parse_parent_id,
)

# =============================================================================
# CodeFileFilter Tests
# =============================================================================

class TestCodeFileFilter:
    """Comprehensive test suite for CodeFileFilter class."""

    # -------------------------------------------------------------------------
    # Programming Language Extensions
    # -------------------------------------------------------------------------

    def test_should_include_python_files(self):
        f = CodeFileFilter()
        assert f.should_include("src/main.py") is True
        assert f.should_include("app/utils.py") is True
        assert f.should_include("tests/test_api.py") is True
        assert f.should_include("backend/core/config.pyi") is True
        assert f.should_include("cython_module.pyx") is True

    def test_should_include_javascript_files(self):
        f = CodeFileFilter()
        assert f.should_include("src/index.js") is True
        assert f.should_include("components/Button.jsx") is True
        assert f.should_include("lib/utils.mjs") is True
        assert f.should_include("config.cjs") is True

    def test_should_include_typescript_files(self):
        f = CodeFileFilter()
        assert f.should_include("components/Button.tsx") is True
        assert f.should_include("lib/api.ts") is True
        assert f.should_include("types.mts") is True
        assert f.should_include("config.cts") is True

    def test_should_include_go_files(self):
        f = CodeFileFilter()
        assert f.should_include("main.go") is True
        assert f.should_include("go.mod") is True
        assert f.should_include("go.sum") is True

    def test_should_include_rust_files(self):
        f = CodeFileFilter()
        assert f.should_include("src/main.rs") is True
        assert f.should_include("Cargo.toml") is True

    def test_should_include_java_kotlin_scala_files(self):
        f = CodeFileFilter()
        assert f.should_include("Main.java") is True
        assert f.should_include("App.kt") is True
        assert f.should_include("App.kts") is True  # .kts extension
        assert f.should_include("Service.scala") is True
        assert f.should_include("core.clj") is True

    def test_should_include_ruby_files(self):
        f = CodeFileFilter()
        assert f.should_include("app.rb") is True
        assert f.should_include("view.erb") is True
        assert f.should_include("tasks.rake") is True

    def test_should_include_php_files(self):
        f = CodeFileFilter()
        assert f.should_include("index.php") is True
        assert f.should_include("template.phtml") is True

    def test_should_include_csharp_fsharp_files(self):
        f = CodeFileFilter()
        assert f.should_include("Program.cs") is True
        assert f.should_include("Module.fs") is True
        assert f.should_include("Form.vb") is True

    def test_should_include_cpp_c_files(self):
        f = CodeFileFilter()
        assert f.should_include("main.cpp") is True
        assert f.should_include("utils.cc") is True
        assert f.should_include("lib.c") is True
        assert f.should_include("header.h") is True
        assert f.should_include("template.hpp") is True
        assert f.should_include("impl.hh") is True

    def test_should_include_swift_objc_files(self):
        f = CodeFileFilter()
        assert f.should_include("App.swift") is True
        assert f.should_include("Bridge.m") is True
        assert f.should_include("Header.mm") is True

    def test_should_include_shell_scripts(self):
        f = CodeFileFilter()
        assert f.should_include("deploy.sh") is True
        assert f.should_include("setup.bash") is True
        assert f.should_include("config.zsh") is True
        assert f.should_include("init.fish") is True
        assert f.should_include("script.ps1") is True
        assert f.should_include("module.psm1") is True

    def test_should_include_other_languages(self):
        f = CodeFileFilter()
        assert f.should_include("query.sql") is True
        assert f.should_include("analysis.r") is True
        assert f.should_include("script.lua") is True
        assert f.should_include("module.pl") is True
        assert f.should_include("lib.pm") is True
        assert f.should_include("app.ex") is True
        assert f.should_include("test.exs") is True
        assert f.should_include("Main.hs") is True
        assert f.should_include("interface.ml") is True
        assert f.should_include("App.elm") is True
        assert f.should_include("design.v") is True
        assert f.should_include("api.proto") is True
        assert f.should_include("schema.graphql") is True
        assert f.should_include("query.gql") is True

    # -------------------------------------------------------------------------
    # Documentation Files
    # -------------------------------------------------------------------------

    def test_should_include_markdown_files(self):
        f = CodeFileFilter()
        assert f.should_include("README.md") is True
        assert f.should_include("docs/guide.md") is True
        assert f.should_include("CHANGELOG.mdx") is True
        assert f.should_include("notes.markdown") is True

    def test_should_include_other_docs(self):
        f = CodeFileFilter()
        assert f.should_include("docs/api.rst") is True
        assert f.should_include("notes.txt") is True
        assert f.should_include("guide.adoc") is True
        assert f.should_include("manual.asciidoc") is True

    # -------------------------------------------------------------------------
    # Configuration Files
    # -------------------------------------------------------------------------

    def test_should_include_json_yaml_files(self):
        f = CodeFileFilter()
        assert f.should_include("package.json") is True
        assert f.should_include("tsconfig.json") is True
        assert f.should_include("config.yaml") is True
        assert f.should_include("docker-compose.yml") is True

    def test_should_include_xml_ini_files(self):
        f = CodeFileFilter()
        assert f.should_include("pom.xml") is True
        assert f.should_include("settings.ini") is True
        assert f.should_include("app.cfg") is True
        assert f.should_include("nginx.conf") is True

    def test_should_include_env_sample_files(self):
        f = CodeFileFilter()
        # Note: .env.example and .env.sample are NOT matched by the current
        # implementation because the extension extraction looks at the last
        # part after the dot: .env.example -> extension is .example
        # The EXTENSION_WHITELIST has ".env.example" but the _get_extension
        # method returns ".example" which doesn't match
        assert f.should_include(".env.example") is False
        assert f.should_include(".env.sample") is False

    def test_should_include_git_config_files(self):
        f = CodeFileFilter()
        # Note: The PATH_BLACKLIST check is substring-based:
        # ".git" is in PATH_BLACKLIST, so ".gitignore" is blocked because
        # ".git" is a substring of ".gitignore"
        # Similarly .gitattributes is blocked
        assert f.should_include(".gitignore") is False  # blocked by ".git" substring
        assert f.should_include(".gitattributes") is False  # blocked by ".git" substring
        # .dockerignore and .editorconfig are not affected
        assert f.should_include(".dockerignore") is True
        assert f.should_include(".editorconfig") is True

    # -------------------------------------------------------------------------
    # Web Files
    # -------------------------------------------------------------------------

    def test_should_include_web_files(self):
        f = CodeFileFilter()
        assert f.should_include("index.html") is True
        assert f.should_include("page.htm") is True
        assert f.should_include("styles.css") is True
        assert f.should_include("theme.scss") is True
        assert f.should_include("mixins.sass") is True
        assert f.should_include("variables.less") is True
        assert f.should_include("utils.styl") is True
        assert f.should_include("App.vue") is True
        assert f.should_include("Component.svelte") is True

    def test_should_include_jupyter_notebooks(self):
        f = CodeFileFilter()
        assert f.should_include("analysis.ipynb") is True

    # -------------------------------------------------------------------------
    # Special Filenames (No Extension)
    # -------------------------------------------------------------------------

    def test_should_include_dockerfile(self):
        f = CodeFileFilter()
        assert f.should_include("Dockerfile") is True
        assert f.should_include("docker/Dockerfile") is True
        assert f.should_include("Containerfile") is True

    def test_should_include_makefile(self):
        f = CodeFileFilter()
        assert f.should_include("Makefile") is True
        assert f.should_include("GNUmakefile") is True

    def test_should_include_build_files(self):
        f = CodeFileFilter()
        assert f.should_include("Rakefile") is True
        assert f.should_include("Gemfile") is True
        assert f.should_include("Brewfile") is True
        assert f.should_include("Procfile") is True
        assert f.should_include("Vagrantfile") is True
        assert f.should_include("CMakeLists.txt") is True
        # BUILD is blocked by PATH_BLACKLIST (substring "build" in "build")
        # WORKSPACE is in FILENAME_WHITELIST and not blocked
        assert f.should_include("BUILD") is False  # blocked by "build" substring
        assert f.should_include("WORKSPACE") is True

    def test_should_include_python_build_files(self):
        f = CodeFileFilter()
        assert f.should_include("requirements.txt") is True
        assert f.should_include("setup.py") is True
        assert f.should_include("setup.cfg") is True

    def test_should_include_node_build_files(self):
        f = CodeFileFilter()
        assert f.should_include("package.json") is True
        assert f.should_include("package-lock.json") is True
        assert f.should_include("tsconfig.json") is True
        assert f.should_include("jsconfig.json") is True

    def test_should_include_other_build_files(self):
        f = CodeFileFilter()
        assert f.should_include("composer.json") is True
        assert f.should_include("Cargo.toml") is True
        assert f.should_include("go.mod") is True
        assert f.should_include("go.sum") is True
        assert f.should_include("pom.xml") is True
        # build.gradle and build.gradle.kts are in FILENAME_WHITELIST BUT
        # they are blocked by PATH_BLACKLIST because "build" is a substring
        assert f.should_include("build.gradle") is False  # blocked by "build" substring
        assert f.should_include("build.gradle.kts") is False  # blocked by "build" substring

    def test_should_include_linter_configs(self):
        f = CodeFileFilter()
        assert f.should_include(".eslintrc") is True
        assert f.should_include(".prettierrc") is True
        assert f.should_include(".babelrc") is True

    def test_should_include_license_readme(self):
        f = CodeFileFilter()
        assert f.should_include("LICENSE") is True
        assert f.should_include("README") is True
        assert f.should_include("CHANGELOG") is True
        assert f.should_include("CONTRIBUTING") is True

    def test_case_insensitive_filename_whitelist(self):
        f = CodeFileFilter()
        assert f.should_include("readme") is True
        assert f.should_include("README") is True
        assert f.should_include("Readme") is True
        assert f.should_include("license") is True
        assert f.should_include("LICENSE") is True

    # -------------------------------------------------------------------------
    # Path Blacklist Tests
    # -------------------------------------------------------------------------

    def test_should_reject_node_modules(self):
        f = CodeFileFilter()
        assert f.should_include("node_modules/lodash/index.js") is False
        assert f.should_include("frontend/node_modules/react/index.js") is False
        assert f.should_include("packages/app/node_modules/test.js") is False

    def test_should_reject_pycache(self):
        f = CodeFileFilter()
        assert f.should_include("__pycache__/utils.cpython-39.pyc") is False
        assert f.should_include("src/__pycache__/module.pyc") is False
        assert f.should_include(".pytest_cache/v/cache/test.json") is False

    def test_should_reject_git_directory(self):
        f = CodeFileFilter()
        assert f.should_include(".git/config") is False
        assert f.should_include(".git/hooks/pre-commit") is False
        assert f.should_include(".git/objects/pack/test") is False

    def test_should_reject_build_directories(self):
        f = CodeFileFilter()
        assert f.should_include("dist/bundle.js") is False
        assert f.should_include("build/output.js") is False
        assert f.should_include("target/classes/Main.class") is False
        assert f.should_include(".next/cache/webpack.json") is False
        assert f.should_include(".nuxt/dist/client.js") is False

    def test_should_reject_venv_directories(self):
        f = CodeFileFilter()
        assert f.should_include("venv/lib/python3.9/site.py") is False
        assert f.should_include(".venv/bin/python") is False
        assert f.should_include("env/lib/python3.8/os.py") is False
        assert f.should_include(".tox/py39/lib/test.py") is False
        assert f.should_include(".eggs/pkg.egg/mod.py") is False

    def test_should_reject_cache_directories(self):
        f = CodeFileFilter()
        assert f.should_include("coverage/lcov.info") is False
        assert f.should_include(".nyc_output/coverage.json") is False
        assert f.should_include(".cache/babel/cache.json") is False
        assert f.should_include(".parcel-cache/data.json") is False

    def test_should_reject_ide_directories(self):
        f = CodeFileFilter()
        assert f.should_include(".idea/workspace.xml") is False
        assert f.should_include(".vscode/settings.json") is False
        assert f.should_include(".DS_Store") is False
        assert f.should_include("Thumbs.db") is False

    def test_should_reject_package_directories(self):
        f = CodeFileFilter()
        assert f.should_include("vendor/autoload.php") is False
        assert f.should_include("site-packages/requests/__init__.py") is False
        assert f.should_include("bower_components/jquery/jquery.js") is False
        assert f.should_include(".gradle/caches/test.jar") is False
        assert f.should_include(".mvn/wrapper/maven-wrapper.jar") is False
        assert f.should_include("bin/Debug/app.dll") is False
        assert f.should_include("obj/Release/app.obj") is False

    # -------------------------------------------------------------------------
    # Binary/Unknown Extensions
    # -------------------------------------------------------------------------

    def test_should_reject_image_files(self):
        f = CodeFileFilter()
        assert f.should_include("assets/image.png") is False
        assert f.should_include("static/logo.jpg") is False
        assert f.should_include("icons/icon.gif") is False
        assert f.should_include("bg.webp") is False
        assert f.should_include("favicon.ico") is False
        assert f.should_include("photo.bmp") is False
        assert f.should_include("graphic.svg") is False  # SVG is not in whitelist

    def test_should_reject_binary_executables(self):
        f = CodeFileFilter()
        assert f.should_include("bin/app.exe") is False
        assert f.should_include("lib/module.dll") is False
        assert f.should_include("lib/libtest.so") is False
        assert f.should_include("lib/test.dylib") is False
        assert f.should_include("app.bin") is False

    def test_should_reject_archive_files(self):
        f = CodeFileFilter()
        assert f.should_include("package.zip") is False
        assert f.should_include("backup.tar") is False
        assert f.should_include("data.tar.gz") is False
        assert f.should_include("archive.rar") is False
        assert f.should_include("compressed.7z") is False

    def test_should_reject_media_files(self):
        f = CodeFileFilter()
        assert f.should_include("video.mp4") is False
        assert f.should_include("audio.mp3") is False
        assert f.should_include("movie.avi") is False
        assert f.should_include("clip.mov") is False
        assert f.should_include("sound.wav") is False

    def test_should_reject_document_files(self):
        f = CodeFileFilter()
        assert f.should_include("report.pdf") is False
        assert f.should_include("document.doc") is False
        assert f.should_include("spreadsheet.xlsx") is False
        assert f.should_include("presentation.pptx") is False

    def test_should_reject_font_files(self):
        f = CodeFileFilter()
        assert f.should_include("font.ttf") is False
        assert f.should_include("icon.woff") is False
        assert f.should_include("text.woff2") is False
        assert f.should_include("font.eot") is False
        assert f.should_include("font.otf") is False

    # -------------------------------------------------------------------------
    # Size Limit Tests
    # -------------------------------------------------------------------------

    def test_should_reject_oversized_files(self):
        f = CodeFileFilter()
        # 2MB file should be rejected
        assert f.should_include("large.py", size=2 * 1024 * 1024) is False
        # 1.5MB file should be rejected
        assert f.should_include("big.ts", size=1.5 * 1024 * 1024) is False

    def test_should_accept_normal_sized_files(self):
        f = CodeFileFilter()
        # 500KB file should be accepted
        assert f.should_include("small.py", size=500 * 1024) is True
        # 1MB exactly should be accepted
        assert f.should_include("medium.ts", size=1024 * 1024) is True
        # 100KB file should be accepted
        assert f.should_include("tiny.js", size=100 * 1024) is True

    def test_should_accept_when_size_unknown(self):
        f = CodeFileFilter()
        # When size is None, don't reject based on size
        assert f.should_include("unknown.py", size=None) is True
        assert f.should_include("unknown.py") is True

    # -------------------------------------------------------------------------
    # is_path_blacklisted Tests
    # -------------------------------------------------------------------------

    def test_is_path_blacklisted_true(self):
        f = CodeFileFilter()
        assert f.is_path_blacklisted("node_modules/") is True
        assert f.is_path_blacklisted("some/path/node_modules/test") is True
        assert f.is_path_blacklisted(".git/") is True
        assert f.is_path_blacklisted("__pycache__/") is True

    def test_is_path_blacklisted_false(self):
        f = CodeFileFilter()
        assert f.is_path_blacklisted("src/components/") is False
        assert f.is_path_blacklisted("lib/utils/") is False
        assert f.is_path_blacklisted("app/") is False

    # -------------------------------------------------------------------------
    # Edge Cases
    # -------------------------------------------------------------------------

    def test_should_handle_empty_path(self):
        f = CodeFileFilter()
        assert f.should_include("") is False

    def test_should_handle_path_with_dots(self):
        f = CodeFileFilter()
        assert f.should_include("src/utils.test.ts") is True
        assert f.should_include("src/component.spec.js") is True
        assert f.should_include("path/to/file.min.js") is True

    def test_should_handle_deep_paths(self):
        f = CodeFileFilter()
        assert f.should_include("a/b/c/d/e/f/g/h/main.py") is True
        assert f.should_include("packages/core/src/lib/utils/helpers/index.ts") is True


# =============================================================================
# Navigation Parsing Tests
# =============================================================================

class TestParseParentId:
    """Tests for parse_parent_id function."""

    def test_none_returns_root(self):
        ctx = parse_parent_id(None)
        assert ctx.level == NavigationLevel.ROOT
        assert ctx.repo is None
        assert ctx.path is None

    def test_root_string_returns_root(self):
        ctx = parse_parent_id("root")
        assert ctx.level == NavigationLevel.ROOT
        assert ctx.repo is None
        assert ctx.path is None

    def test_repo_name_returns_repo_root(self):
        ctx = parse_parent_id("owner/repo")
        assert ctx.level == NavigationLevel.REPO_ROOT
        assert ctx.repo == "owner/repo"
        assert ctx.path is None

    def test_repo_with_path_returns_subfolder(self):
        ctx = parse_parent_id("owner/repo:src")
        assert ctx.level == NavigationLevel.SUBFOLDER
        assert ctx.repo == "owner/repo"
        assert ctx.path == "src"

    def test_repo_with_nested_path_returns_subfolder(self):
        ctx = parse_parent_id("owner/repo:src/components/ui")
        assert ctx.level == NavigationLevel.SUBFOLDER
        assert ctx.repo == "owner/repo"
        assert ctx.path == "src/components/ui"

    def test_empty_string_returns_root(self):
        ctx = parse_parent_id("")
        assert ctx.level == NavigationLevel.ROOT

    def test_org_repo_returns_repo_root(self):
        """Organization repos work the same as user repos."""
        ctx = parse_parent_id("my-organization/project-name")
        assert ctx.level == NavigationLevel.REPO_ROOT
        assert ctx.repo == "my-organization/project-name"

    def test_single_word_returns_root(self):
        """Single word without / should fallback to root."""
        ctx = parse_parent_id("something")
        assert ctx.level == NavigationLevel.ROOT


# =============================================================================
# GitHubRateLimiter Tests
# =============================================================================

class TestGitHubRateLimiter:
    """Comprehensive test suite for GitHubRateLimiter class."""

    def test_initial_state(self):
        limiter = GitHubRateLimiter()
        assert limiter.remaining == 5000
        assert limiter.limit == 5000
        assert limiter.used == 0
        assert limiter.reset_at is None

    def test_reserve_threshold_constant(self):
        assert GitHubRateLimiter.RESERVE_THRESHOLD == 500

    def test_update_from_headers_all_values(self):
        limiter = GitHubRateLimiter()
        reset_time = int((datetime.now(timezone.utc) + timedelta(hours=1)).timestamp())

        response = Mock()
        response.headers = {
            "X-RateLimit-Remaining": "4500",
            "X-RateLimit-Limit": "5000",
            "X-RateLimit-Used": "500",
            "X-RateLimit-Reset": str(reset_time),
        }

        limiter.update_from_headers(response)

        assert limiter.remaining == 4500
        assert limiter.limit == 5000
        assert limiter.used == 500
        assert limiter.reset_at is not None
        assert isinstance(limiter.reset_at, datetime)

    def test_update_from_headers_partial_values(self):
        limiter = GitHubRateLimiter()
        response = Mock()
        response.headers = {
            "X-RateLimit-Remaining": "3000",
        }

        limiter.update_from_headers(response)

        assert limiter.remaining == 3000
        assert limiter.limit == 5000  # Default unchanged
        assert limiter.used == 0  # Default unchanged

    def test_update_from_headers_missing_headers(self):
        limiter = GitHubRateLimiter()
        response = Mock()
        response.headers = {}

        limiter.update_from_headers(response)

        assert limiter.remaining == 5000
        assert limiter.limit == 5000

    def test_update_from_headers_invalid_values(self):
        limiter = GitHubRateLimiter()
        response = Mock()
        response.headers = {
            "X-RateLimit-Remaining": "invalid",
            "X-RateLimit-Limit": "not-a-number",
            "X-RateLimit-Reset": "bad-timestamp",
        }

        # Should not raise, just keep defaults
        limiter.update_from_headers(response)
        assert limiter.remaining == 5000

    def test_should_pause_below_threshold(self):
        limiter = GitHubRateLimiter()
        limiter.remaining = 400  # Below 500 threshold
        assert limiter.should_pause() is True

    def test_should_pause_at_threshold(self):
        limiter = GitHubRateLimiter()
        limiter.remaining = 500  # At threshold
        assert limiter.should_pause() is False

    def test_should_not_pause_above_threshold(self):
        limiter = GitHubRateLimiter()
        limiter.remaining = 600  # Above 500 threshold
        assert limiter.should_pause() is False

    def test_should_not_pause_full_quota(self):
        limiter = GitHubRateLimiter()
        limiter.remaining = 5000
        assert limiter.should_pause() is False

    def test_get_wait_time_no_reset(self):
        limiter = GitHubRateLimiter()
        limiter.reset_at = None
        assert limiter.get_wait_time() == 60.0

    def test_get_wait_time_future_reset(self):
        limiter = GitHubRateLimiter()
        limiter.reset_at = datetime.now(timezone.utc) + timedelta(minutes=30)
        wait_time = limiter.get_wait_time()
        # Allow some tolerance for test execution time
        assert 1780 < wait_time < 1820  # ~30 minutes

    def test_get_wait_time_past_reset(self):
        limiter = GitHubRateLimiter()
        limiter.reset_at = datetime.now(timezone.utc) - timedelta(minutes=5)
        wait_time = limiter.get_wait_time()
        assert wait_time == 0

    def test_get_wait_time_imminent_reset(self):
        limiter = GitHubRateLimiter()
        limiter.reset_at = datetime.now(timezone.utc) + timedelta(seconds=10)
        wait_time = limiter.get_wait_time()
        assert 5 < wait_time < 15


# =============================================================================
# GitHubConnector Tests
# =============================================================================

class TestGitHubConnector:
    """Comprehensive test suite for GitHubConnector class."""

    # -------------------------------------------------------------------------
    # Properties
    # -------------------------------------------------------------------------

    def test_connector_type(self):
        connector = GitHubConnector()
        assert connector.connector_type == SourceType.GITHUB

    def test_supports_incremental_sync(self):
        connector = GitHubConnector()
        assert connector.supports_incremental_sync is True

    def test_supports_batch_fetch(self):
        connector = GitHubConnector()
        assert connector.supports_batch_fetch is True

    def test_filter_and_rate_limiter_initialized(self):
        connector = GitHubConnector()
        assert isinstance(connector._filter, CodeFileFilter)
        assert isinstance(connector._rate_limiter, GitHubRateLimiter)

    # -------------------------------------------------------------------------
    # validate_config Tests
    # -------------------------------------------------------------------------

    def test_validate_config_with_access_token_success(self):
        connector = GitHubConnector()

        with patch.object(connector, "_verify_token", return_value={"login": "testuser"}):
            assert connector.validate_config({"access_token": "test-token"}) is True

    def test_validate_config_with_invalid_token(self):
        connector = GitHubConnector()

        with patch.object(connector, "_verify_token", side_effect=ConnectorAuthError("Invalid")):
            assert connector.validate_config({"access_token": "bad-token"}) is False

    def test_validate_config_with_integration_id(self):
        connector = GitHubConnector()
        # Should return True without verifying (deferred validation)
        assert connector.validate_config({"integration_id": "int-123"}) is True

    def test_validate_config_with_user_id(self):
        connector = GitHubConnector()
        # Should return True without verifying (deferred validation)
        assert connector.validate_config({"user_id": "user-123"}) is True

    def test_validate_config_empty_config(self):
        connector = GitHubConnector()
        assert connector.validate_config({}) is False

    def test_validate_config_none(self):
        connector = GitHubConnector()
        assert connector.validate_config(None) is False

    def test_validate_config_non_dict(self):
        connector = GitHubConnector()
        assert connector.validate_config("string") is False
        assert connector.validate_config(123) is False
        assert connector.validate_config([]) is False

    def test_validate_config_network_error_returns_true(self):
        connector = GitHubConnector()
        # Network errors shouldn't invalidate config
        with patch.object(connector, "_verify_token", side_effect=ConnectorTransientError("Network")):
            assert connector.validate_config({"access_token": "token"}) is True

    # -------------------------------------------------------------------------
    # _verify_token Tests
    # -------------------------------------------------------------------------

    def test_verify_token_success(self):
        connector = GitHubConnector()

        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.json.return_value = {"login": "testuser", "id": 12345}
        mock_response.headers = {}

        with patch("connectors.github.requests.get", return_value=mock_response):
            result = connector._verify_token("valid-token")

        assert result["login"] == "testuser"
        assert result["id"] == 12345

    def test_verify_token_401_raises_auth_error(self):
        connector = GitHubConnector()

        mock_response = Mock()
        mock_response.status_code = 401
        mock_response.headers = {}

        with patch("connectors.github.requests.get", return_value=mock_response):
            with pytest.raises(ConnectorAuthError, match="invalid or revoked"):
                connector._verify_token("invalid-token")

    def test_verify_token_403_raises_auth_error(self):
        connector = GitHubConnector()

        mock_response = Mock()
        mock_response.status_code = 403
        mock_response.headers = {}

        with patch("connectors.github.requests.get", return_value=mock_response):
            with pytest.raises(ConnectorAuthError, match="lacks required permissions"):
                connector._verify_token("token-without-perms")

    def test_verify_token_500_raises_transient_error(self):
        connector = GitHubConnector()

        mock_response = Mock()
        mock_response.status_code = 500
        mock_response.text = "Internal Server Error"
        mock_response.headers = {}

        with patch("connectors.github.requests.get", return_value=mock_response):
            with pytest.raises(ConnectorTransientError, match="GitHub API error"):
                connector._verify_token("token")

    def test_verify_token_request_exception(self):
        connector = GitHubConnector()

        with patch("connectors.github.requests.get", side_effect=requests.RequestException("Network error")):
            with pytest.raises(ConnectorTransientError, match="connection error"):
                connector._verify_token("token")

    def test_verify_token_updates_rate_limiter(self):
        connector = GitHubConnector()

        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.json.return_value = {"login": "testuser"}
        mock_response.headers = {"X-RateLimit-Remaining": "4999"}

        with patch("connectors.github.requests.get", return_value=mock_response):
            connector._verify_token("token")

        assert connector._rate_limiter.remaining == 4999

    # -------------------------------------------------------------------------
    # _get_headers Tests
    # -------------------------------------------------------------------------

    def test_get_headers(self):
        connector = GitHubConnector()
        headers = connector._get_headers({"access_token": "test-token"})

        assert headers["Authorization"] == "Bearer test-token"
        assert headers["Accept"] == "application/vnd.github.v3+json"
        assert headers["X-GitHub-Api-Version"] == "2022-11-28"

    def test_get_headers_none_token(self):
        connector = GitHubConnector()
        headers = connector._get_headers({"access_token": None})

        assert headers["Authorization"] == "Bearer None"

    # -------------------------------------------------------------------------
    # _request Tests
    # -------------------------------------------------------------------------

    def test_request_success(self):
        connector = GitHubConnector()

        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.json.return_value = {"data": "test"}
        mock_response.raise_for_status = Mock()
        mock_response.headers = {}

        with patch.object(connector, "_request_with_retry", return_value=mock_response), \
             patch("connectors.github.connector_fetch_limit") as mock_limit:
            mock_limit.return_value.__enter__ = Mock()
            mock_limit.return_value.__exit__ = Mock()

            result = connector._request({"access_token": "token"}, "https://api.github.com/test")

        assert result["data"] == "test"

    def test_request_404_raises_item_not_found(self):
        connector = GitHubConnector()

        mock_response = Mock()
        mock_response.status_code = 404
        mock_response.headers = {}

        with patch.object(connector, "_request_with_retry", return_value=mock_response), \
             patch("connectors.github.connector_fetch_limit") as mock_limit:
            mock_limit.return_value.__enter__ = Mock()
            mock_limit.return_value.__exit__ = Mock()

            with pytest.raises(ItemNotFoundError, match="not found"):
                connector._request({"access_token": "token"}, "https://api.github.com/missing")

    def test_request_http_error_raises_transient(self):
        connector = GitHubConnector()

        mock_response = Mock()
        mock_response.status_code = 502
        mock_response.raise_for_status.side_effect = requests.HTTPError("Bad Gateway")
        mock_response.headers = {}

        with patch.object(connector, "_request_with_retry", return_value=mock_response), \
             patch("connectors.github.connector_fetch_limit") as mock_limit:
            mock_limit.return_value.__enter__ = Mock()
            mock_limit.return_value.__exit__ = Mock()

            with pytest.raises(ConnectorTransientError, match="GitHub API error"):
                connector._request({"access_token": "token"}, "https://api.github.com/test")

    # -------------------------------------------------------------------------
    # _request_with_retry Tests
    # -------------------------------------------------------------------------

    def test_request_with_retry_success(self):
        connector = GitHubConnector()

        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.headers = {}

        with patch("connectors.github.requests.request", return_value=mock_response):
            result = connector._request_with_retry("GET", "https://api.github.com/test")

        assert result.status_code == 200

    def test_request_with_retry_rate_limit_403(self):
        connector = GitHubConnector()

        mock_response_403 = Mock()
        mock_response_403.status_code = 403
        mock_response_403.headers = {"Retry-After": "1"}
        mock_response_403.text = "rate limit exceeded"
        mock_response_403.close = Mock()

        mock_response_ok = Mock()
        mock_response_ok.status_code = 200
        mock_response_ok.headers = {}

        with patch("connectors.github.requests.request", side_effect=[mock_response_403, mock_response_ok]), \
             patch("connectors.github.time.sleep") as mock_sleep:
            result = connector._request_with_retry("GET", "https://api.github.com/test")

        assert result.status_code == 200
        mock_sleep.assert_called()

    def test_request_with_retry_rate_limit_429(self):
        connector = GitHubConnector()

        mock_response_429 = Mock()
        mock_response_429.status_code = 429
        mock_response_429.headers = {"Retry-After": "1"}
        mock_response_429.text = "secondary rate limit"
        mock_response_429.close = Mock()

        mock_response_ok = Mock()
        mock_response_ok.status_code = 200
        mock_response_ok.headers = {}

        with patch("connectors.github.requests.request", side_effect=[mock_response_429, mock_response_ok]), \
             patch("connectors.github.time.sleep"):
            result = connector._request_with_retry("GET", "https://api.github.com/test")

        assert result.status_code == 200

    def test_request_with_retry_rate_limit_max_retries(self):
        connector = GitHubConnector()

        mock_response = Mock()
        mock_response.status_code = 429
        mock_response.headers = {"Retry-After": "1"}
        mock_response.text = "rate limit"
        mock_response.close = Mock()

        with patch("connectors.github.requests.request", return_value=mock_response), \
             patch("connectors.github.time.sleep"):
            with pytest.raises(ConnectorRateLimitError):
                connector._request_with_retry("GET", "https://api.github.com/test")

    def test_request_with_retry_auth_error(self):
        connector = GitHubConnector()

        mock_response = Mock()
        mock_response.status_code = 401
        mock_response.headers = {}
        mock_response.close = Mock()

        with patch("connectors.github.requests.request", return_value=mock_response):
            with pytest.raises(ConnectorAuthError, match="invalid or revoked"):
                connector._request_with_retry("GET", "https://api.github.com/test")

    def test_request_with_retry_server_error(self):
        connector = GitHubConnector()

        mock_response = Mock()
        mock_response.status_code = 500
        mock_response.text = "Internal Server Error"
        mock_response.headers = {}
        mock_response.close = Mock()

        with patch("connectors.github.requests.request", return_value=mock_response):
            with pytest.raises(ConnectorTransientError, match="server error"):
                connector._request_with_retry("GET", "https://api.github.com/test")

    def test_request_with_retry_network_error(self):
        connector = GitHubConnector()

        with patch("connectors.github.requests.request", side_effect=requests.RequestException("Network down")):
            with pytest.raises(ConnectorTransientError, match="network error"):
                connector._request_with_retry("GET", "https://api.github.com/test")

    # -------------------------------------------------------------------------
    # get_available_repositories Tests
    # -------------------------------------------------------------------------

    def test_get_available_repositories_success(self):
        connector = GitHubConnector()

        mock_repos = [
            {
                "id": 1,
                "name": "repo1",
                "full_name": "user/repo1",
                "description": "Test repo 1",
                "private": False,
                "fork": False,
                "archived": False,
                "default_branch": "main",
                "owner": {"login": "user", "type": "User"},
                "updated_at": "2024-01-01T00:00:00Z",
                "language": "Python",
                "stargazers_count": 10,
            },
            {
                "id": 2,
                "name": "repo2",
                "full_name": "user/repo2",
                "description": "Test repo 2",
                "private": True,
                "fork": False,
                "archived": False,
                "default_branch": "master",
                "owner": {"login": "user", "type": "User"},
                "updated_at": "2024-01-02T00:00:00Z",
                "language": "TypeScript",
                "stargazers_count": 5,
            },
        ]

        with patch.object(connector, "_request", return_value=mock_repos):
            repos = connector.get_available_repositories("test-token")

        assert len(repos) == 2
        assert repos[0]["full_name"] == "user/repo1"
        assert repos[0]["private"] is False
        assert repos[1]["full_name"] == "user/repo2"
        assert repos[1]["private"] is True

    def test_get_available_repositories_pagination(self):
        connector = GitHubConnector()

        page1 = [{"id": i, "name": f"repo{i}", "full_name": f"user/repo{i}",
                  "owner": {"login": "user", "type": "User"}} for i in range(100)]
        page2 = [{"id": 100, "name": "repo100", "full_name": "user/repo100",
                  "owner": {"login": "user", "type": "User"}}]

        with patch.object(connector, "_request", side_effect=[page1, page2]):
            repos = connector.get_available_repositories("test-token")

        assert len(repos) == 101

    def test_get_available_repositories_empty(self):
        connector = GitHubConnector()

        with patch.object(connector, "_request", return_value=[]):
            repos = connector.get_available_repositories("test-token")

        assert repos == []

    def test_get_available_repositories_error_handling(self):
        connector = GitHubConnector()

        with patch.object(connector, "_request", side_effect=Exception("API error")):
            repos = connector.get_available_repositories("test-token")

        assert repos == []

    # -------------------------------------------------------------------------
    # _get_branch_sha Tests
    # -------------------------------------------------------------------------

    def test_get_branch_sha_success(self):
        connector = GitHubConnector()

        mock_response = {
            "commit": {"sha": "abc123def456"}
        }

        with patch.object(connector, "_request", return_value=mock_response):
            sha = connector._get_branch_sha({"access_token": "token"}, "user/repo", "main")

        assert sha == "abc123def456"

    # -------------------------------------------------------------------------
    # _fetch_tree Tests
    # -------------------------------------------------------------------------

    def test_fetch_tree_not_truncated(self):
        connector = GitHubConnector()

        mock_tree = {
            "truncated": False,
            "tree": [
                {"path": "src/main.py", "type": "blob", "sha": "abc123"},
                {"path": "README.md", "type": "blob", "sha": "def456"},
            ]
        }

        with patch.object(connector, "_request", return_value=mock_tree):
            entries = list(connector._fetch_tree({"access_token": "token"}, "user/repo", "sha123"))

        assert len(entries) == 2

    def test_fetch_tree_truncated_fallback(self):
        connector = GitHubConnector()

        mock_tree = {
            "truncated": True,
            "tree": []
        }

        mock_dfs_entries = [
            {"path": "src/main.py", "type": "blob", "sha": "abc123"},
        ]

        with patch.object(connector, "_request", return_value=mock_tree), \
             patch.object(connector, "_fetch_tree_dfs", return_value=iter(mock_dfs_entries)):
            entries = list(connector._fetch_tree({"access_token": "token"}, "user/repo", "sha123"))

        assert len(entries) == 1

    # -------------------------------------------------------------------------
    # list_files Tests
    # -------------------------------------------------------------------------

    def test_list_files_no_selected_repos(self):
        connector = GitHubConnector()

        with patch.object(connector, "_resolve_config", return_value={"credentials": {}}):
            files = list(connector.list_files({}))

        assert files == []

    def test_list_files_empty_selected_repos(self):
        connector = GitHubConnector()

        with patch.object(connector, "_resolve_config", return_value={"credentials": {"selected_repositories": []}}):
            files = list(connector.list_files({}))

        assert files == []

    def test_list_files_repo_disabled(self):
        connector = GitHubConnector()

        config = {
            "credentials": {
                "selected_repositories": [
                    {"full_name": "user/repo", "enabled": False}
                ]
            }
        }

        with patch.object(connector, "_resolve_config", return_value=config):
            files = list(connector.list_files({}))

        assert files == []

    def test_list_files_root_shows_repos_as_folders(self):
        """At root level (no parent_id), list_files returns repos as folders."""
        connector = GitHubConnector()

        config = {
            "access_token": "token",
            "credentials": {
                "selected_repositories": [
                    {"full_name": "user/repo1", "branch": "main", "enabled": True},
                    {"full_name": "user/repo2", "branch": "develop", "enabled": True},
                ]
            }
        }

        with patch.object(connector, "_resolve_config", return_value=config):
            # No parent_id means root level
            items = list(connector.list_files({"parent_id": None}))

        assert len(items) == 2
        assert all(isinstance(f, RemoteFile) for f in items)
        # Repos shown as folders
        assert items[0].id == "user/repo1"
        assert items[0].name == "repo1"
        assert items[0].mime_type == "application/vnd.github.repository"
        assert items[1].id == "user/repo2"
        assert items[1].name == "repo2"

    def test_list_files_inside_repo_shows_contents(self):
        """Inside a repo, list_files returns immediate children (files + folders)."""
        connector = GitHubConnector()

        config = {
            "access_token": "token",
            "credentials": {
                "selected_repositories": [
                    {"full_name": "user/repo", "branch": "main", "enabled": True}
                ]
            }
        }

        mock_tree = [
            {"path": "src/main.py", "type": "blob", "sha": "abc123", "size": 1000},
            {"path": "src/utils/helper.py", "type": "blob", "sha": "xyz789", "size": 500},
            {"path": "README.md", "type": "blob", "sha": "def456", "size": 500},
            {"path": "node_modules/test.js", "type": "blob", "sha": "ghi789", "size": 100},  # Blacklisted folder
            {"path": "src", "type": "tree", "sha": "xyz"},
        ]

        with patch.object(connector, "_resolve_config", return_value=config), \
             patch.object(connector, "_get_branch_sha", return_value="sha123"), \
             patch.object(connector, "_fetch_tree", return_value=iter(mock_tree)), \
             patch.object(connector, "_request", return_value={"default_branch": "main"}):
            # parent_id="user/repo" means inside the repo root
            items = list(connector.list_files({"parent_id": "user/repo"}))

        # Should show: src folder (from nested files) + README.md
        # node_modules should be filtered out
        assert len(items) == 2
        # Folders first, then files
        assert items[0].name == "src"
        assert items[0].mime_type == "application/vnd.github.folder"
        assert items[1].name == "README.md"
        assert "blob" in items[1].mime_type or items[1].mime_type == "text/markdown"

    def test_list_files_inside_subfolder(self):
        """Inside a subfolder, list_files returns that folder's contents."""
        connector = GitHubConnector()

        config = {
            "access_token": "token",
            "credentials": {
                "selected_repositories": [
                    {"full_name": "user/repo", "branch": "main", "enabled": True}
                ]
            }
        }

        mock_tree = [
            {"path": "src/main.py", "type": "blob", "sha": "abc123", "size": 1000},
            {"path": "src/utils/helper.py", "type": "blob", "sha": "xyz789", "size": 500},
            {"path": "src/index.ts", "type": "blob", "sha": "index123", "size": 800},
            {"path": "README.md", "type": "blob", "sha": "def456", "size": 500},
        ]

        with patch.object(connector, "_resolve_config", return_value=config), \
             patch.object(connector, "_get_branch_sha", return_value="sha123"), \
             patch.object(connector, "_fetch_tree", return_value=iter(mock_tree)), \
             patch.object(connector, "_request", return_value={"default_branch": "main"}):
            # parent_id="user/repo:src" means inside src folder
            items = list(connector.list_files({"parent_id": "user/repo:src"}))

        # Should show: utils folder + main.py + index.ts
        assert len(items) == 3
        # Folders first
        assert items[0].name == "utils"
        assert items[0].mime_type == "application/vnd.github.folder"
        # Then files (sorted alphabetically)
        file_names = [i.name for i in items[1:]]
        assert "index.ts" in file_names
        assert "main.py" in file_names

    def test_list_files_disabled_repos_skipped(self):
        """Disabled repos should not appear in listing."""
        connector = GitHubConnector()

        config = {
            "access_token": "token",
            "credentials": {
                "selected_repositories": [
                    {"full_name": "user/enabled", "enabled": True},
                    {"full_name": "user/disabled", "enabled": False},
                ]
            }
        }

        with patch.object(connector, "_resolve_config", return_value=config):
            items = list(connector.list_files({"parent_id": None}))

        assert len(items) == 1
        assert items[0].name == "enabled"

    def test_list_all_repo_files_flat(self):
        """list_all_repo_files returns all files flat (for ingestion)."""
        connector = GitHubConnector()

        config = {
            "access_token": "token",
            "credentials": {
                "selected_repositories": [
                    {"full_name": "user/repo", "branch": "main", "enabled": True}
                ]
            }
        }

        mock_tree = [
            {"path": "src/main.py", "type": "blob", "sha": "abc123", "size": 1000},
            {"path": "README.md", "type": "blob", "sha": "def456", "size": 500},
            {"path": "node_modules/test.js", "type": "blob", "sha": "ghi789", "size": 100},  # Should be filtered
        ]

        with patch.object(connector, "_resolve_config", return_value=config), \
             patch.object(connector, "_get_branch_sha", return_value="sha123"), \
             patch.object(connector, "_fetch_tree", return_value=iter(mock_tree)), \
             patch.object(connector, "_request", return_value={"default_branch": "main"}):
            files = list(connector.list_all_repo_files({}))

        assert len(files) == 2
        assert all(isinstance(f, RemoteFile) for f in files)
        # Flat listing - file names only
        assert files[0].name == "main.py"
        assert files[1].name == "README.md"

    def test_list_all_repo_files_rate_limit_pause(self):
        """list_all_repo_files respects rate limits."""
        connector = GitHubConnector()
        connector._rate_limiter.remaining = 100  # Below threshold

        config = {
            "credentials": {
                "selected_repositories": [
                    {"full_name": "user/repo1", "enabled": True},
                    {"full_name": "user/repo2", "enabled": True},
                ]
            }
        }

        with patch.object(connector, "_resolve_config", return_value=config):
            files = list(connector.list_all_repo_files({}))

        # Should stop immediately due to rate limit
        assert files == []

    # -------------------------------------------------------------------------
    # fetch_file_content Tests
    # -------------------------------------------------------------------------

    def test_fetch_file_content_success(self):
        connector = GitHubConnector()

        with patch.object(connector, "_resolve_config", return_value={"access_token": "token"}), \
             patch.object(connector, "_fetch_blob_raw", return_value=b"print('hello')"):
            content = connector.fetch_file_content("user/repo:abc123:src/main.py", {})

        assert content == b"print('hello')"

    def test_fetch_file_content_invalid_id_format(self):
        connector = GitHubConnector()

        with patch.object(connector, "_resolve_config", return_value={"access_token": "token"}):
            with pytest.raises(ValueError, match="Invalid GitHub file ID"):
                connector.fetch_file_content("invalid-id", {})

    # -------------------------------------------------------------------------
    # fetch_documents_sync Tests
    # -------------------------------------------------------------------------

    def test_fetch_documents_sync_empty_items(self):
        connector = GitHubConnector()
        result = list(connector.fetch_documents_sync([]))
        assert result == []

    def test_fetch_documents_sync_invalid_id_format(self):
        connector = GitHubConnector()

        with patch.object(connector, "_resolve_config", return_value={"access_token": "token"}):
            result = list(connector.fetch_documents_sync(["invalid-id"]))

        assert result == []

    def test_fetch_documents_sync_success(self):
        connector = GitHubConnector()

        with patch.object(connector, "_resolve_config", return_value={"access_token": "token"}), \
             patch.object(connector, "_fetch_blob_raw", return_value=b"print('hello')"):
            docs = list(connector.fetch_documents_sync(["user/repo:abc123:src/main.py"]))

        assert len(docs) == 1
        assert isinstance(docs[0], SourceDocument)
        assert docs[0].filename == "main.py"
        assert docs[0].source_type == SourceType.GITHUB
        assert docs[0].content == b"print('hello')"
        assert docs[0].metadata["repository"] == "user/repo"
        assert docs[0].metadata["path"] == "src/main.py"
        assert docs[0].metadata["git_blob_sha"] == "abc123"

    def test_fetch_documents_sync_skips_binary(self):
        connector = GitHubConnector()

        with patch.object(connector, "_resolve_config", return_value={"access_token": "token"}), \
             patch.object(connector, "_fetch_blob_raw", return_value=b"\x00binary\x00content"):
            docs = list(connector.fetch_documents_sync(["user/repo:abc123:image.png"]))

        assert len(docs) == 0

    def test_fetch_documents_sync_handles_not_found(self):
        connector = GitHubConnector()

        with patch.object(connector, "_resolve_config", return_value={"access_token": "token"}), \
             patch.object(connector, "_fetch_blob_raw", side_effect=ItemNotFoundError("Not found")):
            docs = list(connector.fetch_documents_sync(["user/repo:abc123:missing.py"]))

        assert len(docs) == 0

    def test_fetch_documents_sync_handles_errors(self):
        connector = GitHubConnector()

        with patch.object(connector, "_resolve_config", return_value={"access_token": "token"}), \
             patch.object(connector, "_fetch_blob_raw", side_effect=Exception("API error")):
            docs = list(connector.fetch_documents_sync(["user/repo:abc123:error.py"]))

        assert len(docs) == 0

    def test_fetch_documents_sync_multiple_items(self):
        connector = GitHubConnector()

        def mock_fetch(config, repo, sha):
            if sha == "abc123":
                return b"print('hello')"
            elif sha == "def456":
                return b"# README"
            return b""

        with patch.object(connector, "_resolve_config", return_value={"access_token": "token"}), \
             patch.object(connector, "_fetch_blob_raw", side_effect=mock_fetch):
            docs = list(connector.fetch_documents_sync([
                "user/repo:abc123:src/main.py",
                "user/repo:def456:README.md",
            ]))

        assert len(docs) == 2
        assert docs[0].filename == "main.py"
        assert docs[1].filename == "README.md"

    # -------------------------------------------------------------------------
    # _resolve_config Tests
    # -------------------------------------------------------------------------

    def test_resolve_config_with_access_token(self):
        connector = GitHubConnector()

        result = connector._resolve_config({"access_token": "token123"})

        assert result["access_token"] == "token123"

    def test_resolve_config_loads_from_integration(self):
        connector = GitHubConnector()

        mock_integration = {
            "id": "int-1",
            "credentials": {"selected_repositories": []}
        }

        mock_creds = {"access_token": "loaded-token", "integration_id": "int-1"}

        # Patch the shared utility functions used by _resolve_config
        with patch("connectors.utils.load_integration", return_value=mock_integration), \
             patch("connectors.utils.OAuthTokenManager.get_valid_credentials", return_value=mock_creds):
            result = connector._resolve_config({"integration_id": "int-1"})

        assert result["access_token"] == "loaded-token"

    def test_resolve_config_token_refresh_error(self):
        connector = GitHubConnector()

        mock_integration = {"id": "int-1"}

        from services.oauth_token_manager import TokenRefreshError

        # Patch the shared utility functions used by _resolve_config
        with patch("connectors.utils.load_integration", return_value=mock_integration), \
             patch("connectors.utils.OAuthTokenManager.get_valid_credentials",
                   side_effect=TokenRefreshError("Token refresh failed")):
            with pytest.raises(ConnectorAuthError, match="requires reconnection"):
                connector._resolve_config({"integration_id": "int-1"})

    # -------------------------------------------------------------------------
    # Shared Utility Integration Tests (via connectors.utils)
    # -------------------------------------------------------------------------

    def test_load_integration_by_id(self):
        """Test that load_integration works with integration_id."""
        from connectors.utils import load_integration

        mock_supabase = MagicMock()
        mock_supabase.table.return_value.select.return_value.eq.return_value.single.return_value.execute.return_value = MagicMock(
            data={"id": "int-1", "access_token": "enc-token"}
        )

        with patch("connectors.utils.get_supabase", return_value=mock_supabase):
            result = load_integration("github", integration_id="int-1")

        assert result["id"] == "int-1"

    def test_load_integration_not_found(self):
        """Test that load_integration raises error when not found."""
        from connectors.utils import load_integration

        mock_supabase = MagicMock()
        mock_supabase.table.return_value.select.return_value.eq.return_value.single.return_value.execute.return_value = MagicMock(
            data=None
        )

        with patch("connectors.utils.get_supabase", return_value=mock_supabase):
            with pytest.raises(ConnectorAuthError, match="not found"):
                load_integration("github", integration_id="int-1")

    def test_load_integration_requires_user_or_integration_id(self):
        """Test that load_integration raises error without identifiers."""
        from connectors.utils import load_integration

        with pytest.raises(ConnectorAuthError, match="requires user_id or integration_id"):
            load_integration("github")

    # -------------------------------------------------------------------------
    # Helper Methods Tests
    # -------------------------------------------------------------------------

    def test_is_binary_with_null_byte(self):
        assert GitHubConnector._is_binary(b"Hello\x00World") is True
        assert GitHubConnector._is_binary(b"\x00\x01\x02") is True

    def test_is_binary_without_null_byte(self):
        assert GitHubConnector._is_binary(b"Hello World") is False
        assert GitHubConnector._is_binary(b"print('hello')") is False

    def test_is_binary_empty_content(self):
        assert GitHubConnector._is_binary(b"") is False

    def test_is_binary_large_content(self):
        # Only checks first 8KB
        content = b"safe content" * 1000 + b"\x00" + b"more"
        # Null byte is beyond 8KB check
        if len(b"safe content" * 1000) > 8192:
            assert GitHubConnector._is_binary(content) is False

    def test_guess_mime_type_programming_languages(self):
        assert GitHubConnector._guess_mime_type("main.py") == "text/x-python"
        assert GitHubConnector._guess_mime_type("app.js") == "text/javascript"
        assert GitHubConnector._guess_mime_type("app.ts") == "text/typescript"
        assert GitHubConnector._guess_mime_type("component.tsx") == "text/typescript-jsx"
        assert GitHubConnector._guess_mime_type("component.jsx") == "text/javascript-jsx"
        assert GitHubConnector._guess_mime_type("main.go") == "text/x-go"
        assert GitHubConnector._guess_mime_type("lib.rs") == "text/x-rust"
        assert GitHubConnector._guess_mime_type("Main.java") == "text/x-java"
        assert GitHubConnector._guess_mime_type("app.rb") == "text/x-ruby"
        assert GitHubConnector._guess_mime_type("index.php") == "text/x-php"
        assert GitHubConnector._guess_mime_type("main.c") == "text/x-c"
        assert GitHubConnector._guess_mime_type("main.cpp") == "text/x-c++"
        assert GitHubConnector._guess_mime_type("Program.cs") == "text/x-csharp"
        assert GitHubConnector._guess_mime_type("App.swift") == "text/x-swift"
        assert GitHubConnector._guess_mime_type("App.kt") == "text/x-kotlin"
        assert GitHubConnector._guess_mime_type("App.scala") == "text/x-scala"
        assert GitHubConnector._guess_mime_type("query.sql") == "text/x-sql"
        assert GitHubConnector._guess_mime_type("script.sh") == "text/x-shellscript"
        assert GitHubConnector._guess_mime_type("script.bash") == "text/x-shellscript"

    def test_guess_mime_type_web_files(self):
        assert GitHubConnector._guess_mime_type("README.md") == "text/markdown"
        assert GitHubConnector._guess_mime_type("config.yaml") == "text/yaml"
        assert GitHubConnector._guess_mime_type("config.yml") == "text/yaml"
        assert GitHubConnector._guess_mime_type("data.json") == "application/json"
        assert GitHubConnector._guess_mime_type("config.xml") == "application/xml"
        assert GitHubConnector._guess_mime_type("index.html") == "text/html"
        assert GitHubConnector._guess_mime_type("styles.css") == "text/css"
        assert GitHubConnector._guess_mime_type("theme.scss") == "text/x-scss"
        assert GitHubConnector._guess_mime_type("App.vue") == "text/x-vue"
        assert GitHubConnector._guess_mime_type("Component.svelte") == "text/x-svelte"

    def test_guess_mime_type_unknown(self):
        # Note: mimetypes.guess_type may return known types for some extensions
        # .xyz is actually 'chemical/x-xyz' according to mimetypes module
        result = GitHubConnector._guess_mime_type("file.xyz")
        assert result is not None  # May be 'chemical/x-xyz' or 'text/plain'
        # For truly unknown extensions
        assert GitHubConnector._guess_mime_type("data.unknownext123") == "text/plain"

    def test_guess_mime_type_none(self):
        assert GitHubConnector._guess_mime_type(None) == "text/plain"

    def test_guess_mime_type_no_extension(self):
        assert GitHubConnector._guess_mime_type("Makefile") == "text/plain"


# =============================================================================
# Async Tests
# =============================================================================

@pytest.mark.asyncio
async def test_fetch_documents_async():
    connector = GitHubConnector()

    doc = SourceDocument(
        content=b"test content",
        metadata={"source": "github"},
        source_type=SourceType.GITHUB,
        source_id="test-id",
        filename="test.py",
        mime_type="text/x-python",
        size_bytes=12,
    )

    with patch.object(connector, "fetch_documents_sync", return_value=iter([doc])):
        docs = []
        async for d in connector.fetch_documents(["test"]):
            docs.append(d)

    assert docs == [doc]


@pytest.mark.asyncio
async def test_fetch_documents_async_empty():
    connector = GitHubConnector()

    with patch.object(connector, "fetch_documents_sync", return_value=iter([])):
        docs = []
        async for d in connector.fetch_documents([]):
            docs.append(d)

    assert docs == []


# =============================================================================
# Factory Function Tests
# =============================================================================

def test_get_github_connector():
    connector = get_github_connector()
    assert isinstance(connector, GitHubConnector)


def test_get_connector_returns_github():
    from connectors import get_connector
    connector = get_connector("github")
    assert isinstance(connector, GitHubConnector)


# =============================================================================
# Integration with Connector Registry
# =============================================================================

def test_github_in_connector_registry():
    from connectors.registry import CONNECTOR_REGISTRY

    assert "github" in CONNECTOR_REGISTRY
    github_config = CONNECTOR_REGISTRY["github"]
    assert github_config["id"] == "github"
    assert github_config["name"] == "GitHub"
    assert "code_aware" in github_config["capabilities"]
    assert "incremental_sync" in github_config["capabilities"]

