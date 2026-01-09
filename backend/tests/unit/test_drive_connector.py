import asyncio
import base64
from types import SimpleNamespace
from unittest.mock import MagicMock, patch

import pytest

from connectors.drive import DriveConnector
from services.oauth_token_manager import TokenRefreshError
from core.config import settings


def test_authorize_implementation_true():
    supabase = MagicMock()
    supabase.table.return_value.select.return_value.eq.return_value.single.return_value.execute.return_value = MagicMock(
        data={"id": "def-1"}
    )
    supabase.table.return_value.select.return_value.eq.return_value.eq.return_value.execute.return_value = MagicMock(
        data=[{"id": "int-1"}]
    )

    with patch("connectors.drive.get_supabase", return_value=supabase):
        connector = DriveConnector()
        assert connector._authorize_implementation("user-1") is True


def test_get_credentials_by_integration_refresh_error():
    connector = DriveConnector()
    with patch("services.oauth_token_manager.OAuthTokenManager.get_valid_credentials", side_effect=TokenRefreshError("fail")):
        with pytest.raises(ValueError):
            connector._get_credentials_by_integration({"id": "int-1"})


def test_get_credentials_missing_definition():
    supabase = MagicMock()
    supabase.table.return_value.select.return_value.eq.return_value.single.return_value.execute.return_value = MagicMock(
        data=None
    )

    with patch("connectors.drive.get_supabase", return_value=supabase):
        connector = DriveConnector()
        with pytest.raises(ValueError):
            connector._get_credentials("user-1")


def test_list_items_implementation_returns_items():
    connector = DriveConnector()
    files = [
        {"id": "folder-1", "name": "Folder", "mimeType": "application/vnd.google-apps.folder"},
        {"id": "file-1", "name": "Doc", "mimeType": "text/plain"},
    ]

    with patch.object(connector, "_get_credentials", return_value=MagicMock()), \
         patch("connectors.drive.build", return_value=MagicMock()), \
         patch.object(connector, "_drive_list", return_value={"files": files}):
        items = connector._list_items_implementation("user-1", parent_id=None)

    assert len(items) == 2
    assert items[0].type == "folder"


def test_drive_list_calls_execute():
    connector = DriveConnector()
    service = MagicMock()
    service.files.return_value.list.return_value.execute.return_value = {"files": []}
    result = connector._drive_list(service, q="test")
    assert result["files"] == []


def test_authorize_async_wrapper():
    connector = DriveConnector()

    async def run():
        with patch("connectors.drive.run_in_threadpool", side_effect=lambda fn, *args: fn(*args)), \
             patch.object(connector, "_authorize_implementation", return_value=True):
            return await connector.authorize("user-1")

    assert asyncio.run(run()) is True


def test_list_items_async_wrapper():
    connector = DriveConnector()

    async def run():
        with patch("connectors.drive.run_in_threadpool", side_effect=lambda fn, *args: fn(*args)), \
             patch.object(connector, "_list_items_implementation", return_value=[]):
            return await connector.list_items("user-1", parent_id=None)

    assert asyncio.run(run()) == []


def test_ingest_async_wrapper():
    connector = DriveConnector()

    async def run():
        with patch("starlette.concurrency.iterate_in_threadpool", return_value=iter([])):
            return await connector.ingest({"item_ids": []})

    assert list(asyncio.run(run())) == []


def test_sync_async_wrapper():
    connector = DriveConnector()

    async def run():
        with patch("connectors.drive.run_in_threadpool", side_effect=lambda fn, *args: fn(*args)), \
             patch.object(connector, "_sync_implementation", return_value={"status": "ok"}):
            return await connector.sync("user-1", "int-1")

    assert asyncio.run(run()) == {"status": "ok"}


def test_sync_handles_file_processing_error():
    connector = DriveConnector()
    supabase = MagicMock()
    supabase.table.return_value.select.return_value.eq.return_value.single.return_value.execute.return_value = MagicMock(
        data={"id": "int-1"}
    )
    supabase.table.return_value.insert.return_value.execute.return_value = MagicMock(data=[{"id": "job-1"}])

    with patch("connectors.drive.get_supabase", return_value=supabase), \
         patch.object(connector, "_get_credentials_by_integration", return_value=MagicMock()), \
         patch("connectors.drive.build", return_value=MagicMock()), \
         patch.object(connector, "_drive_list", return_value={"files": [{"id": "file-1", "name": "Doc", "mimeType": "text/plain"}]}), \
         patch.object(connector, "_download_file_content", side_effect=Exception("boom")), \
         patch("worker.tasks.create_file_status", return_value="file-status"), \
         patch("worker.tasks.update_file_status") as update_status:
        connector._sync_implementation("user-1", "int-1")

    update_status.assert_called()


