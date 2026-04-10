from pathlib import Path

import pytest

pytestmark = pytest.mark.unit


def _latest_hybrid_search_scoped_migration() -> tuple[Path, str]:
    repo_root = Path(__file__).resolve().parents[3]
    migration_dir = repo_root / "supabase" / "migrations"
    latest_match: tuple[Path, str] | None = None

    for path in sorted(migration_dir.glob("*.sql")):
        text = path.read_text(encoding="utf-8")
        if "CREATE OR REPLACE FUNCTION public.hybrid_search_scoped" in text:
            latest_match = (path, text)

    assert latest_match is not None, "Expected a migration defining hybrid_search_scoped"
    return latest_match


def _latest_function_migration(function_name: str) -> tuple[Path, str]:
    repo_root = Path(__file__).resolve().parents[3]
    migration_dir = repo_root / "supabase" / "migrations"
    latest_match: tuple[Path, str] | None = None
    marker = f"CREATE OR REPLACE FUNCTION public.{function_name}"

    for path in sorted(migration_dir.glob("*.sql")):
        text = path.read_text(encoding="utf-8")
        if marker in text:
            latest_match = (path, text)

    assert latest_match is not None, f"Expected a migration defining {function_name}"
    return latest_match


def test_latest_hybrid_search_scoped_includes_null_scope_visibility_guard():
    path, text = _latest_hybrid_search_scoped_migration()

    assert text.count("d.scope_id IS NULL") >= 2, (
        f"{path.name} should preserve NULL scope visibility in both semantic and keyword branches"
    )


def test_latest_hybrid_search_scoped_keeps_language_regconfig_querying():
    path, text = _latest_hybrid_search_scoped_migration()

    assert "plainto_tsquery(search_language::regconfig, query_text)" in text, (
        f"{path.name} should keep per-language tsquery execution"
    )
    assert "search_language := 'simple'" not in text, (
        f"{path.name} should not regress to a hardcoded simple-only search language"
    )


@pytest.mark.parametrize("function_name", ["hybrid_search", "hybrid_search_scoped"])
def test_latest_search_functions_exclude_identity_documents(function_name: str):
    path, text = _latest_function_migration(function_name)

    assert "NOT IN ('identity', 'scope_identity')" in text, (
        f"{path.name} should exclude identity documents in {function_name}"
    )
    assert "identity_card" in text, (
        f"{path.name} should preserve identity card metadata exclusion in {function_name}"
    )


@pytest.mark.parametrize("function_name", ["hybrid_search", "hybrid_search_scoped"])
def test_latest_search_functions_set_search_path_public(function_name: str):
    path, text = _latest_function_migration(function_name)

    assert "SECURITY DEFINER" in text, f"{path.name} should preserve SECURITY DEFINER for {function_name}"
    assert "SET search_path = public" in text, (
        f"{path.name} should pin search_path for {function_name}"
    )
