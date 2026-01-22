/**
 * Chat Area - Production Grade Implementation
 * 
 * Clean, scrollable message list without virtualization complexity.
 * Includes Universal Context support for scope clarification.
 * Features ThinkingIndicator for RAG pipeline visualization.
 * Includes user feedback collection (thumbs up/down) for quality analytics.
 */

"use client";

import { useRef, useEffect, useCallback } from "react";
import { Message } from "@/hooks/useChatHistory";
import { MessageBubble } from "./MessageBubble";
import { ChatInput } from "./ChatInput";
import { EmptyState } from "./EmptyState";
import { ClarificationCard } from "./ClarificationCard";
import { ThinkingIndicator, ThinkingStatus, TypingIndicator } from "./ThinkingIndicator";
import { ModelId } from "@/lib/types";
import { useFeedback, type FeedbackRating, type SourceSnapshot } from "@/hooks/useFeedback";
import { SourceMetadata } from "./SourceCard";

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
  /** RAG processing status for thinking indicator */
  thinkingStatus?: ThinkingStatus | null;
  /** Current conversation ID for feedback tracking */
  conversationId?: string;
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
  thinkingStatus = null,
  conversationId,
}: ChatAreaProps) {
  const scrollRef = useRef<HTMLDivElement>(null);
  const messagesEndRef = useRef<HTMLDivElement>(null);
  const showEmptyState = messages.length === 0 && !isTyping && !streamingMessage && !thinkingStatus;
  
  // Feedback hook for collecting user ratings on AI responses
  const { submitFeedback, isSubmitting: isFeedbackSubmitting, feedbackState } = useFeedback(conversationId);
  
  /**
   * Find the previous user message for context.
   * Used to provide the user's question when submitting feedback.
   */
  const getPreviousUserQuery = useCallback((messageIndex: number): string => {
    // Look backwards from current message to find the user's question
    for (let i = messageIndex - 1; i >= 0; i--) {
      if (messages[i]?.role === 'user') {
        return messages[i].content;
      }
    }
    return '';
  }, [messages]);
  
  /**
   * Handle feedback submission from MessageBubble.
   */
  const handleFeedbackSubmit = useCallback(async (
    messageId: string,
    rating: FeedbackRating,
    feedbackText?: string
  ) => {
    // Find the message to get its sources and content
    const message = messages.find(m => m.id === messageId);
    if (!message) return;
    
    const messageIndex = messages.findIndex(m => m.id === messageId);
    const queryText = getPreviousUserQuery(messageIndex);
    
    // Convert sources to SourceSnapshot format
    const sources: SourceSnapshot[] = (message.sources || []).map((source, idx) => {
      if (typeof source === 'string') {
        return { label: source, index: idx + 1 };
      }
      const s = source as SourceMetadata;
      return {
        index: s.index ?? idx + 1,
        type: s.type ?? s.source_type ?? s.source,
        label: s.label ?? s.title ?? s.source,
        url: s.url ?? s.source_url,
        page: s.page,
        section: s.section,
      };
    });
    
    await submitFeedback({
      messageId,
      rating,
      queryText,
      answerPreview: message.content.slice(0, 500),
      sources,
      feedbackText,
    });
  }, [messages, getPreviousUserQuery, submitFeedback]);

  // Smooth scroll to bottom when new messages arrive or thinking status changes
  useEffect(() => {
    messagesEndRef.current?.scrollIntoView({ behavior: "smooth" });
  }, [messages.length, isTyping, streamingMessage, thinkingStatus]);

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
            {messages.map((message, index) => {
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
              
              // Get the previous user query for feedback context
              const previousUserQuery = message.role === 'assistant' 
                ? getPreviousUserQuery(index) 
                : undefined;
              
              // Regular message bubble with feedback support
              return (
                <MessageBubble
                  key={message.id}
                  message={{
                    ...message,
                    timestamp: message.created_at,
                  }}
                  previousUserQuery={previousUserQuery}
                  feedbackRating={feedbackState[message.id]}
                  onFeedbackSubmit={handleFeedbackSubmit}
                  isFeedbackSubmitting={isFeedbackSubmitting}
                />
              );
            })}

            {/* Thinking indicator - shows RAG pipeline progress */}
            {isTyping && thinkingStatus && !streamingMessage && (
              <ThinkingIndicator status={thinkingStatus} />
            )}
            
            {/* Fallback typing indicator (bouncing dots) when no status */}
            {isTyping && !thinkingStatus && !streamingMessage && (
              <TypingIndicator />
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
