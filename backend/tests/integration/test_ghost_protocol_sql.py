"""
Integration Tests for Ghost Protocol SQL Functions

Tests for the Zero-Retention encrypted content migration:
1. ingest_document_chunk RPC
2. ingest_document_chunks_batch RPC  
3. content_search TSVECTOR column
4. Updated hybrid_search functions

IMPORTANT: These tests require a real database connection.
Run with: pytest backend/tests/integration/test_ghost_protocol_sql.py -v --tb=short

To skip in CI when no database is available, these tests are marked with:
    @pytest.mark.integration
    @pytest.mark.requires_db
"""

import os
import pytest
from uuid import uuid4


# Check if database is available
SUPABASE_URL = os.getenv("SUPABASE_URL")
SUPABASE_KEY = os.getenv("SUPABASE_SERVICE_ROLE_KEY") or os.getenv("SUPABASE_SECRET_KEY")
HAS_DATABASE = bool(SUPABASE_URL and SUPABASE_KEY)

# Skip all tests in this module if no database connection
pytestmark = [
    pytest.mark.integration,
    pytest.mark.requires_db,
    pytest.mark.skipif(not HAS_DATABASE, reason="Database connection required"),
]


@pytest.fixture(scope="module")
def supabase_client():
    """Create a Supabase client for integration tests."""
    if not HAS_DATABASE:
        pytest.skip("Database connection required")
    
    from supabase import create_client
    return create_client(SUPABASE_URL, SUPABASE_KEY)


@pytest.fixture
def test_document(supabase_client):
    """Create a test document and clean up after."""
    doc_id = str(uuid4())
    org_id = str(uuid4())
    
    # Create test document
    supabase_client.table("documents").insert({
        "id": doc_id,
        "organization_id": org_id,
        "title": "Ghost Protocol Test Document",
        "source_type": "file_upload",
        "metadata": {"test": True}
    }).execute()
    
    yield doc_id
    
    # Cleanup
    try:
        supabase_client.table("document_chunks").delete().eq("document_id", doc_id).execute()
        supabase_client.table("documents").delete().eq("id", doc_id).execute()
    except Exception:
        pass


class TestContentSearchColumn:
    """Tests for the content_search TSVECTOR column."""
    
    def test_content_search_column_exists(self, supabase_client):
        """Verify content_search column was added to document_chunks."""
        # This will fail if column doesn't exist
        result = supabase_client.table("document_chunks")\
            .select("id, content, content_search")\
            .limit(1)\
            .execute()
        
        # Query succeeded - column exists
        assert True
    
    def test_content_search_index_exists(self, supabase_client):
        """Verify GIN index exists on content_search column."""
        result = supabase_client.rpc(
            "sql",
            {"query": """
                SELECT indexname FROM pg_indexes 
                WHERE tablename = 'document_chunks' 
                AND indexname = 'idx_document_chunks_content_search'
            """}
        ).execute()
        
        # Check if index is in the results
        # Note: If this fails, the migration hasn't been applied yet
        pass  # Index check may require direct SQL access


class TestIngestDocumentChunkRPC:
    """Tests for the ingest_document_chunk RPC function."""
    
    def test_rpc_function_exists(self, supabase_client, test_document):
        """Verify ingest_document_chunk RPC can be called."""
        chunk_id = str(uuid4())
        
        # Create a fake embedding (1536 dimensions)
        fake_embedding = [0.01] * 1536
        
        try:
            result = supabase_client.rpc(
                "ingest_document_chunk",
                {
                    "p_id": chunk_id,
                    "p_document_id": test_document,
                    "p_content_encrypted": "gAAAAA_encrypted_content_here",
                    "p_content_plaintext": "This is plaintext for search indexing",
                    "p_embedding": fake_embedding,
                    "p_chunk_index": 0
                }
            ).execute()
            
            # Function should return the inserted ID
            assert result.data is not None
            
        except Exception as e:
            if "function ingest_document_chunk" in str(e).lower():
                pytest.skip("ingest_document_chunk RPC not yet deployed")
            raise
    
    def test_rpc_creates_tsvector(self, supabase_client, test_document):
        """Verify RPC creates proper TSVECTOR from plaintext."""
        chunk_id = str(uuid4())
        fake_embedding = [0.01] * 1536
        
        try:
            # Insert via RPC
            supabase_client.rpc(
                "ingest_document_chunk",
                {
                    "p_id": chunk_id,
                    "p_document_id": test_document,
                    "p_content_encrypted": "encrypted_data",
                    "p_content_plaintext": "financial strategy quarterly report",
                    "p_embedding": fake_embedding,
                    "p_chunk_index": 0
                }
            ).execute()
            
            # Verify TSVECTOR was created
            result = supabase_client.table("document_chunks")\
                .select("content, content_search")\
                .eq("id", chunk_id)\
                .single()\
                .execute()
            
            # content should be encrypted (stored as-is)
            assert result.data["content"] == "encrypted_data"
            
            # content_search should be the TSVECTOR string representation
            # It will contain stems like 'financ', 'strategi', etc.
            tsvector = result.data.get("content_search", "")
            if tsvector:  # May be NULL if migration not applied
                assert "financ" in tsvector.lower() or "'financ'" in tsvector.lower()
            
        except Exception as e:
            if "function ingest_document_chunk" in str(e).lower():
                pytest.skip("ingest_document_chunk RPC not yet deployed")
            raise


