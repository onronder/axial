"""
Test Suite for Chat API

Tests for:
- GET /api/v1/chats - List user chats
- POST /api/v1/chats - Create new chat
- GET /api/v1/chats/{id}/messages - Get messages
- POST /api/v1/chats/{id}/messages - Add message
- DELETE /api/v1/chats/{id} - Delete chat
- POST /api/v1/chat - RAG chat endpoint
"""

import asyncio
from types import SimpleNamespace
from unittest.mock import AsyncMock, MagicMock, Mock, patch

import pytest
from fastapi import HTTPException
from starlette.requests import Request

import api.v1.chat  # Ensure module is loaded for patching
from services.guardrails import GuardrailResult


def _make_mock_request(method="GET", path="/api/v1/chat"):
    """Helper to create mock requests for chat endpoints."""
    scope = {
        "type": "http",
        "method": method,
        "path": path,
        "query_string": b"",
        "headers": [],
        "server": ("testserver", 80),
        "client": ("127.0.0.1", 12345),
        "app": None,
    }
    return Request(scope=scope)


def make_guardrail_result(
    is_safe=True,
    intent="RAG_QUERY",
    complexity="SIMPLE",
    language="en",
    reply=None,
    has_document_context=False,
) -> GuardrailResult:
    """Helper to create a GuardrailResult for tests."""
    return GuardrailResult(
        is_safe=is_safe,
        intent=intent,
        complexity=complexity,
        language=language,
        reply=reply,
        has_document_context=has_document_context,
    )


@pytest.fixture(autouse=True)
def mock_org_id():
    with patch(
        "api.v1.chat.team_service.get_organization_id",
        new_callable=AsyncMock,
        return_value="org-1",
    ):
        yield


@pytest.fixture(autouse=True)
def mock_effective_plan():
    with patch(
        "api.v1.chat.team_service.get_effective_plan",
        new_callable=AsyncMock,
        return_value="pro",
    ):
        yield


@pytest.fixture(autouse=True)
def mock_llm_quota():
    with patch(
        "api.v1.chat.check_llm_quota",
        new_callable=AsyncMock,
        return_value={"balance": 1000},
    ), patch(
        "api.v1.chat.record_llm_usage",
        new_callable=AsyncMock,
        return_value=None,
    ):
        yield


class TestChatList:
    """Tests for GET /api/v1/chats."""

    @pytest.mark.unit
    def test_list_chats_returns_user_chats_only(self):
        """Chat list must filter by organization_id (RLS equivalent)."""
        mock_supabase = MagicMock()
        table = MagicMock()
        table.select.return_value = table
        table.eq.return_value = table
        table.order.return_value = table
        table.range.return_value = table
        table.execute.return_value = MagicMock(data=[{"id": "chat-1", "organization_id": "org-1"}])
        mock_supabase.table.return_value = table

        with patch("api.v1.chat.get_supabase", return_value=mock_supabase):
            from api.v1.chat import list_conversations

            result = asyncio.run(list_conversations(
                request=_make_mock_request(),
                user_id="user-1",
                organization_id="org-1",
                limit=200,
                offset=0,
            ))

        assert result[0]["id"] == "chat-1"
        table.eq.assert_any_call("organization_id", "org-1")

    @pytest.mark.unit
    def test_list_chats_ordered_by_updated_at_desc(self):
        """Most recently updated chats should appear first."""
        mock_supabase = MagicMock()
        table = MagicMock()
        table.select.return_value = table
        table.eq.return_value = table
        table.order.return_value = table
        table.range.return_value = table
        table.execute.return_value = MagicMock(data=[])
        mock_supabase.table.return_value = table

        with patch("api.v1.chat.get_supabase", return_value=mock_supabase):
            from api.v1.chat import list_conversations

            asyncio.run(list_conversations(
                request=_make_mock_request(),
                user_id="user-1",
                organization_id="org-1",
                limit=200,
                offset=0,
            ))

        table.order.assert_called_with("updated_at", desc=True)

    @pytest.mark.unit
    def test_list_chats_empty_for_new_user(self):
        """New user should get empty array, not error."""
        mock_supabase = MagicMock()
        table = MagicMock()
        table.select.return_value = table
        table.eq.return_value = table
        table.order.return_value = table
        table.range.return_value = table
        table.execute.return_value = MagicMock(data=[])
        mock_supabase.table.return_value = table

        with patch("api.v1.chat.get_supabase", return_value=mock_supabase):
            from api.v1.chat import list_conversations

            result = asyncio.run(list_conversations(
                request=_make_mock_request(),
                user_id="user-1",
                organization_id="org-1",
                limit=200,
                offset=0,
            ))

        assert result == []


@pytest.mark.asyncio
class TestChatCreate:
    """Tests for POST /api/v1/conversations."""

    async def test_create_chat_returns_new_chat(self):
        """Creating a chat should return the new chat object."""
        # Arrange
        mock_supabase = MagicMock()
        mock_response = MagicMock()
        mock_response.data = [{"id": "new-chat-id", "title": "New Chat"}]
        mock_supabase.table.return_value.insert.return_value.execute.return_value = mock_response

        with patch("api.v1.chat.get_supabase", return_value=mock_supabase):
            from api.v1.chat import ConversationCreate, create_conversation

            # Act
            payload = ConversationCreate(title="Test Chat")
            result = await create_conversation(
                request=_make_mock_request(method="POST"),
                payload=payload,
                user_id="test-user",
                organization_id="org-1"
            )

            # Assert
            assert result["id"] == "new-chat-id"
            mock_supabase.table.assert_called_with("conversations")
            mock_supabase.table().insert.assert_called()


