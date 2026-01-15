/**
 * Chat Area - Production Grade Implementation
 * 
 * Clean, scrollable message list without virtualization complexity.
 * Includes Universal Context support for scope clarification.
 */

"use client";

import { useRef, useEffect } from "react";
import { Message } from "@/hooks/useChatHistory";
import { MessageBubble } from "./MessageBubble";
import { ChatInput } from "./ChatInput";
import { EmptyState } from "./EmptyState";
import { ClarificationCard } from "./ClarificationCard";
import { AxioLogo } from "@/components/branding/AxioLogo";
import { ModelId } from "@/lib/types";

interface ChatAreaProps {
  messages: Message[];
  onSendMessage: (content: string) => void;
  /** Handler for scope selection from clarification card */
  onSelectScope?: (scopeId: string, originalQuery: string) => void;
  isTyping?: boolean;
  streamingMessage?: string | null;
  disabled?: boolean;
  selectedModel: ModelId;
  onModelSelect: (model: ModelId) => void;
  /** True when re-sending with scope selection */
  isResending?: boolean;
}

export function ChatArea({
  messages,
  onSendMessage,
  onSelectScope,
  isTyping = false,
  streamingMessage = null,
  disabled = false,
  selectedModel,
  onModelSelect,
  isResending = false,
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
      <div className="pointer-events-none absolute inset-0 bg-[radial-gradient(circle_at_top,_rgba(139,92,246,0.08),transparent_45%),radial-gradient(circle_at_bottom,_rgba(6,182,212,0.06),transparent_40%)]" />
      <div className="pointer-events-none absolute inset-0 bg-[linear-gradient(120deg,hsl(var(--muted)/0.3),transparent_30%,hsl(var(--muted)/0.3))]" />
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
        <div className="mx-auto w-full max-w-5xl rounded-2xl border border-border bg-card/50 backdrop-blur-xl shadow-lg p-3 sm:p-4">
          {/* Messages stack naturally with proper spacing */}
          <div className="flex flex-col gap-4">
            {messages.map((message) => {
              // Handle clarification messages specially
              if (message.role === 'clarification' && message.candidates) {
                return (
                  <ClarificationCard
                    key={message.id}
                    message={message.content}
                    candidates={message.candidates}
                    onSelectScope={(scopeId) => {
                      if (onSelectScope && message.original_query) {
                        onSelectScope(scopeId, message.original_query);
                      }
                    }}
                    isLoading={isResending}
                  />
                );
              }
              
              // Regular message bubble
              return (
                <MessageBubble
                  key={message.id}
                  message={{
                    ...message,
                    timestamp: message.created_at,
                  }}
                />
              );
            })}

            {/* Typing indicator */}
            {isTyping && (
              <div className="flex items-start gap-3 animate-fade-in">
                <div className="flex h-8 w-8 shrink-0 items-center justify-center rounded-lg bg-muted border border-border">
                  <AxioLogo variant="icon" size="sm" />
                </div>
                <div className="rounded-2xl bg-muted border border-border px-4 py-3">
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
