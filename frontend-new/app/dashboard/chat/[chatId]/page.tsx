"use client";

import { useState, useEffect, useCallback, useRef } from "react";
import { useParams, useRouter } from "next/navigation";
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
 * IMPORTANT: Conversation ID is managed via component state, NOT derived from URL params.
 * This prevents the bug where window.history.replaceState doesn't update Next.js routing state,
 * which would cause each message to create a new conversation.
 * 
 * State Flow:
 * 1. Initial load: activeConversationId synced from URL params
 * 2. New chat created: activeConversationId updated in state, URL updated for bookmarking
 * 3. Navigation: activeConversationId synced when chatId param changes
 */
export default function ChatPage() {
    const params = useParams();
    const router = useRouter();
    const chatIdFromUrl = params.chatId as string;
    const isNewChatUrl = chatIdFromUrl === "new";

    const { getMessagesById, createNewChat } = useChatHistory();
    const { isEmpty: hasNoDocuments, isLoading: docCountLoading } = useDocumentCount();
    const { profile, isLoading: profileLoading } = useProfile();
    const { toast } = useToast();

    // ============================================================================
    // CORE FIX: Track conversation ID in state, not derived from URL
    // This prevents multiple conversations being created when URL doesn't update
    // ============================================================================
    const [activeConversationId, setActiveConversationId] = useState<string | null>(
        isNewChatUrl ? null : chatIdFromUrl
    );
    
    // Use ref to access current conversation ID in async callbacks without stale closures
    const conversationIdRef = useRef<string | null>(activeConversationId);
    useEffect(() => {
        conversationIdRef.current = activeConversationId;
    }, [activeConversationId]);

    // Track the previous URL to detect actual navigation (not just internal URL updates)
    const previousUrlRef = useRef<string>(chatIdFromUrl);

    // State
    const [messages, setMessages] = useState<Message[]>([]);
    const [isLoading, setIsLoading] = useState(!isNewChatUrl);
    const [isTyping, setIsTyping] = useState(false);
    const [streamingMessage, setStreamingMessage] = useState<string | null>(null);
    const [showOnboarding, setShowOnboarding] = useState(false);
    const [selectedModel, setSelectedModel] = useState<ModelId>('fast');
    
    // Universal Context state
    const [isResending, setIsResending] = useState(false);
    const [currentScopeId, setCurrentScopeId] = useState<string | null>(null);

    // ============================================================================
    // Sync conversation ID when URL changes (navigation between chats)
    // This handles: clicking sidebar items, browser back/forward, direct URL access
    // 
    // IMPORTANT: Only sync when URL actually changes from external navigation,
    // not when we internally update the URL after creating a conversation.
    // ============================================================================
    useEffect(() => {
        const urlChanged = chatIdFromUrl !== previousUrlRef.current;
        const previousUrl = previousUrlRef.current;
        previousUrlRef.current = chatIdFromUrl;

        // Only sync state from URL if the URL actually changed (external navigation)
        if (!urlChanged) {
            return;
        }

        console.log('🔄 [ChatPage] URL navigation detected:', {
            from: previousUrl,
            to: chatIdFromUrl,
            activeConversationId: activeConversationId?.slice(0, 8) + '...',
        });

        if (isNewChatUrl) {
            // User navigated to /new - reset for a fresh conversation
            // Only reset if we don't already have a conversation in progress
            // (handles case where URL update is delayed after conversation creation)
            if (!activeConversationId || chatIdFromUrl === 'new') {
                console.log('🔄 [ChatPage] Resetting for new chat');
                setActiveConversationId(null);
                setMessages([]);
                setCurrentScopeId(null);
            }
        } else if (chatIdFromUrl && chatIdFromUrl !== activeConversationId) {
            // User navigated to a different existing chat
            console.log('🔄 [ChatPage] Switching to conversation:', chatIdFromUrl);
            setActiveConversationId(chatIdFromUrl);
            setCurrentScopeId(null);
        }
    }, [chatIdFromUrl, isNewChatUrl, activeConversationId]);

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
        if (isNewChatUrl && hasNoDocuments && !docCountLoading && !profileLoading) {
            // Only show onboarding if user is explicitly NOT in a team
            if (!profile?.has_team) {
                setShowOnboarding(true);
            }
        }
    }, [isNewChatUrl, hasNoDocuments, docCountLoading, profileLoading, profile?.has_team]);

    // Load messages for existing chats when conversation ID changes
    useEffect(() => {
        if (!activeConversationId) {
            setMessages([]);
            setIsLoading(false);
            return;
        }

        const loadMessages = async () => {
            setIsLoading(true);
            try {
                console.log('📄 [ChatPage] Loading messages for:', activeConversationId);
                const msgs = await getMessagesById(activeConversationId);
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
    }, [activeConversationId, getMessagesById]);

    /**
     * Handle sending a message (with optional scope selection).
     * 
     * CRITICAL: Uses activeConversationId state (via ref) instead of URL params.
     * This ensures subsequent messages in the same chat use the correct conversation ID
     * even when window.history.replaceState doesn't trigger a React re-render.
     */
    const handleSendMessage = useCallback(async (content: string, scopeId?: string) => {
        // Use ref to get current conversation ID (avoids stale closure)
        let conversationId = conversationIdRef.current;

        // DEBUG: Log conversation state for troubleshooting
        console.log('💬 [ChatPage] Sending message:', {
            hasExistingConversation: !!conversationId,
            conversationId: conversationId?.slice(0, 8) + '...',
            urlChatId: chatIdFromUrl,
            isNewChatUrl,
        });

        // For new chats, create the conversation first
        if (!conversationId) {
            try {
                console.log('💬 [ChatPage] Creating NEW conversation (first message)...');
                const title = generateSmartTitle(content);
                conversationId = await createNewChat(title);
                console.log('💬 [ChatPage] Created conversation:', conversationId);

                // CRITICAL: Update state immediately so subsequent messages use this ID
                setActiveConversationId(conversationId);
                conversationIdRef.current = conversationId;

                // Update URL for bookmarking and sharing (doesn't affect routing state)
                // Using router.replace for proper Next.js integration
                router.replace(`/dashboard/chat/${conversationId}`, { scroll: false });
            } catch (error) {
                console.error('💬 [ChatPage] Failed to create chat:', error);
                toast({
                    title: 'Error',
                    description: 'Failed to create new chat. Please try again.',
                    variant: 'destructive',
                });
                return;
            }
        }

        // Add user message to UI immediately (only if not re-sending with scope)
        if (!scopeId) {
            const userMessage: Message = {
                id: `user-${Date.now()}`,
                role: "user",
                content,
                created_at: new Date().toISOString(),
            };
            setMessages(prev => [...prev, userMessage]);
        }
        
        setIsTyping(true);

        // Prepare placeholder for AI response
        const aiMessageId = `assistant-${Date.now()}`;
        let aiContent = "";
        let aiSources: Source[] = [];
        let aiScopeContext: ScopeContext | undefined;

        setStreamingMessage("");

        try {
            // Stream the response
            const resolvedScopeId =
                scopeId === '__all__' ? '__all__' : scopeId || currentScopeId || undefined;
            
            // DEBUG: Log the exact payload being sent to backend
            console.log('💬 [ChatPage] Sending chat request:', {
                conversation_id: conversationId,
                messageCount: messages.length,
                model: selectedModel,
            });
            
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
                        id: `clarification-${Date.now()}`,
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
                        id: `error-${Date.now()}`,
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
                id: `error-${Date.now()}`,
                role: "assistant",
                content: display.description,
                created_at: new Date().toISOString(),
            };
            setMessages(prev => [...prev, errorMessage]);
        }
    }, [createNewChat, currentScopeId, messages, router, selectedModel, toast]);

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