@pytest.mark.asyncio
class TestRAGChatEndpoint:
    """Tests for POST /api/v1/chat - the RAG endpoint."""

    async def test_chat_uses_condensed_question(self):
        """Verify LLM is invoked with condensed question, not original query."""
        from fastapi import Request

        # Arrange
        mock_request = MagicMock(spec=Request)
        mock_request.client.host = "127.0.0.1"

        mock_bg_tasks = MagicMock()
        mock_supabase = MagicMock()

        # Mock user profile plan
        mock_supabase.table().select().eq().single().execute.return_value.data = {"plan": "starter"}

        guardrail = make_guardrail_result(is_safe=True, intent="RAG_QUERY", complexity="SIMPLE")

        with patch("api.v1.chat.get_supabase", return_value=mock_supabase), \
             patch("api.v1.chat.guardrail_service.analyze_query_with_context", return_value=guardrail), \
             patch("api.v1.chat.llm_router.select_model") as mock_router, \
             patch("api.v1.chat.condense_question", new_callable=AsyncMock, return_value="Condensed Question?") as mock_condense, \
             patch("services.embeddings.get_embeddings_model") as mock_embed, \
             patch("api.v1.chat.LLMFactory") as mock_llm_factory, \
             patch("api.v1.chat.save_messages") as mock_save_messages:

            # Mock Save Messages
            mock_save_messages.return_value = "msg-123"

            # Mock Router
            mock_router.return_value.provider = "openai"
            mock_router.return_value.model = "gpt-4o"

            # Mock LLM Chain
            mock_chain = MagicMock()
            mock_chain.invoke.return_value = "Test Answer"

            # Properly mock the chain construction: prompt | llm | parser
            # We can mock the final invoke call
            with patch("api.v1.chat.StrOutputParser"), \
                 patch("api.v1.chat.ChatPromptTemplate") as mock_prompt_cls:

                # Make the chain object returned by the pipe operators
                mock_prompt = MagicMock()
                mock_llm = MagicMock()
                mock_parser = MagicMock()

                mock_prompt_cls.from_messages.return_value = mock_prompt

                # Mock the pipe operation: prompt | llm | parser -> chain
                mock_prompt.__or__.return_value = mock_llm
                mock_llm.__or__.return_value = mock_chain

                from api.v1.chat import ChatRequest, chat_endpoint

                # Act
                payload = ChatRequest(query="Original Query", history=[{"role": "user", "content": "prev"}], model="auto")
                await chat_endpoint(mock_request, payload, mock_bg_tasks, user_id="test-user")

                # Assert
                # Verify condense was called
                mock_condense.assert_called_with("Original Query", payload.history)

                # Verify chain invoked with CONDENSED question
                call_args = mock_chain.invoke.call_args
                assert call_args is not None
                args, kwargs = call_args
                # chain.invoke({...}) is a positional arg
                assert args[0]['question'] == "Condensed Question?"


    async def test_chat_captures_sentry_exception(self):
        """Mock sentry_sdk and trigger an error to verify capture."""
        from fastapi import Request

        # Arrange
        mock_request = MagicMock(spec=Request)
        mock_request.client.host = "127.0.0.1"

        mock_bg_tasks = MagicMock()
        mock_supabase = MagicMock()
        mock_supabase.table().select().eq().single().execute.return_value.data = {"plan": "starter"}

        guardrail = make_guardrail_result(is_safe=True, intent="RAG_QUERY")

        with patch("api.v1.chat.get_supabase", return_value=mock_supabase), \
             patch("api.v1.chat.guardrail_service.analyze_query_with_context", return_value=guardrail), \
             patch("api.v1.chat.condense_question", new_callable=AsyncMock, return_value="Q"), \
             patch("services.embeddings.get_embeddings_model"), \
             patch("api.v1.chat.LLMFactory"), \
             patch("api.v1.chat.sentry_sdk") as mock_sentry:

            # Force an error during routing or generation
            with patch("api.v1.chat.llm_router.select_model", side_effect=Exception("Test Error")):

                from api.v1.chat import ChatRequest, chat_endpoint

                # Act & Assert
                with pytest.raises(Exception): # or HTTP 500
                   payload = ChatRequest(query="Test", history=[], model="auto")
                   await chat_endpoint(mock_request, payload, mock_bg_tasks, user_id="test-user")

                # Ideally check if error was logged/captured, but note that
                # generic Exceptions in earlier steps might just raise HTTP 500 without capturing
                # (Rate limiting capture was added to generation block).
                # Let's target the Generation block failure for our Sentry test.

    async def test_generation_exception_captures_sentry(self):
         # Arrange
        from fastapi import Request
        mock_request = MagicMock(spec=Request)
        mock_request.client.host = "127.0.0.1"

        mock_bg_tasks = MagicMock()
        mock_supabase = MagicMock()
        mock_supabase.table().select().eq().single().execute.return_value.data = {"plan": "starter"}

        guardrail = make_guardrail_result(is_safe=True, intent="RAG_QUERY", complexity="SIMPLE")

        with patch("api.v1.chat.get_supabase", return_value=mock_supabase), \
             patch("api.v1.chat.guardrail_service.analyze_query_with_context", return_value=guardrail), \
             patch("api.v1.chat.llm_router.select_model") as mock_router, \
             patch("api.v1.chat.condense_question", new_callable=AsyncMock, return_value="Q"), \
             patch("services.embeddings.get_embeddings_model"), \
             patch("api.v1.chat.LLMFactory"), \
             patch("api.v1.chat.sentry_sdk") as mock_sentry:

            mock_router.return_value.provider = "openai"

            # FORCE ERROR IN CHAIN INVOKE
            mock_chain = MagicMock()
            mock_chain.invoke.side_effect = Exception("Generation Failed")

            with patch("api.v1.chat.StrOutputParser"), \
                 patch("api.v1.chat.ChatPromptTemplate") as mock_prompt_cls:

                mock_prompt = MagicMock()
                mock_prompt_cls.from_messages.return_value = mock_prompt
                mock_prompt.__or__.return_value = MagicMock(__or__=MagicMock(return_value=mock_chain))

                from api.v1.chat import ChatRequest, HTTPException, chat_endpoint

                # Act
                payload = ChatRequest(query="Test", model="auto")
                with pytest.raises(HTTPException):
                    await chat_endpoint(mock_request, payload, mock_bg_tasks, user_id="test-user")

                # Assert
                mock_sentry.capture_exception.assert_called_once()
                args, _ = mock_sentry.capture_exception.call_args
                assert str(args[0]) == "Generation Failed"


