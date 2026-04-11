from unittest.mock import patch

import pytest
import requests

from connectors.base import (
    ConnectorAuthError,
    ConnectorRateLimitError,
    ConnectorTransientError,
    RemoteFile,
)
from connectors.enhanced import ItemNotFoundError
from connectors.microsoft import GRAPH_API_DOMAINS, MicrosoftGraphConnector


class FakeResponse:
    def __init__(self, status_code=200, json_data=None, headers=None, content_chunks=None, text=None):
        self.status_code = status_code
        self._json_data = json_data or {}
        self.headers = headers or {}
        self._content_chunks = content_chunks or []
        self.text = text if text is not None else str(self._json_data)
        self.closed = False

    def json(self):
        return self._json_data

    def raise_for_status(self):
        if self.status_code >= 400:
            raise requests.HTTPError(f"{self.status_code} error")

    def iter_content(self, chunk_size=1024):
        for chunk in self._content_chunks:
            yield chunk

    def close(self):
        self.closed = True


def _base_config():
    return {"access_token": "token", "user_id": "user-1", "target_type": "onedrive"}


def test_list_files_delta_updates_cursor():
    connector = MicrosoftGraphConnector("onedrive")
    config = _base_config()
    delta_items = [
        {
            "id": "file-1",
            "name": "Doc.txt",
            "file": {"mimeType": "text/plain"},
            "size": 12,
            "lastModifiedDateTime": "2025-01-01T00:00:00Z",
        },
        {"id": "folder-1", "name": "Folder", "folder": {}},
    ]

    with patch.object(connector, "_resolve_config", return_value=config), \
        patch.object(connector, "validate_config", return_value=True), \
        patch.object(connector, "_resolve_drive_id", return_value=("drive-1", None)), \
        patch.object(connector, "_delta_listing", return_value=(delta_items, "delta-link")), \
        patch("connectors.microsoft.SyncManager") as sync_manager:
        items = connector._list_files_sync(config, since=None)

    # Delta listing returns both files and folders
    assert len(items) == 2
    assert all(isinstance(item, RemoteFile) for item in items)
    sync_manager.return_value.update_state.assert_called_once_with(last_cursor="delta-link")


def test_list_files_children_returns_items():
    connector = MicrosoftGraphConnector("onedrive")
    config = _base_config()
    config["parent_id"] = "root"
    remote = RemoteFile(
        id="folder-1",
        name="Folder",
        mime_type="inode/directory",
        size=None,
        modified_at=None,
        parent_id=None,
        web_view_url=None,
    )

    with patch.object(connector, "_resolve_config", return_value=config), \
        patch.object(connector, "validate_config", return_value=True), \
        patch.object(connector, "_resolve_drive_id", return_value=("drive-1", None)), \
        patch.object(connector, "_list_children_items", return_value=[remote]):
        items = connector._list_files_sync(config, since=None)

    assert items == [remote]


def test_download_content_follows_redirect():
    connector = MicrosoftGraphConnector("onedrive")
    config = {"access_token": "token", "drive_id": "drive-1", "target_type": "onedrive"}
    redirect = FakeResponse(
        status_code=302,
        headers={"Location": "https://tenant.sharepoint.com/download"},
    )
    ok = FakeResponse(status_code=200, content_chunks=[b"hello"])

    with patch("connectors.microsoft.validate_redirect_url", side_effect=lambda url, _domains: url), \
        patch.object(connector, "_request_with_retry", side_effect=[redirect, ok]) as request_mock:
        data = connector._download_content(config, "item-1")

    assert data == b"hello"
    first_headers = request_mock.call_args_list[0].kwargs["headers"]
    second_headers = request_mock.call_args_list[1].kwargs["headers"]
    assert "Authorization" in first_headers
    assert second_headers == {}


def test_download_content_rejects_disallowed_redirect():
    connector = MicrosoftGraphConnector("onedrive")
    config = {"access_token": "token", "drive_id": "drive-1", "target_type": "onedrive"}
    redirect = FakeResponse(
        status_code=302,
        headers={"Location": "https://169.254.169.254/latest/meta-data"},
    )

    with patch(
        "connectors.microsoft.validate_redirect_url",
        side_effect=ConnectorTransientError("blocked"),
    ), patch.object(connector, "_request_with_retry", return_value=redirect) as request_mock:
        with pytest.raises(ConnectorTransientError, match="blocked"):
            connector._download_content(config, "item-1")

    assert request_mock.call_count == 1


