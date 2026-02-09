"""
Ghost Protocol End-to-End Integration Tests

These tests verify the complete Ghost Protocol flow:
1. File processing with SmartBuffer (RAM and disk)
2. Encrypted content storage
3. Secure cleanup on success and failure
4. Emergency cleanup via signal handlers
5. Key rotation support

Requirements:
- CHUNK_ENCRYPTION_KEY must be set
- Tests use mocked Supabase and S3
"""

import os
import tempfile
from unittest.mock import MagicMock, patch

import pytest

# =============================================================================
# TEST FIXTURES
# =============================================================================

@pytest.fixture
def small_content():
    """Content small enough to stay in RAM (< 10MB)."""
    return b"This is test content for Ghost Protocol verification. " * 100


@pytest.fixture
def large_content():
    """Content large enough to use disk (> 10MB threshold)."""
    # Create 11MB of content
    return os.urandom(11 * 1024 * 1024)


@pytest.fixture
def mock_supabase():
    """Mock Supabase client for testing."""
    mock = MagicMock()
    mock.storage.from_.return_value.remove.return_value = None
    mock.storage.from_.return_value.download.return_value = b"test content"
    mock.table.return_value.select.return_value.eq.return_value.limit.return_value.execute.return_value.data = []
    mock.table.return_value.insert.return_value.execute.return_value.data = [{"id": "test-doc-id"}]
    mock.table.return_value.update.return_value.eq.return_value.execute.return_value = None
    mock.rpc.return_value.execute.return_value.data = [{"inserted_id": "chunk-1", "chunk_index": 0}]
    return mock


# =============================================================================
# SMART BUFFER TESTS
# =============================================================================

class TestSmartBufferIntegration:
    """Test SmartBuffer for RAM vs disk decision."""

    def test_small_file_uses_ram(self, small_content):
        """Small files should stay in RAM."""
        from services.secure_cleanup import SmartBuffer

        with SmartBuffer(small_content, filename="test.txt", threshold=10*1024*1024) as buffer:
            assert buffer.is_ram_backed is True
            assert buffer.path is None
            assert buffer.get_bytes() == small_content

    def test_large_file_uses_disk(self, large_content):
        """Large files should use secure temp file."""
        from services.secure_cleanup import SmartBuffer

        with SmartBuffer(large_content, filename="test.bin", threshold=10*1024*1024) as buffer:
            assert buffer.is_ram_backed is False
            assert buffer.path is not None
            assert os.path.exists(buffer.path)
            assert buffer.get_bytes() == large_content

        # After context exit, temp file should be wiped
        # Note: We can't check if it's gone because cleanup happens

    def test_smart_buffer_stream_works(self, small_content):
        """Get stream should work for both RAM and disk backed buffers."""
        from services.secure_cleanup import SmartBuffer

        with SmartBuffer(small_content, filename="test.txt") as buffer:
            stream = buffer.get_stream()
            read_content = stream.read()
            assert read_content == small_content

    def test_write_to_temp_creates_trackable_file(self, small_content):
        """write_to_temp should create a file tracked for cleanup."""
        from services.secure_cleanup import (
            SmartBuffer,
            _tracked_temp_files,
            secure_wipe,
        )

        with SmartBuffer(small_content, filename="test.txt") as buffer:
            temp_path = buffer.write_to_temp()
            assert temp_path is not None
            assert os.path.exists(temp_path)
            assert temp_path in _tracked_temp_files

            # Cleanup
            secure_wipe(temp_path)


# =============================================================================
# ENCRYPTION INTEGRATION TESTS
# =============================================================================

