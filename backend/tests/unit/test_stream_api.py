from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from fastapi import BackgroundTasks, Request
from starlette.responses import StreamingResponse

from api.v1.chat import ChatRequest
from api.v1.stream import stream_chat


@pytest.mark.asyncio
async def test_stream_chat_delegates_to_chat_endpoint():
    request = MagicMock(spec=Request)
    background_tasks = BackgroundTasks()
    payload = ChatRequest(
        query="hello",
        conversation_id="conv-1",
        history=[{"role": "user", "content": "hi"}],
        model="fast",
        scope_id="scope://test",
        stream=False,
    )
    response = StreamingResponse(iter([b"data: {}"]), media_type="text/event-stream")

    with patch("api.v1.stream.chat_endpoint", new_callable=AsyncMock, return_value=response) as mock_chat:
        result = await stream_chat(payload, request, background_tasks, user_id="user-1")

    assert result is response
    args, _kwargs = mock_chat.call_args
    chat_payload = args[1]
    assert chat_payload.query == "hello"
    assert chat_payload.conversation_id == "conv-1"
    assert chat_payload.history == [{"role": "user", "content": "hi"}]
    assert chat_payload.model == "fast"
    assert chat_payload.scope_id == "scope://test"
    assert chat_payload.stream is True
