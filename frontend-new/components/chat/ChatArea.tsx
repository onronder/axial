"use client";

import { useRef, useEffect } from "react";
import { Message } from "@/hooks/useChatHistory";
import { MessageBubble } from "./MessageBubble";
import { ChatInput } from "./ChatInput";
import { EmptyState } from "./EmptyState";
import { AxioLogo } from "@/components/branding/AxioLogo";

import { ModelId } from "@/lib/types";

/**
 * ChatArea - Pure display component for chat messages.
 * All business logic (loading, sending) is handled by the page.
 */
interface ChatAreaProps {
  messages: Message[];
  onSendMessage: (content: string) => void;
  isTyping?: boolean;
  streamingMessage?: string | null;
  disabled?: boolean;
  selectedModel: ModelId;
  onModelSelect: (model: ModelId) => void;
}

export function ChatArea({
  messages,
  onSendMessage,
  isTyping = false,
  streamingMessage = null,
  disabled = false,
  selectedModel,
  onModelSelect,
}: ChatAreaProps) {
  const messagesEndRef = useRef<HTMLDivElement>(null);

  // Scroll to bottom when messages change
  useEffect(() => {
    messagesEndRef.current?.scrollIntoView({ behavior: "smooth" });
  }, [messages, isTyping, streamingMessage]);

  const showEmptyState = messages.length === 0 && !isTyping && !streamingMessage;

  return (
    <div className="flex h-full flex-col">
      <div className="flex-1 overflow-y-auto">
        {showEmptyState ? (
          <EmptyState onQuerySelect={onSendMessage} />
        ) : (
          <div className="mx-auto max-w-3xl px-4 py-8 space-y-6">
            {messages.map((message) => (
              <MessageBubble
                key={message.id}
                message={{
                  ...message,
                  timestamp: message.created_at,
                }}
              />
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
      <ChatInput
        onSend={onSendMessage}
        disabled={disabled}
        selectedModel={selectedModel}
        onModelSelect={onModelSelect}
      />
    </div>
  );
}