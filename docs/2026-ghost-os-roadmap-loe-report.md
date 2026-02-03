# Axiohub 2026 Ghost OS & Agentic Roadmap
## Compatibility Analysis and Level of Effort (LOE) Report

**Document Version:** 1.0
**Date:** 2026-02-03
**Prepared By:** Lead Architect
**Classification:** Internal Technical Document

---

## Executive Summary

This report provides a comprehensive analysis of the Axiohub codebase against the 2026 Ghost OS & Agentic Roadmap requirements. Each item has been evaluated for current state gaps, implementation complexity, and Ghost Protocol compatibility risks.

| Item | Priority | Effort | Man-Days | Risk Level |
|------|----------|--------|----------|------------|
| DoD 5220.22-M Wipe Automation | P0 | **M** | 5-7 | Low |
| MCP Server Implementation | P0 | **XL** | 20-25 | Medium |
| Vision LLM Description Layer | P1 | **L** | 12-15 | Medium |
| Scope Guard Action Approval | P1 | **L** | 10-12 | Low |
| KVKK 2026 Granular Consent | P2 | **L** | 12-15 | Medium |

**Total Estimated Effort:** 59-74 man-days

---

## 1. [P0] DoD 5220.22-M Wipe Automation

### 1.1 Current Status

**File:** `backend/services/secure_cleanup.py` (579 lines)

| Aspect | Current State | Gap |
|--------|---------------|-----|
| Wipe Pattern | ALL passes use `os.urandom()` only | Does NOT follow DoD 5220.22-M (0x00 → 0xFF → Random) |
| Pass Count | Configurable 1 or 3 (default: 1) | Default should be 3 for enterprise |
| Verify Read | **NOT IMPLEMENTED** | No post-erasure verification layer |
| Disk Sync | Uses `fsync()` after each pass | Compliant |
| Chunk Size | 1MB chunks | Memory efficient |

**Code Reference - Current Implementation:**
```python
# secure_cleanup.py:220-245
# Current: All passes write random data
for pass_num in range(passes):
    f.seek(0)
    remaining = file_size
    while remaining > 0:
        chunk = min(1024 * 1024, remaining)
        f.write(os.urandom(chunk))  # Always random, not DoD pattern
        remaining -= chunk
    f.flush()
    os.fsync(f.fileno())
```

### 1.2 Technical Implementation Plan

#### Phase 1: Implement DoD 5220.22-M Pattern (2 days)

**Modify:** `backend/services/secure_cleanup.py`

```python
# NEW: Add pattern-aware wipe pass function
def _dod_wipe_pass(
    f: BinaryIO,
    file_size: int,
    pass_num: int,  # 1, 2, or 3
    chunk_size: int = 1024 * 1024
) -> None:
    """
    DoD 5220.22-M compliant wipe pass.
    Pass 1: 0x00 (zeros)
    Pass 2: 0xFF (ones)
    Pass 3: Random data
    """
    f.seek(0)
    remaining = file_size

    while remaining > 0:
        write_size = min(chunk_size, remaining)
        if pass_num == 1:
            data = b'\x00' * write_size
        elif pass_num == 2:
            data = b'\xFF' * write_size
        else:
            data = os.urandom(write_size)
        f.write(data)
        remaining -= write_size

    f.flush()
    os.fsync(f.fileno())
```

#### Phase 2: Add Verify Read Layer (2 days)

**Modify:** `backend/services/secure_cleanup.py`

```python
# NEW: Post-erasure verification
def _verify_erasure(
    path: str,
    file_size: int,
    sample_count: int = 3,
    chunk_size: int = 1024
) -> bool:
    """
    Verify file content is randomized (not original data).

    Samples 3 positions and checks entropy.
    """
    try:
        with open(path, 'rb') as f:
            for i in range(sample_count):
                offset = (file_size // (sample_count + 1)) * (i + 1)
                f.seek(offset)
                sample = f.read(min(chunk_size, file_size - offset))

                # Fail if sample is all zeros (pattern leak)
                if sample == b'\x00' * len(sample):
                    return False
                # Fail if sample is all ones (pattern leak)
                if sample == b'\xFF' * len(sample):
                    return False
        return True
    except Exception:
        return False
```

#### Phase 3: Configuration Updates (1 day)

**Modify:** `backend/core/config.py`

```python
# Ghost Protocol Configuration (lines 169-191)
SECURE_WIPE_PASSES: int = 3  # CHANGED: Default to DoD 3-pass
SECURE_WIPE_PATTERN: str = "dod_5220_22_m"  # NEW: "random" | "dod_5220_22_m"
SECURE_WIPE_VERIFY: bool = True  # NEW: Enable verify read
```

#### Phase 4: Metrics & Testing (1-2 days)

**Modify:** `backend/core/metrics.py`

