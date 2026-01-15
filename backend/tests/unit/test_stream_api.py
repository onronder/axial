import asyncio
from types import SimpleNamespace
from unittest.mock import MagicMock, Mock, patch, AsyncMock

import pytest

from api.v1.stream import (
    StreamingCallbackHandler,
    StreamingChatRequest,
    stream_chat,
    stream_generator,
)


@pytest.fixture(autouse=True)
def mock_org_id():
    with patch(
        "api.v1.stream.team_service.get_organization_id",
        new_callable=AsyncMock,
        return_value="org-1",
    ):
        yield


@pytest.mark.asyncio
async def test_stream_generator_no_docs():
    supabase = MagicMock()
    supabase.rpc.return_value.execute.return_value = Mock(data=[])

    embeddings = MagicMock()
    embeddings.embed_query.return_value = [0.1]

    with patch("api.v1.stream.get_supabase", return_value=supabase), \
         patch("api.v1.stream.OpenAIEmbeddings", return_value=embeddings):
        events = [chunk async for chunk in stream_generator("q", "user-1")]

    assert any("event: sources" in event for event in events)
    assert any("event: token" in event for event in events)
    assert any("event: done" in event for event in events)


@pytest.mark.asyncio
async def test_stream_generator_streams_tokens():
    supabase = MagicMock()

    def rpc_side_effect(name, params):
        if name == "hybrid_search":
            return Mock(execute=Mock(return_value=Mock(data=[{
                "content": "Doc",
                "source_type": "file_upload",
                "metadata": {"title": "Doc"},
            }])))
        raise AssertionError(name)

    supabase.rpc.side_effect = rpc_side_effect

    embeddings = MagicMock()
    embeddings.embed_query.return_value = [0.1]

    class FakeLLM:
        def __init__(self, *args, **kwargs):
            self.callbacks = kwargs.get("callbacks", [])

        async def ainvoke(self, _):
            for cb in self.callbacks:
                cb.on_llm_new_token("Hi")
                cb.on_llm_end(None)

    with patch("api.v1.stream.get_supabase", return_value=supabase), \
         patch("api.v1.stream.OpenAIEmbeddings", return_value=embeddings), \
         patch("api.v1.stream.ChatOpenAI", FakeLLM):
        events = [chunk async for chunk in stream_generator("q", "user-1")]

    assert any("event: token" in event for event in events)
    assert any("event: done" in event for event in events)


@pytest.mark.asyncio
async def test_stream_generator_handles_error():
    embeddings = MagicMock()
    embeddings.embed_query.side_effect = Exception("boom")

    with patch("api.v1.stream.OpenAIEmbeddings", return_value=embeddings), \
         patch("api.v1.stream.get_supabase", return_value=MagicMock()):
        events = [chunk async for chunk in stream_generator("q", "user-1")]

    assert any("event: error" in event for event in events)


def test_streaming_callback_handler_marks_done_on_error():
    handler = StreamingCallbackHandler()

    handler.on_llm_error(RuntimeError("boom"))

    assert handler.done is True
    assert handler.queue.get_nowait() is None


@pytest.mark.asyncio
async def test_stream_generator_fallbacks_to_match_documents():
    supabase = MagicMock()

    def rpc_side_effect(name, _params):
        if name == "hybrid_search":
            raise RuntimeError("rpc error")
        if name == "match_documents":
            return Mock(execute=Mock(return_value=Mock(data=[{
                "content": "Doc",
                "source_type": "file_upload",
                "metadata": {"title": "Doc"},
            }])))
        raise AssertionError(name)

    supabase.rpc.side_effect = rpc_side_effect

    embeddings = MagicMock()
    embeddings.embed_query.return_value = [0.1]

    class FakeLLM:
        def __init__(self, *args, **kwargs):
            self.callbacks = kwargs.get("callbacks", [])

        async def ainvoke(self, _):
            for cb in self.callbacks:
                cb.on_llm_end(None)

    with patch("api.v1.stream.get_supabase", return_value=supabase), \
         patch("api.v1.stream.OpenAIEmbeddings", return_value=embeddings), \
         patch("api.v1.stream.ChatOpenAI", FakeLLM):
        events = [chunk async for chunk in stream_generator("q", "user-1")]

    assert any("event: sources" in event for event in events)
    assert any("event: done" in event for event in events)


@pytest.mark.asyncio
async def test_stream_generator_handles_llm_error():
    supabase = MagicMock()
    supabase.rpc.return_value.execute.return_value = Mock(data=[{
        "content": "Doc",
        "source_type": "file_upload",
        "metadata": {"title": "Doc"},
    }])

    embeddings = MagicMock()
    embeddings.embed_query.return_value = [0.1]

    class FailingLLM:
        def __init__(self, *args, **kwargs):
            pass

        async def ainvoke(self, _):
            raise RuntimeError("llm failed")

    with patch("api.v1.stream.get_supabase", return_value=supabase), \
         patch("api.v1.stream.OpenAIEmbeddings", return_value=embeddings), \
         patch("api.v1.stream.ChatOpenAI", FailingLLM):
        events = [chunk async for chunk in stream_generator("q", "user-1")]

    assert any("event: done" in event for event in events)


@pytest.mark.asyncio
async def test_stream_generator_times_out_on_wait():
    supabase = MagicMock()
    supabase.rpc.return_value.execute.return_value = Mock(data=[{
        "content": "Doc",
        "source_type": "file_upload",
        "metadata": {"title": "Doc"},
    }])

    embeddings = MagicMock()
    embeddings.embed_query.return_value = [0.1]

    class SilentLLM:
        def __init__(self, *args, **kwargs):
            pass

        async def ainvoke(self, _):
            return None

    async def fake_wait_for(awaitable, timeout):
        awaitable.close()
        raise asyncio.TimeoutError()

    with patch("api.v1.stream.get_supabase", return_value=supabase), \
         patch("api.v1.stream.OpenAIEmbeddings", return_value=embeddings), \
         patch("api.v1.stream.ChatOpenAI", SilentLLM), \
         patch("api.v1.stream.asyncio.wait_for", side_effect=fake_wait_for):
        events = [chunk async for chunk in stream_generator("q", "user-1")]

    assert any("event: done" in event for event in events)


@pytest.mark.asyncio
async def test_stream_chat_returns_streaming_response():
    payload = StreamingChatRequest(query="hello")
    response = await stream_chat(payload, user_id="user-1")

    assert response.media_type == "text/event-stream"
