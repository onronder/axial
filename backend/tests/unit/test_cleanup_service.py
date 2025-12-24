"""
Unit Tests for Account Cleanup Service

Tests the AccountCleanupService class for GDPR/CCPA compliant deletion.
Validates deletion from all systems: vectors, storage, database, and auth.
"""

import pytest
from unittest.mock import Mock, patch, AsyncMock, MagicMock
import sys
import os

# Add backend to path for imports
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', '..'))


class TestAccountCleanupServiceInitialization:
    """Tests for AccountCleanupService initialization."""
    
    def test_service_creates_supabase_client(self):
        """Service should initialize with a Supabase client."""
        with patch('services.cleanup.get_supabase') as mock_get_supabase:
            mock_supabase = Mock()
            mock_get_supabase.return_value = mock_supabase
            
            from services.cleanup import AccountCleanupService
            service = AccountCleanupService()
            
            assert service.supabase == mock_supabase


class TestExecuteAccountDeletion:
    """Tests for execute_account_deletion method."""
    
    @pytest.fixture
    def mock_service(self):
        """Create a mocked AccountCleanupService instance."""
        with patch('services.cleanup.get_supabase') as mock_get_supabase:
            mock_supabase = Mock()
            mock_get_supabase.return_value = mock_supabase
            
            from services.cleanup import AccountCleanupService
            service = AccountCleanupService()
            
            # Mock all cleanup methods
            service._cleanup_vectors = AsyncMock(return_value={"deleted": 5, "status": "success"})
            service._cleanup_storage = AsyncMock(return_value={"deleted": 3, "status": "success"})
            service._cleanup_database = AsyncMock(return_value={"status": "success"})
            service._cleanup_auth = AsyncMock(return_value={"status": "success"})
            
            yield service
    
    @pytest.mark.asyncio
    async def test_execute_deletion_calls_all_cleanup_methods(self, mock_service):
        """Should call all cleanup methods in correct order."""
        user_id = "user-123"
        
        results = await mock_service.execute_account_deletion(user_id)
        
        mock_service._cleanup_vectors.assert_called_once_with(user_id)
        mock_service._cleanup_storage.assert_called_once_with(user_id)
        mock_service._cleanup_database.assert_called_once_with(user_id)
        mock_service._cleanup_auth.assert_called_once_with(user_id)
    
    @pytest.mark.asyncio
    async def test_execute_deletion_returns_aggregated_results(self, mock_service):
        """Should return results from all cleanup operations."""
        user_id = "user-123"
        
        results = await mock_service.execute_account_deletion(user_id)
        
        assert results["user_id"] == user_id
        assert results["vector_store"]["deleted"] == 5
        assert results["storage"]["deleted"] == 3
        assert results["database"]["status"] == "success"
        assert results["auth"]["status"] == "success"
    
    @pytest.mark.asyncio
    async def test_execute_deletion_raises_on_critical_failure(self, mock_service):
        """Should raise exception when a critical step fails."""
        mock_service._cleanup_database.side_effect = Exception("Database error")
        
        with pytest.raises(Exception) as exc_info:
            await mock_service.execute_account_deletion("user-123")
        
        assert "Database error" in str(exc_info.value)


