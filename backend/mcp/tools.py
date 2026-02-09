"""
MCP Tool Definitions

Defines the tools available to AI agents via MCP protocol.
Each tool has a schema, description, and execution handler.
"""

import logging
from typing import Any

logger = logging.getLogger(__name__)


# =============================================================================
# Tool Definitions (JSON Schema)
# =============================================================================

MCP_TOOLS = [
    {
        "name": "search_documents",
        "description": (
            "Semantic search over the organization's knowledge base. "
            "Returns relevant document chunks with content and metadata. "
            "Use this for finding specific information across documents."
        ),
        "inputSchema": {
            "type": "object",
            "properties": {
                "query": {
                    "type": "string",
                    "description": "The search query (natural language)",
                },
                "scope_ids": {
                    "type": "array",
                    "items": {"type": "string"},
                    "description": "Optional list of scope IDs to search within",
                },
                "limit": {
                    "type": "integer",
                    "default": 10,
                    "minimum": 1,
                    "maximum": 50,
                    "description": "Maximum number of results to return",
                },
            },
            "required": ["query"],
        },
    },
    {
        "name": "ask_question",
        "description": (
            "RAG-based question answering with source citations. "
            "Retrieves relevant context and generates a natural language answer. "
            "Use this for complex questions that require synthesis."
        ),
        "inputSchema": {
            "type": "object",
            "properties": {
                "question": {
                    "type": "string",
                    "description": "The question to answer",
                },
                "scope_id": {
                    "type": "string",
                    "description": "Optional scope ID to restrict the answer context",
                },
            },
            "required": ["question"],
        },
    },
    {
        "name": "list_scopes",
        "description": (
            "List available document scopes (sources/collections). "
            "Returns scope IDs, names, and document counts. "
            "Use this to discover what knowledge is available."
        ),
        "inputSchema": {
            "type": "object",
            "properties": {},
        },
    },
    {
        "name": "get_document_summary",
        "description": (
            "Get a summary of a specific document by ID. "
            "Returns title, source, chunk count, and metadata."
        ),
        "inputSchema": {
            "type": "object",
            "properties": {
                "document_id": {
                    "type": "string",
                    "description": "The document ID to summarize",
                },
            },
            "required": ["document_id"],
        },
    },
]


# =============================================================================
# Tool Execution
# =============================================================================

async def execute_tool(
    tool_name: str,
    arguments: dict[str, Any],
    organization_id: str,
    agent_id: str,
    allowed_scopes: list[str] | None = None,
) -> dict[str, Any]:
    """
    Execute an MCP tool and return results.

    Args:
        tool_name: Name of the tool to execute
        arguments: Tool arguments from the request
        organization_id: Organization context
        agent_id: Agent making the request
        allowed_scopes: Optional scope whitelist for this agent

    Returns:
        Tool execution result

    Raises:
        ValueError: If tool not found or invalid arguments
        PermissionError: If agent lacks access to requested scope
    """
    # Validate tool exists
    tool_names = {t["name"] for t in MCP_TOOLS}
    if tool_name not in tool_names:
        raise ValueError(f"Unknown tool: {tool_name}")

    # Route to handler
    if tool_name == "search_documents":
        return await _execute_search_documents(
            arguments, organization_id, agent_id, allowed_scopes
        )
    elif tool_name == "ask_question":
        return await _execute_ask_question(
            arguments, organization_id, agent_id, allowed_scopes
        )
    elif tool_name == "list_scopes":
        return await _execute_list_scopes(
            arguments, organization_id, agent_id, allowed_scopes
        )
    elif tool_name == "get_document_summary":
        return await _execute_get_document_summary(
            arguments, organization_id, agent_id, allowed_scopes
        )
    else:
        raise ValueError(f"Tool not implemented: {tool_name}")


# =============================================================================
# Tool Handlers
# =============================================================================

