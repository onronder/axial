"""
Comprehensive Integration Tests for New Modules

Tests:
1. MCP Module Integration
2. Vision LLM Module
3. Scope Guard Module
4. Consent Module
5. Secure Cleanup Module

Run with: pytest tests/integration/test_new_modules_comprehensive.py -v
"""

import os
import tempfile
import time
from datetime import datetime, timedelta, timezone
from unittest.mock import patch

# =============================================================================
# 1. MCP MODULE INTEGRATION TESTS
# =============================================================================

class TestMCPModule:
    """Test MCP authentication, zero retention, and tools."""

    def test_api_key_generation(self):
        """Test MCP API key generation format and entropy."""
        from mcp.auth import generate_api_key, hash_api_key

        key = generate_api_key()

        # Check format
        assert key.startswith("axio_mcp_"), f"Key should start with 'axio_mcp_', got: {key[:15]}"

        # Check length (prefix + 48 hex chars)
        assert len(key) == 9 + 48, f"Key length should be 57, got: {len(key)}"

        # Check randomness - generate multiple keys and ensure uniqueness
        keys = [generate_api_key() for _ in range(10)]
        assert len(set(keys)) == 10, "Generated keys should be unique"

        # Test hashing
        hashed = hash_api_key(key)
        assert len(hashed) == 64, "SHA-256 hash should be 64 hex chars"

        # Same key should produce same hash
        assert hash_api_key(key) == hashed, "Hashing should be deterministic"

        # Different keys should produce different hashes
        key2 = generate_api_key()
        assert hash_api_key(key2) != hashed, "Different keys should have different hashes"

        print(f"[PASS] API key generation: {key[:20]}...")
        print(f"[PASS] Hash: {hashed[:16]}...")

    def test_mcp_api_key_model(self):
        """Test MCPApiKey model validation."""
        from mcp.auth import MCPApiKey

        key = MCPApiKey(
            id="test-id-123",
            organization_id="org-456",
            agent_name="Test Agent",
            scopes=["*", "documents:*"],
            created_at=datetime.now(timezone.utc),
            expires_at=datetime.now(timezone.utc) + timedelta(days=30),
        )

        assert key.id == "test-id-123"
        assert key.organization_id == "org-456"
        assert key.agent_name == "Test Agent"
        assert "*" in key.scopes
        assert key.expires_at is not None

        print(f"[PASS] MCPApiKey model: agent={key.agent_name}")

    def test_mcp_zero_retention_wrapper(self):
        """Test MCPZeroRetention response wrapping."""
        from mcp.zero_retention import MCPZeroRetention

        content = {"results": [{"id": 1, "text": "test"}]}
        metadata = {"query": "test query"}

        wrapped = MCPZeroRetention.wrap_response(content, metadata)

        # Check structure
        assert "content" in wrapped
        assert "_ghost_protocol" in wrapped
        assert wrapped["content"] == content

        # Check ghost protocol markers
        gp = wrapped["_ghost_protocol"]
        assert gp["ephemeral"] is True
        assert gp["retention_policy"] == "zero"
        assert gp["cache_control"] == "no-store"
        assert "timestamp" in gp
        assert gp.get("metadata") == metadata

        print(f"[PASS] Zero retention wrapper: ephemeral={gp['ephemeral']}")

    def test_mcp_zero_retention_headers(self):
        """Test Ghost Protocol HTTP headers."""
        from mcp.zero_retention import MCPZeroRetention

        headers = MCPZeroRetention.get_response_headers()

        assert "no-store" in headers["Cache-Control"]
        assert "no-cache" in headers["Pragma"]
        assert headers["X-Ghost-Protocol"] == "zero-retention"

        print(f"[PASS] Ghost Protocol headers: {len(headers)} headers set")

    def test_mcp_request_intent_validation(self):
        """Test request intent validation against abuse."""
        from mcp.zero_retention import MCPZeroRetention

        # Valid requests should pass
        assert MCPZeroRetention.validate_request_intent(
            "search_documents", {"query": "test", "limit": 10}
        ) is True

        # Excessive limit should fail
        assert MCPZeroRetention.validate_request_intent(
            "search_documents", {"query": "test", "limit": 100}
        ) is False

        # Very long query should fail
        long_query = "x" * 3000
        assert MCPZeroRetention.validate_request_intent(
            "search_documents", {"query": long_query}
        ) is False

        print("[PASS] Request intent validation working correctly")

    def test_mcp_tool_schema_validation(self):
        """Test MCP tool definitions and schemas."""
        from mcp.tools import MCP_TOOLS

        # Check all tools exist
        tool_names = {t["name"] for t in MCP_TOOLS}
        expected_tools = {"search_documents", "ask_question", "list_scopes", "get_document_summary"}

        assert tool_names == expected_tools, f"Missing tools: {expected_tools - tool_names}"

        # Validate schema structure for each tool
        for tool in MCP_TOOLS:
            assert "name" in tool
            assert "description" in tool
            assert "inputSchema" in tool
            assert tool["inputSchema"]["type"] == "object"
            assert "properties" in tool["inputSchema"]

            # If required fields specified, they should be in properties
            required = tool["inputSchema"].get("required", [])
            properties = tool["inputSchema"]["properties"]
            for req in required:
                assert req in properties, f"Required field {req} missing from properties in {tool['name']}"

        print(f"[PASS] Tool schema validation: {len(MCP_TOOLS)} tools validated")

    def test_scope_allowed_helper(self):
        """Test scope pattern matching."""
        from mcp.tools import _scope_allowed

        # Wildcard allows everything
        assert _scope_allowed("gdrive:123", ["*"]) is True
        assert _scope_allowed("notion:abc", ["*"]) is True

        # Prefix matching
        assert _scope_allowed("gdrive:123", ["gdrive:*"]) is True
        assert _scope_allowed("gdrive:456", ["gdrive:*"]) is True
        assert _scope_allowed("notion:abc", ["gdrive:*"]) is False

        # Exact matching
        assert _scope_allowed("scope-123", ["scope-123"]) is True
        assert _scope_allowed("scope-456", ["scope-123"]) is False

        # Empty allowed_scopes allows all
        assert _scope_allowed("anything", []) is True

        print("[PASS] Scope pattern matching working correctly")


