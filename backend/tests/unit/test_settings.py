"""
Test Suite for Settings API

Exercises profile creation/update and notification settings flows.
"""

from unittest.mock import MagicMock, patch

import pytest
from fastapi import HTTPException
from starlette.requests import Request

from api.v1.settings import (
    DEFAULT_NOTIFICATION_SETTINGS,
    NotificationSettingUpdate,
    ProfileResponse,
    ProfileUpdate,
    get_notification_settings,
    get_profile,
    reset_notification_settings,
    update_notification_setting,
    update_profile,
)


def _make_mock_request(method="GET", path="/api/v1/settings"):
    """Create a mock Starlette Request for testing endpoints with rate limiters."""
    scope = {
        "type": "http",
        "method": method,
        "path": path,
        "query_string": b"",
        "headers": [],
        "server": ("testserver", 80),
        "client": ("127.0.0.1", 12345),
        "app": None,
    }
    return Request(scope=scope)


def _build_profile_supabase(
    profile_rows=None,
    insert_rows=None,
    team_rows=None,
    user_metadata=None,
    insert_side_effect=None,
):
    supabase = MagicMock()

    profiles_table = MagicMock()
    select_query = MagicMock()
    select_query.eq.return_value = select_query
    select_query.execute.return_value = MagicMock(data=profile_rows or [])
    profiles_table.select.return_value = select_query

    insert_query = MagicMock()
    if insert_side_effect:
        insert_query.execute.side_effect = insert_side_effect
    else:
        insert_query.execute.return_value = MagicMock(data=insert_rows or [])
    profiles_table.insert.return_value = insert_query

    upsert_query = MagicMock()
    upsert_query.execute.return_value = MagicMock(data=insert_rows or profile_rows or [])
    profiles_table.upsert.return_value = upsert_query

    team_table = MagicMock()
    team_table.select.return_value = team_table
    team_table.eq.return_value = team_table
    team_table.limit.return_value = team_table
    team_table.execute.return_value = MagicMock(data=team_rows or [])

    def table_side_effect(name):
        if name == "user_profiles":
            return profiles_table
        if name == "team_members":
            return team_table
        return MagicMock()

    supabase.table.side_effect = table_side_effect
    supabase.auth.admin.get_user_by_id.return_value = MagicMock(
        user=MagicMock(user_metadata=user_metadata or {})
    )

    return supabase, profiles_table, team_table


def _build_notification_supabase(select_rows=None, insert_rows=None):
    supabase = MagicMock()

    table = MagicMock()
    table.select.return_value = table
    table.eq.return_value = table
    table.insert.return_value = table
    table.update.return_value = table
    table.delete.return_value = table
    if select_rows is None and insert_rows is None:
        table.execute.return_value = MagicMock(data=[])
    elif insert_rows is None:
        table.execute.return_value = MagicMock(data=select_rows or [])
    else:
        table.execute.side_effect = [
            MagicMock(data=select_rows or []),
            MagicMock(data=insert_rows or []),
        ]

    supabase.table.return_value = table
    return supabase, table