async def _execute_search_documents(
    arguments: dict[str, Any],
    organization_id: str,
    agent_id: str,
    allowed_scopes: list[str] | None = None,
) -> dict[str, Any]:
    """
    Execute semantic search over documents.

    Returns content chunks with metadata and relevance scores.
    """
    from core.config import settings
    from core.db import get_supabase
    from core.security import decrypt_text

    query = arguments.get("query")
    if not query or not query.strip():
        raise ValueError("Query cannot be empty")

    scope_ids = arguments.get("scope_ids", [])
    limit = min(arguments.get("limit", 10), 50)

    # Validate scope access
    if allowed_scopes and scope_ids:
        for scope_id in scope_ids:
            if not _scope_allowed(scope_id, allowed_scopes):
                raise PermissionError(f"Access denied to scope: {scope_id}")

    supabase = get_supabase()

    # Generate embedding for query
    from langchain_openai import OpenAIEmbeddings

    # Generate embedding using langchain (same as search.py)
    embeddings_model = OpenAIEmbeddings(
        model="text-embedding-3-small",
        api_key=settings.OPENAI_API_KEY,
    )
    query_embedding = embeddings_model.embed_query(query)

    # Execute search using appropriate RPC
    if scope_ids:
        # Use scoped search when explicit scope filter provided
        result = supabase.rpc("hybrid_search_scoped", {
            "query_text": query,
            "query_embedding": query_embedding,
            "match_count": limit,
            "filter_org_id": organization_id,
            "filter_scope_ids": scope_ids,
            "similarity_threshold": settings.RAG_SIMILARITY_THRESHOLD,
        }).execute()
    else:
        # Standard hybrid search
        result = supabase.rpc("hybrid_search", {
            "query_text": query,
            "query_embedding": query_embedding,
            "match_count": limit,
            "filter_org_id": organization_id,
            "similarity_threshold": settings.RAG_SIMILARITY_THRESHOLD,
        }).execute()

    # Process results
    chunks = []
    for row in result.data or []:
        # Decrypt content (Ghost Protocol)
        content = row.get("content", "")
        try:
            content = decrypt_text(content)
        except Exception:
            content = "[Content unavailable]"

        chunks.append({
            "chunk_id": row.get("id"),
            "document_id": row.get("document_id"),
            "document_title": row.get("title", "Unknown"),
            "content": content,
            "score": row.get("score", 0),
            "scope_id": row.get("scope_id"),
            "metadata": row.get("metadata", {}),
        })

    logger.info(
        f"[MCP] search_documents: agent={agent_id[:8]}... "
        f"query='{query[:50]}...' results={len(chunks)}"
    )

    return {
        "query": query,
        "results": chunks,
        "total": len(chunks),
    }


async def _execute_ask_question(
    arguments: dict[str, Any],
    organization_id: str,
    agent_id: str,
    allowed_scopes: list[str] | None = None,
) -> dict[str, Any]:
    """
    Execute RAG-based question answering.

    Retrieves relevant context, generates answer, and includes citations.
    """
    from services.llm_factory import get_llm_client

    question = arguments.get("question")
    if not question or not question.strip():
        raise ValueError("Question cannot be empty")

    scope_id = arguments.get("scope_id")

    # Validate scope access
    if allowed_scopes and scope_id:
        if not _scope_allowed(scope_id, allowed_scopes):
            raise PermissionError(f"Access denied to scope: {scope_id}")

    # First, search for relevant context
    search_args = {
        "query": question,
        "limit": 5,
    }
    if scope_id:
        search_args["scope_ids"] = [scope_id]

    search_result = await _execute_search_documents(
        search_args, organization_id, agent_id, allowed_scopes
    )

    # Build context from search results
    context_chunks = search_result.get("results", [])
    if not context_chunks:
        return {
            "question": question,
            "answer": "I couldn't find relevant information to answer this question.",
            "sources": [],
            "context_used": 0,
        }

    # Format context for LLM
    context_text = "\n\n".join([
        f"[Source: {c['document_title']}]\n{c['content']}"
        for c in context_chunks
    ])

    # Generate answer using LLM
    llm = get_llm_client()
    system_prompt = (
        "You are a helpful assistant that answers questions based on the provided context. "
        "Always cite your sources when possible. If the context doesn't contain enough "
        "information to fully answer the question, say so clearly."
    )

    user_prompt = f"""Based on the following context, please answer the question.

Context:
{context_text}

Question: {question}

Provide a clear, accurate answer based only on the context provided."""

    response = await llm.chat.completions.create(
        model="gpt-4o-mini",
        messages=[
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_prompt},
        ],
        max_tokens=1000,
        temperature=0.7,
    )

    answer = response.choices[0].message.content

    # Extract source citations
    sources = [
        {
            "document_id": c["document_id"],
            "title": c["document_title"],
            "scope_id": c["scope_id"],
        }
        for c in context_chunks
    ]

    logger.info(
        f"[MCP] ask_question: agent={agent_id[:8]}... "
        f"question='{question[:50]}...' sources={len(sources)}"
    )

    return {
        "question": question,
        "answer": answer,
        "sources": sources,
        "context_used": len(context_chunks),
    }