```python
# NEW metrics
secure_wipe_verify_total = Counter(
    "ghost_protocol_secure_wipe_verify_total",
    "Verify read results",
    ["result"]  # "pass" | "fail"
)
secure_wipe_pattern_total = Counter(
    "ghost_protocol_secure_wipe_pattern_total",
    "Wipe patterns used",
    ["pattern"]  # "random" | "dod_5220_22_m"
)
```

### 1.3 Estimated Effort

| Task | Effort |
|------|--------|
| DoD pattern implementation | 2 days |
| Verify read layer | 2 days |
| Config + metrics | 1 day |
| Testing + edge cases | 1-2 days |
| **Total** | **5-7 days (M)** |

### 1.4 Risk Factors

| Risk | Impact | Mitigation |
|------|--------|------------|
| SSD wear-leveling bypass | Medium | Document limitation; DoD pattern provides compliance, not physical guarantee on SSDs |
| Performance degradation (3x I/O) | Low | Make pattern configurable; keep "random" option for non-regulated data |
| Verify read false positives | Low | Sample-based verification; don't check every byte |
| Emergency cleanup timeout | Medium | Emergency handler falls back to single random pass |

**Ghost Protocol Compatibility:** FULLY COMPATIBLE - Enhances zero-retention guarantee

---

## 2. [P0 - Agentic] MCP Server Implementation

### 2.1 Current Status

**Finding:** NO MCP/JSON-RPC implementation exists in the codebase.

| Aspect | Current State | Gap |
|--------|---------------|-----|
| Protocol | REST/HTTP only (FastAPI) | No JSON-RPC 2.0 layer |
| Agent Access | None | No MCP Host/Server architecture |
| Tool Exposure | N/A | No tool definitions for AI agents |
| Zero-Retention | REST responses not marked ephemeral | Need MCP-specific ephemeral markers |

**Existing Infrastructure to Leverage:**
- `backend/api/v1/chat.py` - RAG implementation (can be exposed as MCP tool)
- `backend/services/scope_analysis.py` - Scope disambiguation (reuse for MCP)
- `backend/api/v1/dependencies.py` - Auth patterns (adapt for API keys)
- `backend/services/audit.py` - Audit logging (extend for MCP events)

### 2.2 Technical Implementation Plan

#### Phase 1: MCP Core Infrastructure (5 days)

**Create:** `backend/mcp/` module

```
backend/mcp/
├── __init__.py
├── server.py          # JSON-RPC 2.0 handler
├── tools.py           # Tool definitions
├── resources.py       # Resource handlers
├── auth.py            # API key authentication
└── zero_retention.py  # Ghost Protocol enforcement
```

**server.py - Core Classes:**

```python
class JSONRPCRequest(BaseModel):
    jsonrpc: str = "2.0"
    method: str
    params: Optional[Dict[str, Any]] = None
    id: Optional[str | int] = None

class MCPServer:
    """Model Context Protocol Server for AI agent access."""

    METHODS = {
        "initialize": "handle_initialize",
        "tools/list": "handle_tools_list",
        "tools/call": "handle_tools_call",
        "resources/list": "handle_resources_list",
        "resources/read": "handle_resources_read",
    }

    async def handle_request(
        self,
        request: JSONRPCRequest,
        organization_id: str,
        agent_id: str,
    ) -> JSONRPCResponse:
        """Route JSON-RPC request to handler."""
```

#### Phase 2: Tool Definitions (4 days)

**Create:** `backend/mcp/tools.py`

```python
MCP_TOOLS = [
    {
        "name": "search_documents",
        "description": "Semantic search over organization knowledge base",
        "inputSchema": {
            "type": "object",
            "properties": {
                "query": {"type": "string"},
                "scope_ids": {"type": "array", "items": {"type": "string"}},
                "limit": {"type": "integer", "default": 10},
            },
            "required": ["query"],
        },
    },
    {
        "name": "ask_question",
        "description": "RAG-based Q&A with source citations",
        "inputSchema": {
            "type": "object",
            "properties": {
                "question": {"type": "string"},
                "scope_id": {"type": "string"},
            },
            "required": ["question"],
        },
    },
    {
        "name": "list_scopes",
        "description": "List available document scopes/sources",
        "inputSchema": {"type": "object", "properties": {}},
    },
]
```

#### Phase 3: Authentication Layer (3 days)

**Create:** `backend/mcp/auth.py`

```python
class MCPApiKey(BaseModel):
    """API key for MCP agent access."""
    id: str
    organization_id: str
    agent_name: str
    scopes: List[str]  # Allowed scope patterns
    created_at: datetime
    expires_at: Optional[datetime]

async def verify_mcp_api_key(
    api_key: str,
) -> MCPApiKey:
    """Verify API key and return agent context."""
```

**Database Migration:**

```sql
CREATE TABLE mcp_api_keys (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    organization_id UUID NOT NULL REFERENCES teams(id),
    key_hash TEXT NOT NULL UNIQUE,  -- SHA-256 of actual key
    agent_name TEXT NOT NULL,
    scopes TEXT[] DEFAULT '{"*"}',
    created_at TIMESTAMPTZ DEFAULT now(),
    expires_at TIMESTAMPTZ,
    revoked_at TIMESTAMPTZ
);
```