def test_get_all_files_recursive_yields_files():
    connector = DriveConnector()

    first = {"files": [{"id": "folder-1", "mimeType": "application/vnd.google-apps.folder"}], "nextPageToken": None}
    second = {"files": [{"id": "file-1", "mimeType": "text/plain"}], "nextPageToken": None}

    with patch.object(connector, "_drive_list", side_effect=[first, second]):
        files = list(connector._get_all_files_recursive(MagicMock(), "root"))

    assert len(files) == 1
    assert files[0]["id"] == "file-1"


def test_download_file_content_skips_folder():
    connector = DriveConnector()
    content, mime_type, filename = connector._download_file_content(
        MagicMock(), {"id": "folder-1", "mimeType": "application/vnd.google-apps.folder", "name": "Folder"}
    )
    assert content is None
    assert mime_type is None


def test_download_file_content_exports_google_doc():
    connector = DriveConnector()

    class FakeDownloader:
        def __init__(self, fh, request):
            self._fh = fh
            self._done = False

        def next_chunk(self):
            if not self._done:
                self._fh.write(b"hello")
                self._done = True
                return SimpleNamespace(progress=lambda: 1.0), True
            return None, True

    service = MagicMock()
    service.files.return_value.export_media.return_value = MagicMock()

    with patch("googleapiclient.http.MediaIoBaseDownload", FakeDownloader):
        content, mime_type, filename = connector._download_file_content(
            service,
            {
                "id": "file-1",
                "mimeType": "application/vnd.google-apps.document",
                "name": "Doc",
            },
        )

    assert content == b"hello"
    assert mime_type == "text/plain"
    assert filename.endswith(".txt")


def test_download_file_content_binary_download():
    connector = DriveConnector()

    class FakeDownloader:
        def __init__(self, fh, request):
            self._fh = fh
            self._done = False

        def next_chunk(self):
            if not self._done:
                self._fh.write(b"pdf-data")
                self._done = True
                return SimpleNamespace(progress=lambda: 1.0), True
            return None, True

    service = MagicMock()
    service.files.return_value.get_media.return_value = MagicMock()

    with patch("googleapiclient.http.MediaIoBaseDownload", FakeDownloader):
        content, mime_type, filename = connector._download_file_content(
            service,
            {
                "id": "file-1",
                "mimeType": "application/pdf",
                "name": "Doc.pdf",
            },
        )

    assert content == b"pdf-data"
    assert mime_type == "application/pdf"
    assert filename == "Doc.pdf"


def test_download_file_content_export_failure_returns_none():
    connector = DriveConnector()

    class FailingDownloader:
        def __init__(self, *_args, **_kwargs):
            pass

        def next_chunk(self):
            raise Exception("boom")

    service = MagicMock()
    service.files.return_value.export_media.return_value = MagicMock()

    with patch("googleapiclient.http.MediaIoBaseDownload", FailingDownloader):
        content, mime_type, filename = connector._download_file_content(
            service,
            {
                "id": "file-1",
                "mimeType": "application/vnd.google-apps.document",
                "name": "Doc",
            },
        )

    assert content is None
    assert mime_type is None
    assert filename is None


def test_download_file_content_binary_failure_returns_none():
    connector = DriveConnector()

    class FailingDownloader:
        def __init__(self, *_args, **_kwargs):
            pass

        def next_chunk(self):
            raise Exception("boom")

    service = MagicMock()
    service.files.return_value.get_media.return_value = MagicMock()

    with patch("googleapiclient.http.MediaIoBaseDownload", FailingDownloader):
        content, mime_type, filename = connector._download_file_content(
            service,
            {
                "id": "file-1",
                "mimeType": "application/pdf",
                "name": "Doc.pdf",
            },
        )

    assert content is None


def test_get_all_files_recursive_handles_error():
    connector = DriveConnector()
    with patch.object(connector, "_drive_list", side_effect=Exception("fail")):
        files = list(connector._get_all_files_recursive(MagicMock(), "root"))
    assert files == []


def test_authorize_returns_false_when_definition_missing():
    supabase = MagicMock()
    supabase.table.return_value.select.return_value.eq.return_value.single.return_value.execute.return_value = MagicMock(
        data=None
    )

    with patch("connectors.drive.get_supabase", return_value=supabase):
        connector = DriveConnector()
        assert connector._authorize_implementation("user-1") is False


