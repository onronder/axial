"use client";

import { useState, useRef, useEffect, useCallback } from "react";
import { Message, useChatHistory } from "@/hooks/useChatHistory";
import { MessageBubble } from "./MessageBubble";
import { ChatInput } from "./ChatInput";
import { EmptyState } from "./EmptyState";
import { AxioLogo } from "@/components/branding/AxioLogo";
import { api } from "@/lib/api";
import { generateSmartTitle } from "@/lib/chat-utils";

interface ChatAreaProps {
  initialMessages?: Message[];
  conversationId?: string;
  initialQuery?: string;
}

interface DisplayMessage {
  id: string;
  role: 'user' | 'assistant' | 'system';
  content: string;
  timestamp: string;
  sources?: string[];
}

export function ChatArea({ initialMessages = [], conversationId, initialQuery }: ChatAreaProps) {
  const { createNewChat } = useChatHistory();
  const [currentConversationId, setCurrentConversationId] = useState<string | undefined>(conversationId);
  const [messages, setMessages] = useState<DisplayMessage[]>(() =>
    initialMessages.map(m => ({
      ...m,
      timestamp: m.created_at
    }))
  );
  const [isTyping, setIsTyping] = useState(false);
  const [streamingMessage, setStreamingMessage] = useState<string | null>(null);
  const messagesEndRef = useRef<HTMLDivElement>(null);
  const hasProcessedInitialQuery = useRef(false);
  const lastConversationId = useRef<string | undefined>(conversationId);

  const scrollToBottom = () => {
    messagesEndRef.current?.scrollIntoView({ behavior: "smooth" });
  };

  useEffect(() => {
    scrollToBottom();
  }, [messages, isTyping, streamingMessage]);

  // Update messages when navigating to a DIFFERENT chat
  // Don't reset if this is just a re-render from context updates
  useEffect(() => {
    if (conversationId === lastConversationId.current && messages.length > 0) {
      return; // Skip reset - same chat, already has messages
    }
    lastConversationId.current = conversationId;

    setMessages(initialMessages.map(m => ({
      ...m,
      timestamp: m.created_at
    })));
  }, [initialMessages, conversationId]);

  // Process initial query if provided (from dashboard)
  useEffect(() => {
    if (initialQuery && !hasProcessedInitialQuery.current) {
      hasProcessedInitialQuery.current = true;
      handleSendMessage(initialQuery);
    }
  }, [initialQuery]);

  const simulateStreaming = useCallback(async (fullText: string): Promise<string> => {
    const words = fullText.split(" ");
    let currentText = "";

    for (let i = 0; i < words.length; i++) {
      currentText += (i > 0 ? " " : "") + words[i];
      setStreamingMessage(currentText);
      await new Promise((resolve) => setTimeout(resolve, 20 + Math.random() * 60));
    }

    return currentText;
  }, []);

  const handleSendMessage = async (content: string) => {
    let chatId = currentConversationId;
    let isNewChat = false;

    // If no conversation exists, create one first with a smart title
    if (!chatId) {
      isNewChat = true;
      try {
        console.log('💬 Creating new chat for first message...');
        // Generate a smart title from the user's message
        const smartTitle = generateSmartTitle(content);
        chatId = await createNewChat(smartTitle);
        setCurrentConversationId(chatId);
        // NOTE: We intentionally don't update the URL here to prevent
        // component remounts during the chat response. The chat works
        // fine without URL change, and user can navigate after finishing.
        console.log('💬 Chat created with title:', smartTitle, 'ID:', chatId);
      } catch (error) {
        console.error('💬 Failed to create chat:', error);
        return; // Don't continue if chat creation failed
      }
    }

    const userMessage: DisplayMessage = {
      id: Date.now().toString(),
      role: "user",
      content,
      timestamp: new Date().toISOString(),
    };

    setMessages((prev) => [...prev, userMessage]);
    setIsTyping(true);

    try {
      // Call real chat API with the conversation ID
      const { data } = await api.post('api/v1/chat', {
        query: content,
        conversation_id: chatId,
        history: messages.slice(-10).map(m => ({
          role: m.role,
          content: m.content
        }))
      });

      setIsTyping(false);

      // Stream the response for visual effect
      await simulateStreaming(data.answer);

      const aiMessage: DisplayMessage = {
        id: data.message_id || (Date.now() + 1).toString(),
        role: "assistant",
        content: data.answer,
        timestamp: new Date().toISOString(),
        sources: data.sources,
      };

      setStreamingMessage(null);
      setMessages((prev) => [...prev, aiMessage]);

    } catch (error) {
      console.error('Chat API error:', error);
      setIsTyping(false);
      setStreamingMessage(null);

      const errorMessage: DisplayMessage = {
        id: (Date.now() + 1).toString(),
        role: "assistant",
        content: "Sorry, I encountered an error processing your request. Please try again.",
        timestamp: new Date().toISOString(),
      };
      setMessages((prev) => [...prev, errorMessage]);
    }
  };

  const handleStarterQuery = (query: string) => {
    handleSendMessage(query);
  };

  const isDisabled = isTyping || streamingMessage !== null;

  return (
    <div className="flex h-full flex-col">
      <div className="flex-1 overflow-y-auto">
        {messages.length === 0 && !isTyping && !streamingMessage ? (
          <EmptyState onQuerySelect={handleStarterQuery} />
        ) : (
          <div className="mx-auto max-w-3xl px-4 py-8 space-y-6">
            {messages.map((message) => (
              <MessageBubble key={message.id} message={message} />
            ))}
            {isTyping && (
              <div className="flex items-start gap-3 animate-fade-in">
                <div className="flex h-8 w-8 shrink-0 items-center justify-center rounded-lg bg-muted">
                  <AxioLogo variant="icon" size="sm" />
                </div>
                <div className="rounded-2xl bg-muted px-4 py-3">
                  <div className="flex items-center gap-1.5">
                    <span className="h-2 w-2 rounded-full bg-primary animate-bounce" style={{ animationDelay: "0ms" }} />
                    <span className="h-2 w-2 rounded-full bg-primary animate-bounce" style={{ animationDelay: "150ms" }} />
                    <span className="h-2 w-2 rounded-full bg-primary animate-bounce" style={{ animationDelay: "300ms" }} />
                  </div>
                </div>
              </div>
            )}
            {streamingMessage && (
              <MessageBubble
                message={{
                  id: "streaming",
                  role: "assistant",
                  content: streamingMessage,
                  timestamp: new Date().toISOString(),
                }}
                isStreaming
              />
            )}
            <div ref={messagesEndRef} />
          </div>
        )}
      </div>
      <ChatInput onSend={handleSendMessage} disabled={isDisabled} />
    </div>
  );
}