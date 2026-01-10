import json
import requests


DEFAULT_URL = "http://127.0.0.1:8000/api/v1/uploads/upload-url"
DUMMY_TOKEN = (
    "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9."
    "eyJzdWIiOiIxMjM0NTY3ODkwIiwibmFtZSI6IkpvaG4gRG9lIiwiaWF0IjoxNTE2MjM5MDIyfQ."
    "SflKxwRJSMeKKF2QT4fwpMeJf36POk6yJV_adQssw5c"
)


def run_requests(
    *,
    url: str = DEFAULT_URL,
    requests_module=requests,
    print_fn=print,
):
    """Send malformed and dummy JWT requests for debugging."""
    data = {"filename": "test.txt", "file_type": "text/plain", "file_size": 4}
    results = []

    print_fn("--- Sending MALFORMED token ---")
    headers = {"Authorization": "Bearer bad.token"}
    try:
        resp = requests_module.post(url, headers=headers, json=data)
        print_fn(f"Status: {resp.status_code}")
        print_fn(f"Body: {resp.text}")
        results.append({"status_code": resp.status_code, "text": resp.text})
    except Exception as exc:
        print_fn(f"Request failed: {exc}")
        results.append({"error": str(exc)})

    print_fn("\n--- Sending DUMMY token (valid structure, invalid signature) ---")
    headers = {"Authorization": f"Bearer {DUMMY_TOKEN}"}
    try:
        resp = requests_module.post(url, headers=headers, json=data)
        print_fn(f"Status: {resp.status_code}")
        print_fn(f"Body: {resp.text}")
        results.append({"status_code": resp.status_code, "text": resp.text})
    except Exception as exc:
        print_fn(f"Request failed: {exc}")
        results.append({"error": str(exc)})

    return results


if __name__ == "__main__":
    run_requests()
