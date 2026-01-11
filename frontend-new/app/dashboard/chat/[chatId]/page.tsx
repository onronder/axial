"use client";

import { useState, useEffect } from "react";
import { useParams } from "next/navigation";
import { useChatHistory, Message } from "@/hooks/useChatHistory";
import { useDocumentCount } from "@/hooks/useDocumentCount";
import { useProfile } from "@/hooks/useProfile";
import { ChatArea } from "@/components/chat/ChatArea";
import { OnboardingModal } from "@/components/onboarding/OnboardingModal";
import { Loader2 } from "lucide-react";
import { generateSmartTitle, streamChatResponse } from "@/lib/chat-utils";
import { ModelId } from "@/lib/types";
import { Source } from "@/types";

/**
 * Unified ChatPage handles both:
 * - /dashboard/chat/new → New chat with empty state
 * - /dashboard/chat/[id] → Existing chat with loaded messages
 * 
 * URL is the single source of truth for which chat is active.
 */
export default function ChatPage() {
    const params = useParams();
    const chatId = params.chatId as string;
    const isNewChat = chatId === "new";

    const { getMessagesById, createNewChat } = useChatHistory();
    const { isEmpty: hasNoDocuments, isLoading: docCountLoading } = useDocumentCount();
    const { profile, isLoading: profileLoading } = useProfile();

    // State
    const [messages, setMessages] = useState<Message[]>([]);
    const [isLoading, setIsLoading] = useState(!isNewChat);
    const [isTyping, setIsTyping] = useState(false);
    const [streamingMessage, setStreamingMessage] = useState<string | null>(null);
    const [showOnboarding, setShowOnboarding] = useState(false);
    const [selectedModel, setSelectedModel] = useState<ModelId>('fast'); // Default to Fast

    const normalizeSources = (rawSources: unknown): Source[] => {
        if (!Array.isArray(rawSources)) return [];
        return rawSources.map((entry, idx) => {
            if (typeof entry === "string") {
                return {
                    index: idx + 1,
                    type: "Source",
                    label: entry,
                };
            }
            const source = entry as Record<string, unknown>;
            return {
                index: (source.index as number) ?? idx + 1,
                type: (source.type as string) || (source.source as string) || "Source",
                label: (source.label as string)
                    || (source.title as string)
                    || (source.source as string)
                    || `Source ${idx + 1}`,
                url: (source.url as string) || (source.source_url as string),
                page: (source.page as number) || (source.page_number as number),
                section: (source.section as string) || (source.header_path as string),
            };
        });
    };

    // Show onboarding modal when user has no documents and this is a new chat
    // TASK 3: Skip if user is already in a team (e.g. invited via email)
    useEffect(() => {
        if (isNewChat && hasNoDocuments && !docCountLoading && !profileLoading) {
            // Only show onboarding if user is explicitly NOT in a team
            if (!profile?.has_team) {
                setShowOnboarding(true);
            }
        }
    }, [isNewChat, hasNoDocuments, docCountLoading, profileLoading, profile?.has_team]);

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

                // Update URL without navigation
                window.history.replaceState(null, '', `/dashboard/chat/${conversationId}`);
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

        // Prepare placeholder for AI response
        const aiMessageId = (Date.now() + 1).toString();
        let aiContent = "";
        let aiSources: Source[] = [];

        // Only set streaming message if NOT using simulateStreaming (which we are deleting)
        setStreamingMessage("");

        try {
            // Stream the response
            const generator = streamChatResponse({
                query: content,
                conversation_id: conversationId,
                history: messages.slice(-10).map(m => ({
                    role: m.role,
                    content: m.content
                })),
                model: selectedModel
            });

            for await (const event of generator) {
                if (event.type === 'token') {
                    aiContent += event.content;
                    setStreamingMessage(aiContent);
                } else if (event.type === 'sources') {
                    aiSources = normalizeSources(event.sources);
                } else if (event.type === 'error') {
                    throw new Error(event.message);
                }
            }

            // Stream complete
            setIsTyping(false);
            setStreamingMessage(null);

            // Add final AI message to state
        const aiMessage: Message = {
            id: aiMessageId,
            role: "assistant",
            content: aiContent,
            created_at: new Date().toISOString(),
            sources: aiSources
        };
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
            <ChatArea
                messages={messages}
                onSendMessage={handleSendMessage}
                isTyping={isTyping}
                streamingMessage={streamingMessage}
                disabled={isDisabled}
                selectedModel={selectedModel}
                onModelSelect={setSelectedModel}
            />

            {/* Onboarding Modal for new users */}
            <OnboardingModal
                open={showOnboarding}
                onOpenChange={setShowOnboarding}
            />
        </div>
    );
}
