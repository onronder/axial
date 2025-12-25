"use client";

import { useState, useEffect, useCallback } from "react";
import { useParams, useRouter } from "next/navigation";
import { useChatHistory, Message } from "@/hooks/useChatHistory";
import { useDocumentCount } from "@/hooks/useDocumentCount";
import { MessageBubble } from "@/components/chat/MessageBubble";
import { ChatInput } from "@/components/chat/ChatInput";
import { EmptyState } from "@/components/chat/EmptyState";
import { OnboardingModal } from "@/components/onboarding/OnboardingModal";
import { AxioLogo } from "@/components/branding/AxioLogo";
import { Loader2 } from "lucide-react";
import { api } from "@/lib/api";
import { generateSmartTitle } from "@/lib/chat-utils";

/**
 * Unified ChatPage handles both:
 * - /dashboard/chat/new → New chat with empty state
 * - /dashboard/chat/[id] → Existing chat with loaded messages
 * 
 * URL is the single source of truth for which chat is active.
 */
export default function ChatPage() {
    const router = useRouter();
    const params = useParams();
    const chatId = params.chatId as string;
    const isNewChat = chatId === "new";

    const { getMessagesById, createNewChat } = useChatHistory();
    const { isEmpty: hasNoDocuments, isLoading: docCountLoading } = useDocumentCount();

    // State
    const [messages, setMessages] = useState<Message[]>([]);
    const [isLoading, setIsLoading] = useState(!isNewChat);
    const [isTyping, setIsTyping] = useState(false);
    const [streamingMessage, setStreamingMessage] = useState<string | null>(null);
    const [showOnboarding, setShowOnboarding] = useState(false);

    // Show onboarding modal when user has no documents and this is a new chat
    useEffect(() => {
        if (isNewChat && hasNoDocuments && !docCountLoading) {
            setShowOnboarding(true);
        }
    }, [isNewChat, hasNoDocuments, docCountLoading]);

    // Load messages for existing chats
    useEffect(() => {
        if (isNewChat) {
            setMessages([]);
            setIsLoading(false);
            return;
        }

        const loadMessages = async () => {
            setIsLoading(true);
            try {
                console.log('📄 [ChatPage] Loading messages for:', chatId);
                const msgs = await getMessagesById(chatId);
                console.log('📄 [ChatPage] Loaded', msgs.length, 'messages');
                setMessages(msgs);
            } catch (error) {
                console.error('📄 [ChatPage] Failed to load messages:', error);
                setMessages([]);
            } finally {
                setIsLoading(false);
            }
        };

        loadMessages();
    }, [chatId, isNewChat, getMessagesById]);

    // Simulate streaming for visual effect
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

    // Handle sending a message
    const handleSendMessage = async (content: string) => {
        let conversationId = isNewChat ? null : chatId;

        // For new chats, create the conversation first
        if (!conversationId) {
            try {
                console.log('💬 [ChatPage] Creating new chat...');
                const title = generateSmartTitle(content);
                conversationId = await createNewChat(title);
                console.log('💬 [ChatPage] Created chat:', conversationId);

                // Navigate to the new chat URL (this won't remount, just update URL)
                router.replace(`/dashboard/chat/${conversationId}`);
            } catch (error) {
                console.error('💬 [ChatPage] Failed to create chat:', error);
                return;
            }
        }

        // Add user message to UI immediately
        const userMessage: Message = {
            id: Date.now().toString(),
            role: "user",
            content,
            created_at: new Date().toISOString(),
        };
        setMessages(prev => [...prev, userMessage]);
        setIsTyping(true);

        try {
            // Call chat API
            const { data } = await api.post('/chat', {
                query: content,
                conversation_id: conversationId,
                history: messages.slice(-10).map(m => ({
                    role: m.role,
                    content: m.content
                }))
            });

            setIsTyping(false);

            // Stream the response
            await simulateStreaming(data.answer);

            // Add AI message
            const aiMessage: Message = {
                id: data.message_id || (Date.now() + 1).toString(),
                role: "assistant",
                content: data.answer,
                created_at: new Date().toISOString(),
                sources: data.sources,
            };

            setStreamingMessage(null);
            setMessages(prev => [...prev, aiMessage]);

        } catch (error) {
            console.error('💬 [ChatPage] Chat API error:', error);
            setIsTyping(false);
            setStreamingMessage(null);

            const errorMessage: Message = {
                id: (Date.now() + 1).toString(),
                role: "assistant",
                content: "Sorry, I encountered an error. Please try again.",
                created_at: new Date().toISOString(),
            };
            setMessages(prev => [...prev, errorMessage]);
        }
    };

    // Loading state for existing chats
    if (isLoading) {
        return (
            <div className="flex h-full items-center justify-center">
                <Loader2 className="h-8 w-8 animate-spin text-primary" />
            </div>
        );
    }

    const isDisabled = isTyping || streamingMessage !== null;

    return (
        <div className="flex h-full flex-col">
            <div className="flex-1 overflow-y-auto">
                {messages.length === 0 && !isTyping && !streamingMessage ? (
                    <EmptyState onQuerySelect={handleSendMessage} />
                ) : (
                    <div className="mx-auto max-w-3xl px-4 py-8 space-y-6">
                        {messages.map((message) => (
                            <MessageBubble
                                key={message.id}
                                message={{
                                    ...message,
                                    timestamp: message.created_at
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
                    </div>
                )}
            </div>
            <ChatInput onSend={handleSendMessage} disabled={isDisabled} />

            {/* Onboarding Modal for new users */}
            <OnboardingModal
                open={showOnboarding}
                onOpenChange={setShowOnboarding}
            />
        </div>
    );
}