# =============================================================================
# 2. VISION LLM MODULE TESTS
# =============================================================================

class TestVisionModule:
    """Test Vision LLM components."""

    def test_diagram_type_enum(self):
        """Test DiagramType enum values."""
        from services.vision.base import DiagramType

        expected_types = [
            "flowchart", "architecture", "sequence", "er_diagram",
            "uml", "chart", "graph", "schematic", "infographic",
            "screenshot", "photo", "document_scan", "unknown"
        ]

        actual_types = [dt.value for dt in DiagramType]

        assert set(actual_types) == set(expected_types), \
            f"Missing types: {set(expected_types) - set(actual_types)}"

        print(f"[PASS] DiagramType enum: {len(actual_types)} types defined")

    def test_vision_result_creation(self):
        """Test VisionResult dataclass with all DiagramTypes."""
        from services.vision.base import DiagramType, VisionResult

        for dtype in DiagramType:
            result = VisionResult(
                description=f"Test description for {dtype.value}",
                diagram_type=dtype,
                entities=["Entity1", "Entity2"],
                relationships=["Entity1 connects to Entity2"],
                text_content="Sample text",
                confidence=0.95,
                model_used="test-model",
                metadata={"test": True},
            )

            assert result.diagram_type == dtype
            assert result.confidence == 0.95
            assert len(result.entities) == 2
            assert len(result.relationships) == 1

        print(f"[PASS] VisionResult creation: tested with all {len(DiagramType)} diagram types")

    def test_vision_result_to_searchable_text(self):
        """Test to_searchable_text method."""
        from services.vision.base import DiagramType, VisionResult

        result = VisionResult(
            description="This is a system architecture diagram showing microservices.",
            diagram_type=DiagramType.ARCHITECTURE,
            entities=["API Gateway", "User Service", "Database"],
            relationships=["API Gateway routes to User Service", "User Service connects to Database"],
            text_content="Auth Module v2.0",
            confidence=0.92,
            model_used="gpt-4o",
        )

        searchable = result.to_searchable_text()

        # Should contain diagram type
        assert "Architecture" in searchable

        # Should contain description
        assert "microservices" in searchable

        # Should contain entities
        assert "API Gateway" in searchable
        assert "User Service" in searchable

        # Should contain relationships
        assert "routes to" in searchable

        # Should contain text content
        assert "Auth Module" in searchable

        print(f"[PASS] to_searchable_text: {len(searchable)} chars generated")
        print(f"  Preview: {searchable[:100]}...")

    def test_circuit_breaker_states(self):
        """Test circuit breaker state transitions."""
        from services.vision.circuit import CircuitState, VisionCircuitBreaker

        cb = VisionCircuitBreaker(
            name="TestCircuit",
            failure_threshold=3,
            recovery_timeout=1,  # 1 second for test
            quota_timeout=2,     # 2 seconds for test
        )

        # Initial state should be CLOSED
        assert cb.state == CircuitState.CLOSED
        can_exec, reason = cb.can_execute()
        assert can_exec is True
        assert reason == "ok"

        print(f"  Initial state: {cb.state.value}")

        # Record failures up to threshold
        cb.record_failure("error")
        assert cb.state == CircuitState.CLOSED  # Still closed
        cb.record_failure("error")
        assert cb.state == CircuitState.CLOSED  # Still closed
        cb.record_failure("error")

        # Should now be OPEN
        assert cb.state == CircuitState.OPEN
        can_exec, reason = cb.can_execute()
        assert can_exec is False
        assert reason == "circuit_open"

        print(f"  After 3 failures: {cb.state.value}")

        # Wait for recovery timeout
        time.sleep(1.1)

        # Should transition to HALF_OPEN
        assert cb.state == CircuitState.HALF_OPEN
        can_exec, reason = cb.can_execute()
        assert can_exec is True
        assert reason == "testing"

        print(f"  After timeout: {cb.state.value}")

        # Record success - should go back to CLOSED
        cb.record_success()
        assert cb.state == CircuitState.CLOSED

        print(f"  After success: {cb.state.value}")
        print("[PASS] Circuit breaker state transitions verified")

    def test_circuit_breaker_quota_errors(self):
        """Test circuit breaker quota error handling."""
        from services.vision.circuit import CircuitState, VisionCircuitBreaker

        cb = VisionCircuitBreaker(
            name="QuotaTest",
            failure_threshold=3,
            recovery_timeout=60,
            quota_timeout=1,  # 1 second for test
        )

        # Quota error should immediately open circuit
        cb.record_failure("quota")
        assert cb.state == CircuitState.OPEN

        can_exec, reason = cb.can_execute()
        assert can_exec is False
        assert reason == "quota_exceeded"

        # Wait for quota timeout
        time.sleep(1.1)

        # Should transition to HALF_OPEN
        assert cb.state == CircuitState.HALF_OPEN

        print("[PASS] Circuit breaker quota error handling verified")


