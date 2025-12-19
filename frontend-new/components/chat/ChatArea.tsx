"use client";

import { useState, useRef, useEffect, useCallback } from "react";
import { Message } from "@/lib/mockData";
import { MessageBubble } from "./MessageBubble";
import { ChatInput } from "./ChatInput";
import { EmptyState } from "./EmptyState";
import { AxioLogo } from "@/components/branding/AxioLogo";

interface ChatAreaProps {
  initialMessages?: Message[];
}

export function ChatArea({ initialMessages = [] }: ChatAreaProps) {
  const [messages, setMessages] = useState<Message[]>(initialMessages);
  const [isTyping, setIsTyping] = useState(false);
  const [streamingMessage, setStreamingMessage] = useState<string | null>(null);
  const messagesEndRef = useRef<HTMLDivElement>(null);

  const scrollToBottom = () => {
    messagesEndRef.current?.scrollIntoView({ behavior: "smooth" });
  };

  useEffect(() => {
    scrollToBottom();
  }, [messages, isTyping, streamingMessage]);

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
    const userMessage: Message = {
      id: Date.now().toString(),
      role: "user",
      content,
      timestamp: new Date().toISOString(),
    };

    setMessages((prev) => [...prev, userMessage]);
    setIsTyping(true);

    // Simulate thinking delay
    await new Promise((resolve) => setTimeout(resolve, 800));
    setIsTyping(false);

    const fullResponse = `I've analyzed your request: "${content.slice(0, 50)}${content.length > 50 ? "..." : ""}"

Based on the documents in your knowledge base, here's what I found:

**Key Points:**
- Your data contains relevant information that matches this query
- I've cross-referenced multiple sources for accuracy
- The analysis covers the main topics you're interested in

**Details:**
The information retrieved from your knowledge base shows several relevant connections. I've analyzed the context and can provide specific insights based on your ingested documents.

Would you like me to dive deeper into any specific aspect?`;

    // Stream the response
    await simulateStreaming(fullResponse);

    const aiMessage: Message = {
      id: (Date.now() + 1).toString(),
      role: "assistant",
      content: fullResponse,
      timestamp: new Date().toISOString(),
    };

    setStreamingMessage(null);
    setMessages((prev) => [...prev, aiMessage]);
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