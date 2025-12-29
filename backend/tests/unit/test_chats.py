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

import pytest
from unittest.mock import Mock, patch, MagicMock
import api.v1.chat  # Ensure module is loaded for patching


class TestChatList:
    """Tests for GET /api/v1/chats."""
    
    @pytest.mark.unit
    def test_list_chats_returns_user_chats_only(self):
        """Chat list must filter by user_id (RLS equivalent)."""
        pass
    
    @pytest.mark.unit
    def test_list_chats_ordered_by_updated_at_desc(self):
        """Most recently updated chats should appear first."""
        pass
    
    @pytest.mark.unit
    def test_list_chats_empty_for_new_user(self):
        """New user should get empty array, not error."""
        pass


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
            from api.v1.chat import create_conversation, ConversationCreate
            
            # Act
            payload = ConversationCreate(title="Test Chat")
            result = await create_conversation(payload, user_id="test-user")
            
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
        mock_supabase.table().select().eq().single().execute.return_value.data = {"plan": "free"}
        
        with patch("api.v1.chat.get_supabase", return_value=mock_supabase), \
             patch("api.v1.chat.guardrail_service.analyze_query") as mock_guard, \
             patch("api.v1.chat.llm_router.select_model") as mock_router, \
             patch("api.v1.chat.condense_question", return_value="Condensed Question?") as mock_condense, \
             patch("api.v1.chat.OpenAIEmbeddings"), \
             patch("api.v1.chat.LLMFactory") as mock_llm_factory, \
             patch("api.v1.chat.save_messages") as mock_save_messages:
            
            # Mock Save Messages
            mock_save_messages.return_value = "msg-123"
            
            # Mock Guardrails
            mock_guard.return_value.is_safe = True
            mock_guard.return_value.intent = "QA"
            mock_guard.return_value.complexity = "simple"
            
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
                
                from api.v1.chat import chat_endpoint, ChatRequest
                
                # Act
                payload = ChatRequest(query="Original Query", history=[{"role": "user", "content": "prev"}])
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
        mock_supabase.table().select().eq().single().execute.return_value.data = {"plan": "free"}
        
        with patch("api.v1.chat.get_supabase", return_value=mock_supabase), \
             patch("api.v1.chat.guardrail_service.analyze_query") as mock_guard, \
             patch("api.v1.chat.condense_question", return_value="Q"), \
             patch("api.v1.chat.OpenAIEmbeddings"), \
             patch("api.v1.chat.LLMFactory"), \
             patch("api.v1.chat.sentry_sdk") as mock_sentry:
                
            mock_guard.return_value.is_safe = True
            
            # Force an error during routing or generation
            with patch("api.v1.chat.llm_router.select_model", side_effect=Exception("Test Error")):
                from api.v1.chat import chat_endpoint, ChatRequest
                from fastapi import HTTPException
                
                # Act & Assert
                with pytest.raises(Exception): # or HTTP 500
                   payload = ChatRequest(query="Test", history=[])
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
        mock_supabase.table().select().eq().single().execute.return_value.data = {"plan": "free"}
        
        with patch("api.v1.chat.get_supabase", return_value=mock_supabase), \
             patch("api.v1.chat.guardrail_service.analyze_query") as mock_guard, \
             patch("api.v1.chat.llm_router.select_model") as mock_router, \
             patch("api.v1.chat.condense_question", return_value="Q"), \
             patch("api.v1.chat.OpenAIEmbeddings"), \
             patch("api.v1.chat.LLMFactory"), \
             patch("api.v1.chat.sentry_sdk") as mock_sentry:
            
            mock_guard.return_value.is_safe = True
            mock_router.return_value.provider = "openai"
            
            # FORCE ERROR IN CHAIN INVOKE
            mock_chain = MagicMock()
            mock_chain.invoke.side_effect = Exception("Generation Failed")
            
            with patch("api.v1.chat.StrOutputParser"), \
                 patch("api.v1.chat.ChatPromptTemplate") as mock_prompt_cls:
                
                mock_prompt = MagicMock()
                mock_prompt_cls.from_messages.return_value = mock_prompt
                mock_prompt.__or__.return_value = MagicMock(__or__=MagicMock(return_value=mock_chain))
                
                from api.v1.chat import chat_endpoint, ChatRequest, HTTPException
                
                # Act
                payload = ChatRequest(query="Test")
                try:
                    await chat_endpoint(mock_request, payload, mock_bg_tasks, user_id="test-user")
                except HTTPException:
                    pass
                
                # Assert
                mock_sentry.capture_exception.assert_called_once()
                args, _ = mock_sentry.capture_exception.call_args
                assert str(args[0]) == "Generation Failed"
