import asyncio
from datetime import datetime, timezone
from types import SimpleNamespace
from unittest.mock import MagicMock, patch

import pytest

from connectors.drive import DriveConnector
from connectors.enhanced import AuthenticationError, SourceDocument, SourceType
from services.oauth_token_manager import TokenRefreshError


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
    with patch(
        "services.oauth_token_manager.OAuthTokenManager.get_valid_credentials",
        side_effect=TokenRefreshError("fail"),
    ), pytest.raises(ValueError):
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


def test_list_files_sync_returns_items():
    connector = DriveConnector()
    files = [
        {"id": "folder-1", "name": "Folder", "mimeType": "application/vnd.google-apps.folder"},
        {"id": "file-1", "name": "Doc", "mimeType": "text/plain", "size": "1024"},
    ]

    with patch.object(connector, "_get_credentials", return_value=MagicMock()), \
         patch("connectors.drive.build", return_value=MagicMock()), \
         patch.object(connector, "_list_drive_children", return_value=files), \
         patch.object(connector, "_list_shared_drives", return_value=[]):
        items = connector._list_files_sync("user-1", parent_id=None)

    assert len(items) == 2
    assert items[0].mime_type == "application/vnd.google-apps.folder"


def test_list_files_sync_applies_since_and_populates_modified_at():
    connector = DriveConnector()
    files = [
        {
            "id": "file-1",
            "name": "Doc",
            "mimeType": "text/plain",
            "size": "1024",
            "modifiedTime": "2026-04-11T08:00:00Z",
        }
    ]
    since = "2026-04-10T12:00:00Z"

    with patch.object(connector, "_get_credentials", return_value=MagicMock()), \
         patch("connectors.drive.build", return_value=MagicMock()), \
         patch.object(connector, "_list_drive_children", return_value=files) as mock_children:
        items = connector._list_files_sync("user-1", parent_id=None, since=since)

    called_since = mock_children.call_args.kwargs["since"]
    assert isinstance(called_since, datetime)
    assert items[0].modified_at == datetime(2026, 4, 11, 8, 0, tzinfo=timezone.utc)


def test_list_files_sync_root_includes_shared_drives():
    connector = DriveConnector()

    with patch.object(connector, "_get_credentials", return_value=MagicMock()), \
         patch("connectors.drive.build", return_value=MagicMock()), \
         patch.object(connector, "_list_drive_children", return_value=[]), \
         patch.object(connector, "_list_shared_drives", return_value=[{"id": "drv-1", "name": "Team Drive"}]):
        items = connector._list_files_sync("user-1", parent_id=None)

    assert any(item.id == "shared_drive:drv-1:root" for item in items)
    assert any(item.name == "Team Drive" for item in items)


def test_list_files_sync_shared_drive_items_encode_ids():
    connector = DriveConnector()
    files = [
        {
            "id": "folder-1",
            "name": "Folder",
            "mimeType": "application/vnd.google-apps.folder",
            "modifiedTime": "2026-04-11T08:00:00Z",
        },
        {
            "id": "file-1",
            "name": "Doc",
            "mimeType": "text/plain",
            "size": "12",
            "modifiedTime": "2026-04-11T09:00:00Z",
        },
    ]

    with patch.object(connector, "_get_credentials", return_value=MagicMock()), \
         patch("connectors.drive.build", return_value=MagicMock()), \
         patch.object(connector, "_list_drive_children", return_value=files):
        items = connector._list_files_sync("user-1", parent_id="shared_drive:drv-1:root")

    assert items[0].id == "shared_drive:drv-1:folder-1"
    assert items[1].id == "shared_drive:drv-1:file-1"
    assert all(item.parent_id == "shared_drive:drv-1:root" for item in items)


def test_drive_list_calls_execute():
    connector = DriveConnector()
    service = MagicMock()
    service.files.return_value.list.return_value.execute.return_value = {"files": []}
    result = connector._drive_list(service, q="test")
    assert result["files"] == []


def test_drive_get_calls_execute():
    connector = DriveConnector()
    service = MagicMock()
    service.files.return_value.get.return_value.execute.return_value = {"id": "file-1"}
    result = connector._drive_get(service, fileId="file-1")
    assert result["id"] == "file-1"


