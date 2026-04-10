"""Unit tests for the SFTP connector."""

from __future__ import annotations

import io
import stat
from contextlib import contextmanager

import pytest

import connectors.sftp as sftp_module
from connectors.sftp import SFTP_PREFETCH_THRESHOLD_BYTES, SFTPConnector


class FakeAttrs:
    def __init__(self, filename: str, mode: int, size: int = 0, mtime: int = 0):
        self.filename = filename
        self.st_mode = mode
        self.st_size = size
        self.st_mtime = mtime


class FakeRemoteFile:
    def __init__(self, data: bytes):
        self._buffer = io.BytesIO(data)
        self.prefetch_called = False

    def prefetch(self) -> None:
        self.prefetch_called = True

    def read(self, size: int) -> bytes:
        return self._buffer.read(size)

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc, tb):
        return False


class FakeSFTPClient:
    def __init__(self, listing=None, stats=None, files=None):
        self._listing = listing or {}
        self._stats = stats or {}
        self._files = files or {}
        self.last_opened = None

    def listdir_attr(self, path: str):
        return self._listing.get(path, [])

    def stat(self, path: str):
        if path in self._stats:
            return self._stats[path]
        raise FileNotFoundError(path)

    def open(self, path: str, mode: str):
        data = self._files.get(path, b"")
        self.last_opened = FakeRemoteFile(data)
        return self.last_opened


@contextmanager
def fake_connection(client):
    yield client


def test_validate_config_blocks_private_host(monkeypatch):
    connector = SFTPConnector()
    monkeypatch.setattr(sftp_module.socket, "gethostbyname", lambda host: "127.0.0.1")

    config = {
        "host": "localhost",
        "port": 22,
        "username": "user",
        "password": "pass",
        "root_path": "/",
    }

    with pytest.raises(ValueError):
        connector.validate_config(config)


def test_supports_incremental_sync_is_true():
    connector = SFTPConnector()

    assert connector.supports_incremental_sync is True


def test_list_files_recursive(monkeypatch):
    connector = SFTPConnector()
    monkeypatch.setattr(connector, "_ensure_safe_host", lambda host: None)

    listing = {
        "/": [
            FakeAttrs("folder", stat.S_IFDIR, mtime=100),
            FakeAttrs("a.txt", stat.S_IFREG, size=10, mtime=200),
        ],
        "/folder": [
            FakeAttrs("b.txt", stat.S_IFREG, size=12, mtime=300),
        ],
    }

    fake_sftp = FakeSFTPClient(listing=listing)
    connector._sftp_connection = lambda _config: fake_connection(fake_sftp)

    config = {"host": "example.com", "username": "user", "password": "pass", "root_path": "/"}
    files = list(connector.list_files(config))

    ids = {item.id for item in files}
    assert "/a.txt" in ids
    assert "/folder/b.txt" in ids
    assert all(item.mime_type != "inode/directory" for item in files)


def test_list_files_non_recursive_includes_dirs(monkeypatch):
    connector = SFTPConnector()
    monkeypatch.setattr(connector, "_ensure_safe_host", lambda host: None)

    listing = {
        "/": [
            FakeAttrs("folder", stat.S_IFDIR, mtime=100),
            FakeAttrs("a.txt", stat.S_IFREG, size=10, mtime=200),
        ]
    }

    fake_sftp = FakeSFTPClient(listing=listing)
    connector._sftp_connection = lambda _config: fake_connection(fake_sftp)

    config = {
        "host": "example.com",
        "username": "user",
        "password": "pass",
        "root_path": "/",
        "parent_id": "root",
    }
    files = list(connector.list_files(config))

    dir_items = [item for item in files if item.mime_type == "inode/directory"]
    assert dir_items
    assert dir_items[0].id == "/folder"


def test_fetch_file_content_prefetches_large_files(monkeypatch):
    connector = SFTPConnector()
    monkeypatch.setattr(connector, "_ensure_safe_host", lambda host: None)

    attrs = FakeAttrs(
        "file.txt",
        stat.S_IFREG,
        size=SFTP_PREFETCH_THRESHOLD_BYTES + 1,
        mtime=100,
    )
    fake_sftp = FakeSFTPClient(
        stats={"/file.txt": attrs},
        files={"/file.txt": b"hello"},
    )
    connector._sftp_connection = lambda _config: fake_connection(fake_sftp)

    config = {"host": "example.com", "username": "user", "password": "pass", "root_path": "/"}
    content = connector.fetch_file_content("/file.txt", config)

    assert content == b"hello"
    assert fake_sftp.last_opened is not None
    assert fake_sftp.last_opened.prefetch_called is True
