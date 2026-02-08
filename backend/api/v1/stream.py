"""
Streaming Chat Endpoint

Delegates to the primary /chat pipeline to enforce identical guardrails,
quota enforcement, and failover behavior.
"""

from fastapi import APIRouter, BackgroundTasks, Depends, Request

from api.v1.chat import ChatRequest, chat_endpoint
from api.v1.dependencies import validate_team_access, require_paid_access
from core.security import get_current_user
from core.rate_limit import limiter

router = APIRouter(dependencies=[Depends(validate_team_access), Depends(require_paid_access)])

@router.post("/chat/stream")
@limiter.limit("30/minute")
async def stream_chat(
    request: Request,
    payload: ChatRequest,
    background_tasks: BackgroundTasks,
    user_id: str = Depends(get_current_user),
):
    """
    Stream chat responses using the same pipeline as /chat.

    This ensures dominance guard, org-scoped retrieval, quotas,
    and provider failover are consistently enforced.
    """
    payload_data = payload.model_dump()
    payload_data["stream"] = True
    chat_payload = ChatRequest(**payload_data)
    return await chat_endpoint(request, chat_payload, background_tasks, user_id)