def test_authorize_async_wrapper():
    connector = DriveConnector()

    async def run():
        with patch("connectors.drive.run_in_threadpool", side_effect=lambda fn, *args: fn(*args)), \
             patch.object(connector, "_authorize_implementation", return_value=True):
            return await connector.authorize("user-1")

    assert asyncio.run(run()) is True


def test_list_files_async_wrapper():
    connector = DriveConnector()

    async def run():
        with patch("connectors.drive.run_in_threadpool", side_effect=lambda fn, *args: fn(*args)), \
             patch.object(connector, "_list_files_sync", return_value=[]):
            return await connector.list_files({"user_id": "user-1"}, since=None)

    assert asyncio.run(run()) == []


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
    assert filename is None


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
            {"id": "file-1", "mimeType": "application/pdf", "name": "Doc"},
        )

    assert content == b"pdf-data"
    assert mime_type == "application/pdf"
    assert filename == "Doc"


def test_fetch_documents_sync_requires_credentials_or_user():
    connector = DriveConnector()
    with pytest.raises(AuthenticationError):
        list(connector.fetch_documents_sync(["file-1"]))


def test_fetch_documents_sync_yields_source_document():
    connector = DriveConnector()

    with patch.object(connector, "_get_credentials", return_value=MagicMock()), \
         patch("connectors.drive.build", return_value=MagicMock()), \
         patch.object(connector, "_drive_get", return_value={
             "id": "file-1",
             "name": "Doc",
             "mimeType": "text/plain",
             "webViewLink": "https://drive.google.com/file/test",
         }), patch.object(connector, "_download_file_content", return_value=(b"hello", "text/plain", "Doc.txt")):
        # user_id must be passed via credentials dict due to operator precedence in fetch_documents_sync
        docs = list(connector.fetch_documents_sync(["file-1"], credentials={"user_id": "user-1"}))

    assert isinstance(docs[0], SourceDocument)


def test_fetch_documents_sync_shared_drive_root_recurses():
    connector = DriveConnector()
    service = MagicMock()

    with patch.object(connector, "_get_credentials", return_value=MagicMock()), \
         patch("connectors.drive.build", return_value=service), \
         patch.object(connector, "_get_all_files_recursive", return_value=iter([{"id": "file-1", "name": "Doc", "mimeType": "text/plain"}])), \
         patch.object(connector, "_build_source_document", return_value=SourceDocument(
             content=b"hello",
             metadata={"source": "google_drive"},
             source_type=SourceType.GOOGLE_DRIVE,
             source_id="file-1",
             filename="Doc.txt",
             mime_type="text/plain",
             size_bytes=5,
         )) as mock_build:
        docs = list(connector.fetch_documents_sync(["shared_drive:drv-1:root"], credentials={"user_id": "user-1"}))

    assert len(docs) == 1
    assert mock_build.call_args.kwargs["parent_id"] == "shared_drive:drv-1:root"


def test_connector_type_google_drive():
    connector = DriveConnector()
    assert connector.connector_type == SourceType.GOOGLE_DRIVE


def test_authorize_implementation_missing_definition_returns_false():
    supabase = MagicMock()
    supabase.table.return_value.select.return_value.eq.return_value.single.return_value.execute.return_value = MagicMock(
        data=None
    )

    with patch("connectors.drive.get_supabase", return_value=supabase):
        connector = DriveConnector()
        assert connector._authorize_implementation("user-1") is False


def test_get_credentials_by_integration_success():
    connector = DriveConnector()
    integration = {"id": "int-1"}

    with patch(
        "connectors.drive.OAuthTokenManager.get_valid_credentials",
        return_value={"access_token": "access-1", "refresh_token": "refresh-1"},
    ), patch("connectors.drive.Credentials") as creds_cls:
        creds_cls.return_value = "creds"
        result = connector._get_credentials_by_integration(integration)

    assert result == "creds"
    kwargs = creds_cls.call_args.kwargs
    assert kwargs["token"] == "access-1"
    assert kwargs["refresh_token"] == "refresh-1"