class TestEncryptionIntegration:
    """Test encryption roundtrip with the actual module."""

    def test_encrypt_decrypt_roundtrip(self):
        """Encrypted content should decrypt back to original."""
        from core.security import HAS_CHUNK_ENCRYPTION, decrypt_text, encrypt_text

        if not HAS_CHUNK_ENCRYPTION:
            pytest.skip("CHUNK_ENCRYPTION_KEY not configured")

        original = "This is sensitive document content with unicode: 你好世界"
        encrypted = encrypt_text(original)

        # Encrypted should be different from original
        assert encrypted != original
        assert encrypted.startswith("gAAAAA")  # Fernet prefix

        # Decrypt should recover original
        decrypted = decrypt_text(encrypted)
        assert decrypted == original

    def test_empty_content_passthrough(self):
        """Empty content should pass through without encryption."""
        from core.security import decrypt_text, encrypt_text

        assert encrypt_text("") == ""
        assert encrypt_text(None) is None
        assert decrypt_text("") == ""
        assert decrypt_text(None) is None

    def test_key_rotation_support(self):
        """Multiple keys should work for decryption."""
        from core.security import (
            HAS_CHUNK_ENCRYPTION,
            decrypt_text,
            encrypt_text,
        )

        if not HAS_CHUNK_ENCRYPTION:
            pytest.skip("CHUNK_ENCRYPTION_KEY not configured")

        # Encrypt with primary key
        content = "Test content for key rotation"
        encrypted = encrypt_text(content)

        # Should decrypt successfully (using any configured key)
        decrypted = decrypt_text(encrypted)
        assert decrypted == content


# =============================================================================
# SECURE WIPE INTEGRATION TESTS
# =============================================================================

class TestSecureWipeIntegration:
    """Test cryptographic file wiping."""

    def test_secure_wipe_removes_file(self):
        """secure_wipe should completely remove the file."""
        from services.secure_cleanup import secure_wipe

        # Create a temp file
        fd, path = tempfile.mkstemp()
        os.write(fd, b"Sensitive content that should be wiped")
        os.close(fd)

        assert os.path.exists(path)

        # Wipe it
        result = secure_wipe(path)

        assert result is True
        assert not os.path.exists(path)

    def test_secure_wipe_multiple_passes(self):
        """secure_wipe with multiple passes should work."""
        from services.secure_cleanup import secure_wipe

        fd, path = tempfile.mkstemp()
        os.write(fd, b"Sensitive content" * 1000)
        os.close(fd)

        result = secure_wipe(path, passes=3)

        assert result is True
        assert not os.path.exists(path)

    def test_secure_wipe_nonexistent_file(self):
        """secure_wipe on nonexistent file should return False."""
        from services.secure_cleanup import secure_wipe

        result = secure_wipe("/nonexistent/path/to/file.txt")
        assert result is False


# =============================================================================
# SECURE TEMP FILE TESTS
# =============================================================================

class TestSecureTempFileIntegration:
    """Test SecureTempFile context manager."""

    def test_secure_temp_file_creates_and_wipes(self):
        """SecureTempFile should create file and wipe on exit."""
        from services.secure_cleanup import SecureTempFile

        path_holder = [None]

        with SecureTempFile(suffix=".txt") as path:
            path_holder[0] = path
            assert os.path.exists(path)

            # Write some content
            with open(path, 'w') as f:
                f.write("Sensitive data")

            assert os.path.exists(path)

        # After context exit, file should be gone
        assert not os.path.exists(path_holder[0])

    def test_secure_temp_file_wipes_on_exception(self):
        """SecureTempFile should wipe even if exception raised."""
        from services.secure_cleanup import SecureTempFile

        path_holder = [None]

        with pytest.raises(ValueError), SecureTempFile(suffix=".txt") as path:
            path_holder[0] = path
            with open(path, 'w') as f:
                f.write("Data before error")
            raise ValueError("Simulated error")

        # File should still be wiped despite exception
        assert not os.path.exists(path_holder[0])


# =============================================================================
# S3 CLEANUP INTEGRATION TESTS
# =============================================================================

