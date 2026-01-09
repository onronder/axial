
import os
import pytest
import datetime
import uuid
from jose import jwt
from supabase import create_client, Client, ClientOptions
from dotenv import dotenv_values

# Load real environment variables from .env directly into a dict
# This bypasses any os.environ manipulation done by conftest.py fixtures
env_config = dotenv_values(os.path.join(os.path.dirname(__file__), "../../../.env"))

if os.getenv("RUN_INTEGRATION_TESTS") != "1":
    pytest.skip("Set RUN_INTEGRATION_TESTS=1 to run Supabase-backed security tests.", allow_module_level=True)

def get_real_env_var(key):
    return env_config.get(key)

@pytest.mark.security
def test_authenticated_user_cannot_insert_documents_directly():
    """
    Security Penetration Test:
    Verify that an authenticated user using the Supabase Client (bypassing the backend API)
    CANNOT insert directly into the 'documents' table.
    
    This tests Row Level Security (RLS) policies.
    """
    
    # 1. Setup Configuration
    # env_path debug removed for cleanup

    supabase_url = get_real_env_var("SUPABASE_URL")
    # Try common names for the Anon/Public key
    supabase_key = (
        get_real_env_var("SUPABASE_ANON_KEY") or 
        get_real_env_var("SUPABASE_KEY") or 
        get_real_env_var("SUPABASE_PUBLISHABLE_KEY")
    )
    jwt_secret = get_real_env_var("SUPABASE_JWT_SECRET")

    if not supabase_url or not supabase_key or not jwt_secret:
        pytest.skip("Missing SUPABASE_URL, SUPABASE_KEY, or SUPABASE_JWT_SECRET in .env. Cannot run security test.")

    # 2. Forge a User JWT (Standard authenticated user)
    # This simulates a user who has logged in and has a valid token
    user_id = str(uuid.uuid4())
    payload = {
        "sub": user_id,
        "aud": "authenticated",
        "role": "authenticated",
        "email": "security_test@example.com",
        "exp": datetime.datetime.now(datetime.timezone.utc) + datetime.timedelta(hours=1)
    }
    
    # Sign the token using the project's secret
    token = jwt.encode(payload, jwt_secret, algorithm="HS256")

    # 3. Initialize Supabase Client with user's token
    # We pass the token in headers to simulate an authenticated request
    options = ClientOptions(headers={"Authorization": f"Bearer {token}"})
    client: Client = create_client(supabase_url, supabase_key, options=options)

    # 4. Attempt to Insert a Fake Record
    fake_document = {
        "user_id": user_id,  # Trying to insert for themselves
        "title": "HACKED DOCUMENT",
        "source_type": "file_upload",
        "metadata": {"origin": "security_test"},
        "created_at": datetime.datetime.now(datetime.timezone.utc).isoformat(),
    }

    print(f"\n[Security Test] Attempting Direct Insert into 'documents' table as user {user_id}...")

    try:
        # Provide count='exact' to get confirmation of insert
        response = client.table("documents").insert(fake_document).execute()

        # 5. Analyze Result
        # If we reach here and got data back, the insert SUCCEEDED (Security Flaw)
        if response.data and len(response.data) > 0:
            inserted_id = response.data[0].get('id')
            print(f"\n❌ [FAIL] RLS Violation Detected! Document inserted successfully. ID: {inserted_id}")

            # Cleanup if possible
            try:
                client.table("documents").delete().eq("id", inserted_id).execute()
                print(f"   [Cleanup] Deleted inserted record {inserted_id}.")
            except Exception as e:
                print(f"   [Cleanup] Failed to delete record: {e}")

            # Fail the test
            pytest.fail("Security Violation: Authenticated user was able to INSERT into 'documents' table directly.")

        pytest.fail("Security Violation: Insert returned without error but no data was returned.")
    except Exception as e:
        # If Supabase returns an error (expected 403/401/etc), we might catch it here
        # supabase-py might raise an exception on error responses
        error_msg = str(e)
        if "policy" in error_msg.lower() or "permission denied" in error_msg.lower() or "403" in error_msg:
            print(f"\n✅ [PASS] Security Verified. Insert blocked: {error_msg}")
        else:
            pytest.fail(f"Unexpected error when validating RLS: {error_msg}")