class TestChatHelpers:
    def test_trim_history_keeps_system_and_last(self):
        history = [
            {"role": "system", "content": "system"},
            {"role": "user", "content": "one"},
            {"role": "assistant", "content": "two"},
            {"role": "user", "content": "final"},
        ]

        result = api.v1.chat.trim_history(history.copy(), max_tokens=1)

        assert result[0]["role"] == "system"
        assert result[-1]["content"] == "final"

    @pytest.mark.asyncio
    async def test_condense_question_returns_original_without_history(self):
        assert await api.v1.chat.condense_question("Hello?", []) == "Hello?"

    @pytest.mark.asyncio
    async def test_condense_question_falls_back_on_error(self):
        with patch("api.v1.chat.ChatOpenAI", side_effect=Exception("boom")):
            result = await api.v1.chat.condense_question("Hello?", [{"role": "user", "content": "Context"}])
        assert result == "Hello?"

    def test_format_context_with_citations(self):
        docs = [
            {
                "content": "Doc content",
                "metadata": {"filename": "file.txt"},
                "source_type": "file_upload",
                "title": "Doc",
            },
            {
                "content": "Web content",
                "metadata": {"source_url": "https://example.com"},
                "source_type": "web",
            },
        ]

        context, sources = api.v1.chat.format_context_with_citations(docs)

        assert "[1] File:" in context
        assert sources[0]["label"] == "Doc"
        assert sources[1]["url"] == "https://example.com"

    @pytest.mark.asyncio
    async def test_condense_question_returns_original_on_blank_history(self):
        history = [{"role": "user", "content": ""}]
        assert await api.v1.chat.condense_question("Hello?", history) == "Hello?"

    @pytest.mark.asyncio
    async def test_condense_question_success_path(self):
        chain = MagicMock()
        chain.ainvoke = AsyncMock(return_value="Standalone")

        prompt = MagicMock()
        prompt.__or__.return_value = MagicMock(__or__=MagicMock(return_value=chain))

        with patch("api.v1.chat.LLMFactory") as mock_factory:
            mock_factory.get_model.return_value = (MagicMock(), {})
            with patch("api.v1.chat.ChatPromptTemplate.from_template", return_value=prompt):
                result = await api.v1.chat.condense_question("Hello?", [{"role": "user", "content": "Context"}])

        assert result == "Standalone"


class TestChatSafety:
    @pytest.mark.asyncio
    async def test_chat_endpoint_blocks_unsafe(self):
        from fastapi import Request

        from services.guardrails import GuardrailResult

        mock_request = MagicMock(spec=Request)
        mock_request.client.host = "127.0.0.1"
        mock_bg_tasks = MagicMock()

        # Use proper GuardrailResult instead of SimpleNamespace
        guardrail = GuardrailResult(
            is_safe=False,
            intent="OFF_TOPIC",
            complexity="SIMPLE",
            language="en",
            reply="Blocked",
        )

        # Mock the context-aware method (which is now called by chat_endpoint)
        with patch("api.v1.chat.get_supabase", return_value=MagicMock()), \
             patch("api.v1.chat.guardrail_service.analyze_query_with_context", return_value=guardrail), \
             patch("api.v1.chat.audit_logger.log") as audit_log:
            from api.v1.chat import ChatRequest, chat_endpoint

            payload = ChatRequest(query="bad", history=[], conversation_id="conv-1")
            result = await chat_endpoint(mock_request, payload, mock_bg_tasks, user_id="user-1")

        assert result.answer == "Blocked"
        audit_log.assert_called_once()