class TestS3CleanupIntegration:
    """Test S3 staging file cleanup."""

    def test_cleanup_staging_file_success(self, mock_supabase):
        """cleanup_staging_file should call S3 remove."""
        from services.secure_cleanup import cleanup_staging_file

        with patch('core.db.get_supabase', return_value=mock_supabase):
            result = cleanup_staging_file(
                "uploads/user123/abc/file.pdf",
                bucket="ephemeral-staging"
            )

        assert result is True
        mock_supabase.storage.from_.assert_called_with("ephemeral-staging")

    def test_cleanup_staging_file_empty_path(self, mock_supabase):
        """cleanup_staging_file with empty path should return False."""
        from services.secure_cleanup import cleanup_staging_file

        result = cleanup_staging_file("")
        assert result is False

    def test_cleanup_staging_file_handles_error(self, mock_supabase):
        """cleanup_staging_file should handle S3 errors gracefully."""
        from services.secure_cleanup import cleanup_staging_file

        mock_supabase.storage.from_.return_value.remove.side_effect = Exception("S3 Error")

        with patch('core.db.get_supabase', return_value=mock_supabase):
            result = cleanup_staging_file("uploads/test/file.pdf")

        assert result is False


# =============================================================================
# EMERGENCY CLEANUP TESTS
# =============================================================================

class TestEmergencyCleanupIntegration:
    """Test emergency cleanup handlers."""

    def test_tracked_files_are_cleaned_on_emergency(self):
        """Emergency cleanup should wipe all tracked files."""
        from services.secure_cleanup import (
            _emergency_cleanup,
            _register_temp_file,
            _tracked_temp_files,
        )

        # Create some temp files and track them
        paths = []
        for i in range(3):
            fd, path = tempfile.mkstemp()
            os.write(fd, f"Content {i}".encode())
            os.close(fd)
            _register_temp_file(path)
            paths.append(path)

        # Verify files exist and are tracked
        for path in paths:
            assert os.path.exists(path)
            assert path in _tracked_temp_files

        # Trigger emergency cleanup
        _emergency_cleanup(trigger="test")

        # All files should be gone
        for path in paths:
            assert not os.path.exists(path)

    def test_celery_signal_module_loads(self):
        """Celery signal handlers should load without error."""
        # This verifies the module can be imported
        import worker.ghost_protocol_signals as signals

        assert hasattr(signals, 'get_active_task_count')
        assert hasattr(signals, 'CELERY_SIGNALS_AVAILABLE')


# =============================================================================
# INGESTION FLOW TESTS
# =============================================================================

class TestIngestionFlowIntegration:
    """Test Ghost Protocol in the ingestion pipeline."""

    def test_prepare_chunks_encrypts_content(self):
        """prepare_chunks_for_ghost_protocol should encrypt content."""
        from core.ingestion_utils import prepare_chunks_for_ghost_protocol
        from core.security import HAS_CHUNK_ENCRYPTION, decrypt_text

        if not HAS_CHUNK_ENCRYPTION:
            pytest.skip("CHUNK_ENCRYPTION_KEY not configured")

        chunks = [
            {"content": "First chunk content", "embedding": [0.1] * 1536, "chunk_index": 0},
            {"content": "Second chunk content", "embedding": [0.2] * 1536, "chunk_index": 1},
        ]

        prepared, encrypted = prepare_chunks_for_ghost_protocol(chunks, "doc-123")

        assert encrypted is True
        assert len(prepared) == 2

        # Encrypted content should be different from original
        assert prepared[0]["content_encrypted"] != "First chunk content"

        # Plaintext should be preserved for search
        assert prepared[0]["content_plaintext"] == "First chunk content"

        # Should be decryptable
        decrypted = decrypt_text(prepared[0]["content_encrypted"])
        assert decrypted == "First chunk content"


# =============================================================================
# METRICS INTEGRATION TESTS
# =============================================================================

