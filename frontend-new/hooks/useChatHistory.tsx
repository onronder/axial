'use client';

import { createContext, useContext, useCallback, ReactNode, useEffect, useRef } from 'react';
import { useQuery, useMutation, useQueryClient, QueryClient } from '@tanstack/react-query';
import { api } from '@/lib/api';
import { useToast } from '@/hooks/use-toast';
import { useUsage } from "@/hooks/useUsage";
import { Source, ScopeContext, ScopeCandidate } from '@/types';

// =============================================================================
// QUERY KEY FACTORY
// =============================================================================

/**
 * Query key factory for chat-related queries.
 * Provides type-safe, hierarchical query keys for React Query caching.
 *
 * Usage:
 * - chatKeys.all: Base key for all chat queries (for mass invalidation)
 * - chatKeys.lists(): Key for conversation lists
 * - chatKeys.list(filter): Key for filtered conversation lists
 * - chatKeys.messages(): Base key for all message queries
 * - chatKeys.message(id): Key for a specific conversation's messages
 */
export const chatKeys = {
    all: ['chat'] as const,
    lists: () => [...chatKeys.all, 'list'] as const,
    list: (filter?: string) => [...chatKeys.lists(), filter] as const,
    messages: () => [...chatKeys.all, 'messages'] as const,
    message: (conversationId: string) => [...chatKeys.messages(), conversationId] as const,
};

export interface Message {
    id: string;
    role: 'user' | 'assistant' | 'system' | 'clarification';
    content: string;
    sources?: Array<Source | string | Record<string, unknown>>;
    created_at: string;
    /** Scope context when response is from a specific scope */
    scope_context?: ScopeContext;
    /** Clarification candidates when role is 'clarification' */
    candidates?: ScopeCandidate[];
    /** Original query for clarification messages */
    original_query?: string;
}

export interface ChatConversation {
    id: string;
    title: string;
    created_at: string;
    updated_at: string;
}

export interface GroupedConversation {
    label: string;
    conversations: ChatConversation[];
}

type ApiError = {
    response?: {
        data?: {
            detail?: string;
        };
    };
};

const getErrorDetail = (error: unknown, fallback: string): string => {
    const apiError = error as ApiError;
    return apiError.response?.data?.detail || fallback;
};

interface ChatHistoryContextType {
    conversations: ChatConversation[];
    isLoading: boolean;
    createNewChat: (title?: string) => Promise<string>;
    deleteChat: (id: string) => Promise<void>;
    renameChat: (id: string, title: string) => Promise<void>;
    getMessagesById: (conversationId: string) => Promise<Message[]>;
    refresh: () => void;
}

const ChatHistoryContext = createContext<ChatHistoryContextType | null>(null);

// Query key for chat history (kept for backward compatibility, uses chatKeys factory)
export const CHAT_HISTORY_KEY = chatKeys.lists();

/**
 * Fetch conversations from API.
 */
export async function fetchConversations(signal?: AbortSignal): Promise<ChatConversation[]> {
    const { data } = await api.get('/conversations', { signal });
    return data || [];
}

/**
 * Provider component with React Query integration.
 * Provides automatic caching, deduplication, and background refetching.
 */
