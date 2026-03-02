"""
Chat API Endpoints

Scope-aware conversational RAG with Dominance Guard for context disambiguation.
"""

import asyncio
import json
import logging
import re
import uuid as _uuid
from collections import Counter
from collections.abc import AsyncGenerator
from datetime import datetime, timezone
from typing import Any

import sentry_sdk
from fastapi import (
    APIRouter,
    BackgroundTasks,
    Depends,
    HTTPException,
    Query,
    Request,
    status,
)
from fastapi.responses import JSONResponse, StreamingResponse
from langchain_core.output_parsers import StrOutputParser
from langchain_core.prompts import ChatPromptTemplate
from pydantic import BaseModel, Field, field_validator

from api.v1.dependencies import (
    get_user_allowed_scopes,
    get_user_organization_id,
    require_paid_access,
    validate_team_access,
)
from api.v1.error_utils import (
    ApiErrorCode,
    api_error,
    build_error_payload,
    raise_http_error,
)
from core.config import settings
from core.db import get_supabase
from core.exceptions import QuotaExceededError
from core.ingestion_utils import normalize_source_type
from core.rate_limit import limiter, user_limiter
from core.resilience import CircuitBreakerOpen, is_retryable_error, openai_breaker
from core.security import get_current_user
from services.audit import audit_logger, log_chat_delete
from services.guardrails import guardrail_service
from services.llm_factory import LLMFactory
from services.router import ComplexityEvaluator, ModelSelection, llm_router
from services.scope_analysis import (
    ScopeClassification,
    analyze_scope_distribution,
    filter_docs_by_scope,
)
from services.team_service import team_service
from services.usage import (
    check_llm_quota,
    check_per_request_token_limit,
    record_llm_usage,
    release_reserved_tokens,
    reserve_llm_tokens,
)

logger = logging.getLogger(__name__)

# Global semaphore to limit concurrent LLM calls (Issue #13)
_llm_semaphore: asyncio.Semaphore | None = None
_semaphore_lock = asyncio.Lock()


async def _get_llm_semaphore() -> asyncio.Semaphore:
    """Get or create global LLM concurrency semaphore with double-check locking."""
    global _llm_semaphore
    if _llm_semaphore is not None:
        return _llm_semaphore
    async with _semaphore_lock:
        if _llm_semaphore is None:
            max_concurrent = getattr(settings, 'LLM_MAX_CONCURRENT_REQUESTS', 20)
            _llm_semaphore = asyncio.Semaphore(max_concurrent)
            logger.info(f"🔒 [Chat] Initialized LLM semaphore with max_concurrent={max_concurrent}")
    return _llm_semaphore


# Max match_count allowed for hybrid search RPCs
MATCH_COUNT_CAP = 50


def _safe_sse_json(data: dict) -> str:
    """Safely serialize data to an SSE event string. Falls back to error event on failure."""
    try:
        return f"data: {json.dumps(data, default=str)}\n\n"
    except (TypeError, ValueError, OverflowError) as exc:
        logger.warning("SSE JSON serialization failed: %s", exc)
        fallback = {"type": "error", "message": "Server serialization error", "error": "SSE_SERIALIZE_ERROR"}
        return f"data: {json.dumps(fallback, default=str)}\n\n"


def _categorize_exception(e: Exception) -> str:
    """Map exception types to ApiErrorCode strings for consistent error handling."""
    if isinstance(e, TimeoutError) or isinstance(e, asyncio.TimeoutError):
        return "EXTERNAL_SERVICE_ERROR"
    if isinstance(e, ConnectionError) or isinstance(e, OSError):
        return "SERVICE_UNAVAILABLE"
    return "DATABASE_ERROR"
router = APIRouter(dependencies=[Depends(validate_team_access), Depends(require_paid_access)])

# ============================================================
# CONVERSATION MANAGEMENT ENDPOINTS
# ============================================================

class ConversationCreate(BaseModel):
    title: str = Field(default="New Chat", max_length=200)

class ConversationUpdate(BaseModel):
    title: str = Field(..., max_length=200)

class ConversationResponse(BaseModel):
    id: str
    title: str
    created_at: str
    updated_at: str

class MessageResponse(BaseModel):
    id: str
    role: str
    content: str
    sources: list[Any] = []
    created_at: str

@router.get("/conversations", response_model=list[ConversationResponse])
@limiter.limit("60/minute")
async def list_conversations(
    request: Request,
    user_id: str = Depends(get_current_user),
    organization_id: str = Depends(get_user_organization_id),
    limit: int = Query(default=200, ge=1, le=500),
    offset: int = Query(default=0, ge=0),
):
    """List conversations for the organization (team-shared) with pagination."""
    supabase = get_supabase()

    try:
        # Organization-wide conversation access for team collaboration
        response = supabase.table("conversations").select("*").eq(
            "organization_id", organization_id
        ).order("updated_at", desc=True).range(offset, offset + limit - 1).execute()
        return response.data
    except Exception as e:
        raise api_error(ApiErrorCode.DATABASE_ERROR, e, "fetch_conversations")

@router.post("/conversations", response_model=ConversationResponse)
@limiter.limit("30/minute")
async def create_conversation(
    request: Request,
    payload: ConversationCreate,
    user_id: str = Depends(get_current_user),
    organization_id: str = Depends(get_user_organization_id),
):
    """Create a new conversation (org-scoped for team sharing)."""
    supabase = get_supabase()

    now = datetime.now(timezone.utc).isoformat()
    data = {
        "user_id": user_id,
        "organization_id": organization_id,  # CRITICAL: Enable team-shared conversations
        "title": payload.title,
        "created_at": now,
        "updated_at": now
    }

    try:
        response = supabase.table("conversations").insert(data).execute()
        if not response.data:
            raise api_error(ApiErrorCode.DATABASE_ERROR, None, "create_conversation")
        return response.data[0]
    except Exception as e:
        raise api_error(ApiErrorCode.DATABASE_ERROR, e, "create_conversation")

@router.get("/conversations/{conversation_id}", response_model=ConversationResponse)
@limiter.limit("60/minute")
async def get_conversation(
    request: Request,
    conversation_id: str,
    user_id: str = Depends(get_current_user),
    organization_id: str = Depends(get_user_organization_id),
):
    """Get a specific conversation (org-scoped access)."""
    supabase = get_supabase()

    try:
        # Organization-wide access for team collaboration
        response = supabase.table("conversations").select("*").eq("id", conversation_id).eq("organization_id", organization_id).single().execute()
        if not response.data:
            raise HTTPException(status_code=404, detail="Conversation not found")
        return response.data
    except HTTPException:
        raise
    except Exception as e:
        raise api_error(ApiErrorCode.DATABASE_ERROR, e, "fetch_conversation")

@router.patch("/conversations/{conversation_id}", response_model=ConversationResponse)
@limiter.limit("30/minute")
async def update_conversation(
    request: Request,
    conversation_id: str,
    payload: ConversationUpdate,
    user_id: str = Depends(get_current_user),
    organization_id: str = Depends(get_user_organization_id),
):
    """Update a conversation (e.g., rename). Org-scoped access."""
    supabase = get_supabase()

    try:
        # Organization-wide access for team collaboration
        response = supabase.table("conversations").update({
            "title": payload.title,
            "updated_at": datetime.now(timezone.utc).isoformat()
        }).eq("id", conversation_id).eq("organization_id", organization_id).execute()

        if not response.data:
            raise HTTPException(status_code=404, detail="Conversation not found")
        return response.data[0]
    except HTTPException:
        raise
    except Exception as e:
        raise api_error(ApiErrorCode.DATABASE_ERROR, e, "update_conversation")

@router.delete("/conversations/{conversation_id}")
@limiter.limit("20/minute")
async def delete_conversation(
    conversation_id: str,
    request: Request,
    background_tasks: BackgroundTasks,
    user_id: str = Depends(get_current_user),
    organization_id: str = Depends(get_user_organization_id),
):
    """Delete a conversation and all its messages. Org-scoped access."""
    supabase = get_supabase()

    try:
        # Get conversation info for audit log (org-scoped)
        conv_response = supabase.table("conversations").select("title").eq("id", conversation_id).eq("organization_id", organization_id).single().execute()
        conv_title = conv_response.data.get("title", "Unknown") if conv_response.data else "Unknown"

        # Delete conversation (messages cascade) - org-scoped
        response = supabase.table("conversations").delete().eq("id", conversation_id).eq("organization_id", organization_id).execute()

        # Audit log (async)
        log_chat_delete(background_tasks, user_id, conversation_id, conv_title, request)

        return {"status": "success", "deleted_id": conversation_id}
    except Exception as e:
        raise api_error(ApiErrorCode.DATABASE_ERROR, e, "delete_conversation")

@router.get("/conversations/{conversation_id}/messages", response_model=list[MessageResponse])
@limiter.limit("60/minute")
async def get_messages(
    request: Request,
    conversation_id: str,
    user_id: str = Depends(get_current_user),
    organization_id: str = Depends(get_user_organization_id),
):
    """Get all messages for a conversation. Org-scoped access."""
    supabase = get_supabase()

    # Verify org membership has access to this conversation
    conv_check = supabase.table("conversations").select("id").eq("id", conversation_id).eq("organization_id", organization_id).execute()
    if not conv_check.data:
        raise HTTPException(status_code=404, detail="Conversation not found")

    try:
        response = supabase.table("messages").select("*").eq("conversation_id", conversation_id).order("created_at", desc=False).execute()
        messages = response.data or []
        for msg in messages:
            if "sources" in msg and msg.get("sources") is None:
                msg["sources"] = []
        return messages
    except Exception as e:
        raise api_error(ApiErrorCode.DATABASE_ERROR, e, "fetch_messages")


# ============================================================
# CONVERSATIONAL RAG CHAT ENDPOINT
# ============================================================