def test_get_credentials_missing_integration():
    supabase = MagicMock()
    supabase.table.return_value.select.return_value.eq.return_value.single.return_value.execute.return_value = MagicMock(
        data={"id": "def-1"}
    )
    supabase.table.return_value.select.return_value.eq.return_value.eq.return_value.execute.return_value = MagicMock(
        data=[]
    )

    with patch("connectors.drive.get_supabase", return_value=supabase):
        connector = DriveConnector()
        with pytest.raises(ValueError):
            connector._get_credentials("user-1")


def test_ingest_logic_integration_missing():
    connector = DriveConnector()
    supabase = MagicMock()
    supabase.table.return_value.select.return_value.eq.return_value.single.return_value.execute.return_value = MagicMock(
        data=None
    )

    with patch("connectors.drive.get_supabase", return_value=supabase):
        with pytest.raises(ValueError):
            list(
                connector._ingest_logic(
                    {
                        "item_ids": ["file-1"],
                        "credentials": {"integration_id": "int-1"},
                    }
                )
            )


def test_ingest_logic_handles_decode_error():
    connector = DriveConnector()
    file_meta = {"id": "file-1", "name": "Doc", "mimeType": "text/plain"}

    with patch("connectors.drive.build", return_value=MagicMock()), \
         patch.object(connector, "_drive_get", return_value=file_meta), \
         patch.object(connector, "_download_file_content", return_value=(b"\xff\xfe", "text/plain", "Doc")), \
         patch("connectors.drive.settings.GOOGLE_CLIENT_ID", "id"), \
         patch("connectors.drive.settings.GOOGLE_CLIENT_SECRET", "secret"):
        docs = list(
            connector._ingest_logic(
                {
                    "item_ids": ["file-1"],
                    "credentials": {"access_token": "token", "refresh_token": "refresh"},
                }
            )
        )

    assert docs


def test_sync_implementation_handles_large_file(monkeypatch):
    connector = DriveConnector()
    supabase = MagicMock()

    def make_table(responses):
        table = MagicMock()
        table.select.return_value = table
        table.insert.return_value = table
        table.update.return_value = table
        table.eq.return_value = table
        table.limit.return_value = table
        table.single.return_value = table
        responses_iter = iter(responses)

        def _execute():
            return SimpleNamespace(data=next(responses_iter, responses[-1] if responses else []))

        table.execute.side_effect = _execute
        return table

    tables = {
        "user_integrations": make_table([
            {"id": "int-1", "access_token": "enc", "refresh_token": "enc"},
            [],
        ]),
        "ingestion_jobs": make_table([
            [{"id": "job-1"}],
            [],
        ]),
    }

    supabase.table.side_effect = lambda name: tables.get(name, make_table([[]]))

    monkeypatch.setattr("connectors.drive.get_supabase", lambda: supabase)
    monkeypatch.setattr("connectors.drive.build", lambda *args, **kwargs: MagicMock())
    monkeypatch.setattr(connector, "_get_credentials_by_integration", lambda integration: MagicMock())
    monkeypatch.setattr(connector, "_drive_list", lambda *args, **kwargs: {
        "files": [
            {"id": "file-1", "name": "Doc", "mimeType": "text/plain", "webViewLink": "link", "size": 10}
        ]
    })
    monkeypatch.setattr(connector, "_download_file_content", lambda *args, **kwargs: (b"x" * 5, "text/plain", "Doc"))
    monkeypatch.setattr("worker.tasks.create_file_status", lambda *args, **kwargs: "status-1")
    monkeypatch.setattr("worker.tasks.update_file_status", lambda *args, **kwargs: None)
    monkeypatch.setattr(settings, "MAX_FILE_SIZE", 1)

    result = connector._sync_implementation("user-1", "int-1")
    assert result["status"] == "success"


def test_sync_integration_not_found(monkeypatch):
    connector = DriveConnector()
    supabase = MagicMock()

    table = MagicMock()
    table.select.return_value = table
    table.eq.return_value = table
    table.single.return_value = table
    table.execute.return_value = SimpleNamespace(data=None)
    supabase.table.return_value = table

    monkeypatch.setattr("connectors.drive.get_supabase", lambda: supabase)

    with pytest.raises(ValueError):
        connector._sync_implementation("user-1", "int-1")