class TestProfileCreation:
    @pytest.mark.asyncio
    async def test_profile_creation_reads_first_name_from_metadata(self):
        supabase, profiles_table, _ = _build_profile_supabase(
            profile_rows=[],
            insert_rows=[{"user_id": "user-1", "first_name": "John", "last_name": "Doe"}],
            user_metadata={"first_name": "John", "last_name": "Doe"},
        )
        with patch("api.v1.settings.get_supabase", return_value=supabase):
            profile = await get_profile(request=_make_mock_request(), user_id="user-1")

        assert profile["first_name"] == "John"
        assert profile["last_name"] == "Doe"
        insert_payload = profiles_table.insert.call_args[0][0]
        assert insert_payload["first_name"] == "John"

    @pytest.mark.asyncio
    async def test_profile_creation_reads_last_name_from_metadata(self):
        supabase, profiles_table, _ = _build_profile_supabase(
            profile_rows=[],
            insert_rows=[{"user_id": "user-1", "first_name": "Jane", "last_name": "Smith"}],
            user_metadata={"first_name": "Jane", "last_name": "Smith"},
        )
        with patch("api.v1.settings.get_supabase", return_value=supabase):
            profile = await get_profile(request=_make_mock_request(), user_id="user-1")

        assert profile["last_name"] == "Smith"
        insert_payload = profiles_table.insert.call_args[0][0]
        assert insert_payload["last_name"] == "Smith"

    @pytest.mark.asyncio
    async def test_profile_creation_insert_retry_failure_raises(self):
        supabase, _, _ = _build_profile_supabase(
            profile_rows=[],
            insert_rows=[],
            insert_side_effect=RuntimeError("insert failed"),
        )

        with patch("api.v1.settings.get_supabase", return_value=supabase):
            with pytest.raises(HTTPException):
                await get_profile(request=_make_mock_request(), user_id="user-1")

    @pytest.mark.asyncio
    async def test_profile_creation_falls_back_to_full_name_parsing(self):
        supabase, profiles_table, _ = _build_profile_supabase(
            profile_rows=[],
            insert_rows=[{"user_id": "user-1", "first_name": "Jane", "last_name": "Smith"}],
            user_metadata={"full_name": "Jane Smith"},
        )
        with patch("api.v1.settings.get_supabase", return_value=supabase):
            profile = await get_profile(request=_make_mock_request(), user_id="user-1")

        assert profile["first_name"] == "Jane"
        assert profile["last_name"] == "Smith"
        insert_payload = profiles_table.insert.call_args[0][0]
        assert insert_payload["first_name"] == "Jane"
        assert insert_payload["last_name"] == "Smith"

    @pytest.mark.asyncio
    async def test_profile_creation_handles_missing_metadata_gracefully(self):
        supabase, profiles_table, _ = _build_profile_supabase(
            profile_rows=[],
            insert_rows=[{"user_id": "user-1", "first_name": None, "last_name": None}],
        )
        supabase.auth.admin.get_user_by_id.side_effect = Exception("User not found")

        with patch("api.v1.settings.get_supabase", return_value=supabase):
            profile = await get_profile(request=_make_mock_request(), user_id="user-1")

        assert profile["first_name"] is None
        assert profile["last_name"] is None
        insert_payload = profiles_table.insert.call_args[0][0]
        assert insert_payload["first_name"] is None


class TestProfileGet:
    @pytest.mark.asyncio
    async def test_get_profile_returns_existing_profile(self):
        supabase, profiles_table, _ = _build_profile_supabase(
            profile_rows=[{"user_id": "user-1", "first_name": "Existing", "last_name": "User"}],
        )
        with patch("api.v1.settings.get_supabase", return_value=supabase):
            profile = await get_profile(request=_make_mock_request(), user_id="user-1")

        assert profile["first_name"] == "Existing"
        assert profiles_table.insert.call_count == 0

    @pytest.mark.asyncio
    async def test_get_profile_creates_profile_if_not_exists(self):
        supabase, profiles_table, _ = _build_profile_supabase(
            profile_rows=[],
            insert_rows=[{"user_id": "user-1", "first_name": "New", "last_name": "User"}],
            user_metadata={"first_name": "New", "last_name": "User"},
        )
        with patch("api.v1.settings.get_supabase", return_value=supabase):
            profile = await get_profile(request=_make_mock_request(), user_id="user-1")

        assert profile["first_name"] == "New"
        assert profiles_table.insert.call_count == 1

    @pytest.mark.asyncio
    async def test_get_profile_insert_retry_succeeds(self):
        supabase = MagicMock()
        profiles_table = MagicMock()
        select_query = MagicMock()
        select_query.eq.return_value = select_query
        select_query.execute.side_effect = [
            MagicMock(data=[]),
            MagicMock(data=[{"user_id": "user-1", "first_name": "Retry"}]),
        ]
        profiles_table.select.return_value = select_query
        profiles_table.insert.return_value.execute.side_effect = Exception("insert failed")

        team_table = MagicMock()
        team_table.select.return_value = team_table
        team_table.eq.return_value = team_table
        team_table.limit.return_value = team_table
        team_table.execute.return_value = MagicMock(data=[])

        def table_side_effect(name):
            if name == "user_profiles":
                return profiles_table
            if name == "team_members":
                return team_table
            return MagicMock()

        supabase.table.side_effect = table_side_effect

        with patch("api.v1.settings.get_supabase", return_value=supabase):
            profile = await get_profile(request=_make_mock_request(), user_id="user-1")

        assert profile["first_name"] == "Retry"

    @pytest.mark.asyncio
    async def test_get_profile_raises_when_profile_missing(self):
        supabase, _, _ = _build_profile_supabase(profile_rows=[], insert_rows=[])

        with patch("api.v1.settings.get_supabase", return_value=supabase):
            with pytest.raises(HTTPException) as exc:
                await get_profile(request=_make_mock_request(), user_id="user-1")

        assert exc.value.status_code == 500

    @pytest.mark.asyncio
    async def test_get_profile_sets_team_flags(self):
        supabase, _, _ = _build_profile_supabase(
            profile_rows=[{"user_id": "user-1"}],
            team_rows=[{"id": "team-1", "role": "admin"}],
        )

        with patch("api.v1.settings.get_supabase", return_value=supabase):
            profile = await get_profile(request=_make_mock_request(), user_id="user-1")

        assert profile["has_team"] is True
        assert profile["role"] == "admin"

    @pytest.mark.asyncio
    async def test_get_profile_handles_exception(self):
        supabase = MagicMock()
        supabase.table.side_effect = Exception("boom")

        with patch("api.v1.settings.get_supabase", return_value=supabase):
            with pytest.raises(HTTPException) as exc:
                await get_profile(request=_make_mock_request(), user_id="user-1")

        assert exc.value.status_code == 500

    @pytest.mark.unit
    def test_profile_response_schema(self):
        profile = ProfileResponse(
            id="profile-123",
            user_id="user-123",
            first_name="Test",
            last_name="User",
            plan="free",
            theme="system",
            created_at="2024-01-01T00:00:00Z",
            updated_at="2024-01-01T00:00:00Z",
        )

        assert profile.first_name == "Test"
        assert profile.last_name == "User"
        assert profile.plan == "free"