#### Phase 4: Zero-Retention Enforcement (3 days)

**Create:** `backend/mcp/zero_retention.py`

```python
class MCPZeroRetention:
    """Ghost Protocol enforcement for MCP responses."""

    @staticmethod
    def wrap_response(content: Any, metadata: dict) -> dict:
        return {
            "content": content,
            "ephemeral": True,
            "retention_policy": "zero",
            "_ghost_protocol": True,
        }

    @staticmethod
    def audit_access(
        organization_id: str,
        agent_id: str,
        tool_name: str,
        resource_id: Optional[str],
    ) -> None:
        """Log access WITHOUT storing content."""
```

#### Phase 5: FastAPI Integration (3 days)

**Create:** `backend/api/v1/mcp.py`

```python
@router.post("/mcp/v1/rpc")
async def mcp_rpc_endpoint(
    request: Request,
    body: JSONRPCRequest,
    api_key: MCPApiKey = Depends(verify_mcp_api_key),
):
    """JSON-RPC 2.0 endpoint for MCP agents."""
    server = MCPServer()
    response = await server.handle_request(
        body,
        organization_id=api_key.organization_id,
        agent_id=api_key.id,
    )
    return Response(
        content=response.json(),
        media_type="application/json",
        headers={"Cache-Control": "no-store"},
    )
```

**Modify:** `backend/main.py`

```python
from api.v1.mcp import router as mcp_router
app.include_router(mcp_router, prefix="/api/v1", tags=["mcp"])
```

#### Phase 6: Testing & Documentation (3-4 days)

- Unit tests for JSON-RPC handler
- Integration tests with mock AI agent
- MCP specification compliance validation
- API documentation for external agents

### 2.3 Estimated Effort

| Task | Effort |
|------|--------|
| MCP core infrastructure | 5 days |
| Tool definitions | 4 days |
| Authentication layer | 3 days |
| Zero-retention enforcement | 3 days |
| FastAPI integration | 3 days |
| Testing & documentation | 3-4 days |
| **Total** | **20-25 days (XL)** |

### 2.4 Risk Factors

| Risk | Impact | Mitigation |
|------|--------|------------|
| Agent content caching | High | Mark ALL responses as ephemeral; `Cache-Control: no-store` |
| Audit log content leak | High | Log tool calls + resource IDs only, NEVER content |
| Scope bypass via MCP | High | Enforce same RLS as REST API; scope whitelist per API key |
| API key exposure | Medium | Use hashed keys; support rotation; separate from JWT |
| Rate limiting abuse | Medium | Per-key rate limits; circuit breaker per agent |

**Ghost Protocol Compatibility:** REQUIRES CAREFUL DESIGN - Must enforce zero-retention at every response point

---

## 3. [P1 - Multimodal] Vision LLM Description Layer

### 3.1 Current Status

**File:** `backend/services/parsers.py` (2283 lines)

| Aspect | Current State | Gap |
|--------|---------------|-----|
| Image Processing | Tesseract OCR (local) + LlamaParse fallback | OCR extracts text only, no semantic understanding |
| Diagram Analysis | None | No "meaning" extraction from technical diagrams |
| Vision LLM | **NOT IMPLEMENTED** | No GPT-4V/Gemini Pro Vision integration |
| Image Destruction | SmartBuffer + secure_wipe | Already compliant |

**Current ImageProcessor Flow:**
```
Image → Tesseract OCR → Raw text → Embeddings
         ↓ (if <20 tokens)
      LlamaParse → Markdown text → Embeddings
```

**Missing:**
```
Image → Vision LLM → Semantic description → Embeddings
         ("This flowchart shows data flowing from A to B...")
```

### 3.2 Technical Implementation Plan

#### Phase 1: Vision Processor Abstraction (2 days)

**Create:** `backend/services/vision/` module

```
backend/services/vision/
├── __init__.py
├── base.py             # Abstract VisionProcessor
├── openai_vision.py    # GPT-4o implementation
├── gemini_vision.py    # Gemini Pro Vision implementation
└── circuit.py          # Vision-specific circuit breakers
```

**base.py:**

```python
from abc import ABC, abstractmethod
from dataclasses import dataclass

@dataclass
class VisionResult:
    description: str
    diagram_type: Optional[str]  # flowchart, chart, architecture, etc.
    entities: List[str]
    confidence: float
    model_used: str

class VisionProcessor(ABC):
    @abstractmethod
    async def analyze_image(
        self,
        image_bytes: bytes,
        filename: str,
        prompt: Optional[str] = None,
    ) -> VisionResult:
        pass
```

#### Phase 2: GPT-4o Vision Implementation (3 days)

**Create:** `backend/services/vision/openai_vision.py`

