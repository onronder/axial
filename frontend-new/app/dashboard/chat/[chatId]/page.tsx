"use client";

import { useState, useEffect, useCallback } from "react";
import { useParams } from "next/navigation";
import { useChatHistory, Message } from "@/hooks/useChatHistory";
import { useDocumentCount } from "@/hooks/useDocumentCount";
import { useProfile } from "@/hooks/useProfile";
import { ChatArea } from "@/components/chat/ChatArea";
import { OnboardingModal } from "@/components/onboarding/OnboardingModal";
import { Loader2 } from "lucide-react";
import { generateSmartTitle, streamChatResponse, isChatApiError } from "@/lib/chat-utils";
import { ModelId } from "@/lib/types";
import { Source, ScopeContext } from "@/types";
import { useToast } from "@/hooks/use-toast";

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
    const { toast } = useToast();

    // State
    const [messages, setMessages] = useState<Message[]>([]);
    const [isLoading, setIsLoading] = useState(!isNewChat);
    const [isTyping, setIsTyping] = useState(false);
    const [streamingMessage, setStreamingMessage] = useState<string | null>(null);
    const [showOnboarding, setShowOnboarding] = useState(false);
    const [selectedModel, setSelectedModel] = useState<ModelId>('fast'); // Default to Fast
    
    // Universal Context state
    const [isResending, setIsResending] = useState(false);
    const [currentScopeId, setCurrentScopeId] = useState<string | null>(null);

    const getChatErrorDisplay = (code?: string, fallback?: string) => {
        switch (code) {
            case 'LLM_TIMEOUT':
                return {
                    title: 'Model timeout',
                    description: 'The model took too long to respond. Please try again.',
                };
            case 'PLAN_LIMIT_EXCEEDED':
                return {
                    title: 'Plan limit reached',
                    description: 'You have reached your current plan limit. Upgrade to continue.',
                };
            case 'INTEGRATION_AUTH_FAILED':
                return {
                    title: 'Integration expired',
                    description: 'Your integration needs to be reconnected to continue.',
                };
            case 'CONNECTOR_UNAVAILABLE':
                return {
                    title: 'Service unavailable',
                    description: 'The connector is temporarily unavailable. Please retry shortly.',
                };
            default:
                return {
                    title: 'Chat error',
                    description: fallback || 'Something went wrong. Please try again.',
                };
        }
    };

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



    // Handle sending a message (with optional scope selection)
    const handleSendMessage = async (content: string, scopeId?: string) => {
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

        // Add user message to UI immediately (only if not re-sending)
        if (!scopeId) {
            const userMessage: Message = {
                id: Date.now().toString(),
                role: "user",
                content,
                created_at: new Date().toISOString(),
            };
            setMessages(prev => [...prev, userMessage]);
        }
        
        setIsTyping(true);

        // Prepare placeholder for AI response
        const aiMessageId = (Date.now() + 1).toString();
        let aiContent = "";
        let aiSources: Source[] = [];
        let aiScopeContext: ScopeContext | undefined;

        // Only set streaming message if NOT using simulateStreaming (which we are deleting)
        setStreamingMessage("");

        try {
            // Stream the response
            const resolvedScopeId =
                scopeId === '__all__' ? '__all__' : scopeId || currentScopeId || undefined;
            const generator = streamChatResponse({
                query: content,
                conversation_id: conversationId,
                history: messages.slice(-10).map(m => ({
                    role: m.role === 'clarification' ? 'system' : m.role,
                    content: m.content
                })),
                model: selectedModel,
                scope_id: resolvedScopeId,
            });

            for await (const event of generator) {
                if (event.type === 'token') {
                    aiContent += event.content;
                    setStreamingMessage(aiContent);
                } else if (event.type === 'sources') {
                    aiSources = normalizeSources(event.sources);
                } else if (event.type === 'scope_context') {
                    aiScopeContext = event.scope_context;
                    // Set sticky scope for conversation
                    if (event.scope_context.scope_id) {
                        setCurrentScopeId(event.scope_context.scope_id);
                    }
                } else if (event.type === 'clarification') {
                    // Handle HTTP 300 clarification request
                    console.log('🔍 [ChatPage] Clarification needed:', event.data.candidates.length, 'scopes');
                    setIsTyping(false);
                    setStreamingMessage(null);
                    
                    // Add clarification message to chat
                    const clarificationMessage: Message = {
                        id: (Date.now() + 1).toString(),
                        role: "clarification",
                        content: event.data.message,
                        created_at: new Date().toISOString(),
                        candidates: event.data.candidates,
                        original_query: content,
                    };
                    setMessages(prev => [...prev, clarificationMessage]);
                    return; // Exit early - don't add assistant message
                } else if (event.type === 'error') {
                    const display = getChatErrorDisplay(event.error, event.message);
                    toast({
                        title: display.title,
                        description: display.description,
                        variant: 'destructive',
                    });
                    setIsTyping(false);
                    setStreamingMessage(null);
                    const errorMessage: Message = {
                        id: (Date.now() + 1).toString(),
                        role: "assistant",
                        content: display.description,
                        created_at: new Date().toISOString(),
                    };
                    setMessages(prev => [...prev, errorMessage]);
                    return;
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
                sources: aiSources,
                scope_context: aiScopeContext,
            };
            setMessages(prev => [...prev, aiMessage]);

        } catch (error) {
            console.error('💬 [ChatPage] Chat API error:', error);
            setIsTyping(false);
            setStreamingMessage(null);

            const display = isChatApiError(error)
                ? getChatErrorDisplay(error.code, error.message)
                : getChatErrorDisplay(undefined, error instanceof Error ? error.message : undefined);

            toast({
                title: display.title,
                description: display.description,
                variant: 'destructive',
            });

            const errorMessage: Message = {
                id: (Date.now() + 1).toString(),
                role: "assistant",
                content: display.description,
                created_at: new Date().toISOString(),
            };
            setMessages(prev => [...prev, errorMessage]);
        }
    };

    /**
     * Handle scope selection from clarification card.
     * Re-sends the original query with the selected scope.
     */
    const handleSelectScope = useCallback(async (scopeId: string, originalQuery: string) => {
        console.log('🎯 [ChatPage] Scope selected:', scopeId);
        setIsResending(true);
        
        // Remove the clarification message from the UI
        setMessages(prev => prev.filter(m => m.role !== 'clarification'));
        
        // Handle "search all" option
        const effectiveScopeId = scopeId === '__all__' ? '__all__' : scopeId;
        
        // Set sticky scope
        if (scopeId === '__all__') {
            setCurrentScopeId(null);
        } else if (effectiveScopeId) {
            setCurrentScopeId(effectiveScopeId);
        }
        
        try {
            // Re-send the query with the selected scope
            await handleSendMessage(originalQuery, effectiveScopeId);
        } finally {
            setIsResending(false);
        }
    }, [handleSendMessage]);

    // Loading state for existing chats
    if (isLoading) {
        return (
            <div className="flex h-full items-center justify-center">
                <Loader2 className="h-8 w-8 animate-spin text-primary" />
            </div>
        );
    }

    const isDisabled = isTyping || streamingMessage !== null || isResending;

    return (
        <div className="flex h-full flex-col">
            <ChatArea
                messages={messages}
                onSendMessage={handleSendMessage}
                onSelectScope={handleSelectScope}
                isTyping={isTyping}
                streamingMessage={streamingMessage}
                disabled={isDisabled}
                selectedModel={selectedModel}
                onModelSelect={setSelectedModel}
                isResending={isResending}
            />

            {/* Onboarding Modal for new users */}
            <OnboardingModal
                open={showOnboarding}
                onOpenChange={setShowOnboarding}
            />
        </div>
    );
}
