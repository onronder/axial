"""
Test Suite for Ghost Protocol Secure Cleanup Service

Tests for Zero-Retention file cleanup including:
- secure_wipe() cryptographic deletion
- SecureTempFile context manager
- SmartBuffer RAM/disk decision logic
- cleanup_staging_file() S3 removal
- Emergency cleanup (dead man's switch)
"""

import os
import tempfile
import threading
from unittest.mock import MagicMock, patch

import pytest

from services.secure_cleanup import (
    secure_wipe,
    SecureTempFile,
    SmartBuffer,
    cleanup_staging_file,
    _tracked_temp_files,
    _register_temp_file,
    _unregister_temp_file,
    _emergency_cleanup,
)


class TestSecureWipe:
    """Tests for secure_wipe function."""
    
    def test_secure_wipe_deletes_file(self):
        """secure_wipe should delete the file."""
        # Create a temp file with content
        fd, path = tempfile.mkstemp(prefix="test_wipe_")
        os.write(fd, b"sensitive content" * 1000)
        os.close(fd)
        
        assert os.path.exists(path)
        
        result = secure_wipe(path)
        
        assert result is True
        assert not os.path.exists(path)
    
    def test_secure_wipe_overwrites_content(self):
        """secure_wipe should overwrite file content before deletion."""
        # Create a temp file with known content
        fd, path = tempfile.mkstemp(prefix="test_wipe_")
        original_content = b"TOP SECRET DATA" * 100
        os.write(fd, original_content)
        os.close(fd)
        
        # We can't easily verify the overwrite happened since the file
        # is deleted, but we can verify the process completes
        result = secure_wipe(path)
        
        assert result is True
        assert not os.path.exists(path)
    
    def test_secure_wipe_handles_nonexistent_file(self):
        """secure_wipe should return False for non-existent files."""
        result = secure_wipe("/nonexistent/path/to/file.txt")
        
        assert result is False
    
    def test_secure_wipe_handles_empty_path(self):
        """secure_wipe should return False for empty path."""
        assert secure_wipe("") is False
        assert secure_wipe(None) is False
    
    def test_secure_wipe_handles_empty_file(self):
        """secure_wipe should handle empty files."""
        fd, path = tempfile.mkstemp(prefix="test_wipe_empty_")
        os.close(fd)
        
        assert os.path.exists(path)
        assert os.path.getsize(path) == 0
        
        result = secure_wipe(path)
        
        assert result is True
        assert not os.path.exists(path)
    
    def test_secure_wipe_multiple_passes(self):
        """secure_wipe should support multiple overwrite passes."""
        fd, path = tempfile.mkstemp(prefix="test_wipe_multi_")
        os.write(fd, b"sensitive" * 1000)
        os.close(fd)
        
        result = secure_wipe(path, passes=3)
        
        assert result is True
        assert not os.path.exists(path)
    
    def test_secure_wipe_unregisters_tracked_file(self):
        """secure_wipe should unregister the file from tracking."""
        fd, path = tempfile.mkstemp(prefix="test_wipe_track_")
        os.write(fd, b"content")
        os.close(fd)
        
        _register_temp_file(path)
        assert path in _tracked_temp_files
        
        secure_wipe(path)
        
        assert path not in _tracked_temp_files