class TestConversationErrorPaths:
    @pytest.mark.unit
    def test_list_conversations_handles_error(self):
        supabase = MagicMock()
        table = MagicMock()
        table.select.return_value = table
        table.eq.return_value = table
        table.order.return_value = table
        table.execute.side_effect = Exception("db error")
        supabase.table.return_value = table

        with patch("api.v1.chat.get_supabase", return_value=supabase):
            from api.v1.chat import list_conversations

            with pytest.raises(Exception):
                asyncio.run(list_conversations(user_id="user-1"))

    @pytest.mark.asyncio
    async def test_create_conversation_missing_data(self):
        supabase = MagicMock()
        table = MagicMock()
        table.insert.return_value.execute.return_value = MagicMock(data=[])
        supabase.table.return_value = table

        with patch("api.v1.chat.get_supabase", return_value=supabase):
            from api.v1.chat import ConversationCreate, create_conversation

            with pytest.raises(Exception):
                await create_conversation(ConversationCreate(title="Test"), user_id="user-1")

    @pytest.mark.asyncio
    async def test_get_messages_handles_error(self):
        supabase = MagicMock()
        conv_table = MagicMock()
        conv_table.select.return_value = conv_table
        conv_table.eq.return_value = conv_table
        conv_table.execute.return_value = MagicMock(data=[{"id": "conv-1"}])

        msg_table = MagicMock()
        msg_table.select.return_value = msg_table
        msg_table.eq.return_value = msg_table
        msg_table.order.return_value = msg_table
        msg_table.execute.side_effect = Exception("db error")

        supabase.table.side_effect = lambda name: {
            "conversations": conv_table,
            "messages": msg_table,
        }[name]

        with patch("api.v1.chat.get_supabase", return_value=supabase):
            from api.v1.chat import get_messages

            with pytest.raises(Exception):
                await get_messages("conv-1", user_id="user-1")


class TestChatEndpointErrors:
    @pytest.mark.asyncio
    async def test_chat_plan_fetch_error_falls_back(self):
        from fastapi import Request
        mock_request = MagicMock(spec=Request)
        mock_request.client.host = "127.0.0.1"
        mock_bg_tasks = MagicMock()

        guardrail = make_guardrail_result(is_safe=True, intent="RAG_QUERY", complexity="SIMPLE")

        supabase = MagicMock()
        supabase.table.return_value.select.return_value.eq.return_value.single.return_value.execute.side_effect = Exception("db")
        supabase.rpc.return_value.execute.return_value = MagicMock(data=[])

        with patch("api.v1.chat.get_supabase", return_value=supabase), \
             patch("api.v1.chat.guardrail_service.analyze_query_with_context", return_value=guardrail), \
             patch("api.v1.chat.llm_router.select_model") as mock_router, \
             patch("api.v1.chat.condense_question", new_callable=AsyncMock, return_value="Q"), \
             patch("services.embeddings.get_embeddings_model") as mock_embeddings, \
             patch("api.v1.chat.LLMFactory") as mock_factory, \
             patch("api.v1.chat.ChatPromptTemplate.from_messages") as mock_prompt, \
             patch("api.v1.chat.StrOutputParser"):
            mock_router.return_value.provider = "openai"
            mock_router.return_value.model = "gpt-4o"
            mock_embeddings.return_value.embed_query.return_value = [0.1]
            llm = MagicMock()
            mock_factory.get_model.return_value = llm
            chain = MagicMock()
            chain.invoke.return_value = "Answer"
            prompt_obj = MagicMock()
            prompt_obj.__or__.return_value = MagicMock(__or__=MagicMock(return_value=chain))
            mock_prompt.return_value = prompt_obj

            from api.v1.chat import ChatRequest, chat_endpoint

            result = await chat_endpoint(mock_request, ChatRequest(query="Q", model="auto"), mock_bg_tasks, user_id="user-1")

        assert result.answer == "Answer"

    @pytest.mark.asyncio
    async def test_chat_retrieval_failure_raises(self):
        from fastapi import Request
        mock_request = MagicMock(spec=Request)
        mock_request.client.host = "127.0.0.1"
        mock_bg_tasks = MagicMock()

        guardrail = make_guardrail_result(is_safe=True, intent="RAG_QUERY", complexity="SIMPLE")

        supabase = MagicMock()
        supabase.table.return_value.select.return_value.eq.return_value.single.return_value.execute.return_value = MagicMock(data={"plan": "starter"})
        supabase.rpc.return_value.execute.side_effect = Exception("search down")

        with patch("api.v1.chat.get_supabase", return_value=supabase), \
             patch("api.v1.chat.guardrail_service.analyze_query_with_context", return_value=guardrail), \
             patch("api.v1.chat.llm_router.select_model") as mock_router, \
             patch("api.v1.chat.condense_question", new_callable=AsyncMock, return_value="Q"), \
             patch("services.embeddings.get_embeddings_model") as mock_embeddings:
            mock_router.return_value.provider = "openai"
            mock_router.return_value.model = "gpt-4o"
            mock_embeddings.return_value.embed_query.return_value = [0.1]

            from api.v1.chat import ChatRequest, chat_endpoint

            with pytest.raises(HTTPException):
                await chat_endpoint(mock_request, ChatRequest(query="Q", model="auto"), mock_bg_tasks, user_id="user-1")


