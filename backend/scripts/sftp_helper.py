#!/usr/bin/env python3
"""
SFTP connector helper for manual verification.

Usage examples:
  python -m backend.scripts.sftp_helper --host sftp.example.com --username user --password pass
  python -m backend.scripts.sftp_helper --host sftp.example.com --username user --private-key ~/.ssh/id_rsa --recursive

Env defaults:
  SFTP_HOST, SFTP_PORT, SFTP_USERNAME, SFTP_PASSWORD, SFTP_PRIVATE_KEY, SFTP_ROOT_PATH
"""

from __future__ import annotations

import argparse
import os
import sys
from datetime import datetime

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if BASE_DIR not in sys.path:
    sys.path.insert(0, BASE_DIR)

from connectors.base import ConnectorAuthError, ConnectorTransientError
from connectors.sftp import SFTPConnector


def _read_private_key(value: str | None) -> str | None:
    if not value:
        return None
    if os.path.isfile(value):
        with open(value, encoding="utf-8") as handle:
            return handle.read()
    return value


def _parse_since(value: str | None) -> datetime | None:
    if not value:
        return None
    try:
        return datetime.fromisoformat(value)
    except ValueError as exc:
        raise SystemExit(f"Invalid --since value: {exc}")


def _build_config(args: argparse.Namespace) -> dict:
    host = args.host or os.getenv("SFTP_HOST")
    username = args.username or os.getenv("SFTP_USERNAME")
    password = args.password or os.getenv("SFTP_PASSWORD")
    private_key_raw = args.private_key or os.getenv("SFTP_PRIVATE_KEY")
    private_key = _read_private_key(private_key_raw)

    port = args.port
    if port is None:
        env_port = os.getenv("SFTP_PORT")
        port = int(env_port) if env_port else 22

    root_path = args.root_path or os.getenv("SFTP_ROOT_PATH") or "/"

    return {
        "host": host,
        "port": port,
        "username": username,
        "password": password,
        "private_key": private_key,
        "root_path": root_path,
        "parent_id": None if args.recursive else (args.parent_id or "root"),
    }


def main() -> int:
    parser = argparse.ArgumentParser(description="SFTP connector helper")
    parser.add_argument("--host", help="SFTP host")
    parser.add_argument("--port", type=int, help="SFTP port (default 22)")
    parser.add_argument("--username", help="SFTP username")
    parser.add_argument("--password", help="SFTP password")
    parser.add_argument("--private-key", help="Private key content or file path")
    parser.add_argument("--root-path", help="Root path (default '/')")
    parser.add_argument("--parent-id", help="Directory path to list (non-recursive)")
    parser.add_argument("--recursive", action="store_true", help="Recursively list files")
    parser.add_argument("--since", help="ISO timestamp filter (e.g. 2026-01-12T00:00:00)")
    parser.add_argument("--list-limit", type=int, default=20, help="Max items to print")
    parser.add_argument("--download-first", action="store_true", help="Download first file")
    parser.add_argument("--allow-private", action="store_true", help="Allow private/localhost hosts (testing only)")

    args = parser.parse_args()
    config = _build_config(args)

    # For local testing: bypass SSRF check if --allow-private is set
    if args.allow_private:
        config["_allow_private"] = True

    missing = [key for key in ("host", "username") if not config.get(key)]
    if missing:
        raise SystemExit(f"Missing required fields: {', '.join(missing)}")
    if not (config.get("password") or config.get("private_key")):
        raise SystemExit("Missing credentials: provide --password or --private-key")

    connector = SFTPConnector()
    since = _parse_since(args.since)

    try:
        files = []
        for item in connector.list_files(config, since=since):
            files.append(item)
            if len(files) >= args.list_limit:
                break

        print(f"Listed {len(files)} item(s).")
        for item in files:
            size = item.size if item.size is not None else "-"
            mime = item.mime_type or ""
            print(f"{item.id}\t{size}\t{mime}")

        if args.download_first:
            file_item = next((f for f in files if f.mime_type != "inode/directory"), None)
            if not file_item:
                print("No file entries available to download.")
                return 0
            content = connector.fetch_file_content(file_item.id, config)
            print(f"Downloaded {file_item.id}: {len(content)} bytes")

    except ValueError as exc:
        print(f"Security error: {exc}", file=sys.stderr)
        return 2
    except ConnectorAuthError as exc:
        print(f"Authentication error: {exc}", file=sys.stderr)
        return 2
    except ConnectorTransientError as exc:
        print(f"Transient error: {exc}", file=sys.stderr)
        return 2

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