```python
class GPT4VisionProcessor(VisionProcessor):
    SYSTEM_PROMPT = """Analyze this image as a technical diagram expert.

    Provide:
    1. Detailed description of what the diagram shows
    2. Diagram type (flowchart/architecture/chart/schematic/etc.)
    3. Key entities and their relationships
    4. Any visible text labels

    Format as structured markdown."""

    async def analyze_image(
        self,
        image_bytes: bytes,
        filename: str,
        prompt: Optional[str] = None,
    ) -> VisionResult:
        from openai import AsyncOpenAI

        client = AsyncOpenAI()
        base64_image = base64.b64encode(image_bytes).decode()

        response = await client.chat.completions.create(
            model="gpt-4o",
            messages=[
                {"role": "system", "content": self.SYSTEM_PROMPT},
                {
                    "role": "user",
                    "content": [
                        {"type": "text", "text": prompt or "Analyze this diagram:"},
                        {
                            "type": "image_url",
                            "image_url": {
                                "url": f"data:image/png;base64,{base64_image}",
                                "detail": "high",
                            },
                        },
                    ],
                },
            ],
            max_tokens=1500,
        )

        return VisionResult(
            description=response.choices[0].message.content,
            model_used="gpt-4o",
            confidence=0.9,
        )
```

#### Phase 3: Gemini Pro Vision Implementation (2 days)

**Create:** `backend/services/vision/gemini_vision.py`

```python
class GeminiVisionProcessor(VisionProcessor):
    async def analyze_image(
        self,
        image_bytes: bytes,
        filename: str,
        prompt: Optional[str] = None,
    ) -> VisionResult:
        import google.generativeai as genai

        model = genai.GenerativeModel('gemini-pro-vision')
        response = await model.generate_content_async([
            prompt or "Analyze this technical diagram in detail:",
            {"mime_type": "image/png", "data": image_bytes}
        ])

        return VisionResult(
            description=response.text,
            model_used="gemini-pro-vision",
        )
```

#### Phase 4: Parser Integration (3 days)

**Modify:** `backend/services/parsers.py` - ImageProcessor class

```python
class ImageProcessor(BaseProcessor):
    """
    4-Tier Resilient Image Processing:

    Tier 1: Tesseract OCR (fast, free, text-only)
    Tier 2: LlamaParse (cloud OCR, better quality)
    Tier 3: Vision LLM (semantic understanding) ← NEW
    Tier 4: Metadata fallback (EXIF only)
    """

    async def process(self, content: bytes, filename: str) -> ProcessedDocument:
        # Tier 1: Tesseract
        text = await self._tesseract_ocr(content)
        if self._has_sufficient_content(text):
            return self._build_result(text, "tesseract")

        # Tier 2: LlamaParse
        if self._llamaparse_available():
            text = await self._llamaparse_ocr(content, filename)
            if self._has_sufficient_content(text):
                return self._build_result(text, "llamaparse")

        # Tier 3: Vision LLM (NEW)
        if settings.VISION_LLM_ENABLED:
            result = await self._vision_llm_analyze(content, filename)
            if result:
                return self._build_result(result.description, "vision_llm")

        # Tier 4: Metadata fallback
        return self._build_metadata_result(filename)

    async def _vision_llm_analyze(
        self,
        content: bytes,
        filename: str,
    ) -> Optional[VisionResult]:
        """NEW: Vision LLM semantic analysis with secure cleanup."""
        from services.vision.openai_vision import GPT4VisionProcessor
        from services.secure_cleanup import SmartBuffer

        with SmartBuffer(content, filename=filename) as buffer:
            processor = GPT4VisionProcessor()
            try:
                return await processor.analyze_image(
                    buffer.get_bytes(),
                    filename,
                )
            except Exception as e:
                logger.warning(f"Vision LLM failed: {e}")
                return None
            # SmartBuffer auto-wipes on exit
```

#### Phase 5: Configuration & Metrics (1 day)

**Modify:** `backend/core/config.py`

```python
# Vision LLM Configuration
VISION_LLM_ENABLED: bool = False  # Opt-in (cost consideration)
VISION_LLM_PROVIDER: str = "openai"  # "openai" | "gemini"
VISION_LLM_MAX_IMAGE_SIZE: int = 20 * 1024 * 1024  # 20MB
```

**Modify:** `backend/core/metrics.py`

```python
vision_llm_total = Counter(
    "vision_llm_analysis_total",
    "Vision LLM analysis attempts",
    ["provider", "result"]
)
vision_llm_duration = Histogram(
    "vision_llm_analysis_duration_seconds",
    "Vision LLM analysis duration",
    ["provider"]
)
```

#### Phase 6: Testing (2-3 days)

- Unit tests with mock Vision APIs
- Integration tests with real diagrams
- Cost estimation tests (token counting)

### 3.3 Estimated Effort

| Task | Effort |
|------|--------|
| Vision processor abstraction | 2 days |
| GPT-4o implementation | 3 days |
| Gemini implementation | 2 days |
| Parser integration | 3 days |
| Config + metrics | 1 day |
| Testing | 2-3 days |
| **Total** | **12-15 days (L)** |