def test_get_credentials_missing_integration_raises():
    def_table = MagicMock()
    def_table.select.return_value = def_table
    def_table.eq.return_value = def_table
    def_table.single.return_value = def_table
    def_table.execute.return_value = MagicMock(data={"id": "def-1"})

    integration_table = MagicMock()
    integration_table.select.return_value = integration_table
    integration_table.eq.return_value = integration_table
    integration_table.execute.return_value = MagicMock(data=[])

    supabase = MagicMock()
    supabase.table.side_effect = lambda name: def_table if name == "connector_definitions" else integration_table

    with patch("connectors.drive.get_supabase", return_value=supabase):
        connector = DriveConnector()
        with pytest.raises(ValueError):
            connector._get_credentials("user-1")


def test_get_credentials_success_calls_integration_lookup():
    def_table = MagicMock()
    def_table.select.return_value = def_table
    def_table.eq.return_value = def_table
    def_table.single.return_value = def_table
    def_table.execute.return_value = MagicMock(data={"id": "def-1"})

    integration_table = MagicMock()
    integration_table.select.return_value = integration_table
    integration_table.eq.return_value = integration_table
    integration_table.execute.return_value = MagicMock(data=[{"id": "int-1"}])

    supabase = MagicMock()
    supabase.table.side_effect = lambda name: def_table if name == "connector_definitions" else integration_table

    with patch("connectors.drive.get_supabase", return_value=supabase), \
         patch.object(DriveConnector, "_get_credentials_by_integration", return_value="creds") as get_creds:
        connector = DriveConnector()
        result = connector._get_credentials("user-1")

    assert result == "creds"
    get_creds.assert_called_once_with({"id": "int-1"})


def test_download_file_content_export_error_raises():
    connector = DriveConnector()
    service = MagicMock()
    service.files.return_value.export_media.side_effect = Exception("boom")

    from connectors.base import ConnectorTransientError
    with pytest.raises(ConnectorTransientError):
        connector._download_file_content(
            service,
            {
                "id": "file-1",
                "mimeType": "application/vnd.google-apps.document",
                "name": "Doc",
            },
        )


def test_download_file_content_binary_error_raises():
    connector = DriveConnector()
    service = MagicMock()
    service.files.return_value.get_media.side_effect = Exception("boom")

    from connectors.base import ConnectorTransientError
    with pytest.raises(ConnectorTransientError):
        connector._download_file_content(
            service,
            {"id": "file-1", "mimeType": "application/pdf", "name": "Doc"},
        )


def test_get_all_files_recursive_handles_error():
    connector = DriveConnector()
    with patch.object(connector, "_drive_list", side_effect=Exception("boom")):
        assert list(connector._get_all_files_recursive(MagicMock(), "root")) == []


def test_fetch_documents_sync_integration_not_found():
    connector = DriveConnector()
    supabase = MagicMock()
    table = MagicMock()
    table.select.return_value = table
    table.eq.return_value = table
    table.maybe_single.return_value = table
    table.execute.return_value = MagicMock(data=None)
    supabase.table.return_value = table

    with patch("connectors.drive.get_supabase", return_value=supabase):
        with pytest.raises(AuthenticationError):
            list(
                connector.fetch_documents_sync(
                    ["file-1"],
                    credentials={"integration_id": "int-1"},
                )
            )


def test_fetch_documents_sync_empty_item_ids_returns_empty():
    connector = DriveConnector()
    assert list(connector.fetch_documents_sync([])) == []


