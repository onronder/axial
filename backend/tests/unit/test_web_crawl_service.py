from types import SimpleNamespace
from unittest.mock import MagicMock, patch

import pytest

from services.web_crawl import queue_web_crawl


def _mock_supabase(insert_data, update_data=None):
    supabase = MagicMock()
    insert_exec = MagicMock()
    insert_exec.data = insert_data

    table_mock = MagicMock()
    table_mock.insert.return_value.execute.return_value = insert_exec
    table_mock.update.return_value.eq.return_value.execute.return_value = MagicMock(data=update_data or [])

    supabase.table.return_value = table_mock
    return supabase


def test_queue_web_crawl_success():
    supabase = _mock_supabase(insert_data=[{"id": "crawl-1"}])
    with patch("services.web_crawl.get_supabase", return_value=supabase):
        with patch("services.web_crawl.crawl_discovery_task.delay") as mock_delay:
            mock_delay.return_value = SimpleNamespace(id="task-1")
            result = queue_web_crawl(
                user_id="user-1",
                root_url="https://example.com",
                crawl_type="single",
                max_depth=1,
                respect_robots=True,
                max_pages=10,
                allow_subdomains=False,
            )

    assert result == {"crawl_id": "crawl-1", "task_id": "task-1"}


def test_queue_web_crawl_insert_failure():
    supabase = _mock_supabase(insert_data=[])
    with patch("services.web_crawl.get_supabase", return_value=supabase):
        with pytest.raises(RuntimeError):
            queue_web_crawl(
                user_id="user-1",
                root_url="https://example.com",
                crawl_type="single",
                max_depth=1,
                respect_robots=True,
                max_pages=10,
                allow_subdomains=False,
            )


def test_queue_web_crawl_task_failure_updates_status():
    supabase = _mock_supabase(insert_data=[{"id": "crawl-1"}])
    with patch("services.web_crawl.get_supabase", return_value=supabase):
        with patch("services.web_crawl.crawl_discovery_task.delay", side_effect=RuntimeError("boom")):
            with pytest.raises(RuntimeError):
                queue_web_crawl(
                    user_id="user-1",
                    root_url="https://example.com",
                    crawl_type="single",
                    max_depth=1,
                    respect_robots=True,
                    max_pages=10,
                    allow_subdomains=False,
                )

    supabase.table.return_value.update.assert_called()
