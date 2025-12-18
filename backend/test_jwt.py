import jwt
import time

# Create a token that is expired
payload = {
    "sub": "1234567890",
    "name": "John Doe",
    "exp": int(time.time()) - 3600  # Expired 1 hour ago
}
secret = "secret"
token = jwt.encode(payload, secret, algorithm="HS256")

print(f"Testing expired token: {token}")

try:
    print("Attempting decode with verify_signature=False...")
    decoded = jwt.decode(token, options={"verify_signature": False})
    print(f"Success! Decoded: {decoded}")
except Exception as e:
    print(f"Failed: {type(e).__name__}: {e}")