export function ChatHistoryProvider({ children }: { children: ReactNode }) {
    const { toast } = useToast();
    const queryClient = useQueryClient();
    const { plan } = useUsage();
    const normalizedPlan = typeof plan === "string" ? plan.toLowerCase() : null;
    const planReady = normalizedPlan !== null;
    const hasChatAccess = planReady && normalizedPlan !== "free" && normalizedPlan !== "none";
    const previousAccess = useRef(hasChatAccess);

    // Main query for fetching conversations
    const {
        data: conversations = [],
        isLoading: queryLoading,
        refetch
    } = useQuery({
        queryKey: CHAT_HISTORY_KEY,
        queryFn: ({ signal }) => fetchConversations(signal),
        enabled: hasChatAccess,
        staleTime: 5 * 60 * 1000, // 5 minutes
        gcTime: 10 * 60 * 1000,   // 10 minutes cache
    });
    const isLoading = planReady ? (hasChatAccess ? queryLoading : false) : true;

    useEffect(() => {
        if (hasChatAccess && !previousAccess.current) {
            refetch();
        }
        previousAccess.current = hasChatAccess;
    }, [hasChatAccess, refetch]);

    const denyChatAccess = useCallback(() => {
        toast({
            title: "Subscription required",
            description: "Upgrade your plan to access chat history.",
            variant: "destructive",
        });
    }, [toast]);

    // Create chat mutation
    const createMutation = useMutation({
        mutationFn: async (title: string) => {
            const { data } = await api.post('/conversations', { title });
            return data;
        },
        onSuccess: (newChat) => {
            // Optimistically add to cache
            queryClient.setQueryData<ChatConversation[]>(CHAT_HISTORY_KEY, (old) =>
                [newChat, ...(old || [])]
            );
        },
        onError: (error: unknown) => {
            toast({
                title: 'Error',
                description: getErrorDetail(error, 'Failed to create new chat.'),
                variant: 'destructive',
            });
        },
    });

    // Delete chat mutation
    const deleteMutation = useMutation({
        mutationFn: async (id: string) => {
            await api.delete(`/conversations/${id}`);
            return id;
        },
        onMutate: async (deletedId) => {
            await queryClient.cancelQueries({ queryKey: CHAT_HISTORY_KEY });
            const previous = queryClient.getQueryData<ChatConversation[]>(CHAT_HISTORY_KEY);
            queryClient.setQueryData<ChatConversation[]>(CHAT_HISTORY_KEY, (old) =>
                old?.filter((c) => c.id !== deletedId) ?? []
            );
            return { previous };
        },
        onSuccess: () => {
            toast({
                title: 'Chat deleted',
                description: 'The conversation has been removed.',
            });
        },
        onError: (error: unknown, _id, context) => {
            if (context?.previous) {
                queryClient.setQueryData(CHAT_HISTORY_KEY, context.previous);
            }
            toast({
                title: 'Error',
                description: getErrorDetail(error, 'Failed to delete chat.'),
                variant: 'destructive',
            });
        },
    });

    // Rename chat mutation
    const renameMutation = useMutation({
        mutationFn: async ({ id, title }: { id: string; title: string }) => {
            const { data } = await api.patch(`/conversations/${id}`, { title });
            return data;
        },
        onSuccess: (updatedChat) => {
            queryClient.setQueryData<ChatConversation[]>(CHAT_HISTORY_KEY, (old) =>
                old?.map((c) => (c.id === updatedChat.id ? updatedChat : c)) ?? []
            );
            toast({
                title: 'Chat renamed',
                description: 'The conversation has been updated.',
            });
        },
        onError: (error: unknown) => {
            toast({
                title: 'Error',
                description: getErrorDetail(error, 'Failed to rename chat.'),
                variant: 'destructive',
            });
        },
    });

    // Get messages (uses separate query per conversation)
    const getMessagesById = useCallback(async (conversationId: string): Promise<Message[]> => {
        if (!planReady || !hasChatAccess) {
            return [];
        }
        try {
            const { data } = await api.get(`/conversations/${conversationId}/messages`);
            return data;
        } catch (error) {
            if (process.env.NODE_ENV !== 'production') {
                console.error('Failed to get messages:', error);
            }
            return [];
        }
    }, [hasChatAccess, planReady]);

    // Wrapper functions for mutations
    const createNewChat = useCallback(async (title: string = 'New Chat'): Promise<string> => {
        if (!hasChatAccess) {
            denyChatAccess();
            throw new Error("Subscription required");
        }
        const result = await createMutation.mutateAsync(title);
        return result.id;
    }, [createMutation, denyChatAccess, hasChatAccess]);

    const deleteChat = useCallback(async (id: string): Promise<void> => {
        if (!hasChatAccess) {
            denyChatAccess();
            return;
        }
        await deleteMutation.mutateAsync(id);
    }, [deleteMutation, denyChatAccess, hasChatAccess]);

    const renameChat = useCallback(async (id: string, title: string): Promise<void> => {
        if (!hasChatAccess) {
            denyChatAccess();
            return;
        }
        await renameMutation.mutateAsync({ id, title });
    }, [renameMutation, denyChatAccess, hasChatAccess]);

    const value: ChatHistoryContextType = {
        conversations: hasChatAccess ? conversations : [],
        isLoading,
        createNewChat,
        deleteChat,
        renameChat,
        getMessagesById,
        refresh: () => {
            if (!hasChatAccess) {
                return;
            }
            refetch();
        },
    };

    return (
        <ChatHistoryContext.Provider value={value}>
            {children}
        </ChatHistoryContext.Provider>
    );
}

