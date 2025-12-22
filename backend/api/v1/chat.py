from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel
from typing import List, Dict, Any, Optional
from core.security import get_current_user
from core.db import get_supabase
from core.config import settings
from langchain_openai import OpenAIEmbeddings, ChatOpenAI
from langchain_core.prompts import ChatPromptTemplate
from langchain_core.output_parsers import StrOutputParser
from datetime import datetime

router = APIRouter()

# ============================================================
# CONVERSATION MANAGEMENT ENDPOINTS
# ============================================================

class ConversationCreate(BaseModel):
    title: str = "New Chat"

class ConversationUpdate(BaseModel):
    title: str

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
# CHAT ENDPOINT (with message persistence)
# ============================================================

class ChatRequest(BaseModel):
    query: str
    conversation_id: Optional[str] = None  # If provided, saves to conversation
    history: Optional[List[Dict[str, str]]] = []
    model: str = "gpt-4o"

class ChatResponse(BaseModel):
    answer: str
    sources: List[str]
    conversation_id: Optional[str] = None
    message_id: Optional[str] = None

@router.post("/chat", response_model=ChatResponse)
async def chat_endpoint(
    payload: ChatRequest,
    user_id: str = Depends(get_current_user)
):
    supabase = get_supabase()
    
    # 1. Embed Query
    embeddings_model = OpenAIEmbeddings(
        model="text-embedding-3-small", 
        api_key=settings.OPENAI_API_KEY
    )
    
    try:
        query_vector = embeddings_model.embed_query(payload.query)
    except Exception as e:
        print(f"ERROR: Embedding failed: {e}")
        raise HTTPException(500, f"Embedding failed: {e}")

    # 2. Retrieve Context using Hybrid Search (Vector + Keyword)
    try:
        # Try hybrid search first (requires migration 002_hybrid_search.sql)
        response = supabase.rpc("hybrid_search", {
            "query_text": payload.query,
            "query_embedding": query_vector,
            "match_count": 5,
            "filter_user_id": user_id,
            "vector_weight": 0.7,
            "keyword_weight": 0.3,
            "similarity_threshold": 0.3
        }).execute()
        
        docs = response.data
        print(f"📚 [Chat] Hybrid search returned {len(docs) if docs else 0} results")
    except Exception as e:
        # Fallback to vector-only search if hybrid_search not available
        print(f"⚠️ [Chat] Hybrid search failed, falling back to vector search: {e}")
        try:
            response = supabase.rpc("match_documents", {
                "query_embedding": query_vector,
                "match_threshold": 0.3, 
                "match_count": 5,
                "filter_user_id": user_id
            }).execute()
            docs = response.data
        except Exception as fallback_e:
            print(f"ERROR: Retrieval failed: {fallback_e}")
            raise HTTPException(500, f"Retrieval failed: {fallback_e}")

    if not docs:
        return ChatResponse(
            answer="I don't have enough information in the provided documents to answer that.",
            sources=[],
            conversation_id=payload.conversation_id
        )

    # 3. Construct Context
    context_text = ""
    sources = []
    
    for d in docs:
        context_text += d['content'] + "\n\n"
        
        metadata = d.get('metadata', {})
        source_type = d.get('source_type', metadata.get("source", "unknown"))
        
        if source_type == "web":
            source_label = metadata.get("url", "Unknown URL")
        elif source_type == "file":
            source_label = metadata.get("filename", metadata.get("file_name", "Unknown File"))
        elif source_type == "drive":
            source_label = metadata.get("title", "Google Drive Doc")
        else:
            source_label = metadata.get("filename", metadata.get("url", "Unknown Source"))
        
        if source_label not in sources:
            sources.append(source_label)

    # 4. Generate Answer
    system_prompt = """You are Axio, an intelligent AI assistant with access to the user's knowledge base.

You MUST use the provided context below to answer the user's question accurately.
If the context contains relevant information, synthesize it into a clear, helpful answer.
If the context doesn't contain enough information to answer the question, say:
"I couldn't find specific information about that in your documents. Would you like me to help with something else?"

Be conversational, helpful, and cite which documents you're drawing from when possible.

---
CONTEXT FROM USER'S KNOWLEDGE BASE:
{context}
---
"""
    
    prompt = ChatPromptTemplate.from_messages([
        ("system", system_prompt),
        ("user", "{question}")
    ])
    
    llm = ChatOpenAI(model=payload.model, temperature=0, api_key=settings.OPENAI_API_KEY)
    chain = prompt | llm | StrOutputParser()
    
    try:
        answer = chain.invoke({"context": context_text, "question": payload.query})
    except Exception as e:
        print(f"ERROR: LLM Generation failed: {e}")
        raise HTTPException(500, f"LLM Generation failed: {e}")

    # 5. Save messages if conversation_id is provided
    message_id = None
    if payload.conversation_id:
        try:
            now = datetime.utcnow().isoformat()
            
            # Save user message
            supabase.table("messages").insert({
                "conversation_id": payload.conversation_id,
                "role": "user",
                "content": payload.query,
                "sources": [],
                "created_at": now
            }).execute()
            
            # Save assistant message
            assistant_msg = supabase.table("messages").insert({
                "conversation_id": payload.conversation_id,
                "role": "assistant",
                "content": answer,
                "sources": sources,
                "created_at": now
            }).execute()
            
            if assistant_msg.data:
                message_id = assistant_msg.data[0]['id']
            
            # Update conversation updated_at
            supabase.table("conversations").update({
                "updated_at": now
            }).eq("id", payload.conversation_id).execute()
            
        except Exception as e:
            print(f"WARNING: Failed to save messages: {e}")
            # Continue anyway - chat worked, just didn't persist

    return ChatResponse(
        answer=answer,
        sources=sources,
        conversation_id=payload.conversation_id,
        message_id=message_id
    )
