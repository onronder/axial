from fastapi import APIRouter, Depends, HTTPException, status, Request, BackgroundTasks
from fastapi.responses import StreamingResponse
from pydantic import BaseModel, Field
from typing import List, Dict, Any, Optional, AsyncGenerator
from core.security import get_current_user
from core.db import get_supabase
from core.config import settings
from services.audit import log_chat_delete, audit_logger
from services.llm_factory import LLMFactory
from services.guardrails import guardrail_service
from services.router import llm_router
from langchain_openai import OpenAIEmbeddings
from langchain_core.prompts import ChatPromptTemplate
from langchain_core.output_parsers import StrOutputParser
from slowapi import Limiter
from slowapi.util import get_remote_address
from datetime import datetime
import logging
import json
import sentry_sdk

logger = logging.getLogger(__name__)
router = APIRouter()

# Rate limiter instance
limiter = Limiter(key_func=get_remote_address)

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
    sources: List[str] = []
    created_at: str

@router.get("/conversations", response_model=List[ConversationResponse])
async def list_conversations(
    user_id: str = Depends(get_current_user)
):
    """List all conversations for the current user."""
    supabase = get_supabase()
    
    try:
        response = supabase.table("conversations").select("*").eq("user_id", user_id).order("updated_at", desc=True).execute()
        return response.data
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to fetch conversations: {str(e)}")

@router.post("/conversations", response_model=ConversationResponse)
async def create_conversation(
    payload: ConversationCreate,
    user_id: str = Depends(get_current_user)
):
    """Create a new conversation."""
    supabase = get_supabase()
    
    now = datetime.utcnow().isoformat()
    data = {
        "user_id": user_id,
        "title": payload.title,
        "created_at": now,
        "updated_at": now
    }
    
    try:
        response = supabase.table("conversations").insert(data).execute()
        if not response.data:
            raise HTTPException(status_code=500, detail="Failed to create conversation")
        return response.data[0]
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to create conversation: {str(e)}")

@router.get("/conversations/{conversation_id}", response_model=ConversationResponse)
async def get_conversation(
    conversation_id: str,
    user_id: str = Depends(get_current_user)
):
    """Get a specific conversation."""
    supabase = get_supabase()
    
    try:
        response = supabase.table("conversations").select("*").eq("id", conversation_id).eq("user_id", user_id).single().execute()
        if not response.data:
            raise HTTPException(status_code=404, detail="Conversation not found")
        return response.data
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to fetch conversation: {str(e)}")

@router.patch("/conversations/{conversation_id}", response_model=ConversationResponse)
async def update_conversation(
    conversation_id: str,
    payload: ConversationUpdate,
    user_id: str = Depends(get_current_user)
):
    """Update a conversation (e.g., rename)."""
    supabase = get_supabase()
    
    try:
        response = supabase.table("conversations").update({
            "title": payload.title,
            "updated_at": datetime.utcnow().isoformat()
        }).eq("id", conversation_id).eq("user_id", user_id).execute()
        
        if not response.data:
            raise HTTPException(status_code=404, detail="Conversation not found")
        return response.data[0]
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to update conversation: {str(e)}")

@router.delete("/conversations/{conversation_id}")
async def delete_conversation(
    conversation_id: str,
    request: Request,
    background_tasks: BackgroundTasks,
    user_id: str = Depends(get_current_user)
):
    """Delete a conversation and all its messages."""
    supabase = get_supabase()
    
    try:
        # Get conversation info for audit log
        conv_response = supabase.table("conversations").select("title").eq("id", conversation_id).eq("user_id", user_id).single().execute()
        conv_title = conv_response.data.get("title", "Unknown") if conv_response.data else "Unknown"
        
        # Delete conversation (messages cascade)
        response = supabase.table("conversations").delete().eq("id", conversation_id).eq("user_id", user_id).execute()
        
        # Audit log (async)
        log_chat_delete(background_tasks, user_id, conversation_id, conv_title, request)
        
        return {"status": "success", "deleted_id": conversation_id}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to delete conversation: {str(e)}")
@router.get("/conversations/{conversation_id}/messages", response_model=List[MessageResponse])
async def get_messages(
    conversation_id: str,
    user_id: str = Depends(get_current_user)
):
    """Get all messages for a conversation."""
    supabase = get_supabase()
    
    # First verify the user owns this conversation
    conv_check = supabase.table("conversations").select("id").eq("id", conversation_id).eq("user_id", user_id).execute()
    if not conv_check.data:
        raise HTTPException(status_code=404, detail="Conversation not found")
    
    try:
        response = supabase.table("messages").select("*").eq("conversation_id", conversation_id).order("created_at", desc=False).execute()
        return response.data
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to fetch messages: {str(e)}")


