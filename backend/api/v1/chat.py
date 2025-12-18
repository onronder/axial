from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel
from typing import List, Dict, Any, Optional
from core.security import get_current_user
from core.db import get_supabase
from core.config import settings
from langchain_openai import OpenAIEmbeddings, ChatOpenAI
from langchain_core.prompts import ChatPromptTemplate
from langchain_core.output_parsers import StrOutputParser

router = APIRouter()

class ChatRequest(BaseModel):
    query: str
    history: Optional[List[Dict[str, str]]] = []
    model: str = "gpt-4o"

class ChatResponse(BaseModel):
    answer: str
    sources: List[str]

@router.post("/chat", response_model=ChatResponse)
async def chat_endpoint(
    payload: ChatRequest,
    user_id: str = Depends(get_current_user)
):
    supabase = get_supabase()
    
    # 1. Embed Query
    # CRITICAL FIX: Must explicitly use 'text-embedding-3-small' to match ingestion.
    embeddings_model = OpenAIEmbeddings(
        model="text-embedding-3-small", 
        api_key=settings.OPENAI_API_KEY
    )
    
    try:
        query_vector = embeddings_model.embed_query(payload.query)
    except Exception as e:
        print(f"ERROR: Embedding failed: {e}")
        raise HTTPException(500, f"Embedding failed: {e}")

    # 2. Retrieve Context
    try:
        # Lower threshold slightly for chat to be more forgiving
        response = supabase.rpc("match_documents", {
            "query_embedding": query_vector,
            "match_threshold": 0.3, 
            "match_count": 5,
            "filter_user_id": user_id
        }).execute()
        
        docs = response.data
    except Exception as e:
        print(f"ERROR: Retrieval failed: {e}")
        raise HTTPException(500, f"Retrieval failed: {e}")

    if not docs:
        return ChatResponse(answer="I don't have enough information in the provided documents to answer that.", sources=[])

    # 3. Construct Context
    # 3. Construct Context
    context_text = ""
    sources = []
    
    for d in docs:
        context_text += d['content'] + "\n\n"
        
        # EXTRACT SOURCE LOGIC
        metadata = d.get('metadata', {})
        source_type = d.get('source_type', metadata.get("source", "unknown"))
        
        if source_type == "web":
            # For web, the valid source is the URL
            source_label = metadata.get("url", "Unknown URL")
        elif source_type == "file":
             # For files, it's usually the filename
            source_label = metadata.get("filename", metadata.get("file_name", "Unknown File"))
        elif source_type == "drive":
            # For drive, use the title
            source_label = metadata.get("title", "Google Drive Doc")
        else:
            # Fallback - try generic fields
            source_label = metadata.get("filename", metadata.get("url", "Unknown Source"))
        
        if source_label not in sources:
            sources.append(source_label)

    # 4. Generate Answer
    system_prompt = """You are Axial, an expert AI assistant. 
    Answer the user's question based ONLY on the following context.
    If the answer is not in the context, say so.
    
    Context:
    {context}
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

    return ChatResponse(answer=answer, sources=sources)
