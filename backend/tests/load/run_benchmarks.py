import json
import os
import sys
import time
from datetime import datetime, timezone
from typing import Dict, List, Optional

import requests
from dotenv import load_dotenv


def _get_env(name: str) -> str:
    value = os.getenv(name)
    if not value:
        raise RuntimeError(f"Missing required env var: {name}")
    return value


def _auth_token(supabase_url: str, supabase_key: str, email: str, password: str) -> str:
    auth_url = f"{supabase_url}/auth/v1/token?grant_type=password"
    response = requests.post(
        auth_url,
        headers={"apikey": supabase_key, "Content-Type": "application/json"},
        json={"email": email, "password": password},
        timeout=30,
    )
    if response.status_code >= 400:
        try:
            detail = response.json()
        except Exception:
            detail = response.text
        raise RuntimeError(f"Supabase auth failed ({response.status_code}): {detail}")
    data = response.json()
    token = data.get("access_token")
    if not token:
        raise RuntimeError("Failed to obtain access_token from Supabase auth.")
    return token


def _post_json(url: str, headers: Dict[str, str], payload: Dict[str, object]) -> Dict[str, object]:
    response = requests.post(url, headers=headers, json=payload, timeout=60)
    response.raise_for_status()
    return response.json()


def _get_json(url: str, headers: Dict[str, str]) -> Dict[str, object]:
    response = requests.get(url, headers=headers, timeout=30)
    response.raise_for_status()
    return response.json()


def _poll_job(base_url: str, headers: Dict[str, str], job_id: str, poll_seconds: int = 5) -> Dict[str, object]:
    status_url = f"{base_url}/api/v1/jobs/{job_id}"
    while True:
        job = _get_json(status_url, headers)
        status = job.get("status")
        if status in {"completed", "failed", "cancelled"}:
            return job
        time.sleep(poll_seconds)


def _fetch_job_files(base_url: str, headers: Dict[str, str], job_id: str) -> List[Dict[str, object]]:
    files_url = f"{base_url}/api/v1/jobs/{job_id}/files"
    return _get_json(files_url, headers)


def _parse_timestamp(value: Optional[str]) -> Optional[datetime]:
    if not value:
        return None
    try:
        return datetime.fromisoformat(value.replace("Z", "+00:00"))
    except Exception:
        return None


def _summarize_files(files: List[Dict[str, object]]) -> Dict[str, object]:
    durations = []
    status_counts: Dict[str, int] = {}

    for item in files:
        status = item.get("status") or "unknown"
        status_counts[status] = status_counts.get(status, 0) + 1
        started = _parse_timestamp(item.get("created_at"))
        ended = _parse_timestamp(item.get("updated_at"))
        if started and ended:
            durations.append((ended - started).total_seconds())

    durations.sort()
    summary = {
        "status_counts": status_counts,
        "durations_seconds": durations,
    }
    return summary


def _percentile(values: List[float], pct: float) -> Optional[float]:
    if not values:
        return None
    if pct <= 0:
        return values[0]
    if pct >= 100:
        return values[-1]
    idx = int(round((pct / 100) * (len(values) - 1)))
    return values[idx]


def _run_drive_job(base_url: str, headers: Dict[str, str], dataset_name: str, folder_id: str) -> Dict[str, object]:
    payload = {"item_ids": [folder_id]}
    response = _post_json(f"{base_url}/api/v1/integrations/google_drive/ingest", headers, payload)
    job_id = response.get("job_id")
    if not job_id:
        raise RuntimeError(f"Missing job_id for dataset {dataset_name}: {response}")

    start_time = datetime.now(timezone.utc)
    job = _poll_job(base_url, headers, job_id)
    end_time = datetime.now(timezone.utc)

    files = _fetch_job_files(base_url, headers, job_id)
    summary = _summarize_files(files)
    durations = summary["durations_seconds"]

    return {
        "dataset": dataset_name,
        "job_id": job_id,
        "status": job.get("status"),
        "processed_files": job.get("processed_files"),
        "total_files": job.get("total_files"),
        "job_duration_seconds": (end_time - start_time).total_seconds(),
        "file_status_counts": summary["status_counts"],
        "file_duration_p50": _percentile(durations, 50),
        "file_duration_p95": _percentile(durations, 95),
        "file_duration_p99": _percentile(durations, 99),
    }


