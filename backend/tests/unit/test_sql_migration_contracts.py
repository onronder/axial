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
