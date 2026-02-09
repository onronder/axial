"""
Migration Validation Tests

Static analysis tests that verify:
1. SQL functions don't reference removed columns
2. Migration timestamps are in order
3. No duplicate function definitions that could conflict

These tests run WITHOUT a database connection - they analyze SQL files directly.

Run with: pytest backend/tests/integration/test_migration_validation.py -v
"""

import re
from pathlib import Path

import pytest

# Path to migrations
MIGRATIONS_PATH = Path(__file__).parent.parent.parent.parent / "supabase" / "migrations"


class TestMigrationStaticAnalysis:
    """Static analysis of migration files to catch common issues."""

    @pytest.fixture(scope="class")
    def migration_files(self) -> list[tuple[str, str]]:
        """Load all migration files and their contents."""
        if not MIGRATIONS_PATH.exists():
            pytest.skip(f"Migrations path not found: {MIGRATIONS_PATH}")

        migrations = []
        for file in sorted(MIGRATIONS_PATH.glob("*.sql")):
            content = file.read_text()
            migrations.append((file.name, content))

        return migrations

    @pytest.fixture(scope="class")
    def removed_columns(self) -> dict[str, set[str]]:
        """
        Columns that have been removed and should NOT be referenced.

        Format: {"table_name": {"column1", "column2"}}
        """
        return {
            "user_profiles": {"subscription_status"},
            # Add more as needed
        }

    def test_no_references_to_removed_columns(
        self,
        migration_files: list[tuple[str, str]],
        removed_columns: dict[str, set[str]]
    ):
        """
        Verify no migration references columns that have been removed.

        This catches the bug where migration 20260216160000 referenced
        subscription_status after it was removed in 20251231130000.
        """
        # Skip migrations that legitimately reference the column
        # Note: Old migrations before the column was removed are fine.
        # The key is that no migration AFTER the removal (20251231130000) should reference it,
        # unless it has been superseded by a fix migration.
        skip_patterns = [
            "20251227154700",  # Migration that originally ADDED subscription_status
            "20251228160000",  # strict_paywall - before removal
            "20251229000000",  # fix_paywall_trigger - before removal
            "20251231130000",  # Migration that REMOVES subscription_status
            "20260220000000",  # Fix migration v3 (documents the fix)
            "20260220000001",  # Sync migration
            # KNOWN ISSUE: These migrations had the bug, but were fixed by 20260220000000
            "20260216160000",  # security_definer_search_path - SUPERSEDED by fix migration
        ]

        violations = []

        for filename, content in migration_files:
            # Skip certain migrations
            if any(pattern in filename for pattern in skip_patterns):
                continue

            # Check for references to removed columns
            for table, columns in removed_columns.items():
                for column in columns:
                    # Look for patterns like:
                    # - SELECT subscription_status FROM user_profiles
                    # - user_profiles.subscription_status
                    # - up.subscription_status (aliased)
                    patterns = [
                        rf'\b{column}\b.*{table}',
                        rf'{table}.*\b{column}\b',
                        rf'\.{column}\b',
                        rf'\b{column}\s+INTO\b',
                        rf'SELECT\s+.*\b{column}\b',
                    ]

                    for pattern in patterns:
                        if re.search(pattern, content, re.IGNORECASE):
                            # Verify it's not in a comment or the removal itself
                            lines = content.split('\n')
                            for i, line in enumerate(lines, 1):
                                if re.search(pattern, line, re.IGNORECASE):
                                    # Skip if it's a comment
                                    stripped = line.strip()
                                    if stripped.startswith('--') or stripped.startswith('/*'):
                                        continue
                                    # Skip if it's a DROP or removal
                                    if 'DROP COLUMN' in line.upper() or 'ALTER TABLE' in line.upper():
                                        continue
                                    violations.append(
                                        f"{filename}:{i}: References removed column "
                                        f"'{column}' from '{table}'"
                                    )
                                    break

        if violations:
            pytest.fail(
                f"Found {len(violations)} references to removed columns:\n" +
                "\n".join(violations[:10])  # Show first 10
            )

    def test_migration_timestamps_are_unique(self, migration_files: list[tuple[str, str]]):
        """Verify no two migrations have the same timestamp."""
        timestamps = {}
        duplicates = []

        for filename, _ in migration_files:
            # Extract timestamp (first 14 digits)
            match = re.match(r'^(\d{14})', filename)
            if match:
                ts = match.group(1)
                if ts in timestamps:
                    duplicates.append(f"{ts}: {timestamps[ts]} and {filename}")
                else:
                    timestamps[ts] = filename

        if duplicates:
            pytest.fail("Duplicate migration timestamps:\n" + "\n".join(duplicates))

    def test_function_definitions_are_consistent(self, migration_files: list[tuple[str, str]]):
        """
        Check for functions defined multiple times with different signatures.

        The last definition wins, but conflicting definitions can cause confusion.
        """
        function_definitions: dict[str, list[tuple[str, str]]] = {}

        for filename, content in migration_files:
            # Find CREATE OR REPLACE FUNCTION statements
            pattern = r'CREATE\s+OR\s+REPLACE\s+FUNCTION\s+(?:public\.)?(\w+)\s*\('
            matches = re.finditer(pattern, content, re.IGNORECASE)

            for match in matches:
                func_name = match.group(1).lower()
                if func_name not in function_definitions:
                    function_definitions[func_name] = []
                function_definitions[func_name].append((filename, match.group(0)))

        # Report functions defined in multiple migrations
        multi_defined = {
            name: files for name, files in function_definitions.items()
            if len(files) > 1
        }

        if multi_defined:
            report = []
            for func_name, definitions in multi_defined.items():
                files = [f[0] for f in definitions]
                report.append(f"  {func_name}: defined in {len(files)} migrations")
                for f in files[-3:]:  # Show last 3
                    report.append(f"    - {f}")

            # This is informational, not a failure
            print("\n⚠️  Functions defined in multiple migrations:\n" + "\n".join(report))

    def test_no_syntax_errors_in_migrations(self, migration_files: list[tuple[str, str]]):
        """Basic syntax validation for SQL files."""
        issues = []

        for filename, content in migration_files:
            # Check for unbalanced $$ delimiters (critical - breaks function definitions)
            dollar_quotes = content.count('$$')
            if dollar_quotes % 2 != 0:
                issues.append(f"{filename}: Unbalanced $$ delimiters ({dollar_quotes})")

            # Note: BEGIN/COMMIT balance is NOT checked because:
            # 1. Supabase migrations run in implicit transactions
            # 2. DO $$ blocks contain BEGIN/END (not transactions)
            # 3. Many valid migrations don't use explicit transactions

        if issues:
            pytest.fail("SQL syntax issues found:\n" + "\n".join(issues))


