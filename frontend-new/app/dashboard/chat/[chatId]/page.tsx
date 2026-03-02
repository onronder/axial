
"use client";

import { useState, useEffect, useCallback, useRef, startTransition } from "react";
import { useParams, useRouter } from "next/navigation";
import { useChatHistory, Message } from "@/hooks/useChatHistory";
import { useDocumentCount } from "@/hooks/useDocumentCount";
import { useProfile } from "@/hooks/useProfile";
import { ChatArea } from "@/components/chat/ChatArea";
import { OnboardingModal } from "@/components/onboarding/OnboardingModal";

import { generateSmartTitle, streamChatResponse, isChatApiError } from "@/lib/chat-utils";
import { ModelId } from "@/lib/types";
import { Source, ScopeContext } from "@/types";
import { useToast } from "@/hooks/use-toast";
import { Spinner } from "@/components/ui/spinner";

// =============================================================================
// PRODUCTION UTILITIES
// =============================================================================

const isDev = process.env.NODE_ENV !== 'production';

/** localStorage key for persisting model preference */
const MODEL_STORAGE_KEY = 'axio-chat-model-preference';

/**
 * Get persisted model preference from localStorage.
 * Returns 'fast' as default if not set or invalid.
 */
function getPersistedModel(): ModelId {
    if (typeof window === 'undefined') return 'fast';
    try {
        const saved = localStorage.getItem(MODEL_STORAGE_KEY);
        return (saved === 'fast' || saved === 'smart') ? saved as ModelId : 'fast';
    } catch {
        return 'fast';
    }
}

/**
 * Save model preference to localStorage.
 */
function persistModel(model: ModelId): void {
    if (typeof window === 'undefined') return;
    try {
        localStorage.setItem(MODEL_STORAGE_KEY, model);
    } catch {
        // localStorage unavailable (e.g. Safari private browsing) - silently ignore
    }
}

/** Conditional logging - only logs in development */
const devLog = (...args: Parameters<typeof console.log>) => {
    if (isDev) console.log(...args);
};

const devError = (...args: Parameters<typeof console.error>) => {
    if (isDev) console.error(...args);
};

/**
 * RAG Processing Status - tracks what the system is doing
 */