def test_sync_skips_when_no_content(monkeypatch):
    connector = DriveConnector()
    supabase = MagicMock()

    def make_table(responses):
        table = MagicMock()
        table.select.return_value = table
        table.insert.return_value = table
        table.update.return_value = table
        table.eq.return_value = table
        table.limit.return_value = table
        table.single.return_value = table
        responses_iter = iter(responses)

        def _execute():
            return SimpleNamespace(data=next(responses_iter, responses[-1] if responses else []))

        table.execute.side_effect = _execute
        return table

    tables = {
        "user_integrations": make_table([
            {"id": "int-1", "access_token": "enc", "refresh_token": "enc"},
            [],
        ]),
        "ingestion_jobs": make_table([
            [{"id": "job-1"}],
            [],
        ]),
    }

    def table_side_effect(name):
        return tables.get(name, make_table([[]]))

    supabase.table.side_effect = table_side_effect

    monkeypatch.setattr("connectors.drive.get_supabase", lambda: supabase)
    monkeypatch.setattr("connectors.drive.build", lambda *args, **kwargs: MagicMock())
    monkeypatch.setattr(connector, "_get_credentials_by_integration", lambda integration: MagicMock())
    monkeypatch.setattr(connector, "_drive_list", lambda *args, **kwargs: {
        "files": [
            {"id": "file-1", "name": "Doc", "mimeType": "text/plain", "webViewLink": "link", "size": 10}
        ]
    })
    monkeypatch.setattr(connector, "_download_file_content", lambda *args, **kwargs: (None, None, None))
    monkeypatch.setattr("worker.tasks.create_file_status", lambda *args, **kwargs: "status-1")
    monkeypatch.setattr("worker.tasks.update_file_status", lambda *args, **kwargs: None)

    result = connector._sync_implementation("user-1", "int-1")
    assert result["status"] == "success"


def test_sync_decode_error_no_chunks(monkeypatch):
    connector = DriveConnector()
    supabase = MagicMock()

    def make_table(responses):
        table = MagicMock()
        table.select.return_value = table
        table.insert.return_value = table
        table.update.return_value = table
        table.eq.return_value = table
        table.limit.return_value = table
        table.single.return_value = table
        responses_iter = iter(responses)

        def _execute():
            return SimpleNamespace(data=next(responses_iter, responses[-1] if responses else []))

        table.execute.side_effect = _execute
        return table

    tables = {
        "user_integrations": make_table([
            {"id": "int-1", "access_token": "enc", "refresh_token": "enc"},
            [],
        ]),
        "ingestion_jobs": make_table([
            [{"id": "job-1"}],
            [],
        ]),
    }

    supabase.table.side_effect = lambda name: tables.get(name, make_table([[]]))

    monkeypatch.setattr("connectors.drive.get_supabase", lambda: supabase)
    monkeypatch.setattr("connectors.drive.build", lambda *args, **kwargs: MagicMock())
    monkeypatch.setattr(connector, "_get_credentials_by_integration", lambda integration: MagicMock())
    monkeypatch.setattr(connector, "_drive_list", lambda *args, **kwargs: {
        "files": [
            {"id": "file-1", "name": "Doc", "mimeType": "text/plain", "webViewLink": "link", "size": 10}
        ]
    })
    monkeypatch.setattr(connector, "_download_file_content", lambda *args, **kwargs: (b"\xff", "text/plain", "Doc"))
    monkeypatch.setattr(connector.text_splitter, "split_text", lambda *_args, **_kwargs: [])
    monkeypatch.setattr("worker.tasks.create_file_status", lambda *args, **kwargs: "status-1")
    monkeypatch.setattr("worker.tasks.update_file_status", lambda *args, **kwargs: None)

    result = connector._sync_implementation("user-1", "int-1")
    assert result["status"] == "success"


def test_ingest_logic_yields_document():
    connector = DriveConnector()
    file_meta = {"id": "file-1", "name": "Doc", "mimeType": "text/plain"}

    with patch("connectors.drive.build", return_value=MagicMock()), \
         patch.object(connector, "_drive_get", return_value=file_meta), \
         patch.object(connector, "_download_file_content", return_value=(b"hello", "text/plain", "Doc")), \
         patch("connectors.drive.settings.GOOGLE_CLIENT_ID", "id"), \
         patch("connectors.drive.settings.GOOGLE_CLIENT_SECRET", "secret"):
        docs = list(
            connector._ingest_logic(
                {
                    "item_ids": ["file-1"],
                    "credentials": {"access_token": "token", "refresh_token": "refresh"},
                }
            )
        )

    assert len(docs) == 1
    assert docs[0].page_content == "hello"


