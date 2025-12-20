"""
SSE (Server-Sent Events) Streaming Chat Endpoint

Provides real-time streaming responses for the chat interface.
"""

import json
import logging
from typing import AsyncGenerator, Optional
from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import StreamingResponse
from pydantic import BaseModel
from langchain_openai import OpenAIEmbeddings, ChatOpenAI
from langchain.callbacks.base import BaseCallbackHandler
from langchain.schema import LLMResult
import asyncio

from core.security import get_current_user
from core.db import get_supabase
from core.config import settings

logger = logging.getLogger(__name__)
router = APIRouter()


class StreamingChatRequest(BaseModel):
    """Request model for streaming chat."""
    query: str
    conversation_id: Optional[str] = None


class StreamingCallbackHandler(BaseCallbackHandler):
    """
    Callback handler that captures streaming tokens.
    
    Tokens are pushed to an async queue that can be consumed
    by a generator for SSE streaming.
    """
    
    def __init__(self):
        self.queue: asyncio.Queue = asyncio.Queue()
        self.done = False
    
    def on_llm_new_token(self, token: str, **kwargs) -> None:
        """Called when a new token is generated."""
        self.queue.put_nowait(token)
    
    def on_llm_end(self, response: LLMResult, **kwargs) -> None:
        """Called when LLM completes."""
        self.done = True
        self.queue.put_nowait(None)  # Signal completion
    
    def on_llm_error(self, error: Exception, **kwargs) -> None:
        """Called when LLM errors."""
        self.done = True
        self.queue.put_nowait(None)


async def stream_generator(
    query: str,
    user_id: str,
    conversation_id: Optional[str] = None
) -> AsyncGenerator[str, None]:
    """
    Generator that yields SSE-formatted events for streaming chat.
    
    Event types:
    - sources: Retrieved document sources
    - token: Partial response token
    - done: Stream complete
    - error: Error occurred
    """
    supabase = get_supabase()
    
    try:
        # 1. Embed the query
        embeddings_model = OpenAIEmbeddings(
            model="text-embedding-3-small",
            api_key=settings.OPENAI_API_KEY
        )
        query_vector = embeddings_model.embed_query(query)
        
        # 2. Retrieve context
        try:
            response = supabase.rpc("hybrid_search", {
                "query_text": query,
                "query_embedding": query_vector,
                "match_count": 5,
                "filter_user_id": user_id,
                "vector_weight": 0.7,
                "keyword_weight": 0.3,
                "similarity_threshold": 0.3
            }).execute()
            docs = response.data or []
        except Exception:
            # Fallback to vector-only search
            response = supabase.rpc("match_documents", {
                "query_embedding": query_vector,
                "match_threshold": 0.3,
                "match_count": 5,
                "filter_user_id": user_id
            }).execute()
            docs = response.data or []
        
        # 3. Send sources as first event
        sources = []
        context_text = ""
        for doc in docs:
            context_text += doc.get("content", "") + "\n\n"
            source_type = doc.get("source_type", "unknown")
            metadata = doc.get("metadata", {})
            
            source_label = metadata.get("title") or metadata.get("url") or doc.get("title", "Document")
            sources.append({
                "title": source_label,
                "type": source_type,
                "url": metadata.get("source_url", metadata.get("url"))
            })
        
        # Yield sources event
        yield f"event: sources\ndata: {json.dumps(sources)}\n\n"
        
        if not docs:
            yield f"event: token\ndata: {json.dumps({'token': 'I don\\'t have enough information to answer that question based on your documents.'})}\n\n"
            yield "event: done\ndata: {}\n\n"
            return
        
        # 4. Set up streaming LLM
        callback = StreamingCallbackHandler()
        llm = ChatOpenAI(
            model="gpt-4o-mini",
            api_key=settings.OPENAI_API_KEY,
            streaming=True,
            callbacks=[callback]
        )
        
        # 5. Create prompt
        system_prompt = f"""You are a helpful AI assistant that answers questions based on the provided context.
Use the following context to answer the user's question. If the answer is not in the context, say so.
Always cite which document(s) you used in your answer.

Context:
{context_text}
"""
        
        # 6. Start streaming in background task
        async def run_llm():
            try:
                await llm.ainvoke([
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": query}
                ])
            except Exception as e:
                logger.error(f"LLM error: {e}")
                callback.queue.put_nowait(None)
        
        # Start LLM generation
        asyncio.create_task(run_llm())
        
        # 7. Stream tokens as they arrive
        while True:
            try:
                token = await asyncio.wait_for(callback.queue.get(), timeout=60.0)
                if token is None:
                    break
                yield f"event: token\ndata: {json.dumps({'token': token})}\n\n"
            except asyncio.TimeoutError:
                logger.warning("SSE stream timeout")
                break
        
        # 8. Send done event
        yield "event: done\ndata: {}\n\n"
        
    except Exception as e:
        logger.error(f"Stream error: {e}")
        yield f"event: error\ndata: {json.dumps({'error': str(e)})}\n\n"


@router.post("/chat/stream")
async def stream_chat(
    payload: StreamingChatRequest,
    user_id: str = Depends(get_current_user)
):
    """
    Stream chat responses using Server-Sent Events (SSE).
    
    Event stream format:
    - event: sources - Retrieved document sources
    - event: token - Partial response token
    - event: done - Stream complete
    - event: error - Error occurred
    """
    return StreamingResponse(
        stream_generator(
            query=payload.query,
            user_id=user_id,
            conversation_id=payload.conversation_id
        ),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no"  # Disable nginx buffering
        }
    )