export interface ThinkingStatus {
    step: 'searching' | 'analyzing' | 'found' | 'generating' | 'complete';
    message: string;
    details?: {
        sourceCount?: number;
        scopeName?: string;
    };
}

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
    
    // FIX: Track if we just created a conversation to skip unnecessary reload
    const justCreatedConversationRef = useRef(false);
    
    // CRITICAL FIX: Track conversation ID that needs URL update AFTER streaming completes
    // This prevents component remount/state reset during the critical streaming phase
    const pendingUrlUpdateRef = useRef<string | null>(null);
    
    // P0 FIX: AbortController for cancelling concurrent streams
    // When user sends new message, cancel any in-flight stream to prevent duplicates
    const abortControllerRef = useRef<AbortController | null>(null);
    
    // P0 FIX: Track if component is mounted to prevent state updates after unmount
    const isMountedRef = useRef(true);
    
    // P1 FIX: Keep latest messages in ref for accurate history in async callbacks
    const messagesRef = useRef<Message[]>([]);
    
    // P2 FIX: Lock to prevent rapid double-sends (set immediately, before async work)
    const isSendLockedRef = useRef(false);

    // State
    const [messages, setMessages] = useState<Message[]>([]);
    const [isLoading, setIsLoading] = useState(!isNewChatUrl);
    const [isTyping, setIsTyping] = useState(false);
    const [streamingMessage, setStreamingMessage] = useState<string | null>(null);
    const [showOnboarding, setShowOnboarding] = useState(false);
    // Initialize model from localStorage for persistence across sessions
    const [selectedModel, setSelectedModel] = useState<ModelId>(() => getPersistedModel());
    
    // RAG thinking status - shows what the system is doing
    const [thinkingStatus, setThinkingStatus] = useState<ThinkingStatus | null>(null);
    
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

        // FIX: Skip sync if we just created this conversation ourselves
        // This prevents race condition where URL update triggers before state update
        if (justCreatedConversationRef.current) {
            devLog('🔄 [ChatPage] Skipping sync - we just created this conversation');
            // Don't reset the flag here - let loadMessages effect handle it
            return;
        }

        devLog('🔄 [ChatPage] URL navigation detected:', {
            from: previousUrl,
            to: chatIdFromUrl,
            activeConversationId: activeConversationId?.slice(0, 8) + '...',
        });

        if (isNewChatUrl) {
            // User navigated to /new - reset for a fresh conversation
            // Only reset if we don't already have a conversation in progress
            // (handles case where URL update is delayed after conversation creation)
            if (!activeConversationId || chatIdFromUrl === 'new') {
                devLog('🔄 [ChatPage] Resetting for new chat');
                setActiveConversationId(null);
                setMessages([]);
                setCurrentScopeId(null);
                setThinkingStatus(null);
            }
        } else if (chatIdFromUrl && chatIdFromUrl !== activeConversationId) {
            // User navigated to a different existing chat
            devLog('🔄 [ChatPage] Switching to conversation:', chatIdFromUrl);
            setActiveConversationId(chatIdFromUrl);
            setCurrentScopeId(null);
            setThinkingStatus(null);
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
        return rawSources.filter(entry => entry != null).map((entry, idx) => {
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

    // P0 FIX: Cleanup on component unmount - cancel any in-flight streams
    useEffect(() => {
        isMountedRef.current = true;
        
        return () => {
            isMountedRef.current = false;
            // Cancel any in-flight stream on unmount
            if (abortControllerRef.current) {
                devLog('🧹 [ChatPage] Cleaning up - aborting stream on unmount');
                abortControllerRef.current.abort();
                abortControllerRef.current = null;
            }
            // Reset streaming state and pending refs to prevent stale fires on remount
            isStreamingRef.current = false;
            pendingUrlUpdateRef.current = null;
            isSendLockedRef.current = false;
        };
    }, []);
    
    // P1 FIX: Keep messages ref in sync for accurate history in async callbacks
    useEffect(() => {
        messagesRef.current = messages;
    }, [messages]);

    // Track if we're currently streaming to prevent state resets
    const isStreamingRef = useRef(false);
    
    // Ref to access getMessagesById without it being a dependency
    // This prevents the effect from re-running when hasChatAccess/planReady changes
    const getMessagesByIdRef = useRef(getMessagesById);
    useEffect(() => {
        getMessagesByIdRef.current = getMessagesById;
    }, [getMessagesById]);
    
    // Load messages for existing chats when conversation ID changes
    // CRITICAL: Only depends on activeConversationId, NOT getMessagesById
    useEffect(() => {
        // FIX: Never reset messages while actively streaming
        // Check this FIRST before anything else
        if (isStreamingRef.current) {
            devLog('📄 [ChatPage] Skipping load - streaming in progress');
            return;
        }
        
        // FIX: Skip loading if we just created this conversation - we already have correct state
        if (justCreatedConversationRef.current) {
            devLog('📄 [ChatPage] Skipping load - just created this conversation');
            justCreatedConversationRef.current = false;
            setIsLoading(false);
            return;
        }
        
        if (!activeConversationId) {
            setMessages([]);
            setIsLoading(false);
            return;
        }

        const loadMessages = async () => {
            // Double-check streaming status before actually loading
            // This handles race conditions where streaming started after effect began
            if (isStreamingRef.current) {
                devLog('📄 [ChatPage] Aborting load - streaming started');
                return;
            }
            
            setIsLoading(true);
            try {
                devLog('📄 [ChatPage] Loading messages for:', activeConversationId);
                const msgs = await getMessagesByIdRef.current(activeConversationId);
                
                // Don't set messages if streaming started during the fetch
                if (isStreamingRef.current) {
                    devLog('📄 [ChatPage] Discarding loaded messages - streaming in progress');
                    return;
                }
                
                devLog('📄 [ChatPage] Loaded', msgs.length, 'messages');
                setMessages(msgs);
            } catch (error) {
                devError('📄 [ChatPage] Failed to load messages:', error);
                if (!isStreamingRef.current) {
                    setMessages([]);
                }
            } finally {
                if (!isStreamingRef.current) {
                    setIsLoading(false);
                }
            }
        };

        loadMessages();
    }, [activeConversationId]); // ONLY activeConversationId - not getMessagesById!

    /**
     * Handle model selection with localStorage persistence.
     * Persists the choice so it survives page refreshes and new chat sessions.
     */
    const handleModelSelect = useCallback((model: ModelId) => {
        setSelectedModel(model);
        persistModel(model);
    }, []);

    /**
     * Helper: Update URL after streaming completes (if needed)
     * This is deferred to prevent component remount during streaming
     */
    const flushPendingUrlUpdate = useCallback(() => {
        const pendingId = pendingUrlUpdateRef.current;
        if (pendingId && chatIdFromUrl === 'new') {
            devLog('🔗 [ChatPage] Updating URL to:', pendingId);
            pendingUrlUpdateRef.current = null;
            // Now it's safe to update the URL - streaming is complete, state is stable
            router.replace(`/dashboard/chat/${pendingId}`, { scroll: false });
        }
    }, [chatIdFromUrl, router]);

    /**
     * Handle sending a message (with optional scope selection).
     * 
     * CRITICAL: Uses activeConversationId state (via ref) instead of URL params.
     * This ensures subsequent messages in the same chat use the correct conversation ID
     * even when window.history.replaceState doesn't trigger a React re-render.
     * 
     * P0 FIXES:
     * - AbortController to cancel concurrent streams
     * - Check isMounted before state updates
     * 
     * P1 FIXES:
     * - Use messagesRef for accurate history (avoids stale closure)
     * - Handle 'done' event with message_id
     */
    const handleSendMessage = useCallback(async (content: string, scopeId?: string) => {
        // P2 FIX: Prevent rapid double-sends
        // This check happens BEFORE any async work
        if (isSendLockedRef.current) {
            devLog('🔒 [ChatPage] Send locked - ignoring duplicate send');
            return;
        }
        isSendLockedRef.current = true;
        
        // P0 FIX: Cancel any in-flight stream before starting a new one
        // This prevents duplicate/interleaved responses
        if (abortControllerRef.current) {
            devLog('🛑 [ChatPage] Cancelling previous stream');
            abortControllerRef.current.abort();
        }
        
        // Create new AbortController for this stream
        const abortController = new AbortController();
        abortControllerRef.current = abortController;
        
        // CRITICAL FIX: Set streaming flag IMMEDIATELY at the start, BEFORE any state 
        // updates or navigation. This prevents the loadMessages effect from running
        // and clearing messages during a re-render triggered by router.replace().
        isStreamingRef.current = true;
        
        // Use ref to get current conversation ID (avoids stale closure)
        let conversationId = conversationIdRef.current;

        devLog('💬 [ChatPage] Sending message:', {
            hasExistingConversation: !!conversationId,
            conversationId: conversationId?.slice(0, 8) + '...',
            urlChatId: chatIdFromUrl,
            isNewChatUrl,
        });

        // For new chats, create the conversation first
        if (!conversationId) {
            try {
                devLog('💬 [ChatPage] Creating NEW conversation (first message)...');
                const title = generateSmartTitle(content);
                conversationId = await createNewChat(title);
                devLog('💬 [ChatPage] Created conversation:', conversationId);

                // P0 FIX: Check if component still mounted before state updates
                if (!isMountedRef.current) {
                    devLog('⚠️ [ChatPage] Component unmounted during conversation creation');
                    isSendLockedRef.current = false; // P2 FIX: Unlock on unmount
                    return;
                }

                // CRITICAL: Update state immediately so subsequent messages use this ID
                setActiveConversationId(conversationId);
                conversationIdRef.current = conversationId;
                
                // FIX: Mark that we just created this conversation to skip unnecessary reload
                justCreatedConversationRef.current = true;

                // CRITICAL FIX: DON'T update URL now - it causes component remount/state reset!
                // Instead, queue the URL update for AFTER streaming completes
                pendingUrlUpdateRef.current = conversationId;
                devLog('💬 [ChatPage] URL update queued for after streaming');
            } catch (error) {
                devError('💬 [ChatPage] Failed to create chat:', error);
                // Reset streaming flag on error
                isStreamingRef.current = false;
                abortControllerRef.current = null;
                isSendLockedRef.current = false; // P2 FIX: Unlock on error
                
                if (isMountedRef.current) {
                    toast({
                        title: 'Error',
                        description: 'Failed to create new chat. Please try again.',
                        variant: 'destructive',
                    });
                }
                return;
            }
        }

        // P0 FIX: Check mounted before state updates
        if (!isMountedRef.current) {
            isSendLockedRef.current = false; // P2 FIX: Unlock on unmount
            return;
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
        
        // Start thinking status - show RAG is working
        setThinkingStatus({
            step: 'searching',
            message: 'Searching knowledge base...',
        });

        // Prepare placeholder for AI response
        const aiMessageId = `assistant-${Date.now()}`;
        let aiContent = "";
        let aiSources: Source[] = [];
        let aiScopeContext: ScopeContext | undefined;
        let serverMessageId: string | undefined;

        setStreamingMessage("");

        try {
            // Stream the response
            const resolvedScopeId =
                scopeId === '__all__' ? '__all__' : scopeId || currentScopeId || undefined;
            
            // P1 FIX: Use messagesRef for accurate history (avoids stale closure)
            const currentMessages = messagesRef.current;
            
            devLog('💬 [ChatPage] Sending chat request:', {
                conversation_id: conversationId,
                messageCount: currentMessages.length,
                model: selectedModel,
            });
            
            // P0 FIX: Pass abort signal to stream for cancellation support
            const generator = streamChatResponse({
                query: content,
                conversation_id: conversationId,
                history: currentMessages.slice(-10).map(m => ({
                    role: m.role === 'clarification' ? 'system' : m.role,
                    content: m.content
                })),
                model: selectedModel,
                scope_id: resolvedScopeId,
            }, abortController.signal);

            devLog('🚀 [ChatPage] Starting stream...');
            
            for await (const event of generator) {
                // P0 FIX: Check if aborted or unmounted
                if (abortController.signal.aborted || !isMountedRef.current) {
                    devLog('🛑 [ChatPage] Stream aborted or component unmounted');
                    isStreamingRef.current = false;
                    abortControllerRef.current = null;
                    isSendLockedRef.current = false; // P2 FIX: Unlock
                    break;
                }
                
                devLog('📨 [ChatPage] Stream event:', event.type);
                
                if (event.type === 'status') {
                    // Handle status events from backend
                    const statusEvent = event as { type: 'status'; step: string; message: string; details?: Record<string, unknown> };
                    devLog('📊 [ChatPage] Status update:', statusEvent.step, statusEvent.message);
                    setThinkingStatus({
                        step: statusEvent.step as ThinkingStatus['step'],
                        message: statusEvent.message,
                        details: statusEvent.details as ThinkingStatus['details'],
                    });
                } else if (event.type === 'token') {
                    // First token received - switch from thinking to generating
                    if (!aiContent) {
                        setThinkingStatus({
                            step: 'generating',
                            message: 'Generating response...',
                        });
                    }
                    aiContent += event.content;
                    setStreamingMessage(aiContent);
                } else if (event.type === 'sources') {
                    aiSources = normalizeSources(event.sources);
                    // Update thinking status with source count
                    if (aiSources.length > 0) {
                        setThinkingStatus(prev => prev ? {
                            ...prev,
                            details: { ...prev.details, sourceCount: aiSources.length }
                        } : null);
                    }
                } else if (event.type === 'scope_context') {
                    aiScopeContext = event.scope_context;
                    // Set sticky scope for conversation
                    if (event.scope_context.scope_id) {
                        setCurrentScopeId(event.scope_context.scope_id);
                    }
                    // Update thinking status with scope name
                    if (event.scope_context.scope_name) {
                        setThinkingStatus(prev => prev ? {
                            ...prev,
                            details: { ...prev.details, scopeName: event.scope_context.scope_name }
                        } : null);
                    }
                } else if (event.type === 'done') {
                    // P1 FIX: Handle 'done' event - capture message_id if provided
                    const doneEvent = event as { type: 'done'; message_id?: string };
                    if (doneEvent.message_id) {
                        serverMessageId = doneEvent.message_id;
                        devLog('✅ [ChatPage] Received server message_id:', serverMessageId);
                    }
                } else if (event.type === 'clarification') {
                    // Handle HTTP 300 clarification request
                    devLog('🔍 [ChatPage] Clarification needed:', event.data.candidates.length, 'scopes');
                    isStreamingRef.current = false;
                    abortControllerRef.current = null;
                    
                    if (!isMountedRef.current) return;
                    
                    setIsTyping(false);
                    setStreamingMessage(null);
                    setThinkingStatus(null);
                    
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
                    
                    // Update URL now that streaming is complete
                    flushPendingUrlUpdate();
                    isSendLockedRef.current = false; // P2 FIX: Unlock on clarification
                    return; // Exit early - don't add assistant message
                } else if (event.type === 'error') {
                    const display = getChatErrorDisplay(event.error, event.message);
                    
                    isStreamingRef.current = false;
                    abortControllerRef.current = null;
                    
                    if (!isMountedRef.current) return;
                    
                    toast({
                        title: display.title,
                        description: display.description,
                        variant: 'destructive',
                    });
                    setIsTyping(false);
                    setStreamingMessage(null);
                    setThinkingStatus(null);
                    const errorMessage: Message = {
                        id: `error-${Date.now()}`,
                        role: "assistant",
                        content: display.description,
                        created_at: new Date().toISOString(),
                    };
                    setMessages(prev => [...prev, errorMessage]);
                    
                    // Update URL now that streaming is complete (even on error)
                    flushPendingUrlUpdate();
                    isSendLockedRef.current = false; // P2 FIX: Unlock on error
                    return;
                }
            }

            // Stream complete - cleanup
            isStreamingRef.current = false;
            abortControllerRef.current = null;
            
            // P0 FIX: Check mounted before final state updates
            if (!isMountedRef.current) {
                devLog('⚠️ [ChatPage] Component unmounted after stream complete');
                isSendLockedRef.current = false; // P2 FIX: Unlock on unmount
                return;
            }
            
            devLog('✅ [ChatPage] Stream complete, content length:', aiContent.length);
            setIsTyping(false);

            // Fix 3.6: Transition through 'complete' status before clearing
            setThinkingStatus({ step: 'complete', message: 'Done' });

            // Fix 4.2: Batch streaming→final transition to prevent visual jump
            const aiMessage: Message = {
                id: serverMessageId || aiMessageId,
                role: "assistant",
                content: aiContent,
                created_at: new Date().toISOString(),
                sources: aiSources,
                scope_context: aiScopeContext,
            };
            startTransition(() => {
                setStreamingMessage(null);
                setMessages(prev => [...prev, aiMessage]);
            });
            devLog('✅ [ChatPage] Final message added to state');

            // Fix 3.6: Clear thinking status after brief animation delay
            setTimeout(() => {
                if (isMountedRef.current) {
                    setThinkingStatus(null);
                }
            }, 300);
            
            // NOW it's safe to update the URL (after streaming is complete and state is stable)
            flushPendingUrlUpdate();
            
            // P2 FIX: Unlock sending
            isSendLockedRef.current = false;

        } catch (error) {
            // P0 FIX: Handle AbortError gracefully (not a real error)
            if (error instanceof Error && error.name === 'AbortError') {
                devLog('🛑 [ChatPage] Stream aborted');
                isStreamingRef.current = false;
                abortControllerRef.current = null;
                isSendLockedRef.current = false; // P2 FIX: Unlock on abort
                return;
            }
            
            devError('💬 [ChatPage] Chat API error:', error);
            isStreamingRef.current = false;
            abortControllerRef.current = null;
            
            // P0 FIX: Check mounted before state updates on error
            if (!isMountedRef.current) {
                isSendLockedRef.current = false; // P2 FIX: Unlock on unmount
                return;
            }
            
            setIsTyping(false);
            setStreamingMessage(null);
            setThinkingStatus(null);

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
            
            // Update URL now that streaming is complete (even on error)
            flushPendingUrlUpdate();
            
            // P2 FIX: Unlock sending
            isSendLockedRef.current = false;
        }
    }, [createNewChat, currentScopeId, flushPendingUrlUpdate, selectedModel, toast, chatIdFromUrl, isNewChatUrl]);

    /**
     * Handle scope selection from clarification card.
     * Re-sends the original query with the selected scope.
     */
    const handleSelectScope = useCallback(async (scopeId: string, originalQuery: string) => {
        devLog('🎯 [ChatPage] Scope selected:', scopeId);
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

    // FIX: Loading state should NOT hide the chat if we're actively streaming
    // This prevents the "kick out" bug where user sees empty screen during RAG processing
    const showLoadingSpinner = isLoading && !isTyping && streamingMessage === null && !thinkingStatus;

    if (showLoadingSpinner) {
        return (
            <div className="flex h-full items-center justify-center">
                <Spinner className="h-8 w-8 animate-spin text-primary" />
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
                onModelSelect={handleModelSelect}
                isResending={isResending}
                thinkingStatus={thinkingStatus}
                conversationId={activeConversationId || undefined}
            />

            {/* Onboarding Modal for new users */}
            <OnboardingModal
                open={showOnboarding}
                onOpenChange={setShowOnboarding}
            />
        </div>
    );
}