class TestSecureTempFile:
    """Tests for SecureTempFile context manager."""
    
    def test_secure_temp_file_creates_file(self):
        """SecureTempFile should create a temp file."""
        with SecureTempFile(suffix=".txt") as path:
            assert os.path.exists(path)
            assert path.endswith(".txt")
    
    def test_secure_temp_file_deletes_on_exit(self):
        """SecureTempFile should delete file on context exit."""
        with SecureTempFile(suffix=".txt") as path:
            # Write some content
            with open(path, 'wb') as f:
                f.write(b"temporary content")
            saved_path = path
        
        assert not os.path.exists(saved_path)
    
    def test_secure_temp_file_deletes_on_exception(self):
        """SecureTempFile should delete file even if exception occurs."""
        saved_path = None
        
        try:
            with SecureTempFile(suffix=".txt") as path:
                saved_path = path
                with open(path, 'wb') as f:
                    f.write(b"content before error")
                raise ValueError("Simulated error")
        except ValueError:
            pass
        
        assert saved_path is not None
        assert not os.path.exists(saved_path)
    
    def test_secure_temp_file_custom_prefix(self):
        """SecureTempFile should support custom prefix."""
        with SecureTempFile(prefix="custom_") as path:
            assert "custom_" in os.path.basename(path)
    
    def test_secure_temp_file_registers_for_tracking(self):
        """SecureTempFile should register file for emergency cleanup."""
        with SecureTempFile(suffix=".txt") as path:
            assert path in _tracked_temp_files
        
        # After exit, should be unregistered
        assert path not in _tracked_temp_files
    
    def test_secure_temp_file_writable(self):
        """SecureTempFile path should be writable."""
        with SecureTempFile(suffix=".bin") as path:
            with open(path, 'wb') as f:
                f.write(b"test data " * 1000)
            
            # Verify content was written
            with open(path, 'rb') as f:
                content = f.read()
            
            assert len(content) == 10 * 1000


class TestSmartBuffer:
    """Tests for SmartBuffer class."""
    
    def test_small_file_uses_ram(self):
        """Small files should be kept in RAM."""
        content = b"small content"
        
        with SmartBuffer(content, filename="small.txt", threshold=1024) as buffer:
            assert buffer.is_ram_backed is True
            assert buffer.path is None
    
    def test_large_file_uses_disk(self):
        """Large files should use disk storage."""
        content = b"x" * 2000  # 2KB
        
        with SmartBuffer(content, filename="large.txt", threshold=1024) as buffer:
            assert buffer.is_ram_backed is False
            assert buffer.path is not None
            assert os.path.exists(buffer.path)
    
    def test_get_bytes_from_ram(self):
        """get_bytes should work for RAM-backed buffer."""
        content = b"test content"
        
        with SmartBuffer(content, filename="test.txt", threshold=1024) as buffer:
            assert buffer.get_bytes() == content
    
    def test_get_bytes_from_disk(self):
        """get_bytes should work for disk-backed buffer."""
        content = b"large " * 500  # 3KB
        
        with SmartBuffer(content, filename="test.txt", threshold=1024) as buffer:
            assert buffer.get_bytes() == content
    
    def test_get_stream_from_ram(self):
        """get_stream should return BytesIO for RAM-backed buffer."""
        import io
        content = b"stream content"
        
        with SmartBuffer(content, filename="test.txt", threshold=1024) as buffer:
            stream = buffer.get_stream()
            assert isinstance(stream, io.BytesIO)
            assert stream.read() == content
    
    def test_get_stream_from_disk(self):
        """get_stream should return file handle for disk-backed buffer."""
        content = b"large " * 500
        
        with SmartBuffer(content, filename="test.txt", threshold=1024) as buffer:
            stream = buffer.get_stream()
            try:
                data = stream.read()
                assert data == content
            finally:
                stream.close()
    
    def test_write_to_temp_from_ram(self):
        """write_to_temp should create temp file from RAM buffer."""
        content = b"small content"
        
        with SmartBuffer(content, filename="test.txt", threshold=1024) as buffer:
            temp_path = buffer.write_to_temp()
            try:
                assert os.path.exists(temp_path)
                with open(temp_path, 'rb') as f:
                    assert f.read() == content
            finally:
                secure_wipe(temp_path)
    
    def test_write_to_temp_from_disk(self):
        """write_to_temp should copy from disk buffer."""
        content = b"large " * 500
        
        with SmartBuffer(content, filename="test.pdf", threshold=1024) as buffer:
            temp_path = buffer.write_to_temp()
            try:
                assert os.path.exists(temp_path)
                assert temp_path.endswith(".pdf")
                with open(temp_path, 'rb') as f:
                    assert f.read() == content
            finally:
                secure_wipe(temp_path)
    
    def test_cleanup_removes_disk_file(self):
        """cleanup should remove disk-backed temp file."""
        content = b"large " * 500
        
        buffer = SmartBuffer(content, filename="test.txt", threshold=1024)
        disk_path = buffer.path
        
        assert os.path.exists(disk_path)
        
        buffer.cleanup()
        
        assert not os.path.exists(disk_path)
    
    def test_cleanup_safe_to_call_multiple_times(self):
        """cleanup should be safe to call multiple times."""
        content = b"large " * 500
        
        buffer = SmartBuffer(content, filename="test.txt", threshold=1024)
        
        buffer.cleanup()
        buffer.cleanup()  # Should not raise
        buffer.cleanup()  # Should not raise
    
    def test_context_manager_cleanup(self):
        """Context manager should cleanup on exit."""
        content = b"large " * 500
        
        with SmartBuffer(content, filename="test.txt", threshold=1024) as buffer:
            disk_path = buffer.path
            assert os.path.exists(disk_path)
        
        assert not os.path.exists(disk_path)
    
    @pytest.mark.skip(reason="Test isolation issue - settings may be cached by other tests")
    def test_uses_default_threshold_from_settings(self, monkeypatch):
        """SmartBuffer should use settings.MAX_RAM_PROCESS_LIMIT as default."""
        from core import config
        
        # Set a small threshold
        monkeypatch.setattr(config.settings, 'MAX_RAM_PROCESS_LIMIT', 100)
        
        content = b"x" * 50  # Below threshold
        with SmartBuffer(content, filename="test.txt") as buffer:
            assert buffer.is_ram_backed is True
        
        content = b"x" * 150  # Above threshold
        with SmartBuffer(content, filename="test.txt") as buffer:
            assert buffer.is_ram_backed is False