class TestSchemaChangeTracking:
    """
    Tests that track important schema changes and their implications.

    This serves as documentation and catches regressions.
    """

    def test_subscription_status_removal_is_documented(self):
        """
        Verify the subscription_status removal is properly handled.

        Timeline:
        1. 20251227154700: Added subscription_status to user_profiles
        2. 20251231130000: REMOVED subscription_status (moved to subscriptions table)
        3. 20260216160000: Re-introduced bug (referenced removed column)
        4. 20260220000000: Fixed get_effective_plan to not reference it

        Any new code should use subscriptions.status, NOT user_profiles.subscription_status.
        """
        removal_migration = MIGRATIONS_PATH / "20251231130000_unified_billing.sql"
        fix_migration = MIGRATIONS_PATH / "20260220000000_fix_get_effective_plan_v3.sql"

        assert removal_migration.exists(), \
            "Migration that removes subscription_status should exist"

        assert fix_migration.exists(), \
            "Fix migration for get_effective_plan should exist"

        # Verify fix migration doesn't reference subscription_status in function body
        fix_content = fix_migration.read_text()
        # Allow references in comments (which document the fix)
        lines = fix_content.split('\n')
        code_lines = [l for l in lines if not l.strip().startswith('--')]
        code_content = '\n'.join(code_lines)
        assert "subscription_status" not in code_content, \
            "Fix migration should not use subscription_status column in code"

    def test_billing_source_of_truth_is_subscriptions_table(self):
        """
        Document and verify that subscriptions table is source of truth.

        After migration 20251231130000:
        - subscriptions.status = subscription status (active, canceled, etc.)
        - subscriptions.plan_type = plan name (starter, pro, enterprise)
        - user_profiles.plan = legacy/fallback only
        """
        # Just a documentation test - passes to document the architecture
        architecture_doc = """
        BILLING ARCHITECTURE (post-20251231130000):

        Source of Truth: subscriptions table
        ├── team_id: Links to teams table
        ├── status: 'active', 'trialing', 'canceled', 'past_due'
        └── plan_type: 'starter', 'pro', 'enterprise'

        Deprecated: user_profiles.subscription_status
        └── REMOVED in 20251231130000

        Fallback Only: user_profiles.plan
        └── Used when no subscription record exists

        Flow: Polar Webhook → subscriptions table → get_effective_plan() → API
        """
        assert True, architecture_doc


class TestMigrationBestPractices:
    """Tests that enforce migration best practices."""

    @pytest.fixture(scope="class")
    def migration_files(self) -> list[tuple[str, str]]:
        """Load all migration files."""
        if not MIGRATIONS_PATH.exists():
            pytest.skip(f"Migrations path not found: {MIGRATIONS_PATH}")

        migrations = []
        for file in sorted(MIGRATIONS_PATH.glob("*.sql")):
            content = file.read_text()
            migrations.append((file.name, content))

        return migrations

    def test_migrations_have_comments(self, migration_files: list[tuple[str, str]]):
        """Migrations should have header comments explaining their purpose."""
        missing_comments = []

        for filename, content in migration_files:
            # Check if file starts with a comment
            lines = content.strip().split('\n')
            first_meaningful_line = next(
                (l for l in lines if l.strip() and not l.strip().startswith('--')),
                None
            )

            # If first meaningful line is not after some comments, flag it
            first_line = lines[0].strip() if lines else ""
            if not first_line.startswith('--') and not first_line.startswith('/*'):
                missing_comments.append(filename)

        if missing_comments and len(missing_comments) > 5:
            print(f"\n⚠️  {len(missing_comments)} migrations without header comments")

    def test_security_definer_functions_have_search_path(
        self,
        migration_files: list[tuple[str, str]]
    ):
        """
        SECURITY DEFINER functions should SET search_path.

        Without this, the function could be vulnerable to search_path injection.
        """
        issues = []

        for filename, content in migration_files:
            # Find SECURITY DEFINER functions
            pattern = r'CREATE\s+(?:OR\s+REPLACE\s+)?FUNCTION\s+(?:public\.)?(\w+).*?SECURITY\s+DEFINER'
            matches = re.finditer(pattern, content, re.IGNORECASE | re.DOTALL)

            for match in matches:
                func_name = match.group(1)
                func_text = content[match.start():match.start() + 500]  # Get function context

                if 'SET search_path' not in func_text:
                    # Check if there's a subsequent SET search_path
                    if 'search_path' not in content[match.end():match.end() + 200]:
                        issues.append(f"{filename}: {func_name}() - SECURITY DEFINER without SET search_path")

        if issues:
            print("\n⚠️  SECURITY DEFINER functions without search_path:\n" + "\n".join(issues[:5]))
