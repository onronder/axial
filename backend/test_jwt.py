import time
import jwt


def build_expired_token(secret: str = "secret", now: float | None = None) -> str:
    """Build an expired JWT for local verification testing."""
    timestamp = int(now if now is not None else time.time())
    payload = {
        "sub": "1234567890",
        "name": "John Doe",
        "exp": timestamp - 3600,
    }
    return jwt.encode(payload, secret, algorithm="HS256")


def decode_token(token: str) -> dict:
    """Decode a JWT without verifying the signature."""
    try:
        decoded = jwt.decode(token, options={"verify_signature": False})
        return {"decoded": decoded}
    except Exception as exc:
        return {"error": f"{type(exc).__name__}: {exc}"}


def run_demo():
    token = build_expired_token()
    print(f"Testing expired token: {token}")

    print("Attempting decode with verify_signature=False...")
    result = decode_token(token)
    if "decoded" in result:
        print(f"Success! Decoded: {result['decoded']}")
    else:
        print(f"Failed: {result['error']}")

    return result


if __name__ == "__main__":
    run_demo()