# ============================================================
# CONVERSATIONAL RAG CHAT ENDPOINT
# ============================================================

class ChatRequest(BaseModel):
    """
    Chat request with input validation.
    
    Constraints:
    - query: max 20,000 chars (~5,000 tokens) - prevents massive payloads
    - conversation_id: max 50 chars (UUIDs are 36 chars)
    - model: max 50 chars - prevents abuse
    """
    query: str = Field(..., min_length=1, max_length=20000)
    conversation_id: Optional[str] = Field(None, max_length=50)
    history: Optional[List[Dict[str, str]]] = []
    model: str = Field(default="gpt-4o", max_length=50)
    stream: bool = Field(default=False)

class ChatResponse(BaseModel):
    answer: str
    sources: List[Dict[str, Any]]  # Enhanced sources with metadata
    conversation_id: Optional[str] = None
    message_id: Optional[str] = None


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

def trim_history(history: List[Dict[str, str]], max_tokens: int = 2000) -> List[Dict[str, str]]:
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

def condense_question(query: str, history: List[Dict[str, str]]) -> str:
    """
    If chat history exists, rewrite the query as a standalone question.
    Uses GPT-4o-mini for speed and cost efficiency.
    """
    if not history:
        return query
    
    # Format history for the prompt
    history_text = ""
    for msg in history[-6:]:  # Last 6 messages max (3 turns)
        role = msg.get("role", "user")
        content = msg.get("content", "")[:500]  # Truncate long messages
        history_text += f"{role.upper()}: {content}\n"
    
    if not history_text.strip():
        return query
    
    try:
        llm = ChatOpenAI(
            model="gpt-4o-mini",  # Fast and cheap for condensing
            temperature=0,
            api_key=settings.OPENAI_API_KEY
        )
        
        prompt = ChatPromptTemplate.from_template(CONDENSE_PROMPT)
        chain = prompt | llm | StrOutputParser()
        
        standalone = chain.invoke({"history": history_text, "question": query})
        logger.info(f"🔄 [Chat] Condensed: '{query[:50]}...' → '{standalone[:50]}...'")
        return standalone.strip()
        
    except Exception as e:
        logger.warning(f"⚠️ [Chat] Condense failed, using original query: {e}")
        return query


# ============================================================
# SYSTEM PROMPT WITH CITATION RULES
# ============================================================

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


def format_context_with_citations(docs: List[Dict]) -> tuple:
    """
    Format retrieved documents with numbered citations.
    
    Returns:
        Tuple of (formatted_context_string, sources_metadata_list)
    """
    if not docs:
        return "", []
    
    context_parts = []
    sources = []
    
    for i, doc in enumerate(docs, 1):
        content = doc.get('content', '')
        metadata = doc.get('metadata', {})
        source_type = doc.get('source_type', metadata.get('source', 'unknown'))
        
        # Build source label based on type
        if source_type == "web":
            source_label = metadata.get("url", metadata.get("source_url", "Web Page"))
            source_type_display = "Web"
        elif source_type == "file":
            source_label = metadata.get("filename", metadata.get("title", "Uploaded File"))
            source_type_display = "File"
        elif source_type == "drive":
            source_label = metadata.get("title", "Google Drive")
            source_type_display = "Drive"
        elif source_type == "notion":
            source_label = metadata.get("title", "Notion Page")
            source_type_display = "Notion"
        else:
            source_label = metadata.get("title", metadata.get("filename", "Document"))
            source_type_display = source_type.title() if source_type else "Doc"
        
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
# MAIN CHAT ENDPOINT
# ============================================================