### 3.4 Risk Factors

| Risk | Impact | Mitigation |
|------|--------|------------|
| Image data sent to cloud | Medium | HTTPS only; audit log (no content); document in privacy policy |
| Vision LLM cost (GPT-4o expensive) | Medium | Make opt-in; default disabled; per-org billing cap |
| API rate limits | Medium | Circuit breaker; fallback to OCR tier |
| Hallucinated descriptions | Low | Include confidence score; human review option |

**Ghost Protocol Compatibility:** COMPATIBLE - SmartBuffer ensures secure image destruction after processing

---

## 4. [P1 - UX] Scope Guard Action Approval (Human-in-the-loop)

### 4.1 Current Status

**File:** `backend/services/scope_analysis.py`

| Aspect | Current State | Gap |
|--------|---------------|-----|
| Scope Disambiguation | HTTP 300 with clarification candidates | Query clarification only, not action approval |
| State Machine | None | No multi-state approval workflow |
| Pause Mode | None | No system pause for critical actions |
| Cryptographic Mandate | None | No signature-based approval |

**Current Flow (Query Clarification):**
```
User Query → Scope Analysis → FRAGMENTED? → HTTP 300 + candidates
                                         → User selects scope → Re-query
```

**Missing (Action Approval):**
```
Agent Action → Pause → Generate Mandate → Admin Approves (signature)
                                        → Execute Action
```

### 4.2 Technical Implementation Plan

#### Phase 1: State Machine Infrastructure (3 days)

**Create:** `backend/services/scope_guard/` module

```
backend/services/scope_guard/
├── __init__.py
├── state_machine.py    # FSM implementation
├── mandate.py          # Cryptographic mandate
├── actions.py          # Action type definitions
└── executor.py         # Approved action executor
```

**state_machine.py:**

```python
class ApprovalState(str, Enum):
    PENDING = "pending"
    APPROVED = "approved"
    REJECTED = "rejected"
    EXPIRED = "expired"
    EXECUTED = "executed"

class ActionType(str, Enum):
    DELETE_SCOPE = "delete_scope"
    BULK_DELETE = "bulk_delete"
    PURGE_ALL = "purge_all"
    REVOKE_ACCESS = "revoke_access"

class ScopeGuardStateMachine:
    """
    State transitions:
    IDLE → PENDING → APPROVED → EXECUTED
                  → REJECTED
                  → EXPIRED (30 min timeout)
    """

    APPROVAL_REQUIRED = {
        ActionType.DELETE_SCOPE,
        ActionType.BULK_DELETE,
        ActionType.PURGE_ALL,
    }

    async def request_approval(
        self,
        action_type: ActionType,
        resource_id: str,
        organization_id: str,
        requested_by: str,
    ) -> dict:
        """Enter PENDING state, generate mandate."""

    async def approve(
        self,
        approval_id: str,
        approver_id: str,
        signature: str,
    ) -> dict:
        """Transition PENDING → APPROVED with signature verification."""

    async def execute(
        self,
        approval_id: str,
        mandate_signature: str,
    ) -> dict:
        """Transition APPROVED → EXECUTED."""
```

#### Phase 2: Cryptographic Mandate (2 days)

**Create:** `backend/services/scope_guard/mandate.py`

```python
@dataclass
class Mandate:
    action: str
    resource_id: str
    organization_id: str
    nonce: str  # 32-byte random
    created_at: str
    expires_at: str
    signature: str  # HMAC-SHA256

class MandateGenerator:
    @classmethod
    def create(
        cls,
        action: str,
        resource_id: str,
        organization_id: str,
        ttl_minutes: int = 30,
    ) -> Mandate:
        nonce = secrets.token_hex(32)
        now = datetime.now(timezone.utc)

        mandate_data = {
            "action": action,
            "resource_id": resource_id,
            "organization_id": organization_id,
            "nonce": nonce,
            "created_at": now.isoformat(),
            "expires_at": (now + timedelta(minutes=ttl_minutes)).isoformat(),
        }

        # Sign with org-specific secret
        signature = hmac.new(
            settings.CHUNK_ENCRYPTION_KEY.encode(),
            json.dumps(mandate_data, sort_keys=True).encode(),
            hashlib.sha256
        ).hexdigest()

        return Mandate(**mandate_data, signature=signature)

    @classmethod
    def verify(cls, mandate: Mandate, signature: str) -> bool:
        computed = cls._compute_signature(mandate)
        return hmac.compare_digest(computed, signature)
```

#### Phase 3: Database Schema (1 day)

**Create:** Migration `20260300000000_scope_guard_approvals.sql`