class TestStreamAndSaveErrors:
    @pytest.mark.asyncio
    async def test_stream_chat_response_emits_error(self):
        prompt = MagicMock()
        chain = MagicMock()
        chain.astream.side_effect = Exception("boom")
        prompt.__or__.return_value = chain

        prompt_builder = MagicMock(return_value=(prompt, {"context": "ctx", "question": "Q", "language": "en"}, "sys"))
        candidate = api.v1.chat.ModelSelection(provider="openai", model="gpt-4o-mini", reason="primary")

        events = []
        with patch("api.v1.chat.LLMFactory.get_model", return_value=MagicMock()):
            async for event in api.v1.chat.stream_chat_response(
                prompt_builder,
                [candidate],
                "fast",
                "ctx",
                "Q",
                [],
                "conv-1",
                "user-1",
                MagicMock(),
                "en",
                None,
                "org-1",
                "starter",
            ):
                events.append(event)

        assert any("error" in event for event in events)

    def test_save_messages_handles_errors(self):
        supabase = MagicMock()
        supabase.table.return_value.insert.side_effect = Exception("db error")

        result = api.v1.chat.save_messages(supabase, "conv-1", "Q", "A", [])
        assert result is None


@pytest.mark.asyncio
class TestConversationEndpoints:
    async def test_get_conversation_returns_404(self):
        mock_supabase = MagicMock()
        mock_supabase.table().select().eq().eq().single().execute.return_value = Mock(data=None)

        with patch("api.v1.chat.get_supabase", return_value=mock_supabase):
            from api.v1.chat import HTTPException, get_conversation
            with pytest.raises(HTTPException) as exc:
                await get_conversation(
                    request=_make_mock_request(),
                    conversation_id="conv-1",
                    user_id="user-1",
                    organization_id="org-1"
                )
            assert exc.value.status_code == 404

    async def test_update_conversation_returns_404(self):
        mock_supabase = MagicMock()
        mock_supabase.table().update().eq().eq().execute.return_value = Mock(data=[])

        with patch("api.v1.chat.get_supabase", return_value=mock_supabase):
            from api.v1.chat import (
                ConversationUpdate,
                HTTPException,
                update_conversation,
            )
            with pytest.raises(HTTPException) as exc:
                await update_conversation(
                    request=_make_mock_request(method="PATCH"),
                    conversation_id="conv-1",
                    payload=ConversationUpdate(title="New"),
                    user_id="user-1",
                    organization_id="org-1"
                )
            assert exc.value.status_code == 404

    async def test_delete_conversation_logs_audit(self):
        from fastapi import BackgroundTasks

        mock_supabase = MagicMock()
        mock_supabase.table().select().eq().eq().single().execute.return_value = Mock(data={"title": "Chat"})
        mock_supabase.table().delete().eq().eq().execute.return_value = Mock(data=[{"id": "conv-1"}])

        background_tasks = BackgroundTasks()

        with patch("api.v1.chat.get_supabase", return_value=mock_supabase), \
             patch("api.v1.chat.log_chat_delete") as mock_audit:
            from api.v1.chat import delete_conversation
            response = await delete_conversation(
                conversation_id="conv-1",
                request=_make_mock_request(method="DELETE"),
                background_tasks=background_tasks,
                user_id="user-1",
                organization_id="org-1"
            )

        assert response["deleted_id"] == "conv-1"
        mock_audit.assert_called_once()

    async def test_get_messages_returns_404(self):
        mock_supabase = MagicMock()
        mock_supabase.table().select().eq().eq().execute.return_value = Mock(data=[])

        with patch("api.v1.chat.get_supabase", return_value=mock_supabase):
            from api.v1.chat import HTTPException, get_messages
            with pytest.raises(HTTPException) as exc:
                await get_messages(
                    request=_make_mock_request(),
                    conversation_id="conv-1",
                    user_id="user-1",
                    organization_id="org-1"
                )
            assert exc.value.status_code == 404