# =============================================================================
# 3. SCOPE GUARD MODULE TESTS
# =============================================================================

class TestScopeGuardModule:
    """Test Scope Guard mandate generation and state machine."""

    def test_mandate_creation_and_verification(self):
        """Test MandateGenerator.create() and .verify()."""
        # Mock settings to avoid needing real encryption key
        with patch('core.config.settings') as mock_settings:
            mock_settings.CHUNK_ENCRYPTION_KEY = "test-encryption-key-32-chars-!"

            from services.scope_guard.mandate import MandateGenerator

            generator = MandateGenerator()
            generator._signing_key = None  # Reset cached key

            # Create mandate
            mandate = generator.create(
                action="delete_scope",
                resource_id="scope-123",
                organization_id="org-456",
                ttl_minutes=30,
            )

            # Verify mandate structure
            assert mandate.action == "delete_scope"
            assert mandate.resource_id == "scope-123"
            assert mandate.organization_id == "org-456"
            assert len(mandate.nonce) == 64  # 32 bytes as hex
            assert len(mandate.signature) == 64  # SHA-256 as hex

            print(f"[PASS] Mandate created: nonce={mandate.nonce[:16]}...")

            # Verify signature
            is_valid = generator.verify(mandate, mandate.signature)
            assert is_valid is True, "Valid signature should verify"

            # Invalid signature should fail
            is_invalid = generator.verify(mandate, "invalid-signature")
            assert is_invalid is False, "Invalid signature should not verify"

            print("[PASS] Mandate signature verification working")

            # Test expiration check
            assert generator.verify_not_expired(mandate) is True

            # Create expired mandate
            expired_mandate = generator.create(
                action="delete_scope",
                resource_id="scope-123",
                organization_id="org-456",
                ttl_minutes=-1,  # Already expired
            )
            assert generator.verify_not_expired(expired_mandate) is False

            print("[PASS] Mandate expiration check working")

    def test_mandate_serialization(self):
        """Test Mandate to_dict and from_dict."""
        with patch('core.config.settings') as mock_settings:
            mock_settings.CHUNK_ENCRYPTION_KEY = "test-encryption-key-32-chars-!"

            from services.scope_guard.mandate import Mandate, MandateGenerator

            generator = MandateGenerator()
            generator._signing_key = None

            mandate = generator.create(
                action="bulk_delete",
                resource_id="batch-789",
                organization_id="org-456",
            )

            # Serialize
            mandate_dict = mandate.to_dict()
            assert isinstance(mandate_dict, dict)
            assert mandate_dict["action"] == "bulk_delete"

            # Deserialize
            restored = Mandate.from_dict(mandate_dict)
            assert restored.action == mandate.action
            assert restored.nonce == mandate.nonce
            assert restored.signature == mandate.signature

            print("[PASS] Mandate serialization/deserialization working")

    def test_approval_state_enum(self):
        """Test ApprovalState enum values."""
        from services.scope_guard.state_machine import ApprovalState

        expected_states = ["pending", "approved", "rejected", "expired", "executed"]
        actual_states = [s.value for s in ApprovalState]

        assert set(actual_states) == set(expected_states)
        print(f"[PASS] ApprovalState enum: {actual_states}")

    def test_action_type_enum(self):
        """Test ActionType enum values."""
        from services.scope_guard.state_machine import ActionType

        expected_actions = [
            "delete_scope", "bulk_delete", "purge_all",
            "revoke_access", "delete_connector"
        ]
        actual_actions = [a.value for a in ActionType]

        assert set(actual_actions) == set(expected_actions)
        print(f"[PASS] ActionType enum: {actual_actions}")

    def test_state_machine_requires_approval(self):
        """Test state machine approval requirements."""
        from services.scope_guard.state_machine import (
            ActionType,
            ScopeGuardStateMachine,
        )

        sm = ScopeGuardStateMachine()

        # These should require approval
        assert sm.requires_approval(ActionType.DELETE_SCOPE) is True
        assert sm.requires_approval(ActionType.BULK_DELETE) is True
        assert sm.requires_approval(ActionType.PURGE_ALL) is True

        # These should not require approval
        assert sm.requires_approval(ActionType.REVOKE_ACCESS) is False
        assert sm.requires_approval(ActionType.DELETE_CONNECTOR) is False

        print("[PASS] State machine approval requirements correct")