class TestVectorCleanup:
    """Tests for _cleanup_vectors method."""
    
    @pytest.fixture
    def service_with_supabase(self):
        """Create service with mocked Supabase."""
        with patch('services.cleanup.get_supabase') as mock_get_supabase:
            mock_supabase = Mock()
            mock_get_supabase.return_value = mock_supabase
            
            from services.cleanup import AccountCleanupService
            service = AccountCleanupService()
            
            yield service, mock_supabase
    
    @pytest.mark.asyncio
    async def test_cleanup_vectors_deletes_document_chunks(self, service_with_supabase):
        """Should delete all document_chunks for the user."""
        service, mock_supabase = service_with_supabase
        
        mock_response = Mock()
        mock_response.data = [{"id": "1"}, {"id": "2"}, {"id": "3"}]
        mock_supabase.table.return_value.delete.return_value.eq.return_value.execute.return_value = mock_response
        
        result = await service._cleanup_vectors("user-123")
        
        mock_supabase.table.assert_called_with("document_chunks")
        mock_supabase.table.return_value.delete.return_value.eq.assert_called_with("user_id", "user-123")
        assert result["deleted"] == 3
        assert result["status"] == "success"
    
    @pytest.mark.asyncio
    async def test_cleanup_vectors_handles_empty_result(self, service_with_supabase):
        """Should handle case where user has no vectors."""
        service, mock_supabase = service_with_supabase
        
        mock_response = Mock()
        mock_response.data = []
        mock_supabase.table.return_value.delete.return_value.eq.return_value.execute.return_value = mock_response
        
        result = await service._cleanup_vectors("user-123")
        
        assert result["deleted"] == 0
        assert result["status"] == "success"
    
    @pytest.mark.asyncio
    async def test_cleanup_vectors_handles_error(self, service_with_supabase):
        """Should return error status on failure."""
        service, mock_supabase = service_with_supabase
        mock_supabase.table.side_effect = Exception("Database connection error")
        
        result = await service._cleanup_vectors("user-123")
        
        assert result["status"] == "error"
        assert "Database connection error" in result["error"]


class TestStorageCleanup:
    """Tests for _cleanup_storage method."""
    
    @pytest.fixture
    def service_with_supabase(self):
        """Create service with mocked Supabase."""
        with patch('services.cleanup.get_supabase') as mock_get_supabase:
            mock_supabase = Mock()
            mock_get_supabase.return_value = mock_supabase
            
            from services.cleanup import AccountCleanupService
            service = AccountCleanupService()
            
            yield service, mock_supabase
    
    @pytest.mark.asyncio
    async def test_cleanup_storage_lists_and_deletes_files(self, service_with_supabase):
        """Should list files and delete them."""
        service, mock_supabase = service_with_supabase
        
        # Mock storage.from_().list()
        mock_storage = Mock()
        mock_supabase.storage.from_.return_value = mock_storage
        mock_storage.list.return_value = [
            {"name": "file1.pdf"},
            {"name": "file2.docx"}
        ]
        mock_storage.remove.return_value = None
        
        result = await service._cleanup_storage("user-123")
        
        mock_supabase.storage.from_.assert_called_with("uploads")
        mock_storage.list.assert_called_with("user-123")
        mock_storage.remove.assert_called_with(["user-123/file1.pdf", "user-123/file2.docx"])
        assert result["deleted"] == 2
        assert result["status"] == "success"
    
    @pytest.mark.asyncio
    async def test_cleanup_storage_handles_empty_bucket(self, service_with_supabase):
        """Should handle case where user has no files."""
        service, mock_supabase = service_with_supabase
        
        mock_storage = Mock()
        mock_supabase.storage.from_.return_value = mock_storage
        mock_storage.list.return_value = []
        
        result = await service._cleanup_storage("user-123")
        
        assert result["deleted"] == 0
        assert result["status"] == "success"
    
    @pytest.mark.asyncio
    async def test_cleanup_storage_handles_nonexistent_bucket(self, service_with_supabase):
        """Should handle case where storage bucket doesn't exist."""
        service, mock_supabase = service_with_supabase
        
        mock_storage = Mock()
        mock_supabase.storage.from_.return_value = mock_storage
        mock_storage.list.side_effect = Exception("Bucket not found")
        
        result = await service._cleanup_storage("user-123")
        
        # Should not raise, just return success with 0 deleted
        assert result["status"] == "success"
        assert result["deleted"] == 0