@router.post("/chat")
@limiter.limit(settings.RATE_LIMIT_DEFAULT)
async def chat_endpoint(
    request: Request,
    payload: ChatRequest,
    background_tasks: BackgroundTasks,
    user_id: str = Depends(get_current_user)
):
    """
    Intelligent Conversational RAG Chat Endpoint.
    
    Pipeline:
    1. Guardrail Analysis - Safety, language, intent, complexity
    2. Fast Exit - Handle greetings/off-topic without RAG
    3. User Plan Lookup - Determine subscription tier
    4. Smart Routing - Select optimal model (GPT-4o or Llama)
    5. RAG Execution - Retrieve context, generate answer
    6. Streaming Support - Optional SSE streaming
    """
    supabase = get_supabase()
    
    # ========== STEP 1: GUARDRAIL ANALYSIS (Ultra-fast via Groq) ==========
    guardrail_result = await guardrail_service.analyze_query(payload.query)
    detected_language = guardrail_result.language
    
    logger.info(f"🛡️ [Chat] Guardrails: lang={detected_language}, "
                f"safe={guardrail_result.is_safe}, intent={guardrail_result.intent}, "
                f"complexity={guardrail_result.complexity}")
    
    # ========== STEP 2: SAFETY CHECK ==========
    if not guardrail_result.is_safe:
        # Log safety violation to audit
        audit_logger.log(
            background_tasks,
            user_id=user_id,
            action="safety_violation",
            resource_type="chat",
            resource_id=payload.conversation_id,
            details={"query": payload.query[:500], "language": detected_language},
            request=request
        )
        
        # Return refusal message
        refusal = guardrail_result.reply or "I cannot assist with that request."
        return ChatResponse(
            answer=refusal,
            sources=[],
            conversation_id=payload.conversation_id
        )
    
    # ========== STEP 3: INTENT CHECK (Fast exit for non-RAG) ==========
    if guardrail_result.intent in ("GREETING", "OFF_TOPIC"):
        # Return pre-generated response (no RAG needed)
        fast_reply = guardrail_result.reply or "How can I help you with your documents today?"
        
        # Save to conversation if conversation_id exists
        if payload.conversation_id:
            save_messages(supabase, payload.conversation_id, payload.query, fast_reply, [])
        
        return ChatResponse(
            answer=fast_reply,
            sources=[],
            conversation_id=payload.conversation_id
        )
    
    # ========== STEP 4: FETCH USER PLAN ==========
    try:
        profile_response = supabase.table("user_profiles").select("plan").eq("user_id", user_id).single().execute()
        user_plan = profile_response.data.get("plan", "free") if profile_response.data else "free"
    except Exception as e:
        logger.warning(f"⚠️ [Chat] Could not fetch user plan: {e}")
        user_plan = "free"
    
    # ========== STEP 5: SMART ROUTING (Select Model) ==========
    model_selection = llm_router.select_model(
        plan=user_plan,
        complexity=guardrail_result.complexity
    )
    logger.info(f"🚀 [Chat] Route: plan={user_plan} → {model_selection.provider}/{model_selection.model}")
    
    # ========== STEP 6: CONDENSE QUESTION (with trimmed history) ==========
    # Task 3: Token-Aware History Pruning
    trimmed_history = trim_history(payload.history or [])
    search_query = condense_question(payload.query, trimmed_history)
    
    # ========== STEP 7: EMBED QUERY ==========
    embeddings_model = OpenAIEmbeddings(
        model="text-embedding-3-small", 
        api_key=settings.OPENAI_API_KEY
    )
    
    try:
        query_vector = embeddings_model.embed_query(search_query)
    except Exception as e:
        logger.error(f"ERROR: Embedding failed: {e}")
        raise HTTPException(500, f"Embedding failed: {e}")

    # ========== STEP 8: HYBRID SEARCH ==========
    try:
        response = supabase.rpc("hybrid_search", {
            "query_text": search_query,
            "query_embedding": query_vector,
            "match_count": 10,  # Fetch more initially, then filter
            "filter_user_id": user_id,
            "vector_weight": 0.7,
            "keyword_weight": 0.3,
            "similarity_threshold": 0.25
        }).execute()
        
        docs = response.data or []
        logger.info(f"📚 [Chat] Hybrid search found {len(docs)} raw candidates")
    except Exception as e:
        logger.warning(f"⚠️ [Chat] Hybrid search failed, using vector: {e}")
        try:
            response = supabase.rpc("match_documents", {
                "query_embedding": query_vector,
                "match_threshold": 0.25, 
                "match_count": 10,
                "filter_user_id": user_id
            }).execute()
            docs = response.data or []
        except Exception as fallback_e:
            logger.error(f"ERROR: Retrieval failed: {fallback_e}")
            raise HTTPException(500, f"Retrieval failed: {fallback_e}")

    # ========== STEP 9: DYNAMIC CONTEXT INJECTION (The 0.75 Rule) ==========
    # Task 2: Only include chunks with similarity > 0.75
    high_quality_docs = [
        d for d in docs 
        if d.get("similarity", 0) >= 0.75
    ]
    
    context_text = ""
    sources_metadata = []
    
    if high_quality_docs:
        logger.info(f"✅ [Chat] High quality context found: {len(high_quality_docs)} docs")
        context_text, sources_metadata = format_context_with_citations(high_quality_docs)
    else:
        # "Empty Context" Logic: If no docs pass threshold, send raw query without context.
        # This saves tokens on irrelevant retrieval and allows general retrieval fallback if desired,
        # or simply general chitchat handling.
        logger.info("📉 [Chat] No Docs > 0.75 similarity. Dropping context (General Query).")
        context_text = ""
        sources_metadata = []

    # ========== STEP 10: GET SELECTED LLM & ENFORCE PLAN ==========
    # Task 1: Hard-Enforce Limits via Factory
    llm = LLMFactory.get_model(
        provider=model_selection.provider,
        model_name=model_selection.model,
        user_plan=user_plan,  # Must pass plan for enforcement
        temperature=0.1,
        streaming=payload.stream
    )
    
    # Prompt Construction
    # If we have context, use RAG prompt. If not, use standard prompt.
    if context_text:
        prompt = ChatPromptTemplate.from_messages([
            ("system", SYSTEM_PROMPT),  # Contains {context} placeholder
            ("user", "{question}")
        ])
        input_vars = {
            "context": context_text,
            "question": search_query,
            "language": detected_language
        }
    else:
        # General/Fallback Prompt without context injection
        # Saves 2000+ tokens by not injecting "No documents found" filler
        GENERAL_SYSTEM_PROMPT = """You are Axio, a helpful AI assistant.
        Answer the user's question directly and helpfully in {language}.
        If the question requires private knowledge that you don't have, politely admit it.
        """
        prompt = ChatPromptTemplate.from_messages([
            ("system", GENERAL_SYSTEM_PROMPT),
            ("user", "{question}")
        ])
        input_vars = {
            "question": search_query,
            "language": detected_language
        }
    
    if payload.stream:
        # ========== STREAMING RESPONSE ==========
        return StreamingResponse(
            stream_chat_response(
                prompt, llm, context_text, search_query, 
                sources_metadata, payload.conversation_id, user_id, supabase,
                detected_language
            ),
            media_type="text/event-stream"
        )
    else:
        # ========== STANDARD RESPONSE ==========
        chain = prompt | llm | StrOutputParser()
        
        try:
            answer = chain.invoke(input_vars)
        except Exception as e:
            logger.error(f"ERROR: LLM Generation failed: {e}")
            sentry_sdk.capture_exception(e)
            raise HTTPException(500, f"LLM Generation failed: {e}")

        # Save messages if conversation_id is provided
        message_id = save_messages(
            supabase, payload.conversation_id, payload.query, answer, 
            [s.get("label", "") for s in sources_metadata]
        )

        return ChatResponse(
            answer=answer,
            sources=sources_metadata,
            conversation_id=payload.conversation_id,
            message_id=message_id
        )