def test_ingest_logic_handles_folder_and_binary():
    connector = DriveConnector()
    folder_meta = {"id": "folder-1", "name": "Folder", "mimeType": "application/vnd.google-apps.folder"}
    file_meta = {"id": "file-1", "name": "Doc", "mimeType": "application/pdf", "webViewLink": "link"}

    with patch("connectors.drive.build", return_value=MagicMock()), \
         patch.object(connector, "_drive_get", return_value=folder_meta), \
         patch.object(connector, "_get_all_files_recursive", return_value=[file_meta]), \
         patch.object(connector, "_download_file_content", return_value=(b"data", "application/pdf", "Doc.pdf")), \
         patch("connectors.drive.settings.GOOGLE_CLIENT_ID", "id"), \
         patch("connectors.drive.settings.GOOGLE_CLIENT_SECRET", "secret"):
        docs = list(
            connector._ingest_logic(
                {
                    "item_ids": ["folder-1"],
                    "credentials": {"access_token": "token", "refresh_token": "refresh"},
                }
            )
        )

    assert len(docs) == 1
    assert docs[0].page_content == base64.b64encode(b"data").decode("ascii")


def test_ingest_logic_requires_credentials_or_user():
    connector = DriveConnector()

    with pytest.raises(ValueError):
        list(connector._ingest_logic({"item_ids": ["file-1"]}))


def test_ingest_logic_uses_integration_id_credentials():
    connector = DriveConnector()
    supabase = MagicMock()
    supabase.table.return_value.select.return_value.eq.return_value.single.return_value.execute.return_value = MagicMock(
        data={"id": "int-1"}
    )

    fake_creds = MagicMock()

    with patch("connectors.drive.get_supabase", return_value=supabase), \
         patch("services.oauth_token_manager.OAuthTokenManager.get_valid_credentials", return_value={
             "access_token": "access",
             "refresh_token": "refresh",
         }), \
         patch("connectors.drive.Credentials", return_value=fake_creds), \
         patch("connectors.drive.build", return_value=MagicMock()), \
         patch.object(connector, "_drive_get", return_value={"id": "file-1", "name": "Doc", "mimeType": "text/plain"}), \
         patch.object(connector, "_download_file_content", return_value=(b"hello", "text/plain", "Doc")), \
         patch("connectors.drive.settings.GOOGLE_CLIENT_ID", "id"), \
         patch("connectors.drive.settings.GOOGLE_CLIENT_SECRET", "secret"):
        docs = list(
            connector._ingest_logic(
                {
                    "item_ids": ["file-1"],
                    "credentials": {"integration_id": "int-1"},
                }
            )
        )

    assert docs


def test_get_credentials_by_integration_success():
    connector = DriveConnector()
    fake_creds = MagicMock()

    with patch("services.oauth_token_manager.OAuthTokenManager.get_valid_credentials", return_value={
        "access_token": "access",
        "refresh_token": "refresh",
    }), \
         patch("connectors.drive.Credentials", return_value=fake_creds), \
         patch("connectors.drive.settings.GOOGLE_CLIENT_ID", "id"), \
         patch("connectors.drive.settings.GOOGLE_CLIENT_SECRET", "secret"):
        creds = connector._get_credentials_by_integration({"id": "int-1"})

    assert creds is fake_creds


def test_sync_implementation_processes_single_file(monkeypatch):
    connector = DriveConnector()
    supabase = MagicMock()

    def make_table(responses):
        table = MagicMock()
        table.select.return_value = table
        table.insert.return_value = table
        table.update.return_value = table
        table.eq.return_value = table
        table.limit.return_value = table
        table.single.return_value = table
        responses_iter = iter(responses)

        def _execute():
            return SimpleNamespace(data=next(responses_iter, responses[-1] if responses else []))

        table.execute.side_effect = _execute
        return table

    tables = {
        "user_integrations": make_table([
            {"id": "int-1", "access_token": "enc", "refresh_token": "enc"},
            [{"id": "int-1"}],
        ]),
        "ingestion_jobs": make_table([
            [{"id": "job-1"}],
            [{"id": "job-1"}],
            [{"id": "job-1"}],
        ]),
        "documents": make_table([
            [],
            [{"id": "doc-1"}],
        ]),
    }

    supabase.table.side_effect = lambda name: tables[name]

    monkeypatch.setattr("connectors.drive.get_supabase", lambda: supabase)
    monkeypatch.setattr("connectors.drive.build", lambda *args, **kwargs: MagicMock())
    monkeypatch.setattr(connector, "_get_credentials_by_integration", lambda integration: MagicMock())
    monkeypatch.setattr(connector, "_drive_list", lambda *args, **kwargs: {
        "files": [
            {"id": "file-1", "name": "Doc", "mimeType": "text/plain", "webViewLink": "link", "size": 10}
        ]
    })
    monkeypatch.setattr(connector, "_download_file_content", lambda *args, **kwargs: (b"hello", "text/plain", "Doc"))
    monkeypatch.setattr("services.embeddings.generate_embeddings_batch_sync", lambda chunks: [[0.1] * 3 for _ in chunks])
    monkeypatch.setattr("connectors.drive.insert_rows_with_retry", lambda *args, **kwargs: (SimpleNamespace(data=[{"id": "c"}]), None))
    monkeypatch.setattr("connectors.drive.compute_content_hash", lambda *_: "hash")
    monkeypatch.setattr("worker.tasks.create_file_status", lambda *args, **kwargs: "status-1")
    monkeypatch.setattr("worker.tasks.update_file_status", lambda *args, **kwargs: None)
    monkeypatch.setattr(settings, "MAX_FILE_SIZE", 10 * 1024 * 1024)
    monkeypatch.setattr(settings, "CHUNK_INSERT_BATCH_SIZE", 10)

    result = connector._sync_implementation("user-1", "int-1")

    assert result["status"] == "success"
    assert result["files_processed"] == 1


