import datetime
import os
import uuid

import pytest
from dotenv import dotenv_values
from jose import jwt
from supabase import Client, ClientOptions, create_client


env_config = dotenv_values(os.path.join(os.path.dirname(__file__), "../../../.env"))

if os.getenv("RUN_INTEGRATION_TESTS") != "1":
    pytest.skip("Set RUN_INTEGRATION_TESTS=1 to run Supabase-backed security tests.", allow_module_level=True)


def get_real_env_var(key: str):
    return env_config.get(key)


def build_user_client(
    supabase_url: str,
    supabase_anon_key: str,
    jwt_secret: str,
    user_id: str,
) -> Client:
    payload = {
        "sub": user_id,
        "aud": "authenticated",
        "role": "authenticated",
        "email": f"{user_id}@example.com",
        "exp": datetime.datetime.now(datetime.timezone.utc) + datetime.timedelta(hours=1),
    }
    token = jwt.encode(payload, jwt_secret, algorithm="HS256")
    options = ClientOptions(headers={"Authorization": f"Bearer {token}"})
    return create_client(supabase_url, supabase_anon_key, options=options)


@pytest.mark.security
def test_rls_blocks_cross_tenant_document_reads():
    supabase_url = get_real_env_var("SUPABASE_URL")
    supabase_anon_key = (
        get_real_env_var("SUPABASE_ANON_KEY")
        or get_real_env_var("SUPABASE_KEY")
        or get_real_env_var("SUPABASE_PUBLISHABLE_KEY")
    )
    supabase_service_key = (
        get_real_env_var("SUPABASE_SECRET_KEY")
        or get_real_env_var("SUPABASE_SERVICE_ROLE_KEY")
        or get_real_env_var("SUPABASE_SERVICE_KEY")
    )
    jwt_secret = get_real_env_var("SUPABASE_JWT_SECRET")

    if not supabase_url or not supabase_anon_key or not supabase_service_key or not jwt_secret:
        pytest.skip(
            "Missing SUPABASE_URL, SUPABASE_ANON_KEY, SUPABASE_SECRET_KEY, or SUPABASE_JWT_SECRET in .env."
        )

    service_client = create_client(supabase_url, supabase_service_key)
    user_a_id = str(uuid.uuid4())
    user_b_id = str(uuid.uuid4())
    organization_id = user_a_id

    doc_id = None
    try:
        insert_result = service_client.table("documents").insert(
            {
                "user_id": user_a_id,
                "organization_id": organization_id,
                "title": "RLS cross-tenant test",
                "source_type": "file_upload",
                "metadata": {"origin": "security_test"},
            }
        ).execute()

        assert insert_result.data, "Expected service role insert to return data"
        doc_id = insert_result.data[0]["id"]

        user_a_client = build_user_client(
            supabase_url,
            supabase_anon_key,
            jwt_secret,
            user_a_id,
        )
        user_b_client = build_user_client(
            supabase_url,
            supabase_anon_key,
            jwt_secret,
            user_b_id,
        )

        response_a = user_a_client.table("documents").select("id").eq("id", doc_id).execute()
        assert response_a.data and len(response_a.data) == 1, "Owner should be able to read their document"

        try:
            response_b = user_b_client.table("documents").select("id").eq("id", doc_id).execute()
            assert not response_b.data, "Non-owner should not see the document"
        except Exception as exc:
            error_msg = str(exc).lower()
            if "policy" not in error_msg and "permission" not in error_msg and "403" not in error_msg:
                raise
    finally:
        if doc_id:
            service_client.table("documents").delete().eq("id", doc_id).execute()
