# Backend Load Testing

This directory contains load testing scripts using [Locust](https://locust.io/).

## Prerequisites

Ensure `locust` is installed:
```bash
pip install locust
```
(It is already included in `requirements.txt`)

## Running the Load Test

Run the following command from the `backend/` directory:

```bash
locust -f tests/load/locustfile.py --host=http://localhost:8000
```

Then open your browser at [http://localhost:8089](http://localhost:8089) to configure the user count and spawn rate.

### Required environment variables

Set these in your shell or `.env` before running:

- `SUPABASE_URL`
- `SUPABASE_PUBLISHABLE_KEY` or `SUPABASE_ANON_KEY`
- `LOAD_TEST_EMAIL`
- `LOAD_TEST_PASSWORD`

### Headless Mode (CI/CLI)

To run without the web UI (e.g., for automated verification):

```bash
locust -f tests/load/locustfile.py --headless -u 10 -r 2 -t 1m --host=http://localhost:8000
```

- `-u`: Number of users (10)
- `-r`: Spawn rate (2 users/second)
- `-t`: Run duration (1 minute)

## Benchmark Runner (Drive + Web)

Use the benchmark script to run datasets A-D and the web crawl pack:

```bash
python tests/load/run_benchmarks.py
```

Required env vars:
- `API_BASE_URL` (e.g. https://axial-production-1503.up.railway.app)
- `SUPABASE_URL`
- `SUPABASE_PUBLISHABLE_KEY` or `SUPABASE_ANON_KEY`
- `LOAD_TEST_EMAIL` and `LOAD_TEST_PASSWORD` (if not using JWT)
- `LOAD_TEST_JWT` (optional: bypass password login)
- `BENCH_DATASET_A_ID`
- `BENCH_DATASET_B_ID`
- `BENCH_DATASET_C_ID`
- `BENCH_DATASET_D_ID`
- `BENCH_WEB_URLS` (comma-separated)

Optional:
- `BENCH_RESULTS_DIR` (default: TEST_RESULTS)