def test_ingest_logic_folder_text_decode_replaces_nulls():
    connector = DriveConnector()
    folder_meta = {"id": "folder-1", "name": "Folder", "mimeType": "application/vnd.google-apps.folder"}
    file_meta = {"id": "file-1", "name": "Doc", "mimeType": "text/plain", "webViewLink": "link"}

    with patch("connectors.drive.build", return_value=MagicMock()), \
         patch.object(connector, "_drive_get", return_value=folder_meta), \
         patch.object(connector, "_get_all_files_recursive", return_value=[file_meta]), \
         patch.object(connector, "_download_file_content", return_value=(b"\xff\x00hello", "text/plain", "Doc")), \
         patch("connectors.drive.settings.GOOGLE_CLIENT_ID", "id"), \
         patch("connectors.drive.settings.GOOGLE_CLIENT_SECRET", "secret"):
        docs = list(
            connector._ingest_logic(
                {
                    "item_ids": ["folder-1"],
                    "credentials": {"access_token": "token", "refresh_token": "refresh"},
                }
            )
        )

    assert len(docs) == 1
    assert "\x00" not in docs[0].page_content


def test_ingest_logic_folder_file_error_continues():
    connector = DriveConnector()
    folder_meta = {"id": "folder-1", "name": "Folder", "mimeType": "application/vnd.google-apps.folder"}
    file_meta = {"id": "file-1", "name": "Doc", "mimeType": "text/plain"}

    with patch("connectors.drive.build", return_value=MagicMock()), \
         patch.object(connector, "_drive_get", return_value=folder_meta), \
         patch.object(connector, "_get_all_files_recursive", return_value=[file_meta]), \
         patch.object(connector, "_download_file_content", side_effect=Exception("boom")), \
         patch("connectors.drive.settings.GOOGLE_CLIENT_ID", "id"), \
         patch("connectors.drive.settings.GOOGLE_CLIENT_SECRET", "secret"):
        docs = list(
            connector._ingest_logic(
                {
                    "item_ids": ["folder-1"],
                    "credentials": {"access_token": "token", "refresh_token": "refresh"},
                }
            )
        )

    assert docs == []


def test_ingest_logic_file_binary_base64():
    connector = DriveConnector()
    file_meta = {"id": "file-1", "name": "Doc", "mimeType": "application/pdf", "webViewLink": "link"}

    with patch("connectors.drive.build", return_value=MagicMock()), \
         patch.object(connector, "_drive_get", return_value=file_meta), \
         patch.object(connector, "_download_file_content", return_value=(b"bin", "application/pdf", "Doc.pdf")), \
         patch("connectors.drive.settings.GOOGLE_CLIENT_ID", "id"), \
         patch("connectors.drive.settings.GOOGLE_CLIENT_SECRET", "secret"):
        docs = list(
            connector._ingest_logic(
                {
                    "item_ids": ["file-1"],
                    "credentials": {"access_token": "token", "refresh_token": "refresh"},
                }
            )
        )

    assert docs[0].page_content == base64.b64encode(b"bin").decode("ascii")


def test_ingest_logic_handles_drive_get_error():
    connector = DriveConnector()

    with patch("connectors.drive.build", return_value=MagicMock()), \
         patch.object(connector, "_drive_get", side_effect=Exception("boom")), \
         patch("connectors.drive.settings.GOOGLE_CLIENT_ID", "id"), \
         patch("connectors.drive.settings.GOOGLE_CLIENT_SECRET", "secret"):
        docs = list(
            connector._ingest_logic(
                {
                    "item_ids": ["file-1"],
                    "credentials": {"access_token": "token", "refresh_token": "refresh"},
                }
            )
        )

    assert docs == []