# =============================================================================
# 4. CONSENT MODULE TESTS
# =============================================================================

class TestConsentModule:
    """Test Consent management module."""

    def test_consent_type_enum(self):
        """Test ConsentType enum values."""
        from services.consent.manager import ConsentType

        assert ConsentType.AI_LEARNING.value == "ai_learning"
        assert ConsentType.EXTERNAL_AGENTS.value == "external_agents"

        print(f"[PASS] ConsentType enum: {[ct.value for ct in ConsentType]}")

    def test_consent_level_enum(self):
        """Test ConsentLevel enum values."""
        from services.consent.manager import ConsentLevel

        expected_levels = ["organization", "scope", "document"]
        actual_levels = [cl.value for cl in ConsentLevel]

        assert set(actual_levels) == set(expected_levels)
        print(f"[PASS] ConsentLevel enum: {actual_levels}")

    def test_consent_decision_dataclass(self):
        """Test ConsentDecision dataclass."""
        from services.consent.manager import ConsentDecision, ConsentLevel, ConsentType

        decision = ConsentDecision(
            allowed=True,
            level=ConsentLevel.ORGANIZATION,
            consent_type=ConsentType.EXTERNAL_AGENTS,
            inherited=False,
            agent_specific=False,
        )

        assert decision.allowed is True
        assert decision.level == ConsentLevel.ORGANIZATION
        assert decision.consent_type == ConsentType.EXTERNAL_AGENTS

        # Test with inheritance
        inherited_decision = ConsentDecision(
            allowed=True,
            level=ConsentLevel.SCOPE,
            consent_type=ConsentType.AI_LEARNING,
            inherited=True,
        )
        assert inherited_decision.inherited is True

        print("[PASS] ConsentDecision dataclass working")

    def test_consent_manager_evaluate_consent(self):
        """Test ConsentManager._evaluate_consent logic."""
        from services.consent.manager import (
            ConsentLevel,
            ConsentManager,
            ConsentType,
        )

        manager = ConsentManager()

        # Test with consent data allowing AI learning
        consent_data = {
            "allow_ai_learning": True,
            "allow_external_agents": False,
        }

        decision = manager._evaluate_consent(
            consent_data=consent_data,
            consent_type=ConsentType.AI_LEARNING,
            agent_id=None,
            level=ConsentLevel.ORGANIZATION,
        )
        assert decision.allowed is True
        assert decision.level == ConsentLevel.ORGANIZATION

        # Test external agents (should be denied)
        decision2 = manager._evaluate_consent(
            consent_data=consent_data,
            consent_type=ConsentType.EXTERNAL_AGENTS,
            agent_id=None,
            level=ConsentLevel.ORGANIZATION,
        )
        assert decision2.allowed is False

        print("[PASS] ConsentManager._evaluate_consent working")

    def test_consent_manager_agent_specific(self):
        """Test agent-specific consent (allowlist/blocklist)."""
        from services.consent.manager import ConsentLevel, ConsentManager, ConsentType

        manager = ConsentManager()

        # Test blocklist
        consent_data = {
            "allow_external_agents": True,
            "blocked_agent_ids": ["blocked-agent-1", "blocked-agent-2"],
            "allowed_agent_ids": [],
        }

        # Blocked agent should be denied
        decision = manager._evaluate_consent(
            consent_data=consent_data,
            consent_type=ConsentType.EXTERNAL_AGENTS,
            agent_id="blocked-agent-1",
            level=ConsentLevel.ORGANIZATION,
        )
        assert decision.allowed is False
        assert decision.agent_specific is True

        # Non-blocked agent should be allowed
        decision2 = manager._evaluate_consent(
            consent_data=consent_data,
            consent_type=ConsentType.EXTERNAL_AGENTS,
            agent_id="allowed-agent-1",
            level=ConsentLevel.ORGANIZATION,
        )
        assert decision2.allowed is True

        # Test allowlist mode
        consent_data_allowlist = {
            "allow_external_agents": True,
            "blocked_agent_ids": [],
            "allowed_agent_ids": ["allowed-agent-1"],
        }

        # Agent in allowlist should be allowed
        decision3 = manager._evaluate_consent(
            consent_data=consent_data_allowlist,
            consent_type=ConsentType.EXTERNAL_AGENTS,
            agent_id="allowed-agent-1",
            level=ConsentLevel.ORGANIZATION,
        )
        assert decision3.allowed is True

        # Agent not in allowlist should be denied
        decision4 = manager._evaluate_consent(
            consent_data=consent_data_allowlist,
            consent_type=ConsentType.EXTERNAL_AGENTS,
            agent_id="other-agent",
            level=ConsentLevel.ORGANIZATION,
        )
        assert decision4.allowed is False

        print("[PASS] Agent-specific consent (allowlist/blocklist) working")

    def test_consent_manager_cache(self):
        """Test consent manager caching."""
        from services.consent.manager import ConsentManager

        manager = ConsentManager()
        manager.CACHE_TTL = 1  # 1 second for testing

        # Set cache
        manager._set_cached("test:key", {"value": 123})

        # Should retrieve from cache
        cached = manager._get_cached("test:key")
        assert cached == {"value": 123}

        # Wait for TTL
        time.sleep(1.1)

        # Should be expired
        expired = manager._get_cached("test:key")
        assert expired is None

        print("[PASS] ConsentManager caching with TTL working")