class ChatRequest(BaseModel):
    """
    Chat request with input validation.

    Constraints:
    - query: max 20,000 chars (~5,000 tokens) - prevents massive payloads
    - conversation_id: max 50 chars (UUIDs are 36 chars)
    - model: "fast" or "smart" (or a model name), max 50 chars
    - scope_id: explicit scope selection (bypasses Dominance Guard)
    """
    query: str = Field(..., min_length=1, max_length=20000)
    conversation_id: str | None = Field(None, max_length=50)
    history: list[dict[str, str]] | None = Field(default=[], max_length=100)
    model: str = Field(default=settings.MODEL_ALIAS_FAST, max_length=50)
    stream: bool = Field(default=False)
    scope_id: str | None = Field(
        None,
        max_length=500,
        description="Explicit scope URI to search within. Use '__all__' to search across sources."
    )

    @field_validator('query')
    @classmethod
    def query_not_whitespace(cls, v: str) -> str:
        stripped = v.strip()
        if not stripped:
            raise ValueError('Query must not be empty or whitespace-only')
        return stripped

    @field_validator('conversation_id')
    @classmethod
    def conversation_id_uuid(cls, v: str | None) -> str | None:
        if v is None:
            return v
        try:
            _uuid.UUID(v)
        except ValueError:
            raise ValueError('conversation_id must be a valid UUID')
        return v

    @field_validator('history')
    @classmethod
    def history_token_limit(cls, v: list[dict[str, str]] | None) -> list[dict[str, str]] | None:
        if not v:
            return v
        max_total_chars = 100_000
        total = 0
        cutoff = len(v)
        for i, msg in enumerate(v):
            total += len(msg.get('content', ''))
            if total > max_total_chars:
                cutoff = i
                break
        return v[:cutoff] if cutoff < len(v) else v


class ScopeCandidate(BaseModel):
    """Scope candidate for clarification response."""
    id: str
    summary: str | None = None
    type: str


class ClarificationResponse(BaseModel):
    """Response when scope clarification is needed (HTTP 300)."""
    action: str = "clarify_scope"
    message: str
    candidates: list[ScopeCandidate]
    query: str


class ScopeContext(BaseModel):
    """Scope context metadata included in successful responses."""
    scope_id: str
    scope_name: str | None = None
    scope_type: str | None = None
    dominance_ratio: float
    classification: str


class ChatResponse(BaseModel):
    """Chat response with optional scope context."""
    answer: str
    sources: list[dict[str, Any]]  # Enhanced sources with metadata
    conversation_id: str | None = None
    message_id: str | None = None
    scope_context: ScopeContext | None = None  # NEW: Scope info for transparency


# ============================================================
# CONDENSE QUESTION: Rewrite follow-up queries to standalone
# ============================================================

CONDENSE_PROMPT = """Given the following conversation history and a follow-up question,
rewrite the follow-up question to be a STANDALONE question that includes all necessary context.
Do NOT answer the question, just rephrase it so it can be understood without the history.

Chat History:
{history}

Follow-up Question: {question}

Standalone Question:"""

import tiktoken

MODEL_CONTEXT_WINDOWS = {
    "gpt-4o": 128000,
    "gpt-4o-mini": 128000,
    "llama-3.3-70b-versatile": 128000,
    "llama-3.1-8b-instant": 8192,
}
DEFAULT_CONTEXT_WINDOW = 8192
SCOPE_IDENTITY_BUDGET_RATIO = 0.70
GLOBAL_IDENTITY_TOKEN_BUDGET = 2000
LONG_QUERY_WORD_THRESHOLD = 2000
LONG_QUERY_TOKEN_THRESHOLD = 8000

if settings.GROK_MODEL_NAME and settings.GROK_MODEL_NAME not in MODEL_CONTEXT_WINDOWS:
    MODEL_CONTEXT_WINDOWS[settings.GROK_MODEL_NAME] = DEFAULT_CONTEXT_WINDOW

try:
    _TOKEN_ENCODER = tiktoken.get_encoding("cl100k_base")
except Exception:
    _TOKEN_ENCODER = None