def test_download_content_limits_redirect_chain():
    connector = MicrosoftGraphConnector("onedrive")
    config = {"access_token": "token", "drive_id": "drive-1", "target_type": "onedrive"}
    redirects = [
        FakeResponse(status_code=302, headers={"Location": f"https://tenant.sharepoint.com/download/{idx}"})
        for idx in range(6)
    ]

    with patch("connectors.microsoft.validate_redirect_url", side_effect=lambda url, _domains: url), \
        patch.object(connector, "_request_with_retry", side_effect=redirects):
        with pytest.raises(ConnectorTransientError, match="Too many redirects"):
            connector._download_content(config, "item-1")


def test_delta_listing_uses_opaque_token_as_query_param():
    connector = MicrosoftGraphConnector("onedrive")
    config = {"access_token": "token"}

    with patch.object(connector, "_get_json", return_value={"value": []}) as get_json_mock:
        items, delta_link = connector._delta_listing(config, "drive-1", "opaque-token")

    assert items == []
    assert delta_link is None
    get_json_mock.assert_called_once_with(
        config,
        "https://graph.microsoft.com/v1.0/drives/drive-1/root/delta",
        params={"token": "opaque-token"},
    )


def test_delta_listing_rejects_unexpected_absolute_token_scheme():
    connector = MicrosoftGraphConnector("onedrive")
    config = {"access_token": "token"}

    with pytest.raises(ConnectorTransientError, match="Invalid Microsoft Graph delta URL"):
        connector._delta_listing(config, "drive-1", "ftp://graph.microsoft.com/v1.0/drives/drive-1/root/delta")


def test_delta_listing_validates_absolute_token_and_pagination_links():
    connector = MicrosoftGraphConnector("onedrive")
    config = {"access_token": "token"}
    responses = [
        {
            "value": [{"id": "item-1"}],
            "@odata.nextLink": "https://graph.microsoft.com/v1.0/drives/drive-1/root/delta?$skiptoken=abc",
            "@odata.deltaLink": "https://graph.microsoft.com/v1.0/drives/drive-1/root/delta?$deltatoken=xyz",
        },
        {"value": []},
    ]

    def validate(url: str) -> str:
        return f"validated:{url}"

    with patch.object(connector, "_validate_graph_url", side_effect=validate) as validate_mock, \
        patch.object(connector, "_get_json", side_effect=responses) as get_json_mock:
        items, delta_link = connector._delta_listing(
            config,
            "drive-1",
            "https://graph.microsoft.com/v1.0/drives/drive-1/root/delta?$token=start",
        )

    assert items == [{"id": "item-1"}]
    assert delta_link == "validated:https://graph.microsoft.com/v1.0/drives/drive-1/root/delta?$deltatoken=xyz"
    assert get_json_mock.call_args_list[0].args == (
        config,
        "validated:https://graph.microsoft.com/v1.0/drives/drive-1/root/delta?$token=start",
    )
    assert get_json_mock.call_args_list[0].kwargs == {"params": None}
    assert get_json_mock.call_args_list[1].args == (
        config,
        "validated:https://graph.microsoft.com/v1.0/drives/drive-1/root/delta?$skiptoken=abc",
    )
    assert validate_mock.call_count == 3


def test_paged_items_validates_next_link():
    connector = MicrosoftGraphConnector("onedrive")
    config = {"access_token": "token"}
    responses = [
        {
            "value": [{"id": "item-1"}],
            "@odata.nextLink": "https://graph.microsoft.com/v1.0/drives/drive-1/root/children?$skiptoken=abc",
        },
        {"value": [{"id": "item-2"}]},
    ]

    with patch.object(connector, "_validate_graph_url", side_effect=lambda url: f"validated:{url}") as validate_mock, \
        patch.object(connector, "_get_json", side_effect=responses) as get_json_mock:
        items = list(connector._paged_items(config, "https://graph.microsoft.com/v1.0/drives/drive-1/root/children"))

    assert items == [{"id": "item-1"}, {"id": "item-2"}]
    assert get_json_mock.call_args_list[1].args == (
        config,
        "validated:https://graph.microsoft.com/v1.0/drives/drive-1/root/children?$skiptoken=abc",
    )
    validate_mock.assert_called_once_with(
        "https://graph.microsoft.com/v1.0/drives/drive-1/root/children?$skiptoken=abc"
    )


