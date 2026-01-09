from fastapi import BackgroundTasks
from starlette.requests import Request
from unittest.mock import MagicMock, patch

import pytest

from services.audit import AuditLogger, log_chat_delete, log_connector_sync, log_document_delete, log_settings_update


def _make_request(headers=None, client_host="127.0.0.1"):
    headers = headers or {}
    scope = {
        "type": "http",
        "headers": [(k.lower().encode(), v.encode()) for k, v in headers.items()],
        "client": (client_host, 12345),
    }
    return Request(scope)


class TestAuditLogger:
    def test_log_adds_background_task_with_forwarded_ip(self):
        logger = AuditLogger()
        background_tasks = BackgroundTasks()
        request = _make_request(
            {"x-forwarded-for": "10.1.1.1, 10.1.1.2", "user-agent": "TestAgent"}
        )

        logger.log(
            background_tasks,
            user_id="user-1",
            action="document.delete",
            resource_type="document",
            resource_id="doc-1",
            details={"title": "Doc"},
            request=request,
        )

        assert len(background_tasks.tasks) == 1
        task = background_tasks.tasks[0]
        assert task.kwargs["ip_address"] == "10.1.1.1"
        assert task.kwargs["user_agent"] == "TestAgent"

    def test_log_respects_disabled_flag(self):
        logger = AuditLogger()
        logger._enabled = False
        background_tasks = BackgroundTasks()

        logger.log(background_tasks, user_id="user-1", action="noop")

        assert background_tasks.tasks == []

    @pytest.mark.asyncio
    async def test_write_log_inserts_record(self):
        logger = AuditLogger()
        supabase = MagicMock()

        with patch("core.db.get_supabase", return_value=supabase):
            await logger._write_log(
                user_id="user-1",
                action="chat.delete",
                resource_type="chat",
                resource_id="chat-1",
                details={"title": "Chat"},
                ip_address="127.0.0.1",
                user_agent="UA",
            )

        supabase.table.assert_called_with("audit_logs")

    @pytest.mark.asyncio
    async def test_write_log_handles_exception(self):
        logger = AuditLogger()

        with patch("core.db.get_supabase", side_effect=Exception("boom")):
            await logger._write_log(
                user_id="user-1",
                action="chat.delete",
                resource_type="chat",
                resource_id="chat-1",
                details={"title": "Chat"},
                ip_address="127.0.0.1",
                user_agent="UA",
            )

    def test_log_sync_inserts_record(self):
        logger = AuditLogger()
        supabase = MagicMock()

        with patch("core.db.get_supabase", return_value=supabase):
            logger.log_sync(
                user_id="user-1",
                action="settings.update",
                resource_type="settings",
                resource_id="theme",
                details={"old": "dark", "new": "light"},
                ip_address="127.0.0.1",
                user_agent="UA",
            )

        supabase.table.assert_called_with("audit_logs")

    def test_log_sync_respects_disabled_flag(self):
        logger = AuditLogger()
        logger._enabled = False
        supabase = MagicMock()

        with patch("core.db.get_supabase", return_value=supabase):
            logger.log_sync(user_id="user-1", action="noop")

        supabase.table.assert_not_called()

    def test_log_sync_handles_exception(self):
        logger = AuditLogger()
        supabase = MagicMock()
        supabase.table.return_value.insert.return_value.execute.side_effect = Exception("boom")

        with patch("core.db.get_supabase", return_value=supabase):
            logger.log_sync(user_id="user-1", action="noop")


class TestAuditConvenienceFunctions:
    def test_log_document_delete_queues_task(self):
        background_tasks = BackgroundTasks()
        request = _make_request({"user-agent": "UA"})

        log_document_delete(background_tasks, "user-1", "doc-1", "Title", request)

        assert len(background_tasks.tasks) == 1

    def test_log_chat_delete_queues_task(self):
        background_tasks = BackgroundTasks()
        request = _make_request({"user-agent": "UA"})

        log_chat_delete(background_tasks, "user-1", "chat-1", "Chat", request)

        assert len(background_tasks.tasks) == 1

    def test_log_connector_sync_uses_sync_logger(self):
        with patch("services.audit.audit_logger.log_sync") as log_sync:
            log_connector_sync("user-1", "google_drive", "start", {"foo": "bar"})

        log_sync.assert_called_once()

    def test_log_settings_update_queues_task(self):
        background_tasks = BackgroundTasks()
        request = _make_request({"user-agent": "UA"})

        log_settings_update(background_tasks, "user-1", "theme", "dark", "light", request)

        assert len(background_tasks.tasks) == 1