```sql
CREATE TYPE approval_status AS ENUM (
    'pending', 'approved', 'rejected', 'expired', 'executed'
);

CREATE TABLE action_approvals (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    organization_id UUID NOT NULL REFERENCES teams(id) ON DELETE CASCADE,

    -- Action
    action_type TEXT NOT NULL,
    resource_type TEXT NOT NULL,
    resource_id TEXT NOT NULL,

    -- State
    status approval_status NOT NULL DEFAULT 'pending',

    -- Mandate
    mandate_nonce TEXT NOT NULL UNIQUE,
    mandate_signature TEXT NOT NULL,

    -- Participants
    requested_by UUID NOT NULL,
    approved_by UUID,

    -- Timing
    requested_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    expires_at TIMESTAMPTZ NOT NULL,
    approved_at TIMESTAMPTZ,
    executed_at TIMESTAMPTZ,

    -- Audit
    request_context JSONB DEFAULT '{}',
    execution_result JSONB DEFAULT '{}'
);

CREATE INDEX idx_approvals_pending ON action_approvals(organization_id, status)
    WHERE status = 'pending';
```

#### Phase 4: API Endpoints (2 days)

**Create:** `backend/api/v1/approvals.py`

```python
@router.post("/approvals/request")
async def request_approval(
    payload: ApprovalRequestPayload,
    user_id: str = Depends(get_current_user),
    org_id: str = Depends(get_user_organization_id),
):
    """Request approval for destructive action. Returns mandate."""

@router.post("/approvals/{approval_id}/approve")
async def approve_action(
    approval_id: str,
    user_id: str = Depends(require_admin),
):
    """Admin approves pending action."""

@router.post("/approvals/{approval_id}/execute")
async def execute_approved(
    approval_id: str,
    payload: ExecutePayload,  # Contains mandate signature
    user_id: str = Depends(get_current_user),
):
    """Execute approved action with mandate verification."""

@router.get("/approvals/pending")
async def list_pending(
    user_id: str = Depends(require_admin),
    org_id: str = Depends(get_user_organization_id),
):
    """List pending approvals for admin dashboard."""
```

#### Phase 5: Integration with Existing Endpoints (2 days)

**Modify:** `backend/api/v1/documents.py`

```python
@router.delete("/documents/scope/{scope_id}")
async def delete_scope(
    scope_id: str,
    approval_id: Optional[str] = None,
    mandate_signature: Optional[str] = None,
    user_id: str = Depends(require_admin),
):
    """Delete entire scope - requires approval."""

    if not approval_id:
        # No approval yet - create request and return mandate
        result = await state_machine.request_approval(
            ActionType.DELETE_SCOPE,
            scope_id,
            org_id,
            user_id,
        )
        return JSONResponse(
            status_code=202,  # Accepted but pending
            content=result,
        )

    # Has approval - verify and execute
    await state_machine.execute(approval_id, mandate_signature)
    # ... perform deletion
```

#### Phase 6: Testing (2-3 days)

- State machine transition tests
- Mandate generation/verification tests
- API integration tests
- Timeout/expiry tests

### 4.3 Estimated Effort

| Task | Effort |
|------|--------|
| State machine infrastructure | 3 days |
| Cryptographic mandate | 2 days |
| Database schema | 1 day |
| API endpoints | 2 days |
| Existing endpoint integration | 2 days |
| Testing | 2-3 days |
| **Total** | **10-12 days (L)** |

### 4.4 Risk Factors

| Risk | Impact | Mitigation |
|------|--------|------------|
| Mandate forgery | High | HMAC-SHA256 with org-specific secret derived from encryption key |
| Replay attack | High | Unique nonce per mandate; mark as used after execution |
| Approval bypass | Medium | State machine enforces transitions; DB constraints |
| Admin impersonation | Medium | JWT verification; audit all approvals |
| UX friction | Low | Clear approval UI; 30-min timeout is reasonable |

**Ghost Protocol Compatibility:** FULLY COMPATIBLE - Enhances audit trail; no content storage

---

## 5. [P2 - Compliance] KVKK 2026 Granular Consent Panel

### 5.1 Current Status

**Current Permission Model:**

| Level | Implementation | Gap |
|-------|---------------|-----|
| Organization | Team-based access | No consent tracking |
| Scope | Scope disambiguation | No per-scope consent |
| Document | RLS by organization | No per-document consent |
| Agent | None | No agent-specific consent |

**KVKK 2026 Requirements:**
- Explicit consent for data processing purposes
- Granular consent (per-document, per-purpose)
- Consent withdrawal capability
- Audit trail of consent changes

### 5.2 Technical Implementation Plan

#### Phase 1: Database Schema (2 days)

**Create:** Migration `20260400000000_consent_management.sql`