@pytest.mark.asyncio
class TestChatEndpointPaths:
    async def test_chat_returns_refusal_on_safety_violation(self):
        from fastapi import BackgroundTasks, Request

        request = MagicMock(spec=Request)
        request.client.host = "127.0.0.1"
        background_tasks = BackgroundTasks()

        guardrail = make_guardrail_result(
            is_safe=False,
            intent="RAG_QUERY",
            reply="Nope",
        )

        with patch("api.v1.chat.get_supabase", return_value=MagicMock()), \
             patch("api.v1.chat.guardrail_service.analyze_query_with_context", return_value=guardrail), \
             patch("api.v1.chat.audit_logger.log") as mock_audit:
            from api.v1.chat import ChatRequest, chat_endpoint
            response = await chat_endpoint(
                request,
                ChatRequest(query="bad", conversation_id="conv-1"),
                background_tasks,
                user_id="user-1",
            )

        assert response.answer == "Nope"
        mock_audit.assert_called_once()

    async def test_chat_returns_fast_reply_on_greeting(self):
        from fastapi import BackgroundTasks, Request

        request = MagicMock(spec=Request)
        request.client.host = "127.0.0.1"
        background_tasks = BackgroundTasks()

        guardrail = make_guardrail_result(
            is_safe=True,
            intent="GREETING",
            reply="Hello",
        )

        with patch("api.v1.chat.get_supabase", return_value=MagicMock()), \
             patch("api.v1.chat.guardrail_service.analyze_query_with_context", return_value=guardrail), \
             patch("api.v1.chat.save_messages") as mock_save:
            from api.v1.chat import ChatRequest, chat_endpoint
            response = await chat_endpoint(
                request,
                ChatRequest(query="hi", conversation_id="conv-1"),
                background_tasks,
                user_id="user-1",
            )

        assert response.answer == "Hello"
        mock_save.assert_called_once()

    async def test_chat_embedding_failure_returns_500(self):
        from fastapi import BackgroundTasks, HTTPException, Request

        request = MagicMock(spec=Request)
        request.client.host = "127.0.0.1"
        background_tasks = BackgroundTasks()

        guardrail = make_guardrail_result(
            is_safe=True,
            intent="RAG_QUERY",
        )

        supabase = MagicMock()
        supabase.table().select().eq().single().execute.return_value = Mock(data={"plan": "starter"})

        embeddings = MagicMock()
        embeddings.embed_query.side_effect = Exception("embed error")

        with patch("api.v1.chat.get_supabase", return_value=supabase), \
             patch("api.v1.chat.guardrail_service.analyze_query_with_context", return_value=guardrail), \
             patch("services.embeddings.get_embeddings_model", return_value=embeddings):
            from api.v1.chat import ChatRequest, chat_endpoint
            with pytest.raises(HTTPException) as exc:
                await chat_endpoint(request, ChatRequest(query="ask"), background_tasks, user_id="user-1")
            assert exc.value.status_code == 500

    async def test_chat_errors_when_hybrid_search_fails(self):
        from fastapi import BackgroundTasks, Request

        request = MagicMock(spec=Request)
        request.client.host = "127.0.0.1"
        background_tasks = BackgroundTasks()

        guardrail = make_guardrail_result(
            is_safe=True,
            intent="RAG_QUERY",
        )

        supabase = MagicMock()
        supabase.table().select().eq().single().execute.return_value = Mock(data={"plan": "starter"})

        supabase.rpc.side_effect = Exception("hybrid fail")

        embeddings = MagicMock()
        embeddings.embed_query.return_value = [0.1]

        with patch("api.v1.chat.get_supabase", return_value=supabase), \
             patch("api.v1.chat.guardrail_service.analyze_query_with_context", return_value=guardrail), \
             patch("api.v1.chat.llm_router.select_model", return_value=SimpleNamespace(provider="openai", model="gpt-4o")), \
             patch("services.embeddings.get_embeddings_model", return_value=embeddings), \
             patch("api.v1.chat.settings.RAG_SIMILARITY_THRESHOLD", 0.1):
            from api.v1.chat import ChatRequest, chat_endpoint
            with pytest.raises(HTTPException) as exc:
                await chat_endpoint(
                    request,
                    ChatRequest(query="ask", conversation_id="conv-1", model="auto"),
                    background_tasks,
                    user_id="user-1",
                )
            assert exc.value.status_code == 500


@pytest.mark.asyncio
async def test_stream_chat_response_emits_events():
    from api.v1.chat import stream_chat_response

    async def astream(_):
        yield SimpleNamespace(content="Hi")

    chain = MagicMock()
    chain.astream = astream

    prompt = MagicMock()
    prompt.__or__.return_value = chain
    prompt_builder = MagicMock(return_value=(prompt, {"context": "context", "question": "question", "language": "en"}, "sys"))
    candidate = api.v1.chat.ModelSelection(provider="openai", model="gpt-4o-mini", reason="primary")

    with patch("api.v1.chat.save_messages", return_value="msg-1"), \
         patch("api.v1.chat.record_llm_usage", new_callable=AsyncMock, return_value=None), \
         patch("api.v1.chat.LLMFactory.get_model", return_value=MagicMock()):
        events = [
            chunk
            async for chunk in stream_chat_response(
                prompt_builder,
                [candidate],
                "fast",
                "context",
                "question",
                [{"label": "Doc"}],
                "conv-1",
                "user-1",
                MagicMock(),
                "en",
                None,
                "org-1",
                "starter",
            )
        ]

    assert any("token" in event for event in events)
    assert any("sources" in event for event in events)
    assert any("done" in event for event in events)


def test_save_messages_returns_none_without_conversation():
    from api.v1.chat import save_messages
    assert save_messages(MagicMock(), None, "q", "a", []) is None


@pytest.mark.asyncio
async def test_get_conversation_success():
    from api.v1.chat import get_conversation

    table = MagicMock()
    table.select.return_value = table
    table.eq.return_value = table
    table.single.return_value = table
    table.execute.return_value = Mock(data={"id": "conv-1"})
    supabase = MagicMock()
    supabase.table.return_value = table

    with patch("api.v1.chat.get_supabase", return_value=supabase):
        result = await get_conversation(
            request=_make_mock_request(),
            conversation_id="conv-1",
            user_id="user-1",
            organization_id="org-1"
        )

    assert result["id"] == "conv-1"


@pytest.mark.asyncio
async def test_get_conversation_handles_error():
    from api.v1.chat import get_conversation

    table = MagicMock()
    table.select.return_value = table
    table.eq.return_value = table
    table.single.return_value = table
    table.execute.side_effect = Exception("boom")
    supabase = MagicMock()
    supabase.table.return_value = table

    with patch("api.v1.chat.get_supabase", return_value=supabase):
        with pytest.raises(HTTPException) as exc:
            await get_conversation(
                request=_make_mock_request(),
                conversation_id="conv-1",
                user_id="user-1",
                organization_id="org-1"
            )

    assert exc.value.status_code == 500


