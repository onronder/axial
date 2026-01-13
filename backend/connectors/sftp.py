"""
SFTP Connector

Securely ingests files from SFTP servers with SSRF protection, timeouts,
and robust error mapping. Implements BaseConnector + EnhancedConnector.
"""

from __future__ import annotations

import io
import ipaddress
import logging
import posixpath
import socket
import stat
from contextlib import contextmanager
from datetime import datetime, timezone
from typing import Any, Dict, Iterator, Optional, AsyncIterator

import paramiko

from connectors.base import (
    BaseConnector,
    RemoteFile,
    ConnectorAuthError,
    ConnectorTransientError,
)
from connectors.enhanced import EnhancedConnector, SourceDocument, SourceType, ItemNotFoundError
from core.db import get_supabase
from core.security import decrypt_token

logger = logging.getLogger(__name__)

SFTP_DEFAULT_PORT = 22
SFTP_TIMEOUT_SECONDS = 30
SFTP_KEEPALIVE_SECONDS = 30
SFTP_PREFETCH_THRESHOLD_BYTES = 1024 * 1024  # 1MB


class SFTPConnector(EnhancedConnector, BaseConnector):
    """
    Connector for SFTP servers using Paramiko.

    Config schema:
      host (required), port (default 22), username (required),
      password (optional), private_key (optional PEM), root_path (default "/")
    """

    @property
    def connector_type(self) -> SourceType:
        return SourceType.SFTP

    def validate_config(self, config: dict) -> bool:
        if not isinstance(config, dict):
            return False

        host = (config.get("host") or "").strip()
        username = (config.get("username") or "").strip()
        port = config.get("port", SFTP_DEFAULT_PORT)
        root_path = config.get("root_path", "/")
        password = config.get("password")
        private_key = config.get("private_key")

        if not host or not username:
            return False
        if not isinstance(port, int):
            return False
        if not isinstance(root_path, str):
            return False
        if not password and not private_key:
            return False

        # Skip SSRF check if _allow_private is set (testing only)
        if not config.get("_allow_private"):
            self._ensure_safe_host(host)
        return True

    def list_files(self, config: dict, since: datetime | None = None) -> Iterator[RemoteFile]:
        """
        List files for browsing or sync.
        - If parent_id is provided and not "root": list that directory (non-recursive).
        - If parent_id is "root": list immediate children of root_path (non-recursive).
        - If parent_id is None: recursive traversal from root_path (full sync).
        """
        resolved = dict(config or {})
        if not resolved.get("host"):
            user_id = resolved.get("user_id")
            if not user_id:
                raise ConnectorAuthError("SFTP credentials missing")
            resolved.update(self._load_credentials_for_user(user_id))
        resolved = self._resolve_config(resolved)
        if not self.validate_config(resolved):
            raise ConnectorAuthError("Invalid SFTP configuration")

        root_path = self._normalize_root(resolved.get("root_path", "/"))
        parent_id = resolved.get("parent_id")
        if parent_id in (None, "root"):
            base_path = root_path
            recursive = parent_id is None
        else:
            base_path = self._normalize_path(root_path, parent_id)
            recursive = False

        since_ts = since.timestamp() if since else None

        with self._sftp_connection(resolved) as sftp:
            if recursive:
                for file_path, attrs in self._walk(sftp, base_path, since_ts):
                    yield RemoteFile(
                        id=file_path,
                        name=posixpath.basename(file_path),
                        mime_type=None,
                        size=attrs.st_size,
                        modified_at=self._to_datetime(attrs.st_mtime),
                        parent_id=posixpath.dirname(file_path),
                        web_view_url=None,
                    )
                return

            for attrs in self._listdir_safe(sftp, base_path):
                if attrs.filename in (".", ".."):
                    continue
                full_path = posixpath.join(base_path, attrs.filename)
                if stat.S_ISDIR(attrs.st_mode):
                    yield RemoteFile(
                        id=full_path,
                        name=attrs.filename,
                        mime_type="inode/directory",
                        size=None,
                        modified_at=self._to_datetime(attrs.st_mtime),
                        parent_id=base_path,
                        web_view_url=None,
                    )
                    continue
                if since_ts and attrs.st_mtime < since_ts:
                    continue
                yield RemoteFile(
                    id=full_path,
                    name=attrs.filename,
                    mime_type=None,
                    size=attrs.st_size,
                    modified_at=self._to_datetime(attrs.st_mtime),
                    parent_id=base_path,
                    web_view_url=None,
                )

    def fetch_file_content(self, file_id: str, config: dict) -> bytes:
        resolved = self._resolve_config(config)
        if not self.validate_config(resolved):
            raise ConnectorAuthError("Invalid SFTP configuration")

        root_path = self._normalize_root(resolved.get("root_path", "/"))
        remote_path = self._normalize_path(root_path, file_id)

        with self._sftp_connection(resolved) as sftp:
            try:
                attrs = sftp.stat(remote_path)
            except FileNotFoundError as exc:
                raise ItemNotFoundError(f"SFTP file not found: {remote_path}") from exc

            if stat.S_ISDIR(attrs.st_mode):
                raise ItemNotFoundError(f"SFTP path is a directory: {remote_path}")

            return self._read_file(sftp, remote_path, attrs)

    async def fetch_documents(
        self,
        item_ids: list[str],
        credentials: Optional[Dict[str, Any]] = None,
        **kwargs,
    ) -> AsyncIterator[SourceDocument]:
        for doc in self.fetch_documents_sync(item_ids, credentials, **kwargs):
            yield doc

    def fetch_documents_sync(
        self,
        item_ids: list[str],
        credentials: Optional[Dict[str, Any]] = None,
        **kwargs,
    ) -> Iterator[SourceDocument]:
        if not item_ids:
            return iter(())

        resolved = self._resolve_config(credentials or {})
        if not self.validate_config(resolved):
            raise ConnectorAuthError("Invalid SFTP configuration")

        root_path = self._normalize_root(resolved.get("root_path", "/"))

        with self._sftp_connection(resolved) as sftp:
            for item_id in item_ids:
                remote_path = self._normalize_path(root_path, item_id)
                try:
                    attrs = sftp.stat(remote_path)
                except FileNotFoundError:
                    logger.warning("⚠️ [SFTP] Not found: %s", remote_path)
                    continue
                if stat.S_ISDIR(attrs.st_mode):
                    for file_path, file_attrs in self._walk(sftp, remote_path, since_ts=None):
                        yield self._build_source_document(sftp, file_path, file_attrs, resolved)
                else:
                    yield self._build_source_document(sftp, remote_path, attrs, resolved)

    def verify_connection(self, config: dict) -> None:
        """
        Light-weight connectivity check for connect flow.
        """
        resolved = self._resolve_config(config)
        if not self.validate_config(resolved):
            raise ConnectorAuthError("Invalid SFTP configuration")

        root_path = self._normalize_root(resolved.get("root_path", "/"))
        with self._sftp_connection(resolved) as sftp:
            self._listdir_safe(sftp, root_path)

    # ---------------------------------------------------------------------
    # Internals
    # ---------------------------------------------------------------------
    def _ensure_safe_host(self, host: str) -> None:
        try:
            ip_addr = socket.gethostbyname(host)
        except socket.gaierror as exc:
            raise ConnectorTransientError(f"SFTP host lookup failed: {exc}") from exc

        ip_obj = ipaddress.ip_address(ip_addr)
        if not ip_obj.is_global:
            raise ValueError("Security Violation: Access to private network denied")

    def _load_credentials_for_user(self, user_id: str) -> dict:
        supabase = get_supabase()
        def_res = supabase.table("connector_definitions").select("id").eq("type", "sftp").single().execute()
        if not def_res.data:
            raise ConnectorAuthError("SFTP connector not registered")
        connector_def_id = def_res.data["id"]
        int_res = supabase.table("user_integrations").select("credentials").eq(
            "user_id", user_id
        ).eq("connector_definition_id", connector_def_id).single().execute()
        if not int_res.data or not int_res.data.get("credentials"):
            raise ConnectorAuthError("SFTP not connected for this user")
        return int_res.data["credentials"]

    def _resolve_config(self, config: dict) -> dict:
        resolved = dict(config or {})
        resolved.setdefault("port", SFTP_DEFAULT_PORT)
        resolved.setdefault("root_path", "/")

        if resolved.get("password"):
            resolved["password"] = self._maybe_decrypt(resolved["password"])
        if resolved.get("private_key"):
            resolved["private_key"] = self._maybe_decrypt(resolved["private_key"])
        return resolved

    def _maybe_decrypt(self, value: str) -> str:
        try:
            return decrypt_token(value)
        except Exception:
            return value

    def _normalize_root(self, root_path: str) -> str:
        root = root_path or "/"
        if not root.startswith("/"):
            root = f"/{root}"
        return posixpath.normpath(root)

    def _normalize_path(self, root_path: str, path: str) -> str:
        if not path:
            return root_path
        normalized = posixpath.normpath(path)
        if not normalized.startswith("/"):
            normalized = posixpath.normpath(posixpath.join(root_path, normalized))
        root = self._normalize_root(root_path)
        if root != "/" and not normalized.startswith(root + "/") and normalized != root:
            raise ConnectorAuthError("Requested path is outside the configured root_path")
        return normalized

    def _load_private_key(self, private_key: str) -> paramiko.PKey:
        key_stream = io.StringIO(private_key)
        key_loaders = (
            paramiko.RSAKey.from_private_key,
            paramiko.Ed25519Key.from_private_key,
            paramiko.ECDSAKey.from_private_key,
            paramiko.DSSKey.from_private_key,
        )
        last_error = None
        for loader in key_loaders:
            key_stream.seek(0)
            try:
                return loader(key_stream)
            except Exception as exc:
                last_error = exc
        raise ConnectorAuthError(f"Invalid private key: {last_error}") from last_error

    @contextmanager
    def _sftp_connection(self, config: dict):
        host = config.get("host")
        port = config.get("port", SFTP_DEFAULT_PORT)
        username = config.get("username")
        password = config.get("password")
        private_key = config.get("private_key")

        # Skip SSRF check if _allow_private is set (testing only)
        if not config.get("_allow_private"):
            self._ensure_safe_host(host)

        client = paramiko.SSHClient()
        client.set_missing_host_key_policy(paramiko.AutoAddPolicy())
        logger.info("🔐 [SFTP] Auto-accepting host key for %s:%s", host, port)

        pkey = None
        if private_key:
            pkey = self._load_private_key(private_key)

        try:
            client.connect(
                hostname=host,
                port=port,
                username=username,
                password=password,
                pkey=pkey,
                timeout=SFTP_TIMEOUT_SECONDS,
                banner_timeout=SFTP_TIMEOUT_SECONDS,
                auth_timeout=SFTP_TIMEOUT_SECONDS,
                look_for_keys=False,
                allow_agent=False,
            )
            transport = client.get_transport()
            if transport:
                transport.set_keepalive(SFTP_KEEPALIVE_SECONDS)

            sftp = client.open_sftp()
            try:
                yield sftp
            finally:
                try:
                    sftp.close()
                except Exception:
                    pass
        except paramiko.AuthenticationException as exc:
            raise ConnectorAuthError("SFTP authentication failed") from exc
        except paramiko.SSHException as exc:
            raise ConnectorTransientError(f"SFTP SSH error: {exc}") from exc
        except (socket.timeout, socket.error) as exc:
            raise ConnectorTransientError(f"SFTP connection error: {exc}") from exc
        finally:
            try:
                client.close()
            except Exception:
                pass

    def _listdir_safe(self, sftp: paramiko.SFTPClient, path: str) -> list[paramiko.SFTPAttributes]:
        try:
            return sftp.listdir_attr(path)
        except OSError as exc:
            if getattr(exc, "errno", None) == 13:
                raise ConnectorAuthError("SFTP permission denied") from exc
            raise ConnectorTransientError(str(exc)) from exc

    def _walk(
        self,
        sftp: paramiko.SFTPClient,
        start_path: str,
        since_ts: float | None,
    ) -> Iterator[tuple[str, paramiko.SFTPAttributes]]:
        stack = [start_path]
        while stack:
            current = stack.pop()
            try:
                entries = sftp.listdir_attr(current)
            except OSError as exc:
                if getattr(exc, "errno", None) == 13:
                    logger.warning("⚠️ [SFTP] Permission denied: %s", current)
                    continue
                raise ConnectorTransientError(str(exc)) from exc

            for attrs in entries:
                if attrs.filename in (".", ".."):
                    continue
                full_path = posixpath.join(current, attrs.filename)
                if stat.S_ISDIR(attrs.st_mode):
                    stack.append(full_path)
                    continue
                if since_ts and attrs.st_mtime < since_ts:
                    continue
                yield full_path, attrs

    def _read_file(self, sftp: paramiko.SFTPClient, path: str, attrs: paramiko.SFTPAttributes) -> bytes:
        try:
            with sftp.open(path, "rb") as remote_file:
                if attrs.st_size and attrs.st_size > SFTP_PREFETCH_THRESHOLD_BYTES:
                    remote_file.prefetch()
                buffer = io.BytesIO()
                while True:
                    chunk = remote_file.read(1024 * 1024)
                    if not chunk:
                        break
                    buffer.write(chunk)
                return buffer.getvalue()
        except OSError as exc:
            if getattr(exc, "errno", None) == 13:
                raise ConnectorAuthError("SFTP permission denied") from exc
            raise ConnectorTransientError(str(exc)) from exc

    def _build_source_document(
        self,
        sftp: paramiko.SFTPClient,
        path: str,
        attrs: paramiko.SFTPAttributes,
        config: dict,
    ) -> SourceDocument:
        content = self._read_file(sftp, path, attrs)
        filename = posixpath.basename(path)
        parent_id = posixpath.dirname(path)

        mime_type = "application/octet-stream"
        try:
            import mimetypes
            guessed, _ = mimetypes.guess_type(filename)
            if guessed:
                mime_type = guessed
        except Exception:
            pass

        return SourceDocument(
            content=content,
            metadata={
                "source": "sftp",
                "path": path,
                "host": config.get("host"),
                "port": config.get("port", SFTP_DEFAULT_PORT),
                "root_path": config.get("root_path", "/"),
                "modified_at": self._to_datetime(attrs.st_mtime).isoformat() if attrs.st_mtime else None,
                "size": attrs.st_size,
            },
            source_type=SourceType.SFTP,
            source_id=path,
            filename=filename,
            mime_type=mime_type,
            size_bytes=len(content),
            parent_id=parent_id,
        )

    @staticmethod
    def _to_datetime(timestamp: float | int | None) -> Optional[datetime]:
        if not timestamp:
            return None
        return datetime.fromtimestamp(timestamp, tz=timezone.utc)