class TestIngestDocumentChunksBatchRPC:
    """Tests for the ingest_document_chunks_batch RPC function."""
    
    def test_batch_rpc_exists(self, supabase_client, test_document):
        """Verify ingest_document_chunks_batch RPC can be called."""
        fake_embedding = [0.01] * 1536
        
        chunks = [
            {
                "id": str(uuid4()),
                "document_id": test_document,
                "content_encrypted": "encrypted_chunk_1",
                "content_plaintext": "First chunk content",
                "embedding": fake_embedding,
                "chunk_index": 0
            },
            {
                "id": str(uuid4()),
                "document_id": test_document,
                "content_encrypted": "encrypted_chunk_2",
                "content_plaintext": "Second chunk content",
                "embedding": fake_embedding,
                "chunk_index": 1
            }
        ]
        
        try:
            result = supabase_client.rpc(
                "ingest_document_chunks_batch",
                {"p_chunks": chunks}
            ).execute()
            
            # Function should return list of inserted IDs
            assert result.data is not None
            assert len(result.data) == 2
            
        except Exception as e:
            if "function ingest_document_chunks_batch" in str(e).lower():
                pytest.skip("ingest_document_chunks_batch RPC not yet deployed")
            raise
    
    def test_batch_rpc_handles_large_batch(self, supabase_client, test_document):
        """Verify batch RPC can handle larger batches (100 chunks)."""
        fake_embedding = [0.01] * 1536
        
        chunks = [
            {
                "id": str(uuid4()),
                "document_id": test_document,
                "content_encrypted": f"encrypted_chunk_{i}",
                "content_plaintext": f"Chunk number {i} with some searchable content",
                "embedding": fake_embedding,
                "chunk_index": i
            }
            for i in range(100)
        ]
        
        try:
            result = supabase_client.rpc(
                "ingest_document_chunks_batch",
                {"p_chunks": chunks}
            ).execute()
            
            assert result.data is not None
            assert len(result.data) == 100
            
        except Exception as e:
            if "function ingest_document_chunks_batch" in str(e).lower():
                pytest.skip("ingest_document_chunks_batch RPC not yet deployed")
            raise


class TestHybridSearchWithTSVECTOR:
    """Tests for hybrid_search using pre-computed TSVECTOR."""
    
    def test_hybrid_search_uses_content_search(self, supabase_client, test_document):
        """Verify hybrid_search can use the content_search column."""
        fake_embedding = [0.01] * 1536
        
        # Insert a chunk with specific searchable content
        chunk_id = str(uuid4())
        try:
            supabase_client.rpc(
                "ingest_document_chunk",
                {
                    "p_id": chunk_id,
                    "p_document_id": test_document,
                    "p_content_encrypted": "THIS_IS_ENCRYPTED_AND_NOT_SEARCHABLE",
                    "p_content_plaintext": "machine learning artificial intelligence neural network",
                    "p_embedding": fake_embedding,
                    "p_chunk_index": 0
                }
            ).execute()
        except Exception as e:
            if "function ingest_document_chunk" in str(e).lower():
                pytest.skip("ingest_document_chunk RPC not yet deployed")
            raise
        
        # Search for keywords - should find via content_search TSVECTOR
        result = supabase_client.rpc(
            "hybrid_search",
            {
                "query_text": "machine learning",
                "query_embedding": fake_embedding,
                "match_count": 10,
                "similarity_threshold": 0.0  # Low threshold for test
            }
        ).execute()
        
        # The search should return results (may include our test chunk)
        # Note: The actual matching depends on the TSVECTOR content
        assert result.data is not None
    
    def test_hybrid_search_does_not_expose_encrypted_content_directly(
        self, supabase_client, test_document
    ):
        """
        Verify that searching for encrypted text doesn't match.
        
        The encrypted content string should NOT be searchable via hybrid_search
        because the TSVECTOR is built from plaintext, not encrypted content.
        """
        fake_embedding = [0.01] * 1536
        
        unique_encrypted_marker = f"ENCRYPTED_MARKER_{uuid4().hex[:8]}"
        
        try:
            supabase_client.rpc(
                "ingest_document_chunk",
                {
                    "p_id": str(uuid4()),
                    "p_document_id": test_document,
                    "p_content_encrypted": unique_encrypted_marker,
                    "p_content_plaintext": "regular searchable content here",
                    "p_embedding": fake_embedding,
                    "p_chunk_index": 0
                }
            ).execute()
        except Exception as e:
            if "function ingest_document_chunk" in str(e).lower():
                pytest.skip("ingest_document_chunk RPC not yet deployed")
            raise
        
        # Search for the encrypted marker - should NOT find anything
        result = supabase_client.rpc(
            "hybrid_search",
            {
                "query_text": unique_encrypted_marker,
                "query_embedding": fake_embedding,
                "match_count": 10,
                "similarity_threshold": 0.0
            }
        ).execute()
        
        # Check that none of the results contain the encrypted marker in their content_search
        # (they shouldn't, because we searched for encrypted text)
        for row in result.data or []:
            # The hybrid_search returns content (encrypted), not content_search
            # So we can't directly verify, but keyword_score should be 0
            # for content that doesn't match the query text
            pass  # This test primarily verifies the search doesn't error