/**
 * Hook for accessing chat history from anywhere in the app.
 * All consumers share the same cached state.
 */
export const useChatHistory = (): ChatHistoryContextType => {
    const context = useContext(ChatHistoryContext);
    if (!context) {
        throw new Error('useChatHistory must be used within a ChatHistoryProvider');
    }
    return context;
};

// =============================================================================
// MESSAGE CACHING HOOKS
// =============================================================================

/**
 * Helper hook to check chat access (extracted for reuse)
 */
export function useChatAccessCheck() {
    const { plan } = useUsage();
    const normalizedPlan = typeof plan === "string" ? plan.toLowerCase() : null;
    const planReady = normalizedPlan !== null;
    const hasChatAccess = planReady && normalizedPlan !== "free" && normalizedPlan !== "none";
    return { hasChatAccess, planReady };
}

/**
 * Fetch messages for a specific conversation.
 * Uses React Query for caching and automatic background refetching.
 *
 * @param conversationId - The conversation ID to fetch messages for (null to disable)
 * @returns Query result with messages, loading state, and error handling
 *
 * Cache behavior:
 * - staleTime: 2 minutes (messages shown as fresh)
 * - gcTime: 10 minutes (cached messages kept in memory)
 */
export function useConversationMessages(conversationId: string | null) {
    const { hasChatAccess, planReady } = useChatAccessCheck();

    return useQuery({
        queryKey: chatKeys.message(conversationId || ''),
        queryFn: async () => {
            const { data } = await api.get(`/conversations/${conversationId}/messages`);
            return (data as Message[]) || [];
        },
        enabled: !!conversationId && hasChatAccess && planReady,
        staleTime: 2 * 60 * 1000, // 2 minutes
        gcTime: 10 * 60 * 1000,   // 10 minutes
    });
}

/**
 * Hook for invalidating message cache.
 * Call this after sending a new message to ensure fresh data.
 *
 * @returns Function to invalidate messages for a specific conversation
 */
export function useInvalidateMessages() {
    const queryClient = useQueryClient();
    return useCallback((conversationId: string) => {
        queryClient.invalidateQueries({ queryKey: chatKeys.message(conversationId) });
    }, [queryClient]);
}

/**
 * Hook for optimistically updating message cache.
 * Used to add new messages to cache before server confirmation.
 *
 * @returns Function to add a message to the cache
 */
export function useOptimisticMessageUpdate() {
    const queryClient = useQueryClient();

    return useCallback((conversationId: string, newMessage: Message) => {
        queryClient.setQueryData<Message[]>(
            chatKeys.message(conversationId),
            (old) => [...(old || []), newMessage]
        );
    }, [queryClient]);
}

/**
 * Prefetch messages for a conversation.
 * Useful for prefetching when hovering over conversation items.
 *
 * @param queryClient - The query client instance
 * @param conversationId - The conversation ID to prefetch
 */
export async function prefetchConversationMessages(
    queryClient: QueryClient,
    conversationId: string
) {
    await queryClient.prefetchQuery({
        queryKey: chatKeys.message(conversationId),
        queryFn: async () => {
            const { data } = await api.get(`/conversations/${conversationId}/messages`);
            return (data as Message[]) || [];
        },
        staleTime: 2 * 60 * 1000,
    });
}

/**
 * Group conversations by date for sidebar display.
 */
export const groupConversationsByDate = (conversations: ChatConversation[]): GroupedConversation[] => {
    const now = new Date();
    const today = new Date(now.getFullYear(), now.getMonth(), now.getDate());
    const yesterday = new Date(today.getTime() - 24 * 60 * 60 * 1000);
    const lastWeek = new Date(today.getTime() - 7 * 24 * 60 * 60 * 1000);

    const groups: GroupedConversation[] = [
        { label: 'Today', conversations: [] },
        { label: 'Yesterday', conversations: [] },
        { label: 'Previous 7 Days', conversations: [] },
        { label: 'Older', conversations: [] },
    ];

    conversations.forEach(conv => {
        const date = new Date(conv.updated_at);

        if (date >= today) {
            groups[0].conversations.push(conv);
        } else if (date >= yesterday) {
            groups[1].conversations.push(conv);
        } else if (date >= lastWeek) {
            groups[2].conversations.push(conv);
        } else {
            groups[3].conversations.push(conv);
        }
    });

    return groups.filter(g => g.conversations.length > 0);
};