def _estimate_token_count(text: str) -> int:
    if not text:
        return 1
    if _TOKEN_ENCODER:
        return len(_TOKEN_ENCODER.encode(text))
    return max(1, len(text) // 4)


def _truncate_to_token_budget(text: str, max_tokens: int) -> str:
    if not text or max_tokens <= 0:
        return ""
    if _TOKEN_ENCODER:
        tokens = _TOKEN_ENCODER.encode(text)
        if len(tokens) <= max_tokens:
            return text
        return _TOKEN_ENCODER.decode(tokens[:max_tokens])
    char_budget = max(1, max_tokens * 4)
    return text[:char_budget]


def _apply_scope_identity_budget(scope_identity: str, context_text: str, model_name: str) -> str:
    if not scope_identity:
        return scope_identity
    context_window = MODEL_CONTEXT_WINDOWS.get(model_name, DEFAULT_CONTEXT_WINDOW)
    budget = int(context_window * SCOPE_IDENTITY_BUDGET_RATIO)
    scope_tokens = _estimate_token_count(scope_identity)
    context_tokens = _estimate_token_count(context_text)
    if scope_tokens + context_tokens <= budget:
        return scope_identity
    logger.info(
        "✂️ [Chat] Truncating scope identity for model=%s (scope=%s context=%s budget=%s)",
        model_name,
        scope_tokens,
        context_tokens,
        budget,
    )
    remaining = budget - context_tokens
    if remaining <= 0:
        return "(Scope identity omitted to preserve context.)"
    return _truncate_to_token_budget(scope_identity, remaining)


def _build_multi_scope_identity_context(
    scope_infos: list[dict[str, Any]],
    budget_tokens: int = GLOBAL_IDENTITY_TOKEN_BUDGET,
) -> str:
    if not scope_infos:
        return ""
    per_scope_budget = max(100, budget_tokens // max(1, len(scope_infos)))
    parts: list[str] = []
    for info in scope_infos:
        scope_id = info.get("id", "unknown")
        scope_type = info.get("type", "unknown")
        summary = info.get("summary", "") or ""
        summary = _truncate_to_token_budget(summary, per_scope_budget)
        parts.append(f"Scope: {scope_id}\nType: {scope_type}\nSummary: {summary}")
    combined = "\n\n".join(parts)
    if _estimate_token_count(combined) > budget_tokens:
        combined = _truncate_to_token_budget(combined, budget_tokens)
    return combined


def _extract_scope_ids(docs: list[dict[str, Any]], max_scopes: int = 5) -> list[str]:
    counts: Counter[str] = Counter()
    for doc in docs:
        scope_id = doc.get("scope_id")
        if not scope_id:
            scope_id = (doc.get("metadata") or {}).get("scope_id")
        if scope_id:
            counts[str(scope_id)] += 1
    return [scope_id for scope_id, _count in counts.most_common(max_scopes)]


def _estimate_prompt_tokens(system_prompt: str, input_vars: dict[str, Any]) -> int:
    total = _estimate_token_count(system_prompt)
    for value in input_vars.values():
        if value is None:
            continue
        total += _estimate_token_count(str(value))
    return total


def _build_prompt_bundle(
    provider: str,
    context_text: str,
    question: str,
    language: str,
    scope_identity_context: str | None = None,
    scope_name: str | None = None,
    multi_scope_identity_context: str | None = None,
) -> tuple[ChatPromptTemplate, dict[str, Any], str]:
    is_grok = provider == "grok"
    if multi_scope_identity_context:
        system_prompt = GROK_MULTI_SCOPE_SYSTEM_PROMPT if is_grok else MULTI_SCOPE_SYSTEM_PROMPT
        input_vars = {
            "context": context_text,
            "question": question,
            "language": language,
            "scope_identities": multi_scope_identity_context,
        }
    elif scope_identity_context:
        system_prompt = GROK_SCOPED_SYSTEM_PROMPT if is_grok else SCOPED_SYSTEM_PROMPT
        input_vars = {
            "context": context_text,
            "question": question,
            "language": language,
            "scope_identity": scope_identity_context,
            "scope_name": scope_name or "Unknown",
        }
    else:
        system_prompt = GROK_SYSTEM_PROMPT if is_grok else SYSTEM_PROMPT
        input_vars = {
            "context": context_text,
            "question": question,
            "language": language,
        }

    prompt = ChatPromptTemplate.from_messages([
        ("system", system_prompt),
        ("user", "{question}")
    ])
    return prompt, input_vars, system_prompt


def _should_failover(exc: Exception) -> bool:
    if isinstance(exc, CircuitBreakerOpen):
        return True
    return is_retryable_error(exc)


def _is_long_query(query: str) -> bool:
    if not query:
        return False
    word_count = len(query.split())
    if word_count >= LONG_QUERY_WORD_THRESHOLD:
        return True
    return _estimate_token_count(query) >= LONG_QUERY_TOKEN_THRESHOLD


def _is_timeout_error(exc: Exception) -> bool:
    if isinstance(exc, (asyncio.TimeoutError, TimeoutError)):
        return True
    return "timeout" in str(exc).lower() or "timed out" in str(exc).lower()

def trim_history(history: list[dict[str, str]], max_tokens: int = 2000) -> list[dict[str, str]]:
    """
    Trim chat history to fit within max_tokens limits.
    Keeps the System Prompt (if present) and the VERY LAST User message.
    Removes oldest messages from the middle.
    """
    if not history:
        return []

    try:
        encoding = tiktoken.get_encoding("cl100k_base")
    except Exception:
        encoding = None

    def count_tokens(text: str):
        if encoding:
            return len(encoding.encode(text))
        return len(text) // 4  # Fallback approximation

    current_tokens = sum(count_tokens(msg.get("content", "")) for msg in history)

    if current_tokens <= max_tokens:
        return history

    logger.info(f"✂️ [Chat] Trimming history: {current_tokens} > {max_tokens}")

    # Preserve key messages
    system_msg = vocab_msg = None
    if history and history[0].get("role") == "system":
        system_msg = history.pop(0)

    # Always keep the last message (current query usually)
    last_msg = history.pop(-1) if history else None

    # Trim middle
    while history and current_tokens > max_tokens:
        removed = history.pop(0)
        current_tokens -= count_tokens(removed.get("content", ""))

    # Reassemble
    result = []
    if system_msg:
        result.append(system_msg)
    result.extend(history)
    if last_msg:
        result.append(last_msg)

    return result


# M7: Heuristic to skip LLM condensing for self-contained queries
_REFERENCE_PATTERNS = [
    re.compile(r'\b(it|this|that|these|those|them|its|their)\b', re.IGNORECASE),
    re.compile(r'\b(above|previous|earlier|mentioned|said)\b', re.IGNORECASE),
]


def _needs_condensing(query: str, history: list[dict[str, str]]) -> bool:
    """Return True if the query references conversation context and needs condensing."""
    if not history:
        return False
    for pattern in _REFERENCE_PATTERNS:
        if pattern.search(query):
            return True
    return False


async def condense_question(query: str, history: list[dict[str, str]]) -> str:
    """
    If chat history exists, rewrite the query as a standalone question.
    Uses GPT-4o-mini for speed and cost efficiency.

    GAP 6 FIX: Uses LLMFactory instead of direct ChatOpenAI() to leverage
    client pooling and consistent timeout configuration.
    """
    if not history or all(not (msg.get("content") or "").strip() for msg in history):
        return query

    # M7: Skip condensing if query is self-contained (no conversational references)
    if not _needs_condensing(query, history):
        logger.info("🔄 [Chat] Skipping condense — query is self-contained")
        return query

    # Format history for the prompt
    history_text = ""
    for msg in history[-6:]:  # Last 6 messages max (3 turns)
        role = msg.get("role", "user")
        content = msg.get("content", "")[:500]  # Truncate long messages
        history_text += f"{role.upper()}: {content}\n"

    try:
        # GAP 6 FIX: Use LLMFactory for pooled connections and timeout config
        llm, _ = LLMFactory.get_model(
            provider="openai",
            model_name="gpt-4o-mini",
            temperature=0,
            streaming=False,
            allow_override=True,
        )

        prompt = ChatPromptTemplate.from_template(CONDENSE_PROMPT)
        chain = prompt | llm | StrOutputParser()

        standalone = await chain.ainvoke({"history": history_text, "question": query})
        logger.info(f"🔄 [Chat] Condensed: '{query[:50]}...' → '{standalone[:50]}...'")
        return standalone.strip()

    except Exception as e:
        logger.warning(f"⚠️ [Chat] Condense failed, using original query: {e}")
        return query


# ============================================================
# SYSTEM PROMPTS WITH CITATION RULES
# ============================================================

# Standard prompt (no scope context)
SYSTEM_PROMPT = """You are Axio, an intelligent AI assistant with access to the user's knowledge base.

## Your Role
- Answer questions using ONLY the provided context documents
- Be helpful, accurate, and conversational
- Synthesize information from multiple sources when relevant
- RESPOND IN {language} (the user's detected language)

## Citation Rules (IMPORTANT)
- Use bracket citations like [1], [2], [3] to reference your sources
- Place citations at the end of sentences or relevant phrases
- Each citation number corresponds to the numbered documents below
- If information comes from multiple sources, cite all relevant ones: [1][3]

## When You Don't Know
If the context doesn't contain enough information, say:
"I couldn't find specific information about that in your documents. [No relevant sources found]"

---

## KNOWLEDGE BASE CONTEXT:

{context}

---

Remember: Cite your sources using [1], [2], etc. Respond in {language}."""


# Scoped prompt (with scope context injection)
SCOPED_SYSTEM_PROMPT = """You are Axio, an intelligent AI assistant with access to the user's knowledge base.

## SCOPE CONTEXT
You are answering questions specifically about:
{scope_identity}

## Your Role
- Answer questions using ONLY the provided context documents from this scope
- Be helpful, accurate, and conversational
- When citing, mention the source is from "{scope_name}" when relevant
- RESPOND IN {language} (the user's detected language)

## Citation Rules (IMPORTANT)
- Use bracket citations like [1], [2], [3] to reference your sources
- Place citations at the end of sentences or relevant phrases
- Each citation number corresponds to the numbered documents below

## When You Don't Know
If the context doesn't contain enough information, say:
"I couldn't find specific information about that in {scope_name}. [No relevant sources found]"

---

## KNOWLEDGE BASE CONTEXT (from {scope_name}):

{context}

---

Remember: Cite your sources using [1], [2], etc. Respond in {language}."""


# Multi-scope prompt (Search All Sources)
MULTI_SCOPE_SYSTEM_PROMPT = """You are Axio, an intelligent AI assistant with access to the user's knowledge base.

## SCOPE DIRECTORY
The user is searching across multiple sources. The following scope summaries
help you orient, but DO NOT cite them as sources:
{scope_identities}

## Your Role
- Answer questions using ONLY the provided context documents below
- Be helpful, accurate, and conversational
- When citing, mention the source when relevant
- RESPOND IN {language} (the user's detected language)

## Citation Rules (IMPORTANT)
- Use bracket citations like [1], [2], [3] to reference your sources
- Place citations at the end of sentences or relevant phrases
- Each citation number corresponds to the numbered documents below

## When You Don't Know
If the context doesn't contain enough information, say:
"I couldn't find specific information about that in your documents. [No relevant sources found]"

---

## KNOWLEDGE BASE CONTEXT (all sources):

{context}

---

Remember: Cite your sources using [1], [2], etc. Respond in {language}."""


# Grok-optimized prompts (short, structured, low-noise)
GROK_SYSTEM_PROMPT = """You are Axio, an AI assistant.

Rules:
- Use ONLY the context provided
- Cite sources using [1], [2], etc.
- If missing, say you couldn't find it in the documents
- Respond in {language}

Context:
{context}
"""


GROK_SCOPED_SYSTEM_PROMPT = """You are Axio, an AI assistant.

Scope Summary (do not cite as a source):
{scope_identity}

Rules:
- Use ONLY the context provided
- Cite sources using [1], [2], etc.
- If missing, say you couldn't find it in {scope_name}
- Respond in {language}

Context:
{context}
"""


GROK_MULTI_SCOPE_SYSTEM_PROMPT = """You are Axio, an AI assistant.

Scope Directory (do not cite as a source):
{scope_identities}

Rules:
- Use ONLY the context provided
- Cite sources using [1], [2], etc.
- If missing, say you couldn't find it in the documents
- Respond in {language}

Context:
{context}
"""


# ============================================================
# SCOPE IDENTITY HELPERS
# ============================================================

def fetch_scope_identity(supabase, scope_id: str, organization_id: str) -> dict[str, Any] | None:
    """
    Fetch scope identity information from scope_identities table.

    Returns scope summary and metadata for system prompt injection.

    Note: Filters out placeholder identities (status='placeholder' or is_placeholder=True)
    to prevent showing "Generating identity..." text in chat responses.
    """
    try:
        response = supabase.table("scope_identities").select(
            "id, type, summary, attributes, file_tree, status"
        ).eq("id", scope_id).eq("organization_id", organization_id).single().execute()

        if response.data:
            # Filter out placeholder identities
            status = response.data.get("status")
            attributes = response.data.get("attributes") or {}
            is_placeholder = attributes.get("is_placeholder", False)

            if status == "placeholder" or is_placeholder:
                logger.debug(f"🔍 [Chat] Skipping placeholder scope identity for {scope_id}")
                return None

            return response.data
        return None
    except Exception as e:
        logger.warning(f"⚠️ [Chat] Failed to fetch scope identity for {scope_id}: {e}")
        return None


def fetch_scope_candidates_with_summaries(
    supabase,
    scope_ids: list[str],
    organization_id: str
) -> list[dict[str, Any]]:
    """
    Fetch scope identities for multiple scopes (for clarification response).

    Returns list of scope info with summaries and types.

    Note: Filters out placeholder identities to prevent showing incomplete data.
    """
    if not scope_ids:
        return []

    try:
        response = supabase.table("scope_identities").select(
            "id, type, summary, attributes, status"
        ).eq("organization_id", organization_id).in_("id", scope_ids).neq(
            "status", "placeholder"
        ).execute()

        # Additional filter for is_placeholder attribute (defense in depth)
        results = []
        for item in (response.data or []):
            attributes = item.get("attributes") or {}
            if not attributes.get("is_placeholder", False):
                results.append(item)

        return results
    except Exception as e:
        logger.warning(f"⚠️ [Chat] Failed to fetch scope candidates: {e}")
        return []


def build_scope_identity_context(scope_identity: dict[str, Any]) -> str:
    """
    Build a human-readable scope identity context for system prompt injection.

    SECURITY FIX (Issue #10): All user-controlled content is sanitized to prevent
    prompt injection attacks via crafted scope names/descriptions.
    """
    if not scope_identity:
        return "(No scope identity available)"

    # Sanitize all user-controlled fields before injection
    scope_id = _sanitize_prompt_content(str(scope_identity.get("id", "Unknown")), max_length=200)
    scope_type = _sanitize_prompt_content(str(scope_identity.get("type", "unknown")), max_length=50)
    summary = _sanitize_prompt_content(str(scope_identity.get("summary", "")), max_length=1000)
    attributes = scope_identity.get("attributes", {}) or {}

    # Extract key attributes (sanitize to prevent injection via metadata)
    file_count = attributes.get("file_count", "unknown")
    if not isinstance(file_count, (int, str)) or (isinstance(file_count, str) and not file_count.isdigit()):
        file_count = "unknown"

    languages = attributes.get("languages", [])
    if isinstance(languages, list):
        # Sanitize each language/extension entry
        languages = [_sanitize_prompt_content(str(lang), max_length=30) for lang in languages[:10]]
    else:
        languages = []

    context_parts = [
        f"Scope: {scope_id}",
        f"Type: {scope_type}",
    ]

    if file_count != "unknown":
        context_parts.append(f"Files: {file_count}")

    if languages:
        context_parts.append(f"Languages/Extensions: {', '.join(languages)}")

    if summary:
        context_parts.append(f"\n{summary}")

    return "\n".join(context_parts)


def _sanitize_prompt_content(text: str, max_length: int = 5000) -> str:
    """
    Sanitize user-controlled content before injecting into system prompts.

    Prevents prompt injection attacks by:
    1. Removing prompt delimiter sequences
    2. Escaping special formatting characters
    3. Truncating to prevent context flooding
    4. Removing control characters

    Issue #10: Scope metadata was injected without sanitization.
    """
    if not text:
        return ""

    # Remove control characters (except newlines and tabs)
    text = re.sub(r'[\x00-\x08\x0b\x0c\x0e-\x1f\x7f]', '', text)

    # Remove common prompt injection patterns
    # These patterns attempt to break out of the context or inject new instructions
    injection_patterns = [
        r'```\s*(system|user|assistant)',  # Code block role injection
        r'<\|?(system|user|assistant|im_start|im_end)\|?>',  # ChatML tags
        r'\[INST\]|\[/INST\]',  # Llama instruction markers
        r'###\s*(System|User|Assistant|Instruction)',  # Markdown role headers
        r'Human:|Assistant:|System:',  # Role prefixes
        r'<\|endoftext\|>',  # Token boundaries
        r'IGNORE\s+(PREVIOUS|ALL)\s+INSTRUCTIONS',  # Explicit injection attempts
    ]

    for pattern in injection_patterns:
        text = re.sub(pattern, '[filtered]', text, flags=re.IGNORECASE)

    # Truncate to max length
    if len(text) > max_length:
        text = text[:max_length] + "... [truncated]"

    return text.strip()


def extract_scope_name(scope_id: str) -> str:
    """
    Extract a human-readable name from a scope URI.

    Examples:
    - github://org/repo@main -> repo
    - s3://bucket/prefix/ -> bucket/prefix
    - box://folder/123:Marketing -> Marketing
    """
    if not scope_id:
        return "Unknown Source"

    try:
        # Handle common patterns
        if scope_id.startswith("github://"):
            # github://org/repo@branch -> repo
            parts = scope_id.replace("github://", "").split("@")[0]
            if "/" in parts:
                return parts.split("/")[-1]
            return parts

        if scope_id.startswith("s3://"):
            # s3://bucket/prefix/ -> bucket/prefix
            return scope_id.replace("s3://", "").rstrip("/") or "S3 Bucket"

        if scope_id.startswith("box://"):
            # box://folder/123:Name -> Name
            if ":" in scope_id:
                return scope_id.split(":")[-1]
            return scope_id.replace("box://folder/", "Box Folder")

        if scope_id.startswith("gdrive://"):
            # gdrive://drive/folder:Name -> Name
            if ":" in scope_id:
                return scope_id.split(":")[-1]
            return "Google Drive"

        if scope_id.startswith("notion://"):
            # notion://workspace/page:Title -> Title
            if ":" in scope_id:
                return scope_id.split(":")[-1]
            return "Notion"

        if scope_id.startswith("dropbox://"):
            # dropbox://namespace/path -> path
            parts = scope_id.replace("dropbox://", "").split("/", 1)
            return parts[-1] if len(parts) > 1 else "Dropbox"

        # Fallback: return last part of URI
        return scope_id.split("/")[-1].split(":")[-1] or scope_id

    except Exception:
        return scope_id[:50]


def _decrypt_search_results(docs: list[dict]) -> list[dict]:
    """
    GHOST PROTOCOL: Decrypt content in search results.

    Iterates through search results and decrypts the 'content' field
    using the Ghost Protocol encryption. Handles errors gracefully
    to ensure search continues even if some content can't be decrypted.

    Args:
        docs: List of search result dicts with 'content' field

    Returns:
        Same list with 'content' field decrypted in-place
    """
    from core.security import (
        HAS_CHUNK_ENCRYPTION,
        EncryptionError,
        UnencryptedContentError,
        decrypt_text,
    )

    if not docs or not HAS_CHUNK_ENCRYPTION:
        return docs

    for doc in docs:
        if doc.get('content'):
            try:
                doc['content'] = decrypt_text(doc['content'])
            except UnencryptedContentError:
                # Strict mode violation - log but don't crash the search
                logger.warning(
                    f"[GhostProtocol] Unencrypted content in search result "
                    f"(doc_id: {doc.get('document_id', 'unknown')[:8]}...)"
                )
                doc['content'] = "[Content unavailable - encryption policy violation]"
            except EncryptionError as e:
                logger.error(
                    f"[GhostProtocol] Decryption failed for search result: {e}"
                )
                doc['content'] = "[Content unavailable - decryption error]"
            except Exception as e:
                # Fallback for unexpected errors
                logger.error(
                    f"[GhostProtocol] Unexpected error decrypting content: {e}"
                )
                # Don't modify - might be plaintext (legacy data)

    return docs


def format_context_with_citations(docs: list[dict]) -> tuple:
    """
    Format retrieved documents with numbered citations.

    Returns:
        Tuple of (formatted_context_string, sources_metadata_list)

    Note: Expects docs to already have decrypted content via _decrypt_search_results()
    """
    if not docs:
        return "", []

    context_parts = []
    sources = []

    for i, doc in enumerate(docs, 1):
        content = doc.get('content', '')
        metadata = doc.get('metadata', {}) or {}  # Ensure dict even if None
        source_type = doc.get('source_type', metadata.get('source', 'unknown'))
        normalized_source_type = normalize_source_type(source_type) or source_type

        # IMPORTANT: hybrid_search returns 'title' at top-level, NOT inside metadata
        # Check top-level first, then fall back to metadata
        doc_title = doc.get('title') or metadata.get('title')

        # Build source label based on type
        if normalized_source_type == "web":
            source_label = metadata.get("url") or metadata.get("source_url") or doc_title or "Web Page"
            source_type_display = "Web"
        elif normalized_source_type == "file_upload":
            source_label = doc_title or metadata.get("filename") or "Uploaded File"
            source_type_display = "File"
        elif normalized_source_type == "google_drive":
            source_label = doc_title or "Google Drive File"
            source_type_display = "Drive"
        elif normalized_source_type == "notion":
            source_label = doc_title or "Notion Page"
            source_type_display = "Notion"
        else:
            source_label = doc_title or metadata.get("filename") or "Document"
            source_type_display = normalized_source_type.title() if normalized_source_type else "Doc"

        # Get additional context (page, section, etc.)
        page_info = ""
        if metadata.get("page_number"):
            page_info = f" (Page {metadata['page_number']})"
        elif metadata.get("header_path"):
            page_info = f" ({metadata['header_path']})"

        # Format the citation block
        citation_header = f"[{i}] {source_type_display}: {source_label}{page_info}"
        context_parts.append(f"{citation_header}\n{content[:1500]}")  # Truncate very long chunks

        # Build source metadata for response
        sources.append({
            "index": i,
            "type": source_type_display,
            "label": source_label,
            "url": metadata.get("source_url") or metadata.get("url"),
            "page": metadata.get("page_number"),
            "section": metadata.get("header_path"),
        })

    formatted_context = "\n\n---\n\n".join(context_parts)
    return formatted_context, sources


# ============================================================
# MAIN CHAT ENDPOINT (with Dominance Guard)
# ============================================================

@router.post("/chat")
@limiter.limit(settings.RATE_LIMIT_DEFAULT)
@user_limiter.limit("30/minute")
async def chat_endpoint(
    request: Request,
    payload: ChatRequest,
    background_tasks: BackgroundTasks,
    user_id: str = Depends(get_current_user),
    allowed_scopes: list[str] | None = Depends(get_user_allowed_scopes),
):
    """
    Intelligent Conversational RAG Chat Endpoint with Scope-Aware Dominance Guard.

    Pipeline:
    1. Guardrail Analysis - Safety, language, intent, complexity
    2. Fast Exit - Handle greetings/off-topic without RAG
    3. User Plan Lookup - Determine subscription tier
    4. Smart Routing - Select optimal model (GPT-4o or Llama)
    5. RAG Execution - Retrieve context
    6. **NEW** Dominance Guard - Analyze scope distribution
       - DOMINANT (≥85%): Proceed with scoped context
       - CONTESTED (60-84%): Proceed with annotation
       - FRAGMENTED (<60%): Return HTTP 300 clarification request
    7. Generation - Generate answer with scope context
    8. Streaming Support - Optional SSE streaming
    """
    supabase = get_supabase()
    request_id = str(_uuid.uuid4())[:8]

    # ========== STEP 1: RESOLVE ORG SCOPE ==========
    try:
        organization_id = await team_service.get_organization_id(user_id)
    except Exception as e:
        logger.warning("[%s] ⚠️ [Chat] Could not resolve org for %s: %s", request_id, user_id, e)
        organization_id = user_id

    if not organization_id:
        raise api_error(ApiErrorCode.DATABASE_ERROR, None, "organization_id is required")

    # ========== STEP 2: FETCH USER PLAN ==========
    try:
        user_plan = await team_service.get_effective_plan(user_id)
    except Exception as e:
        logger.warning(f"⚠️ [Chat] Could not fetch user plan: {e}")
        user_plan = "free"

    # ========== STEP 3: LLM QUOTA CHECK (before any LLM calls) ==========
    try:
        await check_llm_quota(organization_id, user_plan, required_tokens=1)
    except QuotaExceededError as exc:
        raise_http_error(
            status.HTTP_402_PAYMENT_REQUIRED,
            "PLAN_LIMIT_EXCEEDED",
            "LLM token quota exceeded.",
            exc.details if isinstance(exc, QuotaExceededError) else None,
        )

    # ========== STEP 4: GUARDRAIL ANALYSIS (Context-Aware) ==========
    # NEW: Use context-aware guardrails with pre-flight document check
    # This prevents false OFF_TOPIC classifications when documents match the query
    guardrail_result = await guardrail_service.analyze_query_with_context(
        query=payload.query,
        organization_id=organization_id,
        supabase_client=supabase,
    )
    detected_language = guardrail_result.language

    # Log guardrail results with context awareness info
    if guardrail_result.was_overridden:
        logger.info(
            "🛡️ [Chat] Guardrails: lang=%s safe=%s intent=%s (OVERRIDDEN from %s) "
            "complexity=%s preflight_matches=%d",
            detected_language,
            guardrail_result.is_safe,
            guardrail_result.intent,
            guardrail_result.original_intent,
            guardrail_result.complexity,
            guardrail_result.preflight_match_count,
        )
    else:
        logger.info(
            "🛡️ [Chat] Guardrails: lang=%s safe=%s intent=%s complexity=%s "
            "has_doc_context=%s",
            detected_language,
            guardrail_result.is_safe,
            guardrail_result.intent,
            guardrail_result.complexity,
            guardrail_result.has_document_context,
        )

    # ========== STEP 5: SAFETY CHECK ==========
    if not guardrail_result.is_safe:
        audit_logger.log(
            background_tasks,
            user_id=user_id,
            action="safety_violation",
            resource_type="chat",
            resource_id=payload.conversation_id,
            details={"query": payload.query[:500], "language": detected_language},
            request=request
        )

        refusal = guardrail_result.reply or "I cannot assist with that request."
        return ChatResponse(
            answer=refusal,
            sources=[],
            conversation_id=payload.conversation_id
        )

    # ========== STEP 6: INTENT CHECK (Fast exit for non-RAG) ==========
    if guardrail_result.intent in ("GREETING", "OFF_TOPIC"):
        fast_reply = guardrail_result.reply or "How can I help you with your documents today?"

        if payload.conversation_id:
            save_messages(
                supabase, payload.conversation_id, payload.query, fast_reply, [],
                organization_id=organization_id  # Org-scoped validation
            )

        return ChatResponse(
            answer=fast_reply,
            sources=[],
            conversation_id=payload.conversation_id
        )

    # ========== STEP 7: SMART ROUTING (Select Model) ==========
    requested_tier: str | None = None
    model_hint = (payload.model or "").strip().lower()
    force_smart = ComplexityEvaluator.should_force_pro(payload.query)

    if model_hint in {settings.MODEL_ALIAS_FAST, settings.SECONDARY_MODEL_NAME.lower()}:
        requested_tier = settings.MODEL_ALIAS_FAST
    elif model_hint in {settings.MODEL_ALIAS_SMART, settings.PRIMARY_MODEL_NAME.lower()}:
        requested_tier = settings.MODEL_ALIAS_SMART

    if force_smart:
        forced_selection = llm_router.select_model(
            plan=user_plan,
            complexity="COMPLEX",
            query_text=payload.query,
        )
        requested_tier = (
            settings.MODEL_ALIAS_SMART
            if forced_selection.model == settings.PRIMARY_MODEL_NAME
            else settings.MODEL_ALIAS_FAST
        )
        logger.info(
            "🧠 [Chat] Intent override: keyword force → tier=%s",
            requested_tier,
        )
    elif not requested_tier:
        model_selection = llm_router.select_model(
            plan=user_plan,
            complexity=guardrail_result.complexity,
            query_text=payload.query,
        )
        requested_tier = (
            settings.MODEL_ALIAS_SMART
            if model_selection.model == settings.PRIMARY_MODEL_NAME
            else settings.MODEL_ALIAS_FAST
        )
        logger.info(
            "🚀 [Chat] Auto route: plan=%s complexity=%s → tier=%s (%s/%s)",
            user_plan,
            guardrail_result.complexity,
            requested_tier,
            model_selection.provider,
            model_selection.model,
        )
    else:
        logger.info(
            "🚀 [Chat] User-selected tier: plan=%s model=%s → tier=%s",
            user_plan,
            payload.model,
            requested_tier,
        )

    if requested_tier == settings.MODEL_ALIAS_FAST and _is_long_query(payload.query):
        fast_window = MODEL_CONTEXT_WINDOWS.get(settings.SECONDARY_MODEL_NAME, DEFAULT_CONTEXT_WINDOW)
        smart_window = MODEL_CONTEXT_WINDOWS.get(settings.PRIMARY_MODEL_NAME, DEFAULT_CONTEXT_WINDOW)
        if smart_window > fast_window:
            requested_tier = settings.MODEL_ALIAS_SMART
            logger.info(
                "🧠 [Chat] Long query upgrade: words>=%s → tier=%s",
                LONG_QUERY_WORD_THRESHOLD,
                requested_tier,
            )
    # ========== STEP 7.1: RESOLVE ORG SCOPE (already fetched) ==========

    # ========== STEP 6: CONDENSE QUESTION (with trimmed history) ==========
    trimmed_history = trim_history(payload.history or [])
    search_query = await condense_question(payload.query, trimmed_history)

    # ========== STEP 7: EMBED QUERY ==========
    # H2: Reuse embedding from guardrail pre-flight if available
    if getattr(guardrail_result, 'query_embedding', None):
        query_vector = guardrail_result.query_embedding
        logger.info("🔢 [Chat] Reusing query embedding from guardrail pre-flight")
    else:
        from services.embeddings import get_embeddings_model
        embeddings_model = get_embeddings_model()
        try:
            query_vector = embeddings_model.embed_query(search_query)
        except Exception as e:
            logger.error(f"ERROR: Embedding failed: {e}")
            raise api_error(ApiErrorCode.PROCESSING_ERROR, e, "embed_query")

    # ========== STEP 7.5: SEMANTIC CACHE CHECK (H7) ==========
    if getattr(settings, "SEMANTIC_CACHE_ENABLED", False) and not payload.stream:
        try:
            from services.semantic_cache import semantic_cache
            scope_ids_for_cache = [payload.scope_id] if payload.scope_id else []
            cached = await semantic_cache.get(query_vector, scope_ids_for_cache)
            if cached:
                try:
                    from core.metrics import semantic_cache_ops
                    semantic_cache_ops.labels(operation="hit").inc()
                except Exception:
                    pass
                logger.info("🎯 [Chat] Semantic cache HIT — returning cached response")
                return ChatResponse(
                    answer=cached["response"],
                    sources=cached.get("sources", []),
                    conversation_id=payload.conversation_id,
                    message_id=None,
                    scope_context=None,
                )
            else:
                try:
                    from core.metrics import semantic_cache_ops
                    semantic_cache_ops.labels(operation="miss").inc()
                except Exception:
                    pass
        except Exception as e:
            logger.warning("⚠️ [Chat] Semantic cache check error: %s", e)

    # ========== STEP 8: HYBRID SEARCH (Scope-Aware) ==========
    # If explicit scope_id provided, use scoped search
    explicit_scope = payload.scope_id
    force_all_scopes = False
    if explicit_scope == "__all__":
        explicit_scope = None
        force_all_scopes = True

    # Scope-level access control: intersect with allowed scopes (same pattern as search.py)
    if allowed_scopes is not None:
        if explicit_scope:
            if explicit_scope not in allowed_scopes:
                explicit_scope = None  # Revoked scope — will fall through to allowed scopes
        if force_all_scopes:
            force_all_scopes = False  # Restricted user cannot search all scopes
            logger.info("🔒 [Chat] User requested __all__ but has scope restrictions, restricting to allowed scopes")

    _DB_RPC_TIMEOUT = 15  # seconds

    try:
        if explicit_scope:
            # User explicitly selected a scope - use scoped search
            logger.info(f"🎯 [Chat] Explicit scope search: {explicit_scope[:50]}...")
            response = await asyncio.wait_for(asyncio.to_thread(
                lambda: supabase.rpc("hybrid_search_scoped", {
                    "query_text": search_query,
                    "query_embedding": query_vector,
                    "match_count": min(10, MATCH_COUNT_CAP),
                    "filter_org_id": organization_id,
                    "filter_scope_ids": [explicit_scope],
                    "similarity_threshold": 0.25
                }).execute()
            ), timeout=_DB_RPC_TIMEOUT)
        elif force_all_scopes and allowed_scopes is None:
            # Search all sources using scoped RPC (wildcard scope filter)
            response = await asyncio.wait_for(asyncio.to_thread(
                lambda: supabase.rpc("hybrid_search_scoped", {
                    "query_text": search_query,
                    "query_embedding": query_vector,
                    "match_count": min(15, MATCH_COUNT_CAP),
                    "filter_org_id": organization_id,
                    "filter_scope_ids": None,
                    "vector_weight": 0.7,
                    "keyword_weight": 0.3,
                    "similarity_threshold": 0.25
                }).execute()
            ), timeout=_DB_RPC_TIMEOUT)
        elif allowed_scopes is not None:
            # Scope-restricted user — always use scoped search with allowed scopes
            logger.info(f"🔒 [Chat] Scope-restricted search: {len(allowed_scopes)} allowed scopes")
            response = await asyncio.wait_for(asyncio.to_thread(
                lambda: supabase.rpc("hybrid_search_scoped", {
                    "query_text": search_query,
                    "query_embedding": query_vector,
                    "match_count": min(15, MATCH_COUNT_CAP),
                    "filter_org_id": organization_id,
                    "filter_scope_ids": allowed_scopes,
                    "vector_weight": 0.7,
                    "keyword_weight": 0.3,
                    "similarity_threshold": 0.25
                }).execute()
            ), timeout=_DB_RPC_TIMEOUT)
        else:
            # Standard search - Dominance Guard will analyze distribution
            response = await asyncio.wait_for(asyncio.to_thread(
                lambda: supabase.rpc("hybrid_search", {
                    "query_text": search_query,
                    "query_embedding": query_vector,
                    "match_count": min(15, MATCH_COUNT_CAP),
                    "filter_org_id": organization_id,
                    "vector_weight": 0.7,
                    "keyword_weight": 0.3,
                    "similarity_threshold": 0.25
                }).execute()
            ), timeout=_DB_RPC_TIMEOUT)

        docs = response.data or []
        logger.info(f"📚 [Chat] Hybrid search found {len(docs)} raw candidates")

        # H8: Record retrieval similarity scores
        try:
            from core.metrics import retrieval_score
            for doc in docs:
                score = doc.get("similarity") or doc.get("vector_score")
                if score is not None:
                    retrieval_score.observe(float(score))
        except Exception:
            pass

        # GHOST PROTOCOL: Decrypt content before processing
        docs = _decrypt_search_results(docs)

        # GHOST PROTOCOL: Defense-in-depth tombstone filter
        # hybrid_search already filters tombstoned docs at SQL level,
        # but we double-check here for race condition protection
        from services.compliance_switch import compliance_switch
        docs = await compliance_switch.filter_tombstoned_docs(docs, organization_id)

        # M3: Scan retrieved chunks for prompt injection before context assembly
        try:
            from services.guardrails import detect_prompt_injection
            safe_docs = []
            for doc in docs:
                content = doc.get("content", "")
                if detect_prompt_injection(content):
                    logger.warning(
                        "🛡️ [Chat] Prompt injection detected in chunk %s — excluded",
                        str(doc.get("id", "unknown"))[:8],
                    )
                    continue
                safe_docs.append(doc)
            if len(safe_docs) < len(docs):
                logger.info(
                    "🛡️ [Chat] Filtered %d injected chunks, %d remaining",
                    len(docs) - len(safe_docs),
                    len(safe_docs),
                )
            docs = safe_docs
        except Exception as e:
            logger.warning("⚠️ [Chat] Chunk injection scan error: %s", e)

        # H4: Rerank for precision improvement
        if docs and len(docs) > 8:
            try:
                from services.reranker import reranker
                docs = await reranker.rerank(search_query, docs, top_k=8)
            except Exception as e:
                logger.warning("⚠️ [Chat] Reranking failed, using original order: %s", e)

    except asyncio.TimeoutError:
        logger.error("[%s] ERROR: Hybrid search RPC timed out after %ss", request_id, _DB_RPC_TIMEOUT)
        raise api_error(ApiErrorCode.PROCESSING_ERROR, TimeoutError("hybrid search timed out"), "retrieve_documents")
    except Exception as e:
        logger.error("ERROR: Retrieval failed: %s", e)
        raise api_error(ApiErrorCode.PROCESSING_ERROR, e, "retrieve_documents")

    # ========== STEP 9: DOMINANCE GUARD (Scope Analysis) ==========
    scope_context: ScopeContext | None = None
    selected_scope_id: str | None = None
    scope_identity: dict[str, Any] | None = None
    multi_scope_identity_context: str | None = None

    if force_all_scopes:
        logger.info("🌐 [Chat] Search all sources selected - skipping dominance guard")
        scope_ids = _extract_scope_ids(docs)
        if scope_ids:
            scope_infos = fetch_scope_candidates_with_summaries(
                supabase, scope_ids, organization_id
            )
            multi_scope_identity_context = _build_multi_scope_identity_context(
                scope_infos,
                GLOBAL_IDENTITY_TOKEN_BUDGET,
            )
    elif explicit_scope:
        # User explicitly selected scope - skip dominance analysis
        selected_scope_id = explicit_scope
        scope_identity = fetch_scope_identity(supabase, explicit_scope, organization_id)
        scope_context = ScopeContext(
            scope_id=explicit_scope,
            scope_name=extract_scope_name(explicit_scope),
            scope_type=scope_identity.get("type") if scope_identity else None,
            dominance_ratio=1.0,
            classification="explicit",
        )
        logger.info(f"🎯 [Chat] Using explicit scope: {explicit_scope[:50]}...")

    elif docs:
        # Analyze scope distribution
        scope_analysis = analyze_scope_distribution(docs)

        logger.info(
            f"🔍 [Chat] Scope analysis: {scope_analysis.classification.value}, "
            f"primary={scope_analysis.primary_scope_id[:50] if scope_analysis.primary_scope_id else 'None'}..., "
            f"ratio={scope_analysis.dominance_ratio:.2%}"
        )

        # ========== DOMINANCE GUARD DECISION ==========

        if scope_analysis.classification == ScopeClassification.FRAGMENTED:
            # FRAGMENTED: Return HTTP 300 clarification request
            logger.info("⚠️ [Chat] FRAGMENTED scope - requesting clarification")

            # Fetch scope summaries for candidates
            candidate_scope_ids = [
                s.scope_id for s in
                ([scope_analysis.primary_scope_stats] if scope_analysis.primary_scope_stats else []) +
                scope_analysis.secondary_scopes[:4]
            ]

            scope_infos = fetch_scope_candidates_with_summaries(
                supabase, candidate_scope_ids, organization_id
            )

            # Build scope_id -> info lookup
            scope_info_map = {s["id"]: s for s in scope_infos}

            # Build candidates for response
            candidates = []
            for scope_stats in ([scope_analysis.primary_scope_stats] if scope_analysis.primary_scope_stats else []) + scope_analysis.secondary_scopes[:4]:
                info = scope_info_map.get(scope_stats.scope_id, {})
                candidates.append(ScopeCandidate(
                    id=scope_stats.scope_id,
                    summary=info.get("summary", f"{scope_stats.count} relevant documents")[:200],
                    type=info.get("type", "unknown"),
                ))

            # Return HTTP 300 Multiple Choices
            return JSONResponse(
                status_code=300,
                content=ClarificationResponse(
                    action="clarify_scope",
                    message=(
                        "I found relevant information across multiple sources. "
                        "Please specify which source you'd like me to search, "
                        "or I can search all and clearly attribute each piece."
                    ),
                    candidates=candidates,
                    query=payload.query,
                ).model_dump(),
            )

        elif scope_analysis.classification in (ScopeClassification.DOMINANT, ScopeClassification.CONTESTED):
            # DOMINANT or CONTESTED: Proceed with primary scope
            selected_scope_id = scope_analysis.primary_scope_id

            if selected_scope_id:
                scope_identity = fetch_scope_identity(supabase, selected_scope_id, organization_id)
                scope_context = ScopeContext(
                    scope_id=selected_scope_id,
                    scope_name=extract_scope_name(selected_scope_id),
                    scope_type=scope_identity.get("type") if scope_identity else None,
                    dominance_ratio=scope_analysis.dominance_ratio,
                    classification=scope_analysis.classification.value,
                )

            # For DOMINANT, filter docs to primary scope only
            if scope_analysis.classification == ScopeClassification.DOMINANT and selected_scope_id:
                docs = filter_docs_by_scope(docs, selected_scope_id)
                logger.info(f"✅ [Chat] DOMINANT: filtered to {len(docs)} docs from {selected_scope_id[:50]}...")

    # ========== STEP 10: DYNAMIC CONTEXT INJECTION ==========
    high_quality_docs = [
        d for d in docs
        if d.get("vector_score", d.get("similarity", 0)) >= settings.RAG_SIMILARITY_THRESHOLD
    ]

    context_text = ""
    sources_metadata = []

    if high_quality_docs:
        logger.info(f"✅ [Chat] High quality context: {len(high_quality_docs)} docs")
        context_text, sources_metadata = format_context_with_citations(high_quality_docs)
    else:
        scope_name = extract_scope_name(selected_scope_id) if selected_scope_id else "your knowledge base"
        logger.warning(f"⚠️ [Chat] No docs above {settings.RAG_SIMILARITY_THRESHOLD} threshold")
        context_text = f"[No relevant documents found in {scope_name} for this query.]"
        sources_metadata = []

    # ========== STEP 11: GET SELECTED LLM & ENFORCE PLAN ==========
    llm_result = LLMFactory.get_model(
        user_plan=user_plan,
        requested_tier=requested_tier or settings.MODEL_ALIAS_FAST,
        temperature=0,
        streaming=payload.stream,
    )
    if isinstance(llm_result, tuple):
        llm, model_metadata = llm_result
    else:
        llm = llm_result
        model_metadata = {}
    if not isinstance(model_metadata, dict):
        model_metadata = {}

    actual_tier = model_metadata.get("actual_tier", requested_tier or settings.MODEL_ALIAS_FAST)
    primary_provider = model_metadata.get("provider") or (
        settings.PRIMARY_MODEL_PROVIDER
        if actual_tier == settings.MODEL_ALIAS_SMART
        else settings.SECONDARY_MODEL_PROVIDER
    )
    primary_model_name = model_metadata.get("model") or (
        settings.PRIMARY_MODEL_NAME
        if actual_tier == settings.MODEL_ALIAS_SMART
        else settings.SECONDARY_MODEL_NAME
    )

    # Build candidate list with fallbacks for resilience (Issue #5)
    # If primary is OpenAI and circuit is open, insert fallbacks FIRST
    llm_candidates = []
    circuit_open = primary_provider == "openai" and not llm_router.is_provider_available("openai")

    if circuit_open:
        # Circuit breaker is open - try fallbacks first, then OpenAI as last resort
        logger.warning("⚡ [Chat] OpenAI circuit open, prioritizing fallback providers")
        fallbacks = llm_router.get_fallback_models()
        if fallbacks:
            llm_candidates.extend(fallbacks)
        # Still include OpenAI as last resort (circuit might close)
        llm_candidates.append(ModelSelection(provider=primary_provider, model=primary_model_name, reason="primary_fallback"))
    else:
        # Normal operation: primary first, then fallbacks
        llm_candidates.append(ModelSelection(provider=primary_provider, model=primary_model_name, reason="primary"))
        if primary_provider == "openai":
            llm_candidates.extend(llm_router.get_fallback_models())

    candidate_models = [c.model for c in llm_candidates if c.model]
    if candidate_models:
        budget_model_name = min(
            candidate_models,
            key=lambda name: MODEL_CONTEXT_WINDOWS.get(name, DEFAULT_CONTEXT_WINDOW),
        )
    else:
        budget_model_name = primary_model_name

    logger.info(
        "🤖 [Chat] LLM: requested=%s actual=%s model=%s provider=%s fallbacks=%s",
        requested_tier,
        actual_tier,
        primary_model_name,
        primary_provider,
        [f"{c.provider}/{c.model}" for c in llm_candidates[1:]],
    )

    # ========== STEP 12: BUILD PROMPT (Scope-Aware) ==========
    scope_identity_context = None
    scope_name = None
    if scope_identity and selected_scope_id:
        scope_identity_context = build_scope_identity_context(scope_identity)
        scope_name = extract_scope_name(selected_scope_id)
        scope_identity_context = _apply_scope_identity_budget(
            scope_identity_context,
            context_text,
            budget_model_name,
        )

    prompt_cache: dict[str, tuple[ChatPromptTemplate, dict[str, Any], str]] = {}

    def _prompt_bundle_for(provider: str) -> tuple[ChatPromptTemplate, dict[str, Any], str]:
        cached = prompt_cache.get(provider)
        if cached:
            return cached
        bundle = _build_prompt_bundle(
            provider=provider,
            context_text=context_text,
            question=search_query,
            language=detected_language,
            scope_identity_context=scope_identity_context,
            scope_name=scope_name,
            multi_scope_identity_context=multi_scope_identity_context,
        )
        prompt_cache[provider] = bundle
        return bundle

    prompt, input_vars, system_prompt = _prompt_bundle_for(primary_provider)
    provider_set = {candidate.provider for candidate in llm_candidates}
    estimated_input_tokens = max(
        _estimate_prompt_tokens(
            _prompt_bundle_for(provider)[2],
            _prompt_bundle_for(provider)[1],
        )
        for provider in provider_set
    )

    # ========== STEP 12.1: PER-REQUEST TOKEN LIMIT CHECK (Issue #9) ==========
    try:
        check_per_request_token_limit(estimated_input_tokens)
    except QuotaExceededError as exc:
        raise_http_error(
            status.HTTP_400_BAD_REQUEST,
            "REQUEST_TOO_LARGE",
            str(exc),
            exc.details if isinstance(exc, QuotaExceededError) else None,
        )

    # ========== STEP 12.2: ATOMIC TOKEN RESERVATION (Issue #3) ==========
    # Reserve tokens BEFORE making LLM call to prevent race condition
    # where concurrent requests both pass quota check then exceed budget
    estimated_total_tokens = estimated_input_tokens + 4000  # Add buffer for response
    token_reservation = None

    try:
        token_reservation = await reserve_llm_tokens(
            organization_id,
            user_plan,
            estimated_total_tokens,
        )
        logger.debug(
            "🎫 [Chat] Reserved %s tokens for org=%s (remaining=%s)",
            token_reservation.get("reserved_tokens"),
            organization_id,
            token_reservation.get("remaining_balance"),
        )
    except QuotaExceededError as exc:
        raise_http_error(
            status.HTTP_402_PAYMENT_REQUIRED,
            "PLAN_LIMIT_EXCEEDED",
            "LLM token quota exceeded.",
            exc.details if isinstance(exc, QuotaExceededError) else None,
        )

    # ========== STEP 13: GENERATION ==========
    if payload.stream:
        # Wrap the stream to include status events for RAG pipeline visualization
        # Status events provide visual feedback for the RAG pipeline steps
        async def stream_with_status():
            import asyncio

            # Calculate context for status messages
            source_count = len(sources_metadata)
            scope_name = scope_context.scope_name if scope_context else None

            # Determine if this is a complex query that may take longer
            is_complex = guardrail_result.complexity == "COMPLEX" if guardrail_result else False
            is_smart_model = actual_tier == settings.MODEL_ALIAS_SMART

            # === Status 1: Searching ===
            # Show immediately to give user feedback
            searching_message = "Searching knowledge base..."
            if scope_name:
                searching_message = f"Searching {scope_name}..."

            yield _safe_sse_json({'type': 'status', 'step': 'searching', 'message': searching_message, 'details': {'scopeName': scope_name}})

            # Small delay to ensure event is rendered before next
            await asyncio.sleep(0.15)

            # === Status 2: Analyzing ===
            analyzing_message = "Analyzing context..."
            if source_count > 10:
                analyzing_message = f"Analyzing {source_count} documents..."

            yield _safe_sse_json({'type': 'status', 'step': 'analyzing', 'message': analyzing_message, 'details': {'sourceCount': source_count}})

            await asyncio.sleep(0.15)

            # === Status 3: Found ===
            if source_count > 0:
                found_message = f"Found {source_count} relevant sources"
                if scope_name:
                    found_message = f"Found {source_count} sources in {scope_name}"
            else:
                found_message = "No specific sources found, using general knowledge"

            yield _safe_sse_json({'type': 'status', 'step': 'found', 'message': found_message, 'details': {'sourceCount': source_count, 'scopeName': scope_name}})

            await asyncio.sleep(0.1)

            # === Status 4: Generating ===
            # Include model info and complexity warning for transparency
            generating_message = "Generating response..."
            if is_complex and is_smart_model:
                generating_message = "Generating detailed response (complex query)..."
            elif is_smart_model:
                generating_message = "Generating comprehensive response..."

            yield _safe_sse_json({'type': 'status', 'step': 'generating', 'message': generating_message, 'details': {'model': actual_tier, 'isComplex': is_complex}})

            # Yield all events from the actual streaming response
            async for event in stream_chat_response(
                _prompt_bundle_for,
                llm_candidates,
                actual_tier,
                context_text,
                search_query,
                sources_metadata,
                payload.conversation_id,
                user_id,
                supabase,
                detected_language,
                scope_context,
                organization_id,
                user_plan,
                estimated_total_tokens,  # GAP 1 FIX: Pass for token release
            ):
                yield event

        return StreamingResponse(
            stream_with_status(),
            media_type="text/event-stream"
        )
    else:
        # GAP 3 FIX: Acquire semaphore to limit concurrent LLM calls (non-streaming path)
        semaphore = await _get_llm_semaphore()

        async with semaphore:
            answer = None
            used_provider = primary_provider
            used_model = primary_model_name
            used_prompt_tokens = estimated_input_tokens
            last_exc: Exception | None = None
            import time as _time

            for idx, candidate in enumerate(llm_candidates):
                if candidate.provider == "openai" and not llm_router.is_provider_available("openai"):
                    logger.warning("⚡ [Chat] OpenAI circuit open, skipping primary")
                    continue

                # H8: Reset timer per candidate so metrics are accurate per-provider
                _llm_start = _time.monotonic()

                current_llm = llm
                if idx > 0:
                    try:
                        llm_result = LLMFactory.get_model(
                            provider=candidate.provider,
                            model_name=candidate.model,
                            user_plan=user_plan,
                            requested_tier=actual_tier,
                            temperature=0,
                            streaming=False,
                            allow_override=True,
                        )
                        current_llm = llm_result[0] if isinstance(llm_result, tuple) else llm_result
                    except Exception as e:
                        last_exc = e
                        if _should_failover(e):
                            logger.warning("⚠️ [Chat] Fallback init failed for %s/%s: %s", candidate.provider, candidate.model, e)
                            continue
                        # GAP 1 FIX: Release reserved tokens on error before raising
                        await release_reserved_tokens(organization_id, estimated_total_tokens)
                        raise

                candidate_prompt, candidate_vars, system_prompt = _prompt_bundle_for(candidate.provider)
                chain = candidate_prompt | current_llm | StrOutputParser()

                try:
                    # GAP 4 FIX: Wrap chain.invoke() with timeout to prevent indefinite hangs
                    if candidate.provider == "openai":
                        with openai_breaker:
                            answer = await asyncio.wait_for(
                                asyncio.to_thread(chain.invoke, candidate_vars),
                                timeout=settings.LLM_REQUEST_TIMEOUT
                            )
                    else:
                        answer = await asyncio.wait_for(
                            asyncio.to_thread(chain.invoke, candidate_vars),
                            timeout=settings.LLM_REQUEST_TIMEOUT
                        )
                    used_provider = candidate.provider
                    used_model = candidate.model
                    used_prompt_tokens = _estimate_prompt_tokens(system_prompt, candidate_vars)
                    # H8: Record LLM request duration
                    try:
                        from core.metrics import llm_request_duration
                        llm_request_duration.labels(provider=used_provider, model=used_model).observe(_time.monotonic() - _llm_start)
                    except Exception:
                        pass
                    break
                except asyncio.TimeoutError:
                    last_exc = asyncio.TimeoutError(f"LLM request timed out after {settings.LLM_REQUEST_TIMEOUT}s")
                    if _should_failover(last_exc):
                        logger.warning("⚠️ [Chat] LLM timeout, trying fallback from %s/%s", candidate.provider, candidate.model)
                        continue
                    logger.error("ERROR: LLM timeout: %s", last_exc)
                    sentry_sdk.capture_exception(last_exc)
                    # GAP 1 FIX: Release reserved tokens on timeout
                    await release_reserved_tokens(organization_id, estimated_total_tokens)
                    raise_http_error(
                        status.HTTP_504_GATEWAY_TIMEOUT,
                        "LLM_TIMEOUT",
                        "The model took too long to respond. Please try again.",
                        {"reason": str(last_exc)[:500]},
                    )
                except Exception as e:
                    last_exc = e
                    if _should_failover(e):
                        logger.warning("⚠️ [Chat] LLM failover from %s/%s: %s", candidate.provider, candidate.model, e)
                        continue
                    logger.error("ERROR: LLM Generation failed: %s", e)
                    sentry_sdk.capture_exception(e)
                    # GAP 1 FIX: Release reserved tokens on error
                    await release_reserved_tokens(organization_id, estimated_total_tokens)
                    if _is_timeout_error(e):
                        raise_http_error(
                            status.HTTP_504_GATEWAY_TIMEOUT,
                            "LLM_TIMEOUT",
                            "The model took too long to respond. Please try again.",
                            {"reason": str(e)[:500]},
                        )
                    raise_http_error(
                        status.HTTP_500_INTERNAL_SERVER_ERROR,
                        "LLM_FAILED",
                        "LLM generation failed.",
                        {"reason": str(e)[:500]},
                    )

            if answer is None and last_exc is not None:
                logger.error("ERROR: All LLM providers failed: %s", last_exc)
                sentry_sdk.capture_exception(last_exc)
                # GAP 1 FIX: Release reserved tokens when all providers fail
                try:
                    await release_reserved_tokens(organization_id, estimated_total_tokens)
                except Exception as rel_err:
                    logger.error("Failed to release tokens: %s", rel_err)
                if _is_timeout_error(last_exc):
                    raise_http_error(
                        status.HTTP_504_GATEWAY_TIMEOUT,
                        "LLM_TIMEOUT",
                        "The model took too long to respond. Please try again.",
                        {"reason": str(last_exc)[:500]},
                    )
                raise_http_error(
                    status.HTTP_500_INTERNAL_SERVER_ERROR,
                    "LLM_FAILED",
                    "LLM generation failed.",
                    {"reason": str(last_exc)[:500]},
                )

            # Add scope footnote for DOMINANT/CONTESTED classifications
            if scope_context and scope_context.classification in ("dominant", "contested"):
                scope_display = scope_context.scope_name or "your knowledge base"
                footnote = f"\n\n---\n*Answered based on context from **{scope_display}**.*"
                answer = answer + footnote

            # C2: Output safety filter — scan FULL response (including footnote) for PII
            try:
                from services.output_filter import output_filter
                filter_result = output_filter.filter_response(
                    answer, source_count=len(sources_metadata)
                )
                if filter_result.pii_detected:
                    logger.warning(
                        "🛡️ [Chat] PII detected in LLM output: %s",
                        filter_result.pii_detected,
                    )
                    answer = filter_result.filtered_text
            except Exception as e:
                logger.warning("⚠️ [Chat] Output filter error: %s", e)

            # M6: Prefer actual token counts from API when available
            total_tokens = used_prompt_tokens + _estimate_token_count(answer)
            completion_tokens = _estimate_token_count(answer)

            # H8: Record token metrics
            try:
                from core.metrics import llm_tokens_total
                llm_tokens_total.labels(provider=used_provider, model=used_model, type="prompt").inc(used_prompt_tokens)
                llm_tokens_total.labels(provider=used_provider, model=used_model, type="completion").inc(completion_tokens)
            except Exception:
                pass

            try:
                await record_llm_usage(
                    organization_id,
                    total_tokens,
                    plan_code=user_plan,
                    provider=used_provider,
                    model=used_model,
                )
            except Exception as e:
                logger.warning("⚠️ [Chat] Failed to record LLM usage: %s", e)

            # GAP 1 FIX: Release unused reserved tokens after recording actual usage
            unused_tokens = estimated_total_tokens - total_tokens
            if unused_tokens > 0:
                await release_reserved_tokens(organization_id, unused_tokens)

            # H7: Store response in semantic cache
            if getattr(settings, "SEMANTIC_CACHE_ENABLED", False):
                try:
                    from services.semantic_cache import semantic_cache
                    scope_ids_for_cache = [payload.scope_id] if payload.scope_id else []
                    await semantic_cache.put(query_vector, scope_ids_for_cache, answer, sources_metadata)
                    try:
                        from core.metrics import semantic_cache_ops
                        semantic_cache_ops.labels(operation="put").inc()
                    except Exception:
                        pass
                except Exception as e:
                    logger.warning("⚠️ [Chat] Semantic cache put error: %s", e)

            message_id = save_messages(
                supabase, payload.conversation_id, payload.query, answer,
                sources_metadata,
                organization_id=organization_id  # Org-scoped validation
            )

            return ChatResponse(
                answer=answer,
                sources=sources_metadata,
                conversation_id=payload.conversation_id,
                message_id=message_id,
                scope_context=scope_context,
            )


async def _stream_with_timeout_and_heartbeat(
    chain,
    input_vars: dict[str, Any],
    provider: str,
    timeout_seconds: float,
    heartbeat_interval: float,
) -> AsyncGenerator[Any, None]:
    """
    Stream LLM response with timeout protection and heartbeat to detect stalled connections.

    Issue #2: Original chain.astream() had no timeout and could hang indefinitely.
    Issue #4: Heartbeat events help detect mid-stream failures.
    """
    import time

    last_chunk_time = time.monotonic()

    async def stream_generator():
        nonlocal last_chunk_time
        if provider == "openai":
            with openai_breaker:
                async for chunk in chain.astream(input_vars):
                    last_chunk_time = time.monotonic()
                    yield chunk
        else:
            async for chunk in chain.astream(input_vars):
                last_chunk_time = time.monotonic()
                yield chunk

    stream = stream_generator()

    try:
        while True:
            try:
                # Use wait_for with heartbeat interval for chunk-level timeout
                chunk = await asyncio.wait_for(
                    stream.__anext__(),
                    timeout=min(heartbeat_interval, timeout_seconds)
                )
                yield ("chunk", chunk)
            except asyncio.TimeoutError:
                # Check if we've exceeded total timeout
                elapsed = time.monotonic() - last_chunk_time
                if elapsed >= timeout_seconds:
                    raise asyncio.TimeoutError(
                        f"LLM stream timed out after {timeout_seconds}s without new content"
                    )
                # Emit heartbeat to keep connection alive
                yield ("heartbeat", None)
            except StopAsyncIteration:
                break
    finally:
        # Ensure generator is closed
        await stream.aclose()


async def stream_chat_response(
    prompt_builder,
    llm_candidates: list[ModelSelection],
    actual_tier: str,
    context: str,
    question: str,
    sources: list[dict],
    conversation_id: str,
    user_id: str,
    supabase,
    language: str = "en",
    scope_context: ScopeContext | None = None,
    organization_id: str = "",
    plan_code: str = "free",
    estimated_total_tokens: int = 0,  # GAP 1 FIX: Add for token release
) -> AsyncGenerator[str, None]:
    """
    Stream chat response using Server-Sent Events (SSE) with failover support.

    Event format:
    - data: {"type": "token", "content": "..."}
    - data: {"type": "heartbeat"}  -- NEW: Keeps connection alive
    - data: {"type": "sources", "sources": [...]}
    - data: {"type": "scope_context", "scope_context": {...}}
    - data: {"type": "done"}
    - data: {"type": "error", ...}

    Fixes implemented:
    - Issue #2: Timeout wrapper prevents indefinite hangs
    - Issue #4: Heartbeat events for mid-stream failure detection
    - Issue #6: Uses list append + join instead of string concatenation O(n^2)
    - Issue #13: Respects global concurrency semaphore
    - GAP 1: Releases reserved tokens after actual usage recording
    """
    last_exc: Exception | None = None
    stream_timeout = getattr(settings, 'LLM_STREAM_TIMEOUT', 60)
    heartbeat_interval = getattr(settings, 'LLM_HEARTBEAT_INTERVAL', 10.0)

    # Acquire semaphore to limit concurrent LLM calls
    semaphore = _get_llm_semaphore()

    async with semaphore:
        for candidate in llm_candidates:
            if candidate.provider == "openai" and not llm_router.is_provider_available("openai"):
                logger.warning("⚡ [Chat] OpenAI circuit open, skipping stream attempt")
                continue

            # Fix Issue #6: Use list for O(n) string building instead of O(n^2) concatenation
            response_chunks: list[str] = []
            sent_any = False

            try:
                llm_result = LLMFactory.get_model(
                    provider=candidate.provider,
                    model_name=candidate.model,
                    user_plan=plan_code,
                    requested_tier=actual_tier,
                    temperature=0,
                    streaming=True,
                    allow_override=True,
                )
                llm = llm_result[0] if isinstance(llm_result, tuple) else llm_result
            except Exception as e:
                last_exc = e
                if _should_failover(e):
                    logger.warning("⚠️ [Chat] Failed to init stream provider %s/%s: %s", candidate.provider, candidate.model, e)
                    continue
                raise

            prompt, input_vars, system_prompt = prompt_builder(candidate.provider)
            chain = prompt | llm

            try:
                # Issue #2 & #4: Stream with timeout and heartbeat
                async for event_type, event_data in _stream_with_timeout_and_heartbeat(
                    chain,
                    input_vars,
                    candidate.provider,
                    stream_timeout,
                    heartbeat_interval,
                ):
                    if event_type == "heartbeat":
                        # Send heartbeat to keep connection alive and signal health
                        yield _safe_sse_json({'type': 'heartbeat'})
                    elif event_type == "chunk":
                        chunk = event_data
                        if hasattr(chunk, "content") and chunk.content:
                            sent_any = True
                            response_chunks.append(chunk.content)  # O(1) amortized
                            yield _safe_sse_json({'type': 'token', 'content': chunk.content})

                # Join all chunks at end (O(n) total instead of O(n^2))
                full_response = "".join(response_chunks)

                # Add scope footnote for DOMINANT/CONTESTED classifications
                if scope_context and scope_context.classification in ("dominant", "contested"):
                    scope_display = scope_context.scope_name or "your knowledge base"
                    footnote = f"\n\n---\n*Answered based on context from **{scope_display}**.*"
                    full_response += footnote
                    yield _safe_sse_json({'type': 'token', 'content': footnote})

                # Send sources after completion
                yield _safe_sse_json({'type': 'sources', 'sources': sources})

                # Send scope context if available
                if scope_context:
                    yield _safe_sse_json({'type': 'scope_context', 'scope_context': scope_context.model_dump()})

                # Save messages (org-scoped validation)
                message_id = save_messages(
                    supabase, conversation_id, question, full_response,
                    sources,
                    organization_id=organization_id
                )

                # Emit SSE error if message save returned None but we had a conversation
                if message_id is None and conversation_id:
                    sentry_sdk.capture_message(
                        f"Message save failed: conv={conversation_id[:8]}... org={organization_id[:8]}...",
                        level="error",
                    )
                    yield _safe_sse_json({'type': 'error', 'message': 'Failed to save message', 'error': 'MESSAGE_SAVE_FAILED'})

                total_tokens = _estimate_prompt_tokens(system_prompt, input_vars) + _estimate_token_count(full_response)
                usage_recorded = False
                try:
                    await record_llm_usage(
                        organization_id,
                        total_tokens,
                        plan_code=plan_code,
                        provider=candidate.provider,
                        model=candidate.model,
                    )
                    usage_recorded = True
                except Exception as e:
                    logger.warning("⚠️ [Chat] Failed to record LLM usage: %s", e)

                # GAP 1 FIX: Release reserved tokens based on whether usage was recorded
                try:
                    if usage_recorded:
                        unused_tokens = estimated_total_tokens - total_tokens
                        if unused_tokens > 0:
                            await release_reserved_tokens(organization_id, unused_tokens)
                    else:
                        # Usage not recorded, release full reservation
                        await release_reserved_tokens(organization_id, estimated_total_tokens)
                except Exception as rel_err:
                    logger.error("Failed to release tokens: %s", rel_err)

                yield _safe_sse_json({'type': 'done', 'message_id': message_id})
                return

            except Exception as e:
                last_exc = e
                if sent_any:
                    # Issue #4: Enhanced error signaling after partial output
                    logger.error("Streaming error after partial output: %s", e)
                    sentry_sdk.capture_exception(e)

                    # Build partial response from chunks collected so far
                    partial_response = "".join(response_chunks)

                    # GAP 1 FIX: Release reserved tokens on error (partial response)
                    try:
                        await release_reserved_tokens(organization_id, estimated_total_tokens)
                    except Exception as rel_err:
                        logger.error("Failed to release tokens: %s", rel_err)

                    payload = build_error_payload(
                        "LLM_STREAM_INTERRUPTED",
                        "Streaming was interrupted. Partial response may be incomplete.",
                        {
                            "reason": str(e)[:500],
                            "partial_length": len(partial_response),
                            "recoverable": False,
                        },
                    )
                    yield _safe_sse_json({'type': 'error', **payload})
                    return

                if _should_failover(e):
                    logger.warning("⚠️ [Chat] Streaming failover from %s/%s: %s", candidate.provider, candidate.model, e)
                    continue

                logger.error("Streaming error: %s", e)
                sentry_sdk.capture_exception(e)
                # GAP 1 FIX: Release reserved tokens on error
                try:
                    await release_reserved_tokens(organization_id, estimated_total_tokens)
                except Exception as rel_err:
                    logger.error("Failed to release tokens: %s", rel_err)
                if _is_timeout_error(e):
                    payload = build_error_payload(
                        "LLM_TIMEOUT",
                        "The model took too long to respond. Please try again.",
                        {"reason": str(e)[:500]},
                    )
                else:
                    payload = build_error_payload(
                        "LLM_FAILED",
                        "LLM generation failed.",
                        {"reason": str(e)[:500]},
                    )
                yield _safe_sse_json({'type': 'error', **payload})
                return

        if last_exc:
            logger.error("Streaming error: %s", last_exc)
            sentry_sdk.capture_exception(last_exc)
            # GAP 1 FIX: Release reserved tokens when all providers fail
            try:
                await release_reserved_tokens(organization_id, estimated_total_tokens)
            except Exception as rel_err:
                logger.error("Failed to release tokens: %s", rel_err)
            payload = build_error_payload(
                "LLM_FAILED",
                "LLM generation failed.",
                {"reason": str(last_exc)[:500]},
            )
            yield _safe_sse_json({'type': 'error', **payload})


def save_messages(
    supabase,
    conversation_id: str,
    query: str,
    answer: str,
    sources: list[Any],
    organization_id: str = None,
) -> str | None:
    """
    Save user and assistant messages to database.

    SECURITY: When organization_id is provided, validates that the conversation
    belongs to the organization before updating. This prevents cross-org writes
    when using service keys that bypass RLS.
    """
    if not conversation_id:
        return None

    try:
        now = datetime.now(timezone.utc).isoformat()

        # SECURITY: Validate conversation belongs to organization before any writes
        # This prevents ID harvesting attacks across organizational boundaries
        if organization_id:
            conv_check = supabase.table("conversations")\
                .select("id")\
                .eq("id", conversation_id)\
                .eq("organization_id", organization_id)\
                .execute()
            if not conv_check.data:
                logger.warning(
                    f"⚠️ [SaveMessages] Org mismatch: conv {conversation_id[:8]}... "
                    f"not in org {organization_id[:8]}..."
                )
                sentry_sdk.capture_message(
                    f"Org mismatch in save_messages: conv={conversation_id[:8]}... org={organization_id[:8]}...",
                    level="error",
                )
                return None  # Silent fail - don't leak info about other orgs

        # Batch insert both messages atomically to prevent orphaned user messages
        messages_to_insert = [
            {
                "conversation_id": conversation_id,
                "role": "user",
                "content": query,
                "sources": [],
                "created_at": now,
            },
            {
                "conversation_id": conversation_id,
                "role": "assistant",
                "content": answer,
                "sources": sources or [],
                "created_at": now,
            },
        ]
        result = supabase.table("messages").insert(messages_to_insert).execute()

        message_id = None
        if result.data and len(result.data) >= 2:
            message_id = result.data[1]["id"]

        # Update conversation timestamp (org-scoped if provided)
        update_query = supabase.table("conversations").update({
            "updated_at": now
        }).eq("id", conversation_id)
        if organization_id:
            update_query = update_query.eq("organization_id", organization_id)
        update_query.execute()

        return message_id

    except Exception as e:
        logger.warning(f"WARNING: Failed to save messages: {e}")
        sentry_sdk.capture_exception(e)
        return None
