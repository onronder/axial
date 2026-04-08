#!/usr/bin/env python3
"""
Backfill document_chunks.content_search for a single organization.

This script:
- reads encrypted chunk content through the existing Supabase client
- decrypts content in application memory via Ghost Protocol
- updates only the content_search TSVECTOR via RPC

Plaintext is never written back to a persistent table.
"""

import argparse
import os
import sys
from typing import Any

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from dotenv import load_dotenv

load_dotenv()

from core.db import get_supabase
from core.security import UnencryptedContentError, decrypt_text


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Backfill content_search with to_tsvector('simple', ...)",
    )
    parser.add_argument(
        "--org-id",
        required=True,
        help="Organization UUID to backfill",
    )
    parser.add_argument(
        "--batch-size",
        type=int,
        default=100,
        help="Number of chunks to fetch per batch (default: 100)",
    )
    parser.add_argument(
        "--limit",
        type=int,
        default=None,
        help="Optional maximum number of chunks to process",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Decrypt and validate batches without updating content_search",
    )
    parser.add_argument(
        "--fail-fast",
        action="store_true",
        help="Exit immediately on the first non-legacy error",
    )
    args = parser.parse_args()

    if args.batch_size <= 0:
        parser.error("--batch-size must be greater than 0")
    if args.limit is not None and args.limit <= 0:
        parser.error("--limit must be greater than 0 when provided")

    return args


def fetch_chunk_batch(
    supabase: Any,
    organization_id: str,
    batch_size: int,
    last_seen_id: str | None,
) -> list[dict[str, Any]]:
    query = (
        supabase.table("document_chunks")
        .select("id, content, document_id, documents!inner(id, organization_id)")
        .eq("documents.organization_id", organization_id)
        .order("id")
        .range(0, batch_size - 1)
    )

    if last_seen_id:
        query = query.gt("id", last_seen_id)

    response = query.execute()
    return response.data or []


def backfill_content_search(
    organization_id: str,
    batch_size: int,
    limit: int | None = None,
    dry_run: bool = False,
    fail_fast: bool = False,
) -> int:
    supabase = get_supabase()

    total_seen = 0
    total_completed = 0
    total_failed = 0
    total_unencrypted = 0
    last_seen_id: str | None = None

    while True:
        remaining = None if limit is None else limit - total_seen
        if remaining is not None and remaining <= 0:
            break

        current_batch_size = batch_size if remaining is None else min(batch_size, remaining)
        rows = fetch_chunk_batch(supabase, organization_id, current_batch_size, last_seen_id)
        if not rows:
            break

        for row in rows:
            chunk_id = row["id"]
            last_seen_id = chunk_id
            total_seen += 1

            try:
                plaintext = decrypt_text(row.get("content") or "")

                if not dry_run:
                    supabase.rpc(
                        "update_content_search_simple",
                        {
                            "chunk_id": chunk_id,
                            "plaintext": plaintext,
                        },
                    ).execute()

                total_completed += 1
            except UnencryptedContentError as exc:
                total_unencrypted += 1
                print(
                    f"SKIP chunk_id={chunk_id} reason=unencrypted_content detail={exc}"
                )
                if fail_fast:
                    print("Aborting because --fail-fast is enabled.")
                    return 1
            except Exception as exc:
                total_failed += 1
                print(
                    f"ERROR chunk_id={chunk_id} type={type(exc).__name__} detail={exc}"
                )
                if fail_fast:
                    print("Aborting because --fail-fast is enabled.")
                    return 1

        print(
            "Progress: "
            f"seen={total_seen} completed={total_completed} "
            f"unencrypted={total_unencrypted} failed={total_failed}"
        )

    mode = "dry-run" if dry_run else "write"
    print(
        "Completed: "
        f"mode={mode} seen={total_seen} completed={total_completed} "
        f"unencrypted={total_unencrypted} failed={total_failed}"
    )

    if total_unencrypted:
        print(
            "Note: unencrypted rows were skipped under STRICT_ENCRYPTION_MODE. "
            "If these are expected legacy rows, rerun with STRICT_ENCRYPTION_MODE=false."
        )

    return 1 if total_failed else 0


def main() -> int:
    args = parse_args()
    return backfill_content_search(
        organization_id=args.org_id,
        batch_size=args.batch_size,
        limit=args.limit,
        dry_run=args.dry_run,
        fail_fast=args.fail_fast,
    )


if __name__ == "__main__":
    raise SystemExit(main())