def test_sync_skips_empty_decoded_content(monkeypatch):
    connector = DriveConnector()
    supabase = MagicMock()

    def make_table(responses):
        table = MagicMock()
        table.select.return_value = table
        table.insert.return_value = table
        table.update.return_value = table
        table.eq.return_value = table
        table.limit.return_value = table
        table.single.return_value = table
        responses_iter = iter(responses)

        def _execute():
            return SimpleNamespace(data=next(responses_iter, responses[-1] if responses else []))

        table.execute.side_effect = _execute
        return table

    tables = {
        "user_integrations": make_table([{"id": "int-1", "access_token": "enc", "refresh_token": "enc"}]),
        "ingestion_jobs": make_table([[{"id": "job-1"}], [{"id": "job-1"}]]),
    }

    supabase.table.side_effect = lambda name: tables.get(name, make_table([[]]))

    monkeypatch.setattr("connectors.drive.get_supabase", lambda: supabase)
    monkeypatch.setattr("connectors.drive.build", lambda *args, **kwargs: MagicMock())
    monkeypatch.setattr(connector, "_get_credentials_by_integration", lambda integration: MagicMock())
    monkeypatch.setattr(connector, "_drive_list", lambda *args, **kwargs: {
        "files": [
            {"id": "file-1", "name": "Doc", "mimeType": "text/plain", "webViewLink": "link", "size": 10}
        ]
    })
    monkeypatch.setattr(connector, "_download_file_content", lambda *args, **kwargs: (b"   ", "text/plain", "Doc"))
    monkeypatch.setattr("worker.tasks.create_file_status", lambda *args, **kwargs: "status-1")
    monkeypatch.setattr("worker.tasks.update_file_status", lambda *args, **kwargs: None)

    result = connector._sync_implementation("user-1", "int-1")
    assert result["status"] == "success"


def test_sync_reuses_existing_document_and_handles_chunk_insert_failure(monkeypatch):
    connector = DriveConnector()
    supabase = MagicMock()

    def make_table(responses):
        table = MagicMock()
        table.select.return_value = table
        table.insert.return_value = table
        table.update.return_value = table
        table.eq.return_value = table
        table.limit.return_value = table
        table.single.return_value = table
        responses_iter = iter(responses)

        def _execute():
            return SimpleNamespace(data=next(responses_iter, responses[-1] if responses else []))

        table.execute.side_effect = _execute
        return table

    tables = {
        "user_integrations": make_table([{"id": "int-1", "access_token": "enc", "refresh_token": "enc"}]),
        "ingestion_jobs": make_table([[{"id": "job-1"}], [{"id": "job-1"}]]),
        "documents": make_table([[{"id": "doc-1"}], [{"id": "doc-1"}]]),
    }

    supabase.table.side_effect = lambda name: tables.get(name, make_table([[]]))

    monkeypatch.setattr("connectors.drive.get_supabase", lambda: supabase)
    monkeypatch.setattr("connectors.drive.build", lambda *args, **kwargs: MagicMock())
    monkeypatch.setattr(connector, "_get_credentials_by_integration", lambda integration: MagicMock())
    monkeypatch.setattr(connector, "_drive_list", lambda *args, **kwargs: {
        "files": [
            {"id": "file-1", "name": "Doc", "mimeType": "text/plain", "webViewLink": "link", "size": 10}
        ]
    })
    monkeypatch.setattr(connector, "_download_file_content", lambda *args, **kwargs: (b"hello", "text/plain", "Doc"))
    monkeypatch.setattr(connector.text_splitter, "split_text", lambda *_args, **_kwargs: ["a", "b"])
    monkeypatch.setattr("services.embeddings.generate_embeddings_batch_sync", lambda _chunks: [None, [0.1]])
    monkeypatch.setattr("connectors.drive.compute_content_hash", lambda *_: "hash")
    monkeypatch.setattr("connectors.drive.delete_rows_with_retry", lambda *args, **kwargs: None)
    monkeypatch.setattr("connectors.drive.insert_rows_with_retry", lambda *args, **kwargs: (_ for _ in ()).throw(Exception("db fail")))
    monkeypatch.setattr("worker.tasks.create_file_status", lambda *args, **kwargs: "status-1")
    monkeypatch.setattr("worker.tasks.update_file_status", lambda *args, **kwargs: None)

    result = connector._sync_implementation("user-1", "int-1")

    assert result["status"] == "success"
    assert result["errors"]


