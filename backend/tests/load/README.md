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

### Headless Mode (CI/CLI)

To run without the web UI (e.g., for automated verification):

```bash
locust -f tests/load/locustfile.py --headless -u 10 -r 2 -t 1m --host=http://localhost:8000
```

- `-u`: Number of users (10)
- `-r`: Spawn rate (2 users/second)
- `-t`: Run duration (1 minute)
