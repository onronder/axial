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
  // eslint-disable-next-line react-hooks/incompatible-library
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

  const backgroundLayer = (
    <>
      <div className="pointer-events-none absolute inset-0 bg-[radial-gradient(circle_at_top,_rgba(139,92,246,0.12),transparent_45%),radial-gradient(circle_at_bottom,_rgba(6,182,212,0.1),transparent_40%)]" />
      <div className="pointer-events-none absolute inset-0 bg-[linear-gradient(120deg,rgba(255,255,255,0.04),transparent_30%,rgba(255,255,255,0.04))]" />
    </>
  );

  const messageStack = (
    <div className="mx-auto w-full max-w-5xl space-y-2 rounded-2xl border border-white/10 bg-white/5 backdrop-blur-xl shadow-glow p-3 sm:p-4">
      <div
        style={{
          height: `${virtualizer.getTotalSize()}px`,
          width: "100%",
          position: "relative",
        }}
      >
        {virtualizer.getVirtualItems().map((virtualItem) => {
          const message = messages[virtualItem.index];
          return (
            <div
              key={virtualItem.key}
              style={{
                position: "absolute",
                top: 0,
                left: 0,
                width: "100%",
                transform: `translateY(${virtualItem.start}px)`,
              }}
            >
              <div className="px-2 py-2 sm:px-3">
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

      {isTyping && (
        <div className="px-2 py-2 sm:px-3">
          <div className="flex items-start gap-3 animate-fade-in">
            <div className="flex h-8 w-8 shrink-0 items-center justify-center rounded-lg bg-white/10 border border-white/10">
              <AxioLogo variant="icon" size="sm" />
            </div>
            <div className="rounded-2xl bg-white/10 border border-white/10 px-4 py-3">
              <div className="flex items-center gap-1.5">
                <span className="h-2 w-2 rounded-full bg-primary animate-bounce" style={{ animationDelay: "0ms" }} />
                <span className="h-2 w-2 rounded-full bg-primary animate-bounce" style={{ animationDelay: "150ms" }} />
                <span className="h-2 w-2 rounded-full bg-primary animate-bounce" style={{ animationDelay: "300ms" }} />
              </div>
            </div>
          </div>
        </div>
      )}

      {streamingMessage && (
        <div className="px-2 py-2 sm:px-3">
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
  );

  if (showEmptyState) {
    return (
      <div className="relative flex h-full flex-col overflow-hidden bg-background">
        {backgroundLayer}
        <div className="flex-1 overflow-y-auto px-3 py-6 sm:px-6">
          <div className="mx-auto max-w-5xl">
            <EmptyState onQuerySelect={onSendMessage} />
          </div>
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
    <div className="relative flex h-full flex-col overflow-hidden bg-background">
      {backgroundLayer}
      <div ref={parentRef} className="flex-1 overflow-y-auto px-3 py-6 sm:px-6">
        {messageStack}
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