def _run_web_crawl(base_url: str, headers: Dict[str, str], url: str, crawl_type: str, max_depth: int = 1, max_pages: int = 50) -> Dict[str, object]:
    payload = {
        "url": url,
        "crawl_type": crawl_type,
        "max_depth": max_depth,
        "max_pages": max_pages,
        "respect_robots": True,
        "allow_subdomains": False,
    }
    try:
        response = _post_json(f"{base_url}/api/v1/integrations/web/crawl", headers, payload)
    except requests.HTTPError as exc:
        status_code = getattr(exc.response, "status_code", None)
        error_text = getattr(exc.response, "text", None)
        return {
            "url": url,
            "crawl_type": crawl_type,
            "status": "error",
            "error": f"HTTP {status_code}" if status_code else "HTTP error",
            "detail": error_text,
        }
    except Exception as exc:
        return {
            "url": url,
            "crawl_type": crawl_type,
            "status": "error",
            "error": str(exc),
        }
    return {
        "url": url,
        "crawl_type": crawl_type,
        "crawl_id": response.get("crawl_id"),
        "task_id": response.get("task_id"),
        "status": response.get("status"),
    }


def main() -> int:
    load_dotenv()
    base_url = _get_env("API_BASE_URL").rstrip("/")
    supabase_url = _get_env("SUPABASE_URL").rstrip("/")
    supabase_key = os.getenv("SUPABASE_PUBLISHABLE_KEY") or os.getenv("SUPABASE_ANON_KEY")
    if not supabase_key:
        raise RuntimeError("Missing required env var: SUPABASE_PUBLISHABLE_KEY or SUPABASE_ANON_KEY")
    load_test_jwt = os.getenv("LOAD_TEST_JWT")
    email = os.getenv("LOAD_TEST_EMAIL")
    password = os.getenv("LOAD_TEST_PASSWORD")

    datasets = {
        "A": _get_env("BENCH_DATASET_A_ID"),
        "B": _get_env("BENCH_DATASET_B_ID"),
        "C": _get_env("BENCH_DATASET_C_ID"),
        "D": _get_env("BENCH_DATASET_D_ID"),
    }

    web_urls_raw = _get_env("BENCH_WEB_URLS")
    web_urls = [url.strip() for url in web_urls_raw.split(",") if url.strip()]
    if len(web_urls) < 2:
        raise RuntimeError("BENCH_WEB_URLS must include at least 2 URLs.")

    if load_test_jwt:
        token = load_test_jwt
    else:
        if not email or not password:
            raise RuntimeError("Missing LOAD_TEST_EMAIL/LOAD_TEST_PASSWORD or LOAD_TEST_JWT")
        token = _auth_token(supabase_url, supabase_key, email, password)
    headers = {"Authorization": f"Bearer {token}"}

    results = {"datasets": [], "web_crawls": [], "started_at": datetime.now(timezone.utc).isoformat()}
    out_dir = os.getenv("BENCH_RESULTS_DIR", "TEST_RESULTS")
    os.makedirs(out_dir, exist_ok=True)
    stamp = datetime.now(timezone.utc).strftime("%Y%m%d_%H%M%S")
    out_path = os.path.join(out_dir, f"benchmark_{stamp}.json")

    try:
        for name, folder_id in datasets.items():
            try:
                results["datasets"].append(_run_drive_job(base_url, headers, f"Dataset_{name}", folder_id))
            except Exception as exc:
                results["datasets"].append({
                    "dataset": f"Dataset_{name}",
                    "status": "error",
                    "error": str(exc),
                })

        # Web crawl: use sitemap when URL ends in .xml, otherwise recursive
        for url in web_urls:
            crawl_type = "sitemap" if url.endswith(".xml") else "recursive"
            results["web_crawls"].append(_run_web_crawl(base_url, headers, url, crawl_type))
    finally:
        results["finished_at"] = datetime.now(timezone.utc).isoformat()
        with open(out_path, "w", encoding="utf-8") as handle:
            json.dump(results, handle, indent=2)
        print(f"Benchmark results saved to {out_path}")

    return 0


if __name__ == "__main__":
    sys.exit(main())