async def _execute_list_scopes(
    arguments: dict[str, Any],
    organization_id: str,
    agent_id: str,
    allowed_scopes: list[str] | None = None,
) -> dict[str, Any]:
    """
    List available scopes for the organization.

    Returns scope metadata and document counts.
    """
    from core.db import get_supabase

    supabase = get_supabase()

    # Get distinct scopes from documents
    result = supabase.table("documents")\
        .select("scope_id, source_type")\
        .eq("organization_id", organization_id)\
        .neq("source_type", "identity")\
        .neq("source_type", "scope_identity")\
        .execute()

    # Aggregate by scope
    scope_counts: dict[str, dict[str, Any]] = {}
    for row in result.data or []:
        scope_id = row.get("scope_id") or "default"

        # Filter by allowed scopes if specified
        if allowed_scopes and not _scope_allowed(scope_id, allowed_scopes):
            continue

        if scope_id not in scope_counts:
            scope_counts[scope_id] = {
                "scope_id": scope_id,
                "source_type": row.get("source_type"),
                "document_count": 0,
            }
        scope_counts[scope_id]["document_count"] += 1

    scopes = list(scope_counts.values())

    logger.info(
        f"[MCP] list_scopes: agent={agent_id[:8]}... "
        f"scopes={len(scopes)}"
    )

    return {
        "scopes": scopes,
        "total": len(scopes),
    }


async def _execute_get_document_summary(
    arguments: dict[str, Any],
    organization_id: str,
    agent_id: str,
    allowed_scopes: list[str] | None = None,
) -> dict[str, Any]:
    """
    Get summary information for a specific document.
    """
    from core.db import get_supabase

    document_id = arguments.get("document_id")
    if not document_id:
        raise ValueError("document_id is required")

    supabase = get_supabase()

    # Fetch document
    result = supabase.table("documents")\
        .select("id, title, source_type, scope_id, created_at, metadata")\
        .eq("id", document_id)\
        .eq("organization_id", organization_id)\
        .maybe_single()\
        .execute()

    if not result.data:
        raise ValueError(f"Document not found: {document_id}")

    doc = result.data

    # Check scope access
    if allowed_scopes:
        scope_id = doc.get("scope_id") or "default"
        if not _scope_allowed(scope_id, allowed_scopes):
            raise PermissionError(f"Access denied to document in scope: {scope_id}")

    # Get chunk count
    chunk_count_result = supabase.table("document_chunks")\
        .select("id", count="exact")\
        .eq("document_id", document_id)\
        .execute()

    chunk_count = chunk_count_result.count or 0

    logger.info(
        f"[MCP] get_document_summary: agent={agent_id[:8]}... "
        f"doc={document_id[:8]}..."
    )

    return {
        "document_id": doc["id"],
        "title": doc.get("title", "Unknown"),
        "source_type": doc.get("source_type"),
        "scope_id": doc.get("scope_id"),
        "created_at": doc.get("created_at"),
        "chunk_count": chunk_count,
        "metadata": doc.get("metadata", {}),
    }


# =============================================================================
# Helpers
# =============================================================================

def _scope_allowed(scope_id: str, allowed_scopes: list[str]) -> bool:
    """
    Check if a scope ID matches the allowed scope patterns.

    Supports wildcards: "*" matches everything, "gdrive:*" matches all gdrive scopes.
    """
    if not allowed_scopes:
        return True

    for pattern in allowed_scopes:
        if pattern == "*":
            return True
        if pattern.endswith("*"):
            prefix = pattern[:-1]
            if scope_id.startswith(prefix):
                return True
        elif pattern == scope_id:
            return True

    return False
