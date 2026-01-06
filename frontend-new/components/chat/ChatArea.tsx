/**
 * Chat Area with Virtual Scrolling
 * 
 * Optimized for large message histories using @tanstack/react-virtual.
 */

"use client";

import { useRef, useEffect } from "react";
import { useVirtualizer } from "@tanstack/react-virtual";
import { Message } from "@/hooks/useChatHistory";
import { MessageBubble } from "./MessageBubble";
import { ChatInput } from "./ChatInput";
import { EmptyState } from "./EmptyState";
import { AxioLogo } from "@/components/branding/AxioLogo";
import { ModelId } from "@/lib/types";

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
  const parentRef = useRef<HTMLDivElement>(null);
  const showEmptyState = messages.length === 0 && !isTyping && !streamingMessage;

  // Virtual scrolling for performance with large message lists
  const virtualizer = useVirtualizer({
    count: messages.length,
    getScrollElement: () => parentRef.current,
    estimateSize: () => 100, // Estimated message height
    overscan: 5, // Render 5 extra items above/below viewport
  });

  // Auto-scroll to bottom when new messages arrive
  useEffect(() => {
    if (parentRef.current) {
      parentRef.current.scrollTop = parentRef.current.scrollHeight;
    }
  }, [messages.length, isTyping, streamingMessage]);

  if (showEmptyState) {
    return (
      <div className="flex h-full flex-col">
        <div className="flex-1 overflow-y-auto">
          <EmptyState onQuerySelect={onSendMessage} />
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

  return (
    <div className="flex h-full flex-col">
      <div ref={parentRef} className="flex-1 overflow-y-auto">
        <div
          style={{
            height: `${virtualizer.getTotalSize()}px`,
            width: '100%',
            position: 'relative',
          }}
        >
          {virtualizer.getVirtualItems().map((virtualItem) => {
            const message = messages[virtualItem.index];
            return (
              <div
                key={virtualItem.key}
                style={{
                  position: 'absolute',
                  top: 0,
                  left: 0,
                  width: '100%',
                  transform: `translateY(${virtualItem.start}px)`,
                }}
              >
                <div className="mx-auto max-w-3xl px-4 py-3">
                  <MessageBubble
                    message={{
                      ...message,
                      timestamp: message.created_at,
                    }}
                  />
                </div>
              </div>
            );
          })}
        </div>

        {/* Typing indicator */}
        {isTyping && (
          <div className="mx-auto max-w-3xl px-4 py-3">
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
          </div>
        )}

        {/* Streaming message */}
        {streamingMessage && (
          <div className="mx-auto max-w-3xl px-4 py-3">
            <MessageBubble
              message={{
                id: "streaming",
                role: "assistant",
                content: streamingMessage,
                timestamp: new Date().toISOString(),
              }}
              isStreaming
            />
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