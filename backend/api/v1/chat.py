from fastapi import APIRouter, Depends, HTTPException, status, Request
from fastapi.responses import StreamingResponse
from pydantic import BaseModel, Field
from typing import List, Dict, Any, Optional, AsyncGenerator
from core.security import get_current_user
from core.db import get_supabase
from core.config import settings
from langchain_openai import OpenAIEmbeddings, ChatOpenAI
from langchain_core.prompts import ChatPromptTemplate
from langchain_core.output_parsers import StrOutputParser
from slowapi import Limiter
from slowapi.util import get_remote_address
from datetime import datetime
import logging
import json

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
    user_id: str = Depends(get_current_user)
):
    """Delete a conversation and all its messages."""
    supabase = get_supabase()
    
    try:
        # Messages will be deleted automatically due to ON DELETE CASCADE
        response = supabase.table("conversations").delete().eq("id", conversation_id).eq("user_id", user_id).execute()
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

Remember: Cite your sources using [1], [2], etc. and be conversational."""


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
@limiter.limit("50/minute")
async def chat_endpoint(
    request: Request,
    payload: ChatRequest,
    user_id: str = Depends(get_current_user)
):
    """
    Conversational RAG Chat Endpoint.
    
    Features:
    1. Condense Question - Rewrites follow-ups as standalone queries
    2. Hybrid Search - Vector + keyword retrieval
    3. Citation-aware System Prompt
    4. Streaming Support (optional)
    """
    supabase = get_supabase()
    
    # ========== STEP 1: Condense Question (if history exists) ==========
    search_query = condense_question(payload.query, payload.history or [])
    
    # ========== STEP 2: Embed the (potentially condensed) query ==========
    embeddings_model = OpenAIEmbeddings(
        model="text-embedding-3-small", 
        api_key=settings.OPENAI_API_KEY
    )
    
    try:
        query_vector = embeddings_model.embed_query(search_query)
    except Exception as e:
        logger.error(f"ERROR: Embedding failed: {e}")
        raise HTTPException(500, f"Embedding failed: {e}")

    # ========== STEP 3: Hybrid Search (Vector + Keyword) ==========
    try:
        # Hybrid search with weighted scoring
        response = supabase.rpc("hybrid_search", {
            "query_text": search_query,
            "query_embedding": query_vector,
            "match_count": 7,  # Increased for better coverage
            "filter_user_id": user_id,
            "vector_weight": 0.7,
            "keyword_weight": 0.3,
            "similarity_threshold": 0.25  # Slightly lower for more recall
        }).execute()
        
        docs = response.data
        logger.info(f"📚 [Chat] Hybrid search: {len(docs) if docs else 0} results")
    except Exception as e:
        # Fallback to vector-only search
        logger.warning(f"⚠️ [Chat] Hybrid search failed, using vector: {e}")
        try:
            response = supabase.rpc("match_documents", {
                "query_embedding": query_vector,
                "match_threshold": 0.25, 
                "match_count": 7,
                "filter_user_id": user_id
            }).execute()
            docs = response.data
        except Exception as fallback_e:
            logger.error(f"ERROR: Retrieval failed: {fallback_e}")
            raise HTTPException(500, f"Retrieval failed: {fallback_e}")

    # ========== STEP 4: Format Context with Citations ==========
    if not docs:
        no_docs_response = ChatResponse(
            answer="I couldn't find relevant information in your knowledge base to answer that question. Try uploading more documents or rephrasing your question.",
            sources=[],
            conversation_id=payload.conversation_id
        )
        return no_docs_response

    context_text, sources_metadata = format_context_with_citations(docs)

    # ========== STEP 5: Generate Answer ==========
    prompt = ChatPromptTemplate.from_messages([
        ("system", SYSTEM_PROMPT),
        ("user", "{question}")
    ])
    
    llm = ChatOpenAI(
        model=payload.model,
        temperature=0.1,  # Slight creativity for natural responses
        api_key=settings.OPENAI_API_KEY,
        streaming=payload.stream
    )
    
    if payload.stream:
        # ========== STREAMING RESPONSE ==========
        return StreamingResponse(
            stream_chat_response(
                prompt, llm, context_text, payload.query, 
                sources_metadata, payload.conversation_id, user_id, supabase
            ),
            media_type="text/event-stream"
        )
    else:
        # ========== STANDARD RESPONSE ==========
        chain = prompt | llm | StrOutputParser()
        
        try:
            answer = chain.invoke({"context": context_text, "question": payload.query})
        except Exception as e:
            logger.error(f"ERROR: LLM Generation failed: {e}")
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
    sources: List[Dict], conversation_id: str, user_id: str, supabase
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
        
        async for chunk in chain.astream({"context": context, "question": question}):
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
        return None

