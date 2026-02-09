"""
Tests for core/quotas.py - Plan limits and utilities.

Note: Actual quota enforcement (check_admission) is tested in test_services_quotas.py
"""


from core import quotas


def test_format_bytes_under_1kb():
    assert quotas.format_bytes(1024) == "1024.0 B"


def test_format_bytes_kb():
    assert quotas.format_bytes(1025) == "1.0 KB"


def test_format_bytes_mb():
    assert quotas.format_bytes(1048576) == "1024.0 KB"
    assert quotas.format_bytes(1048577) == "1.0 MB"


def test_format_bytes_gb():
    assert quotas.format_bytes(1073741824) == "1024.0 MB"
    assert quotas.format_bytes(1073741825) == "1.0 GB"


def test_get_plan_limits_returns_starter():
    limits = quotas.get_plan_limits("starter")
    assert limits.plan_name == "starter"
    assert limits.max_files > 0


def test_get_plan_limits_returns_pro():
    limits = quotas.get_plan_limits("pro")
    assert limits.plan_name == "pro"
    assert limits.max_team_seats == 5


def test_get_plan_limits_returns_enterprise():
    limits = quotas.get_plan_limits("enterprise")
    assert limits.plan_name == "enterprise"
    assert limits.max_team_seats == 100


def test_get_plan_limits_returns_none():
    """Test 'none' plan for new users who haven't selected a plan."""
    limits = quotas.get_plan_limits("none")
    assert limits.plan_name == "none"
    assert limits.max_files == 0
    assert limits.max_storage_bytes == 0
    assert limits.max_scopes == 0


def test_get_plan_limits_returns_free():
    """Test 'free' plan for users after trial/cancellation."""
    limits = quotas.get_plan_limits("free")
    assert limits.plan_name == "free"
    assert limits.max_files == 0
    assert limits.max_storage_bytes == 0
    assert limits.max_scopes == 0


def test_get_plan_limits_defaults_to_free():
    limits = quotas.get_plan_limits("unknown-plan")
    assert limits.plan_name == "free"
    assert limits.max_files == 0


def test_plan_limits_storage_mb_property():
    limits = quotas.get_plan_limits("starter")
    # max_storage_mb is derived from max_storage_bytes
    assert limits.max_storage_mb == limits.max_storage_bytes / (1024 * 1024)


def test_quota_limits_contains_all_plans():
    """All valid plan types should be in QUOTA_LIMITS."""
    # 'none' = new users, 'free' = post-trial/canceled, rest = paid plans
    expected_plans = {"none", "free", "starter", "pro", "enterprise"}
    actual_plans = set(quotas.QUOTA_LIMITS.keys())
    assert actual_plans == expected_plans