# =============================================================================
# 5. SECURE CLEANUP MODULE TESTS
# =============================================================================

class TestSecureCleanupModule:
    """Test secure cleanup / Ghost Protocol module."""

    def test_dod_wipe_pass(self):
        """Test _dod_wipe_pass with a temporary file."""
        from services.secure_cleanup import _dod_wipe_pass

        # Create temp file with test content
        with tempfile.NamedTemporaryFile(delete=False) as tf:
            test_data = b"SENSITIVE DATA " * 1000  # ~15KB
            tf.write(test_data)
            temp_path = tf.name

        try:
            file_size = os.path.getsize(temp_path)

            # Pass 1: zeros
            with open(temp_path, 'r+b') as f:
                _dod_wipe_pass(f, file_size, pass_num=1)

            # Verify pass 1 wrote zeros
            with open(temp_path, 'rb') as f:
                content = f.read(100)
                assert content == b'\x00' * 100, "Pass 1 should write zeros"

            print("[PASS] DoD wipe pass 1 (zeros) verified")

            # Pass 2: ones
            with open(temp_path, 'r+b') as f:
                _dod_wipe_pass(f, file_size, pass_num=2)

            # Verify pass 2 wrote ones
            with open(temp_path, 'rb') as f:
                content = f.read(100)
                assert content == b'\xFF' * 100, "Pass 2 should write ones"

            print("[PASS] DoD wipe pass 2 (0xFF) verified")

            # Pass 3: random
            with open(temp_path, 'r+b') as f:
                _dod_wipe_pass(f, file_size, pass_num=3)

            # Verify pass 3 wrote random (not all zeros or ones)
            with open(temp_path, 'rb') as f:
                content = f.read(100)
                assert content != b'\x00' * 100, "Pass 3 should not be all zeros"
                assert content != b'\xFF' * 100, "Pass 3 should not be all ones"

            print("[PASS] DoD wipe pass 3 (random) verified")

        finally:
            if os.path.exists(temp_path):
                os.unlink(temp_path)

    def test_verify_erasure(self):
        """Test _verify_erasure on wiped file."""
        from services.secure_cleanup import _verify_erasure

        # Create file with random data (should pass verification)
        with tempfile.NamedTemporaryFile(delete=False) as tf:
            tf.write(os.urandom(10000))
            random_path = tf.name

        try:
            file_size = os.path.getsize(random_path)
            result = _verify_erasure(random_path, file_size)
            assert result is True, "Random data should pass verification"
            print("[PASS] _verify_erasure passes for random data")
        finally:
            os.unlink(random_path)

        # Create file with all zeros (should fail verification)
        with tempfile.NamedTemporaryFile(delete=False) as tf:
            tf.write(b'\x00' * 10000)
            zeros_path = tf.name

        try:
            file_size = os.path.getsize(zeros_path)
            result = _verify_erasure(zeros_path, file_size)
            assert result is False, "All-zeros should fail verification"
            print("[PASS] _verify_erasure fails for all-zeros pattern")
        finally:
            os.unlink(zeros_path)

        # Create file with all ones (should fail verification)
        with tempfile.NamedTemporaryFile(delete=False) as tf:
            tf.write(b'\xFF' * 10000)
            ones_path = tf.name

        try:
            file_size = os.path.getsize(ones_path)
            result = _verify_erasure(ones_path, file_size)
            assert result is False, "All-ones should fail verification"
            print("[PASS] _verify_erasure fails for all-ones pattern")
        finally:
            os.unlink(ones_path)

    def test_secure_wipe_full(self):
        """Test full secure_wipe function."""
        from services.secure_cleanup import secure_wipe

        # Create temp file
        with tempfile.NamedTemporaryFile(delete=False, suffix=".test") as tf:
            test_data = b"TOP SECRET DOCUMENT CONTENT " * 500
            tf.write(test_data)
            temp_path = tf.name

        original_size = os.path.getsize(temp_path)

        # Wipe the file
        result = secure_wipe(temp_path, passes=3, pattern="dod_5220_22_m", verify=True)

        assert result is True, "secure_wipe should return True on success"
        assert not os.path.exists(temp_path), "File should be deleted after wipe"

        print(f"[PASS] secure_wipe completed for {original_size} byte file")

    def test_secure_wipe_nonexistent_file(self):
        """Test secure_wipe on non-existent file."""
        from services.secure_cleanup import secure_wipe

        result = secure_wipe("/nonexistent/path/file.txt")
        assert result is False, "secure_wipe should return False for non-existent file"

        print("[PASS] secure_wipe handles non-existent file correctly")

    def test_secure_temp_file_context_manager(self):
        """Test SecureTempFile context manager."""
        from services.secure_cleanup import SecureTempFile

        created_path = None

        with SecureTempFile(suffix=".pdf") as path:
            created_path = path
            assert os.path.exists(path), "Temp file should exist within context"
            assert path.endswith(".pdf"), "Temp file should have correct suffix"

            # Write some data
            with open(path, 'wb') as f:
                f.write(b"Sensitive PDF content")

            # Verify data was written
            assert os.path.getsize(path) > 0

            print(f"[PASS] SecureTempFile created: {os.path.basename(path)}")

        # File should be wiped after context exit
        assert not os.path.exists(created_path), "File should be wiped after context exit"
        print("[PASS] SecureTempFile automatically wiped on context exit")

    def test_smart_buffer_ram_backed(self):
        """Test SmartBuffer with small content (RAM-backed)."""
        from services.secure_cleanup import SmartBuffer

        small_content = b"Small content " * 100  # ~1.4KB

        with SmartBuffer(small_content, filename="small.txt", threshold=1024*1024) as buffer:
            assert buffer.is_ram_backed is True, "Small content should be RAM-backed"
            assert buffer.path is None, "RAM-backed buffer should not have path"

            # Test get_bytes
            retrieved = buffer.get_bytes()
            assert retrieved == small_content

            # Test get_stream
            stream = buffer.get_stream()
            stream_content = stream.read()
            assert stream_content == small_content

        print("[PASS] SmartBuffer RAM-backed mode working")

    def test_smart_buffer_disk_backed(self):
        """Test SmartBuffer with large content (disk-backed)."""
        from services.secure_cleanup import SmartBuffer

        # Use small threshold to force disk backing
        large_content = b"Large content " * 1000

        with SmartBuffer(large_content, filename="large.txt", threshold=100) as buffer:
            assert buffer.is_ram_backed is False, "Large content should be disk-backed"
            assert buffer.path is not None, "Disk-backed buffer should have path"
            assert os.path.exists(buffer.path), "Temp file should exist"

            # Test get_bytes
            retrieved = buffer.get_bytes()
            assert retrieved == large_content

            temp_path = buffer.path

        # File should be wiped after context exit
        assert not os.path.exists(temp_path), "Disk-backed file should be wiped"
        print("[PASS] SmartBuffer disk-backed mode with auto-cleanup working")

    def test_smart_buffer_write_to_temp(self):
        """Test SmartBuffer.write_to_temp()."""
        from services.secure_cleanup import SmartBuffer, secure_wipe

        content = b"Test content for parser"

        with SmartBuffer(content, filename="test.pdf") as buffer:
            temp_path = buffer.write_to_temp()
            assert os.path.exists(temp_path), "write_to_temp should create file"
            assert temp_path.endswith(".pdf"), "Should preserve suffix"

            with open(temp_path, 'rb') as f:
                assert f.read() == content

            # Clean up the additional temp file
            secure_wipe(temp_path)

        print("[PASS] SmartBuffer.write_to_temp() working")

    def test_temp_file_tracking(self):
        """Test temp file registration for emergency cleanup."""
        from services.secure_cleanup import (
            _register_temp_file,
            _tracked_temp_files,
            _unregister_temp_file,
        )

        test_path = "/tmp/test_tracking_file.txt"

        # Register
        _register_temp_file(test_path)
        assert test_path in _tracked_temp_files

        # Unregister
        _unregister_temp_file(test_path)
        assert test_path not in _tracked_temp_files

        print("[PASS] Temp file tracking (dead man's switch) working")