@pytest.mark.asyncio
async def test_update_conversation_success():
    from api.v1.chat import ConversationUpdate, update_conversation

    table = MagicMock()
    table.update.return_value = table
    table.eq.return_value = table
    table.execute.return_value = Mock(data=[{"id": "conv-1", "title": "New"}])
    supabase = MagicMock()
    supabase.table.return_value = table

    with patch("api.v1.chat.get_supabase", return_value=supabase):
        result = await update_conversation(
            request=_make_mock_request(method="PATCH"),
            conversation_id="conv-1",
            payload=ConversationUpdate(title="New"),
            user_id="user-1",
            organization_id="org-1"
        )

    assert result["title"] == "New"


@pytest.mark.asyncio
async def test_update_conversation_handles_error():
    from api.v1.chat import ConversationUpdate, update_conversation

    table = MagicMock()
    table.update.return_value = table
    table.eq.return_value = table
    table.execute.side_effect = Exception("boom")
    supabase = MagicMock()
    supabase.table.return_value = table

    with patch("api.v1.chat.get_supabase", return_value=supabase):
        with pytest.raises(HTTPException) as exc:
            await update_conversation(
                request=_make_mock_request(method="PATCH"),
                conversation_id="conv-1",
                payload=ConversationUpdate(title="New"),
                user_id="user-1",
                organization_id="org-1"
            )

    assert exc.value.status_code == 500


@pytest.mark.asyncio
async def test_delete_conversation_handles_error():
    from api.v1.chat import delete_conversation

    conv_table = MagicMock()
    conv_table.select.return_value = conv_table
    conv_table.eq.return_value = conv_table
    conv_table.single.return_value = conv_table
    conv_table.execute.return_value = Mock(data={"title": "Title"})
    conv_table.delete.return_value = conv_table
    conv_table.execute.side_effect = [Mock(data={"title": "Title"}), Exception("boom")]

    supabase = MagicMock()
    supabase.table.return_value = conv_table

    with patch("api.v1.chat.get_supabase", return_value=supabase), \
         patch("api.v1.chat.log_chat_delete"), pytest.raises(HTTPException) as exc:
        await delete_conversation(
            conversation_id="conv-1",
            request=_make_mock_request(method="DELETE"),
            background_tasks=MagicMock(),
            user_id="user-1",
            organization_id="org-1"
        )

    assert exc.value.status_code == 500


@pytest.mark.asyncio
async def test_get_messages_success():
    from api.v1.chat import get_messages

    conv_table = MagicMock()
    conv_table.select.return_value = conv_table
    conv_table.eq.return_value = conv_table
    conv_table.execute.return_value = Mock(data=[{"id": "conv-1"}])

    msg_table = MagicMock()
    msg_table.select.return_value = msg_table
    msg_table.eq.return_value = msg_table
    msg_table.order.return_value = msg_table
    msg_table.execute.return_value = Mock(data=[{"id": "m1"}])

    supabase = MagicMock()
    supabase.table.side_effect = lambda name: conv_table if name == "conversations" else msg_table

    with patch("api.v1.chat.get_supabase", return_value=supabase):
        result = await get_messages(
            request=_make_mock_request(),
            conversation_id="conv-1",
            user_id="user-1",
            organization_id="org-1"
        )

    assert result == [{"id": "m1"}]


@pytest.mark.asyncio
async def test_get_messages_handles_error():
    from api.v1.chat import get_messages

    conv_table = MagicMock()
    conv_table.select.return_value = conv_table
    conv_table.eq.return_value = conv_table
    conv_table.execute.return_value = Mock(data=[{"id": "conv-1"}])

    msg_table = MagicMock()
    msg_table.select.return_value = msg_table
    msg_table.eq.return_value = msg_table
    msg_table.order.return_value = msg_table
    msg_table.execute.side_effect = Exception("boom")

    supabase = MagicMock()
    supabase.table.side_effect = lambda name: conv_table if name == "conversations" else msg_table

    with patch("api.v1.chat.get_supabase", return_value=supabase):
        with pytest.raises(HTTPException) as exc:
            await get_messages(
                request=_make_mock_request(),
                conversation_id="conv-1",
                user_id="user-1",
                organization_id="org-1"
            )

    assert exc.value.status_code == 500


def test_trim_history_fallback_without_tiktoken():
    from api.v1.chat import trim_history

    history = [
        {"role": "system", "content": "sys"},
        {"role": "user", "content": "word " * 200},
        {"role": "assistant", "content": "reply"},
    ]

    with patch("api.v1.chat.tiktoken.get_encoding", side_effect=Exception("nope")):
        trimmed = trim_history(history, max_tokens=10)

    assert isinstance(trimmed, list)


@pytest.mark.asyncio
async def test_condense_question_returns_original_for_blank_history():
    from api.v1.chat import condense_question

    query = "What now?"
    history = [{"role": "user", "content": ""}]

    assert await condense_question(query, history) == query


def test_format_context_with_citations_variants():
    from api.v1.chat import format_context_with_citations

    docs = [
        {
            "content": "Drive content",
            "metadata": {"page_number": 2},
            "source_type": "google_drive",
            "title": "Drive Doc",
        },
        {
            "content": "Notion content",
            "metadata": {"header_path": "Section 1"},
            "source_type": "notion",
            "title": "Notion Doc",
        },
        {
            "content": "Other content",
            "metadata": {"filename": "file.txt"},
            "source_type": "slack",
        },
    ]

    context, sources = format_context_with_citations(docs)

    assert "Drive" in context
    assert len(sources) == 3
    assert sources[0]["type"] == "Drive"
    assert sources[1]["type"] == "Notion"