def test_sync_document_insert_failure(monkeypatch):
    connector = DriveConnector()
    supabase = MagicMock()

    def make_table(responses):
        table = MagicMock()
        table.select.return_value = table
        table.insert.return_value = table
        table.update.return_value = table
        table.eq.return_value = table
        table.limit.return_value = table
        table.single.return_value = table
        responses_iter = iter(responses)

        def _execute():
            return SimpleNamespace(data=next(responses_iter, responses[-1] if responses else []))

        table.execute.side_effect = _execute
        return table

    tables = {
        "user_integrations": make_table([{"id": "int-1", "access_token": "enc", "refresh_token": "enc"}]),
        "ingestion_jobs": make_table([[{"id": "job-1"}], [{"id": "job-1"}]]),
        "documents": make_table([[], None]),
    }

    supabase.table.side_effect = lambda name: tables.get(name, make_table([[]]))

    monkeypatch.setattr("connectors.drive.get_supabase", lambda: supabase)
    monkeypatch.setattr("connectors.drive.build", lambda *args, **kwargs: MagicMock())
    monkeypatch.setattr(connector, "_get_credentials_by_integration", lambda integration: MagicMock())
    monkeypatch.setattr(connector, "_drive_list", lambda *args, **kwargs: {
        "files": [
            {"id": "file-1", "name": "Doc", "mimeType": "text/plain", "webViewLink": "link", "size": 10}
        ]
    })
    monkeypatch.setattr(connector, "_download_file_content", lambda *args, **kwargs: (b"hello", "text/plain", "Doc"))
    monkeypatch.setattr(connector.text_splitter, "split_text", lambda *_args, **_kwargs: ["a"])
    monkeypatch.setattr("services.embeddings.generate_embeddings_batch_sync", lambda _chunks: [[0.1]])
    monkeypatch.setattr("connectors.drive.compute_content_hash", lambda *_: "hash")
    monkeypatch.setattr("worker.tasks.create_file_status", lambda *args, **kwargs: "status-1")
    monkeypatch.setattr("worker.tasks.update_file_status", lambda *args, **kwargs: None)

    result = connector._sync_implementation("user-1", "int-1")
    assert result["errors"]


def test_sync_global_exception_marks_job_failed(monkeypatch):
    connector = DriveConnector()
    supabase = MagicMock()

    def make_table(responses):
        table = MagicMock()
        table.select.return_value = table
        table.insert.return_value = table
        table.update.return_value = table
        table.eq.return_value = table
        table.limit.return_value = table
        table.single.return_value = table
        responses_iter = iter(responses)

        def _execute():
            return SimpleNamespace(data=next(responses_iter, responses[-1] if responses else []))

        table.execute.side_effect = _execute
        return table

    ingestion_jobs = make_table([[{"id": "job-1"}], [{"id": "job-1"}], [{"id": "job-1"}]])
    user_integrations = make_table([{"id": "int-1", "access_token": "enc", "refresh_token": "enc"}])
    update_chain = MagicMock()
    update_chain.eq.return_value = update_chain
    update_chain.execute.side_effect = Exception("boom")
    user_integrations.update.return_value = update_chain
    documents = make_table([[], [{"id": "doc-1"}]])

    def table_side_effect(name):
        if name == "ingestion_jobs":
            return ingestion_jobs
        if name == "user_integrations":
            return user_integrations
        if name == "documents":
            return documents
        return make_table([[]])

    supabase.table.side_effect = table_side_effect

    monkeypatch.setattr("connectors.drive.get_supabase", lambda: supabase)
    monkeypatch.setattr("connectors.drive.build", lambda *args, **kwargs: MagicMock())
    monkeypatch.setattr(connector, "_get_credentials_by_integration", lambda integration: MagicMock())
    monkeypatch.setattr(connector, "_drive_list", lambda *args, **kwargs: {
        "files": [
            {"id": "file-1", "name": "Doc", "mimeType": "text/plain", "webViewLink": "link", "size": 10}
        ]
    })
    monkeypatch.setattr(connector, "_download_file_content", lambda *args, **kwargs: (b"hello", "text/plain", "Doc"))
    monkeypatch.setattr(connector.text_splitter, "split_text", lambda *_args, **_kwargs: ["a"])
    monkeypatch.setattr("services.embeddings.generate_embeddings_batch_sync", lambda _chunks: [[0.1]])
    monkeypatch.setattr("connectors.drive.insert_rows_with_retry", lambda *args, **kwargs: (SimpleNamespace(data=[{"id": "c"}]), None))
    monkeypatch.setattr("connectors.drive.compute_content_hash", lambda *_: "hash")
    monkeypatch.setattr("worker.tasks.create_file_status", lambda *args, **kwargs: "status-1")
    monkeypatch.setattr("worker.tasks.update_file_status", lambda *args, **kwargs: None)

    with pytest.raises(Exception):
        connector._sync_implementation("user-1", "int-1")

    assert ingestion_jobs.update.called