```sql
-- Organization-level consent defaults
CREATE TABLE organization_consents (
    organization_id UUID PRIMARY KEY REFERENCES teams(id),

    allow_ai_learning BOOLEAN NOT NULL DEFAULT false,
    ai_learning_consent_at TIMESTAMPTZ,
    ai_learning_consented_by UUID,

    allow_external_agents BOOLEAN NOT NULL DEFAULT false,
    external_agents_consent_at TIMESTAMPTZ,
    external_agents_consented_by UUID,

    retention_policy TEXT DEFAULT 'default'
);

-- Scope-level consent overrides
CREATE TABLE scope_consents (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    scope_id TEXT NOT NULL,
    organization_id UUID NOT NULL REFERENCES teams(id),

    inherit_org_consent BOOLEAN NOT NULL DEFAULT true,
    allow_ai_learning BOOLEAN,
    allow_external_agents BOOLEAN,

    allowed_agent_ids TEXT[] DEFAULT '{}',
    blocked_agent_ids TEXT[] DEFAULT '{}',

    consented_by UUID,
    consented_at TIMESTAMPTZ,

    UNIQUE(scope_id, organization_id)
);

-- Document-level consent overrides
CREATE TABLE document_consents (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    document_id UUID NOT NULL REFERENCES documents(id),
    organization_id UUID NOT NULL REFERENCES teams(id),

    inherit_scope_consent BOOLEAN NOT NULL DEFAULT true,
    allow_ai_learning BOOLEAN,
    allow_external_agents BOOLEAN,

    allowed_agent_ids TEXT[] DEFAULT '{}',
    blocked_agent_ids TEXT[] DEFAULT '{}',

    UNIQUE(document_id, organization_id)
);

-- Consent audit log
CREATE TABLE consent_audit_log (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    organization_id UUID NOT NULL,
    consent_level TEXT NOT NULL,  -- 'organization'|'scope'|'document'
    resource_id TEXT NOT NULL,
    field_changed TEXT NOT NULL,
    old_value JSONB,
    new_value JSONB,
    changed_by UUID NOT NULL,
    changed_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    ip_address INET,
    user_agent TEXT
);
```

#### Phase 2: Consent Manager Service (3 days)

**Create:** `backend/services/consent/` module

```
backend/services/consent/
├── __init__.py
├── manager.py     # Consent CRUD + evaluation
├── policy.py      # Policy evaluation engine
└── audit.py       # Consent change audit
```

**manager.py:**

```python
class ConsentManager:
    """
    Consent hierarchy (most specific wins):
    1. Document consent (if not inheriting)
    2. Scope consent (if not inheriting)
    3. Organization consent (always present)
    """

    async def check_consent(
        self,
        organization_id: str,
        consent_type: ConsentType,  # AI_LEARNING | EXTERNAL_AGENTS
        document_id: Optional[str] = None,
        scope_id: Optional[str] = None,
        agent_id: Optional[str] = None,
    ) -> ConsentDecision:
        """Evaluate consent for specific access request."""

        # Check document level
        if document_id:
            doc_consent = await self._get_document_consent(document_id)
            if doc_consent and not doc_consent.inherit_scope_consent:
                return self._evaluate(doc_consent, consent_type, agent_id)

        # Check scope level
        if scope_id:
            scope_consent = await self._get_scope_consent(scope_id)
            if scope_consent and not scope_consent.inherit_org_consent:
                return self._evaluate(scope_consent, consent_type, agent_id)

        # Fall back to org level
        org_consent = await self._get_org_consent(organization_id)
        return self._evaluate(org_consent, consent_type, agent_id)

    async def set_consent(
        self,
        level: ConsentLevel,
        resource_id: str,
        consent_type: ConsentType,
        allowed: bool,
        user_id: str,
        ip_address: str,
    ) -> None:
        """Set consent with audit logging."""
```

#### Phase 3: API Endpoints (3 days)

**Create:** `backend/api/v1/consent.py`

```python
@router.get("/consent/organization")
async def get_org_consent(org_id: str = Depends(get_user_organization_id)):
    """Get organization consent settings."""

@router.patch("/consent/organization")
async def update_org_consent(
    payload: OrgConsentUpdate,
    user_id: str = Depends(require_admin),
):
    """Update organization consent (admin only)."""

@router.get("/consent/scope/{scope_id}")
async def get_scope_consent(scope_id: str):
    """Get scope consent with inheritance resolution."""

@router.patch("/consent/scope/{scope_id}")
async def update_scope_consent(
    scope_id: str,
    payload: ScopeConsentUpdate,
    user_id: str = Depends(require_admin),
):
    """Update scope consent (admin only)."""

@router.get("/consent/document/{document_id}")
async def get_document_consent(document_id: str):
    """Get document consent with inheritance resolution."""

@router.patch("/consent/document/{document_id}")
async def update_document_consent(
    document_id: str,
    payload: DocumentConsentUpdate,
    user_id: str = Depends(require_editor),
):
    """Update document consent."""

@router.get("/consent/audit")
async def get_consent_audit(
    limit: int = 100,
    user_id: str = Depends(require_admin),
):
    """Get consent change audit log."""

@router.get("/consent/report")
async def get_compliance_report(
    user_id: str = Depends(require_admin),
):
    """Generate KVKK compliance report."""
```

#### Phase 4: Integration with Search/Chat (2 days)

**Modify:** `backend/api/v1/search.py`

