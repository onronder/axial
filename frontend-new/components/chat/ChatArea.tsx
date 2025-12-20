"use client";

import { useState, useRef, useEffect, useCallback } from "react";
import { Message } from "@/hooks/useChatHistory";
import { MessageBubble } from "./MessageBubble";
import { ChatInput } from "./ChatInput";
import { EmptyState } from "./EmptyState";
import { AxioLogo } from "@/components/branding/AxioLogo";
import { api } from "@/lib/api";

interface ChatAreaProps {
  initialMessages?: Message[];
  conversationId?: string;
}

// Adapt Message to what MessageBubble expects
interface DisplayMessage {
  id: string;
  role: 'user' | 'assistant' | 'system';
  content: string;
  timestamp: string;
  sources?: string[];
}

export function ChatArea({ initialMessages = [], conversationId }: ChatAreaProps) {
  const [messages, setMessages] = useState<DisplayMessage[]>(() =>
    initialMessages.map(m => ({
      ...m,
      timestamp: m.created_at
    }))
  );
  const [isTyping, setIsTyping] = useState(false);
  const [streamingMessage, setStreamingMessage] = useState<string | null>(null);
  const messagesEndRef = useRef<HTMLDivElement>(null);

  const scrollToBottom = () => {
    messagesEndRef.current?.scrollIntoView({ behavior: "smooth" });
  };

  useEffect(() => {
    scrollToBottom();
  }, [messages, isTyping, streamingMessage]);

  // Update messages when initialMessages change (e.g., navigation)
  useEffect(() => {
    setMessages(initialMessages.map(m => ({
      ...m,
      timestamp: m.created_at
    })));
  }, [initialMessages]);

  const simulateStreaming = useCallback(async (fullText: string): Promise<string> => {
    const words = fullText.split(" ");
    let currentText = "";

    for (let i = 0; i < words.length; i++) {
      currentText += (i > 0 ? " " : "") + words[i];
      setStreamingMessage(currentText);
      // Random delay between 20-80ms for natural feel
      await new Promise((resolve) => setTimeout(resolve, 20 + Math.random() * 60));
    }

    return currentText;
  }, []);

  const handleSendMessage = async (content: string) => {
    const userMessage: DisplayMessage = {
      id: Date.now().toString(),
      role: "user",
      content,
      timestamp: new Date().toISOString(),
    };

    setMessages((prev) => [...prev, userMessage]);
    setIsTyping(true);

    try {
      // Call real chat API
      const { data } = await api.post('/api/v1/chat', {
        query: content,
        conversation_id: conversationId,
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

      // Show error message
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