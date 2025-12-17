from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel
from typing import List, Dict, Any, Optional
from core.security import get_api_key
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
    api_key: str = Depends(get_api_key)
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
            "match_count": 5
        }).execute()
        
        docs = response.data
    except Exception as e:
        print(f"ERROR: Retrieval failed: {e}")
        raise HTTPException(500, f"Retrieval failed: {e}")

    if not docs:
        return ChatResponse(answer="I don't have enough information in the provided documents to answer that.", sources=[])

    # 3. Construct Context
    context_text = "\n\n".join([d['content'] for d in docs])
    sources = list(set([d['metadata'].get('filename', 'unknown') for d in docs]))

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