async def stream_chat_response(
    prompt, llm, context: str, question: str,
    sources: List[Dict], conversation_id: str, user_id: str, supabase,
    language: str = "en"
) -> AsyncGenerator[str, None]:
    """
    Stream chat response using Server-Sent Events (SSE).
    
    Event format:
    - data: {"type": "token", "content": "..."}
    - data: {"type": "sources", "sources": [...]}
    - data: {"type": "done"}
    """
    full_response = ""
    
    try:
        chain = prompt | llm
        
        async for chunk in chain.astream({"context": context, "question": question, "language": language}):
            if hasattr(chunk, 'content') and chunk.content:
                full_response += chunk.content
                yield f"data: {json.dumps({'type': 'token', 'content': chunk.content})}\n\n"
        
        # Send sources after completion
        yield f"data: {json.dumps({'type': 'sources', 'sources': sources})}\n\n"
        
        # Save messages
        message_id = save_messages(
            supabase, conversation_id, question, full_response,
            [s.get("label", "") for s in sources]
        )
        
        yield f"data: {json.dumps({'type': 'done', 'message_id': message_id})}\n\n"
        
    except Exception as e:
        logger.error(f"Streaming error: {e}")
        sentry_sdk.capture_exception(e)
        yield f"data: {json.dumps({'type': 'error', 'message': str(e)})}\n\n"


def save_messages(supabase, conversation_id: str, query: str, answer: str, sources: List[str]) -> Optional[str]:
    """Save user and assistant messages to database."""
    if not conversation_id:
        return None
    
    try:
        now = datetime.utcnow().isoformat()
        
        # Save user message
        supabase.table("messages").insert({
            "conversation_id": conversation_id,
            "role": "user",
            "content": query,
            "sources": [],
            "created_at": now
        }).execute()
        
        # Save assistant message
        assistant_msg = supabase.table("messages").insert({
            "conversation_id": conversation_id,
            "role": "assistant",
            "content": answer,
            "sources": sources,
            "created_at": now
        }).execute()
        
        message_id = None
        if assistant_msg.data:
            message_id = assistant_msg.data[0]['id']
        
        # Update conversation timestamp
        supabase.table("conversations").update({
            "updated_at": now
        }).eq("id", conversation_id).execute()
        
        return message_id
        
    except Exception as e:
        logger.warning(f"WARNING: Failed to save messages: {e}")
        sentry_sdk.capture_exception(e)
        return None