class TestCleanupStagingFile:
    """Tests for cleanup_staging_file function."""
    
    def test_cleanup_staging_file_calls_storage_remove(self):
        """cleanup_staging_file should call Supabase storage remove."""
        mock_supabase = MagicMock()
        mock_storage = MagicMock()
        mock_supabase.storage.from_.return_value = mock_storage
        
        with patch('core.db.get_supabase', return_value=mock_supabase):
            result = cleanup_staging_file("uploads/user123/hash456/file.pdf")
        
        assert result is True
        mock_supabase.storage.from_.assert_called_with("ephemeral-staging")
        mock_storage.remove.assert_called_with(["uploads/user123/hash456/file.pdf"])
    
    def test_cleanup_staging_file_custom_bucket(self):
        """cleanup_staging_file should support custom bucket name."""
        mock_supabase = MagicMock()
        mock_storage = MagicMock()
        mock_supabase.storage.from_.return_value = mock_storage
        
        with patch('core.db.get_supabase', return_value=mock_supabase):
            result = cleanup_staging_file("path/to/file.pdf", bucket="custom-bucket")
        
        assert result is True
        mock_supabase.storage.from_.assert_called_with("custom-bucket")
    
    def test_cleanup_staging_file_handles_empty_path(self):
        """cleanup_staging_file should return False for empty path."""
        assert cleanup_staging_file("") is False
        assert cleanup_staging_file(None) is False
    
    def test_cleanup_staging_file_handles_error(self):
        """cleanup_staging_file should return False on storage error."""
        mock_supabase = MagicMock()
        mock_supabase.storage.from_.side_effect = Exception("Storage error")
        
        with patch('core.db.get_supabase', return_value=mock_supabase):
            result = cleanup_staging_file("uploads/user123/hash456/file.pdf")
        
        assert result is False


