/**
 * Chat Area - Production Grade Implementation
 * 
 * Clean, scrollable message list without virtualization complexity.
 * Virtualization was causing layout bugs due to fixed height estimates.
 */

"use client";

import { useRef, useEffect } from "react";
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
  const scrollRef = useRef<HTMLDivElement>(null);
  const messagesEndRef = useRef<HTMLDivElement>(null);
  const showEmptyState = messages.length === 0 && !isTyping && !streamingMessage;

  // Smooth scroll to bottom when new messages arrive
  useEffect(() => {
    messagesEndRef.current?.scrollIntoView({ behavior: "smooth" });
  }, [messages.length, isTyping, streamingMessage]);

  const backgroundLayer = (
    <>
      <div className="pointer-events-none absolute inset-0 bg-[radial-gradient(circle_at_top,_rgba(139,92,246,0.12),transparent_45%),radial-gradient(circle_at_bottom,_rgba(6,182,212,0.1),transparent_40%)]" />
      <div className="pointer-events-none absolute inset-0 bg-[linear-gradient(120deg,rgba(255,255,255,0.04),transparent_30%,rgba(255,255,255,0.04))]" />
    </>
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
      
      {/* Scrollable message area - Natural flow layout */}
      <div ref={scrollRef} className="flex-1 overflow-y-auto px-3 py-6 sm:px-6">
        <div className="mx-auto w-full max-w-5xl rounded-2xl border border-white/10 bg-white/5 backdrop-blur-xl shadow-glow p-3 sm:p-4">
          {/* Messages stack naturally with proper spacing */}
          <div className="flex flex-col gap-4">
            {messages.map((message) => (
              <MessageBubble
                key={message.id}
                message={{
                  ...message,
                  timestamp: message.created_at,
                }}
              />
            ))}

            {/* Typing indicator */}
            {isTyping && (
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
            )}

            {/* Streaming message */}
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
            
            {/* Scroll anchor */}
            <div ref={messagesEndRef} />
          </div>
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