# =============================================================================
# RUN ALL TESTS
# =============================================================================

def run_all_tests():
    """Run all tests manually (for direct execution)."""
    print("=" * 70)
    print("COMPREHENSIVE INTEGRATION TESTS FOR NEW MODULES")
    print("=" * 70)

    test_classes = [
        ("MCP Module", TestMCPModule),
        ("Vision LLM Module", TestVisionModule),
        ("Scope Guard Module", TestScopeGuardModule),
        ("Consent Module", TestConsentModule),
        ("Secure Cleanup Module", TestSecureCleanupModule),
    ]

    total_passed = 0
    total_failed = 0

    for module_name, test_class in test_classes:
        print(f"\n{'='*70}")
        print(f"Testing: {module_name}")
        print("=" * 70)

        instance = test_class()
        test_methods = [m for m in dir(instance) if m.startswith("test_")]

        for method_name in test_methods:
            try:
                print(f"\n  Running: {method_name}")
                method = getattr(instance, method_name)
                method()
                total_passed += 1
            except Exception as e:
                print(f"  [FAIL] {method_name}: {e}")
                total_failed += 1

    print("\n" + "=" * 70)
    print(f"RESULTS: {total_passed} passed, {total_failed} failed")
    print("=" * 70)

    return total_failed == 0


if __name__ == "__main__":
    import sys
    success = run_all_tests()
    sys.exit(0 if success else 1)
