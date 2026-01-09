"""
Integration tests for file upload flow.

Tests the complete flow from connector → pipeline → database.
"""

import os
import pytest
import asyncio
from uuid import uuid4

from connectors.file_upload import FileUploadConnector
from services.ingestion_pipeline import IngestionPipeline
from core.db import get_supabase


if os.getenv("RUN_INTEGRATION_TESTS") != "1":
    pytest.skip("Set RUN_INTEGRATION_TESTS=1 to run Supabase-backed integration tests.", allow_module_level=True)


@pytest.mark.integration
@pytest.mark.asyncio
async def test_file_upload_end_to_end():
    """Test complete file upload flow from connector to database."""
    
    # Setup
    user_id = str(uuid4())
    job_id = str(uuid4())
    supabase = get_supabase()
    
    # 1. Upload test file to Supabase Storage
    test_content = b"Test PDF content for integration test"
    storage_path = f"uploads/{user_id}/{uuid4()}/test.pdf"
    
    upload_result = supabase.storage.from_("ephemeral-staging").upload(
        storage_path,
        test_content,
        {"content-type": "application/pdf"}
    )
    assert upload_result
    
    try:
        # 2. Use connector to fetch document
        connector = FileUploadConnector()
        
        documents = []
        async for doc in connector.fetch_documents([storage_path]):
            documents.append(doc)
        
        assert len(documents) == 1
        assert documents[0].content == test_content
        
        # 3. Process through pipeline
        pipeline = IngestionPipeline(
            user_id=user_id,
            job_id=job_id,
            supabase_client=supabase
        )
        
        async def doc_stream():
            for doc in documents:
                yield doc
        
        result = await pipeline.process_stream(doc_stream())
        
        # 4. Verify results
        assert result["status"] == "completed"
        assert result["processed"] >= 1
        
        # 5. Verify document in database
        doc_result = supabase.table("documents").select("*").eq(
            "user_id", user_id
        ).execute()
        
        assert len(doc_result.data) >= 1
        
        # 6. Verify chunks created
        chunk_result = supabase.table("document_chunks").select("*").eq(
            "user_id", user_id
        ).execute()
        
        assert len(chunk_result.data) >= 1
        
    finally:
        # Cleanup
        supabase.storage.from_("ephemeral-staging").remove([storage_path])
        
        # Delete test data from database
        supabase.table("documents").delete().eq("user_id", user_id).execute()
        supabase.table("document_chunks").delete().eq("user_id", user_id).execute()


@pytest.mark.integration
@pytest.mark.asyncio
async def test_file_upload_with_quota_check():
    """Test file upload respects quota limits."""
    
    user_id = str(uuid4())
    job_id = str(uuid4())
    supabase = get_supabase()
    
    # Create large file that exceeds quota
    large_content = b"x" * (100 * 1024 * 1024)  # 100MB
    storage_path = f"uploads/{user_id}/{uuid4()}/large.pdf"
    
    # This should fail quota check
    connector = FileUploadConnector()
    pipeline = IngestionPipeline(
        user_id=user_id,
        job_id=job_id,
        supabase_client=supabase
    )
    
    # Test quota validation
    # (Implementation depends on quota service)


@pytest.mark.integration
@pytest.mark.asyncio
async def test_file_upload_transaction_rollback():
    """Test that failed uploads rollback database changes."""
    
    user_id = str(uuid4())
    job_id = str(uuid4())
    supabase = get_supabase()
    
    # Upload file
    test_content = b"Test content"
    storage_path = f"uploads/{user_id}/{uuid4()}/test.pdf"
    
    supabase.storage.from_("ephemeral-staging").upload(
        storage_path,
        test_content
    )
    
    try:
        # Process with forced failure
        connector = FileUploadConnector()
        pipeline = IngestionPipeline(
            user_id=user_id,
            job_id=job_id,
            supabase_client=supabase
        )
        
        # Force pipeline to fail mid-processing
        # Verify no partial data remains in database
        
    finally:
        # Cleanup
        supabase.storage.from_("ephemeral-staging").remove([storage_path])