class TestDatabaseCleanup:
    """Tests for _cleanup_database method."""
    
    @pytest.fixture
    def service_with_supabase(self):
        """Create service with mocked Supabase."""
        with patch('services.cleanup.get_supabase') as mock_get_supabase:
            mock_supabase = Mock()
            mock_get_supabase.return_value = mock_supabase
            
            from services.cleanup import AccountCleanupService
            service = AccountCleanupService()
            
            yield service, mock_supabase
    
    @pytest.mark.asyncio
    async def test_cleanup_database_deletes_all_tables(self, service_with_supabase):
        """Should delete from all user-related tables."""
        service, mock_supabase = service_with_supabase
        
        mock_supabase.table.return_value.delete.return_value.eq.return_value.execute.return_value = Mock(data=[])
        
        result = await service._cleanup_database("user-123")
        
        # Verify all tables are cleaned
        expected_tables = [
            "documents",
            "conversations",
            "notifications",
            "user_integrations",
            "user_profiles",
            "user_notification_settings",
            "ingestion_jobs"
        ]
        
        actual_table_calls = [call[0][0] for call in mock_supabase.table.call_args_list]
        for table in expected_tables:
            assert table in actual_table_calls, f"Table {table} was not cleaned"
        
        assert result["status"] == "success"
    
    @pytest.mark.asyncio
    async def test_cleanup_database_handles_error(self, service_with_supabase):
        """Should return error status on database failure."""
        service, mock_supabase = service_with_supabase
        mock_supabase.table.side_effect = Exception("Connection timeout")
        
        result = await service._cleanup_database("user-123")
        
        assert result["status"] == "error"
        assert "Connection timeout" in result["error"]


class TestAuthCleanup:
    """Tests for _cleanup_auth method."""
    
    @pytest.fixture
    def service_with_supabase(self):
        """Create service with mocked Supabase."""
        with patch('services.cleanup.get_supabase') as mock_get_supabase:
            mock_supabase = Mock()
            mock_get_supabase.return_value = mock_supabase
            
            from services.cleanup import AccountCleanupService
            service = AccountCleanupService()
            
            yield service, mock_supabase
    
    @pytest.mark.asyncio
    async def test_cleanup_auth_deletes_from_supabase_auth(self, service_with_supabase):
        """Should call Supabase admin API to delete user."""
        service, mock_supabase = service_with_supabase
        mock_supabase.auth.admin.delete_user.return_value = Mock()
        
        result = await service._cleanup_auth("user-123")
        
        mock_supabase.auth.admin.delete_user.assert_called_once_with("user-123")
        assert result["status"] == "success"
    
    @pytest.mark.asyncio
    async def test_cleanup_auth_handles_error(self, service_with_supabase):
        """Should return error status on auth deletion failure."""
        service, mock_supabase = service_with_supabase
        mock_supabase.auth.admin.delete_user.side_effect = Exception("Auth service unavailable")
        
        result = await service._cleanup_auth("user-123")
        
        assert result["status"] == "error"
        assert "Auth service unavailable" in result["error"]


class TestCleanupServiceSingleton:
    """Tests for cleanup_service singleton."""
    
    def test_cleanup_service_singleton_exists(self):
        """Should export a singleton instance for easy import."""
        with patch('services.cleanup.get_supabase'):
            from services.cleanup import cleanup_service
            
            assert cleanup_service is not None


class TestDeletionOrder:
    """Tests for ensuring correct deletion order."""
    
    @pytest.mark.asyncio
    async def test_auth_deletion_happens_last(self):
        """Auth deletion should happen after all other deletions."""
        with patch('services.cleanup.get_supabase') as mock_get_supabase:
            mock_supabase = Mock()
            mock_get_supabase.return_value = mock_supabase
            
            call_order = []
            
            from services.cleanup import AccountCleanupService
            service = AccountCleanupService()
            
            async def mock_vectors(user_id):
                call_order.append("vectors")
                return {"deleted": 0, "status": "success"}
            
            async def mock_storage(user_id):
                call_order.append("storage")
                return {"deleted": 0, "status": "success"}
            
            async def mock_database(user_id):
                call_order.append("database")
                return {"status": "success"}
            
            async def mock_auth(user_id):
                call_order.append("auth")
                return {"status": "success"}
            
            service._cleanup_vectors = mock_vectors
            service._cleanup_storage = mock_storage
            service._cleanup_database = mock_database
            service._cleanup_auth = mock_auth
            
            await service.execute_account_deletion("user-123")
            
            # Auth must be last
            assert call_order[-1] == "auth"
            # Order should be: vectors, storage, database, auth
            assert call_order == ["vectors", "storage", "database", "auth"]