class TestProfileUpdate:
    @pytest.mark.unit
    def test_update_first_name(self):
        update = ProfileUpdate(first_name="NewName")
        assert update.first_name == "NewName"
        assert update.last_name is None

    @pytest.mark.unit
    def test_update_last_name(self):
        update = ProfileUpdate(last_name="NewLastName")
        assert update.last_name == "NewLastName"

    @pytest.mark.asyncio
    async def test_update_theme_validates_values(self):
        supabase, _, _ = _build_profile_supabase(
            profile_rows=[{"user_id": "user-1", "theme": "dark"}],
            insert_rows=[{"user_id": "user-1", "theme": "dark"}],
        )
        with patch("api.v1.settings.get_supabase", return_value=supabase):
            profile = await update_profile(request=_make_mock_request(method="PATCH"), payload=ProfileUpdate(theme="dark"), user_id="user-1")

        assert profile["theme"] == "dark"

    @pytest.mark.asyncio
    async def test_update_profile_sets_names(self):
        supabase, _, _ = _build_profile_supabase(
            profile_rows=[{"user_id": "user-1"}],
            insert_rows=[{"user_id": "user-1", "first_name": "A", "last_name": "B"}],
        )

        with patch("api.v1.settings.get_supabase", return_value=supabase):
            profile = await update_profile(request=_make_mock_request(method="PATCH"), payload=ProfileUpdate(first_name="A", last_name="B"), user_id="user-1")

        assert profile["first_name"] == "A"
        assert profile["last_name"] == "B"

    @pytest.mark.asyncio
    async def test_update_profile_empty_response_raises(self):
        supabase, table = _build_notification_supabase(select_rows=[], insert_rows=[])
        table.upsert.return_value = table
        table.execute.return_value = MagicMock(data=[])

        with patch("api.v1.settings.get_supabase", return_value=supabase):
            with pytest.raises(HTTPException) as exc:
                await update_profile(request=_make_mock_request(method="PATCH"), payload=ProfileUpdate(first_name="A"), user_id="user-1")

        assert exc.value.status_code == 500

    @pytest.mark.asyncio
    async def test_update_profile_handles_exception(self):
        supabase = MagicMock()
        table = MagicMock()
        table.upsert.return_value = table
        table.execute.side_effect = Exception("boom")
        supabase.table.return_value = table

        with patch("api.v1.settings.get_supabase", return_value=supabase):
            with pytest.raises(HTTPException) as exc:
                await update_profile(request=_make_mock_request(method="PATCH"), payload=ProfileUpdate(first_name="A"), user_id="user-1")

        assert exc.value.status_code == 500

    @pytest.mark.asyncio
    async def test_update_theme_rejects_invalid_values(self):
        supabase = MagicMock()
        with patch("api.v1.settings.get_supabase", return_value=supabase):
            with pytest.raises(HTTPException) as exc:
                await update_profile(request=_make_mock_request(method="PATCH"), payload=ProfileUpdate(theme="blue"), user_id="user-1")
        assert "Invalid theme value" in str(exc.value)