```python
async def hybrid_search(query: str, ...):
    # After retrieving results, filter by consent
    results = await _raw_search(query)

    consent_manager = ConsentManager()
    filtered = []
    for doc in results:
        decision = await consent_manager.check_consent(
            organization_id=org_id,
            consent_type=ConsentType.EXTERNAL_AGENTS if is_mcp else ConsentType.AI_LEARNING,
            document_id=doc.id,
            scope_id=doc.scope_id,
            agent_id=agent_id,
        )
        if decision.allowed:
            filtered.append(doc)

    return filtered
```

#### Phase 5: MCP Integration (1 day)

**Modify:** `backend/mcp/tools.py`

```python
async def execute_search_tool(params: dict, agent_id: str):
    # Check consent before returning any results
    consent_manager = ConsentManager()

    for doc in results:
        decision = await consent_manager.check_consent(
            consent_type=ConsentType.EXTERNAL_AGENTS,
            document_id=doc.id,
            agent_id=agent_id,
        )
        if not decision.allowed:
            results.remove(doc)
```

#### Phase 6: Testing (2-3 days)

- Consent hierarchy tests
- Inheritance override tests
- Audit logging tests
- KVKK compliance report validation

### 5.3 Estimated Effort

| Task | Effort |
|------|--------|
| Database schema | 2 days |
| Consent manager service | 3 days |
| API endpoints | 3 days |
| Search/Chat integration | 2 days |
| MCP integration | 1 day |
| Testing | 2-3 days |
| **Total** | **12-15 days (L)** |

### 5.4 Risk Factors

| Risk | Impact | Mitigation |
|------|--------|------------|
| Consent bypass via direct DB | High | RLS policies enforce consent checks |
| Performance overhead | Medium | Cache consent decisions (60s TTL) |
| State inconsistency | Medium | Use transactions for consent + audit |
| Retroactive consent withdrawal | Low | Implement revocation workflow; re-index affected docs |
| UI complexity | Low | Clear inheritance visualization; sensible defaults |

**Ghost Protocol Compatibility:** FULLY COMPATIBLE - Enhances data governance; enables selective zero-retention

---

## Summary & Recommendations

### Implementation Priority Order

1. **[P0] DoD 5220.22-M Wipe** (5-7 days) - Foundation for all other features
2. **[P1] Scope Guard Approval** (10-12 days) - Required before enabling destructive MCP tools
3. **[P0] MCP Server** (20-25 days) - Core agentic capability
4. **[P1] Vision LLM** (12-15 days) - Enhances document understanding
5. **[P2] KVKK Consent** (12-15 days) - Compliance layer

### Critical Files Summary

| Feature | Primary Files |
|---------|--------------|
| DoD Wipe | `backend/services/secure_cleanup.py`, `backend/core/config.py` |
| MCP Server | NEW `backend/mcp/` module, `backend/main.py` |
| Vision LLM | NEW `backend/services/vision/` module, `backend/services/parsers.py` |
| Scope Guard | NEW `backend/services/scope_guard/` module, `backend/api/v1/documents.py` |
| KVKK Consent | NEW `backend/services/consent/` module, `backend/api/v1/search.py` |

### Ghost Protocol Compatibility Matrix

| Feature | Compatibility | Notes |
|---------|--------------|-------|
| DoD Wipe | Full | Enhances zero-retention |
| MCP Server | Careful | Must enforce ephemeral responses |
| Vision LLM | Full | SmartBuffer handles cleanup |
| Scope Guard | Full | Audit without content storage |
| KVKK Consent | Full | Enables selective retention |

---

## Verification Plan

After implementation, verify each feature:

### 1. DoD Wipe
- Run `secure_wipe()` on test file
- Verify 3-pass pattern in debug logs
- Confirm verify read passes

### 2. MCP Server
- Test with `curl` JSON-RPC request
- Verify `Cache-Control: no-store` header
- Check audit log (no content stored)

### 3. Vision LLM
- Upload test diagram image
- Verify semantic description in chunks
- Confirm original image secure-wiped

### 4. Scope Guard
- Attempt scope deletion without approval
- Verify HTTP 202 + mandate returned
- Complete approval flow and verify execution

### 5. KVKK Consent
- Set document consent to deny AI learning
- Verify document excluded from search results
- Check consent audit log entry

---

## Appendix: Dependency Graph

```
                    ┌─────────────────┐
                    │  DoD 5220.22-M  │
                    │     Wipe        │
                    └────────┬────────┘
                             │ (foundation)
              ┌──────────────┼──────────────┐
              │              │              │
              ▼              ▼              ▼
      ┌───────────┐  ┌───────────┐  ┌───────────┐
      │  Vision   │  │   Scope   │  │   KVKK    │
      │   LLM     │  │   Guard   │  │  Consent  │
      └───────────┘  └─────┬─────┘  └─────┬─────┘
              │            │              │
              │            │ (prerequisite)
              │            │              │
              └────────────┼──────────────┘
                           ▼
                    ┌─────────────────┐
                    │   MCP Server    │
                    │  (integrates    │
                    │   all above)    │
                    └─────────────────┘
```

---

*Document End*