def test_format_context_with_citations_empty():
    from api.v1.chat import format_context_with_citations

    context, sources = format_context_with_citations([])

    assert context == ""
    assert sources == []


@pytest.mark.asyncio
async def test_chat_endpoint_streaming_returns_response():
    from fastapi import Request

    from api.v1.chat import ChatRequest, chat_endpoint

    scope = {
        "type": "http",
        "method": "POST",
        "path": "/",
        "headers": [],
        "client": ("127.0.0.1", 1234),
    }
    request = Request(scope)
    bg_tasks = MagicMock()

    supabase = MagicMock()
    supabase.table().select().eq().single().execute.return_value.data = {"plan": "starter"}
    supabase.rpc.return_value.execute.return_value = MagicMock(data=[])

    async def fake_stream(*_args, **_kwargs):
        yield "data: {}\n\n"

    with patch("api.v1.chat.get_supabase", return_value=supabase), \
         patch("api.v1.chat.guardrail_service.analyze_query") as mock_guard, \
         patch("api.v1.chat.llm_router.select_model") as mock_router, \
         patch("services.embeddings.get_embeddings_model"), \
         patch("api.v1.chat.LLMFactory.get_model", return_value=(MagicMock(), {"meta": True})), \
         patch("api.v1.chat.ChatPromptTemplate.from_messages", return_value=MagicMock()), \
         patch("api.v1.chat.stream_chat_response", side_effect=fake_stream):

        mock_guard.return_value.is_safe = True
        mock_guard.return_value.intent = "QA"
        mock_guard.return_value.complexity = "simple"
        mock_router.return_value.provider = "openai"
        mock_router.return_value.model = "gpt-4o"

        payload = ChatRequest(query="Hello", history=[], stream=True, model="auto")
        response = await chat_endpoint(request, payload, bg_tasks, user_id="user-1")

    assert response.media_type == "text/event-stream"


def test_save_messages_success():
    from api.v1.chat import save_messages

    messages_table = MagicMock()
    messages_table.insert.return_value.execute.side_effect = [
        Mock(data=[{"id": "user-msg"}]),
        Mock(data=[{"id": "assistant-msg"}]),
    ]
    conversations_table = MagicMock()
    conversations_table.update.return_value.eq.return_value.execute.return_value = Mock()

    supabase = MagicMock()
    supabase.table.side_effect = lambda name: messages_table if name == "messages" else conversations_table

    message_id = save_messages(supabase, "conv-1", "q", "a", ["src"])

    assert message_id == "assistant-msg"


# ============================================================
# Phase 1 RAG System Tests
# ============================================================

def test_model_context_window_llama_33_70b():
    """H1: Llama 3.3 70B has 128k context, not 8k."""
    from api.v1.chat import MODEL_CONTEXT_WINDOWS
    assert MODEL_CONTEXT_WINDOWS["llama-3.3-70b-versatile"] == 128000

def test_model_context_window_llama_31_8b_unchanged():
    """Guardrails model stays at 8192."""
    from api.v1.chat import MODEL_CONTEXT_WINDOWS
    assert MODEL_CONTEXT_WINDOWS["llama-3.1-8b-instant"] == 8192

@pytest.mark.asyncio
async def test_condense_question_is_async():
    """M2: condense_question must be async to avoid blocking event loop."""
    import inspect

    from api.v1.chat import condense_question
    assert inspect.iscoroutinefunction(condense_question)

def test_rag_temperature_is_zero():
    """L1: RAG responses should use temperature=0 for deterministic citations."""
    import inspect

    from api.v1 import chat as chat_module
    # Read source and check for temperature=0 (not 0.1)
    source = inspect.getsource(chat_module)
    assert "temperature=0.1" not in source, "Found temperature=0.1 — should be temperature=0"


# ============================================================
# Phase 3: M7 Condense Skip Heuristic Tests
# ============================================================

def test_needs_condensing_with_pronouns():
    """M7: Queries with pronouns should trigger condensing."""
    from api.v1.chat import _needs_condensing
    assert _needs_condensing("Tell me more about it", [{"role": "user", "content": "hi"}])


def test_no_condensing_for_standalone_query():
    """M7: Self-contained queries should skip condensing."""
    from api.v1.chat import _needs_condensing
    assert not _needs_condensing("What is Python?", [{"role": "user", "content": "hi"}])


def test_no_condensing_without_history():
    """M7: No history means no condensing needed."""
    from api.v1.chat import _needs_condensing
    assert not _needs_condensing("What is Python?", [])


def test_needs_condensing_with_reference_words():
    """M7: Reference words like 'previous', 'above' should trigger condensing."""
    from api.v1.chat import _needs_condensing
    assert _needs_condensing("Explain the previous point in detail", [{"role": "user", "content": "hi"}])


# ============================================================
# Phase 3: M9 Embedding Batch Size Tests
# ============================================================

def test_embedding_batch_size_is_200():
    from core.config import settings
    assert settings.EMBEDDING_BATCH_SIZE == 200


def test_embedding_sleep_interval_reduced():
    from core.config import settings
    assert settings.EMBEDDING_SLEEP_INTERVAL <= 0.1