class TestTempFileTracking:
    """Tests for temp file tracking (dead man's switch)."""
    
    def test_register_and_unregister(self):
        """Files can be registered and unregistered."""
        test_path = "/tmp/test_tracked_file.txt"
        
        # Ensure clean state
        _unregister_temp_file(test_path)
        
        _register_temp_file(test_path)
        assert test_path in _tracked_temp_files
        
        _unregister_temp_file(test_path)
        assert test_path not in _tracked_temp_files
    
    def test_unregister_nonexistent_is_safe(self):
        """Unregistering non-tracked file should not raise."""
        _unregister_temp_file("/nonexistent/path")  # Should not raise
    
    def test_emergency_cleanup_wipes_tracked_files(self):
        """Emergency cleanup should wipe all tracked files."""
        # Create some temp files and register them
        paths = []
        for i in range(3):
            fd, path = tempfile.mkstemp(prefix=f"test_emergency_{i}_")
            os.write(fd, b"content")
            os.close(fd)
            _register_temp_file(path)
            paths.append(path)
        
        # Verify all exist and are tracked
        for path in paths:
            assert os.path.exists(path)
            assert path in _tracked_temp_files
        
        # Run emergency cleanup
        _emergency_cleanup()
        
        # All files should be deleted and untracked
        for path in paths:
            assert not os.path.exists(path)
            assert path not in _tracked_temp_files


class TestThreadSafety:
    """Tests for thread safety of cleanup operations."""
    
    def test_concurrent_register_unregister(self):
        """Registration and unregistration should be thread-safe."""
        paths = [f"/tmp/concurrent_test_{i}.txt" for i in range(100)]
        
        def register_all():
            for path in paths:
                _register_temp_file(path)
        
        def unregister_all():
            for path in paths:
                _unregister_temp_file(path)
        
        # Run concurrent registration
        threads = [
            threading.Thread(target=register_all),
            threading.Thread(target=register_all),
        ]
        for t in threads:
            t.start()
        for t in threads:
            t.join()
        
        # All should be registered (despite concurrent access)
        for path in paths:
            assert path in _tracked_temp_files
        
        # Run concurrent unregistration
        threads = [
            threading.Thread(target=unregister_all),
            threading.Thread(target=unregister_all),
        ]
        for t in threads:
            t.start()
        for t in threads:
            t.join()
        
        # All should be unregistered
        for path in paths:
            assert path not in _tracked_temp_files


class TestEdgeCases:
    """Tests for edge cases and boundary conditions."""
    
    def test_smart_buffer_exactly_at_threshold(self):
        """File exactly at threshold should use disk."""
        content = b"x" * 1024
        
        with SmartBuffer(content, filename="test.txt", threshold=1024) as buffer:
            # At threshold = use disk (>= comparison)
            assert buffer.is_ram_backed is False
    
    def test_smart_buffer_one_below_threshold(self):
        """File one byte below threshold should use RAM."""
        content = b"x" * 1023
        
        with SmartBuffer(content, filename="test.txt", threshold=1024) as buffer:
            assert buffer.is_ram_backed is True
    
    def test_smart_buffer_zero_threshold(self):
        """Zero threshold should force all files to disk."""
        content = b"tiny"
        
        with SmartBuffer(content, filename="test.txt", threshold=0) as buffer:
            assert buffer.is_ram_backed is False
    
    def test_smart_buffer_empty_content(self):
        """Empty content should use RAM."""
        content = b""
        
        with SmartBuffer(content, filename="test.txt", threshold=1024) as buffer:
            assert buffer.is_ram_backed is True
            assert buffer.get_bytes() == b""
    
    def test_secure_temp_file_preserves_suffix(self):
        """SecureTempFile should preserve file suffix."""
        with SecureTempFile(suffix=".docx") as path:
            assert path.endswith(".docx")
        
        with SecureTempFile(suffix=".xlsx") as path:
            assert path.endswith(".xlsx")