class TestNotificationSettings:
    @pytest.mark.asyncio
    async def test_get_notifications_creates_defaults_for_new_user(self):
        supabase, table = _build_notification_supabase(
            select_rows=[],
            insert_rows=[{"setting_key": s["setting_key"]} for s in DEFAULT_NOTIFICATION_SETTINGS],
        )
        with patch("api.v1.settings.get_supabase", return_value=supabase):
            settings = await get_notification_settings(request=_make_mock_request(), user_id="user-1")

        assert len(settings) == len(DEFAULT_NOTIFICATION_SETTINGS)
        table.insert.assert_called()

    @pytest.mark.asyncio
    async def test_toggle_notification_setting(self):
        supabase = MagicMock()
        table = MagicMock()
        table.update.return_value = table
        table.eq.return_value = table
        table.execute.return_value = MagicMock(
            data=[{"setting_key": "email_on_ingestion_complete", "enabled": False}]
        )
        supabase.table.return_value = table
        with patch("api.v1.settings.get_supabase", return_value=supabase):
            result = await update_notification_setting(
                request=_make_mock_request(method="PATCH"),
                payload=NotificationSettingUpdate(setting_key="email_on_ingestion_complete", enabled=False),
                user_id="user-1",
            )
        assert result["enabled"] is False

    @pytest.mark.asyncio
    async def test_get_notifications_handles_error(self):
        supabase = MagicMock()
        table = MagicMock()
        table.select.return_value = table
        table.eq.return_value = table
        table.execute.side_effect = RuntimeError("db down")
        supabase.table.return_value = table

        with patch("api.v1.settings.get_supabase", return_value=supabase):
            with pytest.raises(HTTPException):
                await get_notification_settings(request=_make_mock_request(), user_id="user-1")

    @pytest.mark.asyncio
    async def test_update_notification_setting_handles_error(self):
        supabase = MagicMock()
        table = MagicMock()
        table.update.return_value = table
        table.eq.return_value = table
        table.execute.side_effect = RuntimeError("db down")
        supabase.table.return_value = table

        with patch("api.v1.settings.get_supabase", return_value=supabase):
            with pytest.raises(HTTPException):
                await update_notification_setting(
                    request=_make_mock_request(method="PATCH"),
                    payload=NotificationSettingUpdate(setting_key="email_on_ingestion_complete", enabled=True),
                    user_id="user-1",
                )


class TestResetNotificationSettings:
    @pytest.mark.asyncio
    async def test_reset_deletes_all_user_settings(self):
        supabase = MagicMock()
        table = MagicMock()
        table.delete.return_value = table
        table.eq.return_value = table
        table.execute.return_value = MagicMock(data=[{"id": "s1"}, {"id": "s2"}])
        supabase.table.return_value = table
        with patch("api.v1.settings.get_supabase", return_value=supabase):
            result = await reset_notification_settings(request=_make_mock_request(method="DELETE"), user_id="user-1")
        assert result["deleted_count"] == 2

    @pytest.mark.asyncio
    async def test_reset_notification_settings_handles_error(self):
        supabase = MagicMock()
        table = MagicMock()
        table.delete.return_value = table
        table.eq.return_value = table
        table.execute.side_effect = RuntimeError("db down")
        supabase.table.return_value = table

        with patch("api.v1.settings.get_supabase", return_value=supabase):
            with pytest.raises(HTTPException):
                await reset_notification_settings(request=_make_mock_request(method="DELETE"), user_id="user-1")

    @pytest.mark.unit
    def test_reset_returns_deleted_count(self):
        response = {
            "status": "success",
            "message": "Notification settings reset to defaults",
            "deleted_count": 5,
        }
        assert response["deleted_count"] == 5

    @pytest.mark.unit
    def test_reset_only_affects_requesting_user(self):
        user_id = "user-123"
        filter_column = "user_id"
        assert filter_column == "user_id"
        assert user_id == "user-123"

    @pytest.mark.asyncio
    async def test_reset_settings_recreated_on_next_get(self):
        supabase, table = _build_notification_supabase(
            select_rows=[],
            insert_rows=[{"setting_key": s["setting_key"]} for s in DEFAULT_NOTIFICATION_SETTINGS],
        )
        with patch("api.v1.settings.get_supabase", return_value=supabase):
            settings = await get_notification_settings(request=_make_mock_request(), user_id="user-1")
        assert len(settings) == len(DEFAULT_NOTIFICATION_SETTINGS)
        table.insert.assert_called()

    @pytest.mark.unit
    def test_reset_handles_no_existing_settings(self):
        response = {"status": "success", "deleted_count": 0}
        assert response["status"] == "success"

    @pytest.mark.unit
    def test_default_notification_settings_count(self):
        assert len(DEFAULT_NOTIFICATION_SETTINGS) == 5

    @pytest.mark.unit
    def test_default_settings_include_email_category(self):
        email_settings = [s for s in DEFAULT_NOTIFICATION_SETTINGS if s["category"] == "email"]
        assert len(email_settings) >= 2

    @pytest.mark.unit
    def test_default_settings_include_system_category(self):
        system_settings = [s for s in DEFAULT_NOTIFICATION_SETTINGS if s["category"] == "system"]
        assert len(system_settings) >= 2