def test_fetch_documents_sync_integration_success():
    connector = DriveConnector()
    supabase = MagicMock()
    table = MagicMock()
    table.select.return_value = table
    table.eq.return_value = table
    table.single.return_value = table
    table.execute.return_value = MagicMock(data={"id": "int-1"})
    supabase.table.return_value = table

    doc = SourceDocument(
        content=b"hello",
        metadata={"title": "Doc"},
        source_type=SourceType.GOOGLE_DRIVE,
        source_id="file-1",
        filename="Doc.txt",
        mime_type="text/plain",
        size_bytes=5,
    )

    with patch("connectors.drive.get_supabase", return_value=supabase), \
         patch("connectors.drive.OAuthTokenManager.get_valid_credentials", return_value={"access_token": "token", "refresh_token": "refresh"}), \
         patch("connectors.drive.Credentials", return_value="creds"), \
         patch("connectors.drive.build", return_value=MagicMock()), \
         patch.object(connector, "_drive_get", return_value={
             "id": "file-1",
             "name": "Doc",
             "mimeType": "text/plain",
             "webViewLink": "https://drive.google.com/file/test",
         }), \
         patch.object(connector, "_build_source_document", return_value=doc) as build_doc:
        docs = list(
            connector.fetch_documents_sync(
                ["file-1"],
                credentials={"integration_id": "int-1"},
            )
        )

    assert docs == [doc]
    build_doc.assert_called_once()


def test_fetch_documents_sync_folder_branch_skips_missing_docs():
    connector = DriveConnector()
    doc = SourceDocument(
        content=b"hello",
        metadata={"title": "Doc"},
        source_type=SourceType.GOOGLE_DRIVE,
        source_id="file-2",
        filename="Doc.txt",
        mime_type="text/plain",
        size_bytes=5,
    )

    files = [
        {"id": "file-1", "name": "Doc1", "mimeType": "text/plain"},
        {"id": "file-2", "name": "Doc2", "mimeType": "text/plain"},
    ]

    with patch.object(connector, "_get_credentials", return_value=MagicMock()), \
         patch("connectors.drive.build", return_value=MagicMock()), \
         patch.object(connector, "_drive_get", return_value={
             "id": "folder-1",
             "name": "Folder",
             "mimeType": "application/vnd.google-apps.folder",
         }), \
         patch.object(connector, "_get_all_files_recursive", return_value=files), \
         patch.object(connector, "_build_source_document", side_effect=[None, doc]):
        # user_id must be passed via credentials dict due to operator precedence in fetch_documents_sync
        docs = list(connector.fetch_documents_sync(["folder-1"], credentials={"user_id": "user-1"}))

    assert docs == [doc]


def test_build_source_document_returns_none_when_no_content():
    connector = DriveConnector()
    with patch.object(connector, "_download_file_content", return_value=(None, None, None)):
        result = connector._build_source_document(
            MagicMock(),
            {"id": "file-1"},
            parent_id=None,
            scope_id="google_drive://drive-1/folder-1",
        )

    assert result is None


@pytest.mark.asyncio
async def test_fetch_documents_async_wrapper():
    connector = DriveConnector()
    doc = SourceDocument(
        content=b"hello",
        metadata={"title": "Doc"},
        source_type=SourceType.GOOGLE_DRIVE,
        source_id="file-1",
        filename="Doc.txt",
        mime_type="text/plain",
        size_bytes=5,
    )

    with patch.object(connector, "fetch_documents_sync", return_value=iter([doc])):
        docs = []
        async for item in connector.fetch_documents(["file-1"], user_id="user-1"):
            docs.append(item)

    assert docs == [doc]


def test_fetch_documents_sync_continues_on_error():
    connector = DriveConnector()
    doc = SourceDocument(
        content=b"hello",
        metadata={"title": "Doc"},
        source_type=SourceType.GOOGLE_DRIVE,
        source_id="file-1",
        filename="Doc.txt",
        mime_type="text/plain",
        size_bytes=5,
    )

    with patch.object(connector, "_get_credentials", return_value=MagicMock()), \
         patch("connectors.drive.build", return_value=MagicMock()), \
         patch.object(connector, "_drive_get", side_effect=[Exception("boom"), {
             "id": "file-1",
             "name": "Doc",
             "mimeType": "text/plain",
             "webViewLink": "https://drive.google.com/file/test",
         }]), \
         patch.object(connector, "_build_source_document", return_value=doc):
        # user_id must be passed via credentials dict due to operator precedence in fetch_documents_sync
        docs = list(connector.fetch_documents_sync(["bad", "good"], credentials={"user_id": "user-1"}))

    assert docs == [doc]