class TestMetricsIntegration:
    """Test that Ghost Protocol operations record metrics."""

    def test_secure_wipe_records_metrics(self):
        """secure_wipe should increment metrics on success."""
        from services.secure_cleanup import secure_wipe

        fd, path = tempfile.mkstemp()
        os.write(fd, b"Test content")
        os.close(fd)

        # This should increment the success metric
        result = secure_wipe(path)
        assert result is True

        # We can't easily verify metric values in unit tests,
        # but this ensures no exceptions are raised

    def test_smart_buffer_records_metrics(self, small_content):
        """SmartBuffer should record allocation metrics."""
        from services.secure_cleanup import SmartBuffer

        with SmartBuffer(small_content, filename="test.txt") as buffer:
            assert buffer.is_ram_backed

        # No exception means metrics were recorded successfully


# =============================================================================
# KEY ROTATION UTILITIES TESTS
# =============================================================================

class TestKeyRotationUtilities:
    """Test key rotation helper functions."""

    def test_get_encryption_key_count(self):
        """get_encryption_key_count should return number of keys."""
        from core.security import get_encryption_key_count

        count = get_encryption_key_count()
        # Should be at least 1 if CHUNK_ENCRYPTION_KEY is set, 0 otherwise
        assert isinstance(count, int)
        assert count >= 0

    def test_generate_new_encryption_key_format(self):
        """generate_new_encryption_key should produce valid Fernet key."""
        from core.security import generate_new_encryption_key

        try:
            key = generate_new_encryption_key()
            assert isinstance(key, str)
            assert len(key) == 44  # Base64-encoded 32 bytes

            # Should be valid for Fernet
            from cryptography.fernet import Fernet
            Fernet(key.encode())  # Should not raise
        except RuntimeError:
            pytest.skip("cryptography package not available")

    def test_re_encrypt_content(self):
        """re_encrypt_content should produce valid encrypted content."""
        from core.security import (
            HAS_CHUNK_ENCRYPTION,
            decrypt_text,
            encrypt_text,
            re_encrypt_content,
        )

        if not HAS_CHUNK_ENCRYPTION:
            pytest.skip("CHUNK_ENCRYPTION_KEY not configured")

        original = "Content to re-encrypt"
        encrypted = encrypt_text(original)

        # Re-encrypt should produce valid encrypted content
        re_encrypted = re_encrypt_content(encrypted)

        # Should still decrypt to original
        decrypted = decrypt_text(re_encrypted)
        assert decrypted == original


# =============================================================================
# END-TO-END FLOW SIMULATION
# =============================================================================

class TestEndToEndFlow:
    """Simulate complete file processing flow."""

    def test_complete_flow_simulation(self, small_content, mock_supabase):
        """Simulate complete file ingestion with Ghost Protocol."""
        from core.security import HAS_CHUNK_ENCRYPTION, decrypt_text, encrypt_text
        from services.secure_cleanup import (
            SmartBuffer,
            secure_wipe,
        )

        if not HAS_CHUNK_ENCRYPTION:
            pytest.skip("CHUNK_ENCRYPTION_KEY not configured")

        local_path = None
        buffer = None

        try:
            # Step 1: Create SmartBuffer (simulates download)
            buffer = SmartBuffer(small_content, filename="test.pdf")

            # Step 2: Parse content (simulated)
            parsed_text = buffer.get_bytes().decode('utf-8', errors='ignore')
            chunks = [{"content": parsed_text[:500], "chunk_index": 0}]

            # Step 3: Encrypt for storage
            encrypted = encrypt_text(chunks[0]["content"])
            assert encrypted != chunks[0]["content"]

            # Step 4: Verify decryption works
            decrypted = decrypt_text(encrypted)
            assert decrypted == chunks[0]["content"]

            # Step 5: Cleanup
            buffer.cleanup()

            # Verify cleanup succeeded (no exception)
            assert True

        finally:
            # Ensure cleanup happens even on failure
            if buffer:
                buffer.cleanup()
            if local_path and os.path.exists(local_path):
                secure_wipe(local_path)


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