def test_get_json_rejects_non_graph_absolute_url():
    connector = MicrosoftGraphConnector("onedrive")

    with patch("connectors.microsoft.validate_redirect_url", side_effect=ConnectorTransientError("blocked")), \
        patch.object(connector, "_request_with_retry") as request_mock:
        with pytest.raises(ConnectorTransientError, match="blocked"):
            connector._get_json(_base_config(), "https://evil.example.com/metadata")

    request_mock.assert_not_called()


def test_get_json_validates_graph_absolute_url():
    connector = MicrosoftGraphConnector("onedrive")
    ok = FakeResponse(status_code=200, json_data={"id": "drive-1"})

    with patch("connectors.microsoft.validate_redirect_url", return_value="https://graph.microsoft.com/v1.0/me/drive") as validate_mock, \
        patch.object(connector, "_request_with_retry", return_value=ok) as request_mock:
        payload = connector._get_json(_base_config(), "https://graph.microsoft.com/v1.0/me/drive")

    assert payload == {"id": "drive-1"}
    validate_mock.assert_called_once_with(
        "https://graph.microsoft.com/v1.0/me/drive",
        GRAPH_API_DOMAINS,
    )
    request_mock.assert_called_once()


def test_request_with_retry_handles_429_then_success():
    connector = MicrosoftGraphConnector("onedrive")
    responses = [
        FakeResponse(status_code=429, headers={"Retry-After": "2"}),
        FakeResponse(status_code=200),
    ]

    with patch("connectors.microsoft.requests.request", side_effect=responses), \
        patch("connectors.microsoft.time.sleep") as sleep_mock:
        response = connector._request_with_retry("GET", "https://graph.microsoft.com/v1.0/me/drive")

    assert response.status_code == 200
    sleep_mock.assert_called_once_with(2)


def test_request_with_retry_raises_after_exhausted():
    connector = MicrosoftGraphConnector("onedrive")
    responses = [
        FakeResponse(status_code=429),
        FakeResponse(status_code=429),
        FakeResponse(status_code=429),
        FakeResponse(status_code=429),
    ]

    with patch("connectors.microsoft.requests.request", side_effect=responses):
        with pytest.raises(ConnectorRateLimitError):
            connector._request_with_retry("GET", "https://graph.microsoft.com/v1.0/me/drive")


def test_fetch_file_content_rejects_folder():
    connector = MicrosoftGraphConnector("onedrive")
    config = _base_config()
    config["drive_id"] = "drive-1"

    # Microsoft Graph returns folder with childCount; use realistic mock data
    folder_item = {"id": "folder-1", "name": "Folder", "folder": {"childCount": 0}}

    with patch.object(connector, "_resolve_config", return_value=config), \
        patch.object(connector, "validate_config", return_value=True), \
        patch.object(connector, "_resolve_drive_id", return_value=("drive-1", None)), \
        patch.object(connector, "_get_item", return_value=folder_item), \
        patch.object(connector, "_download_content") as mock_download:
        with pytest.raises(ItemNotFoundError):
            connector.fetch_file_content("folder-1", config)
        # Should not attempt to download folders
        mock_download.assert_not_called()


def test_fetch_file_content_downloads_bytes():
    connector = MicrosoftGraphConnector("onedrive")
    config = _base_config()

    with patch.object(connector, "_resolve_config", return_value=config), \
        patch.object(connector, "validate_config", return_value=True), \
        patch.object(connector, "_resolve_drive_id", return_value=("drive-1", None)), \
        patch.object(connector, "_get_item", return_value={"id": "file-1", "file": {"mimeType": "text/plain"}}), \
        patch.object(connector, "_download_content", return_value=b"payload"):
        content = connector.fetch_file_content("file-1", config)

    assert content == b"payload"


def test_list_files_invalid_config_raises_auth_error():
    connector = MicrosoftGraphConnector("onedrive")
    with patch.object(connector, "_resolve_config", return_value={"target_type": "onedrive"}):
        with pytest.raises(ConnectorAuthError):
            connector._list_files_sync({"target_type": "onedrive"}, since=None)
