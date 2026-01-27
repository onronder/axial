'use client';

import { createContext, useContext, useCallback, ReactNode, useEffect, useRef } from 'react';
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import { api } from '@/lib/api';
import { useToast } from '@/hooks/use-toast';
import { useUsage } from "@/hooks/useUsage";
import { Source, ScopeContext, ScopeCandidate } from '@/types';

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

// Query key for chat history
export const CHAT_HISTORY_KEY = ['chatHistory'] as const;

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
            console.error('Failed to get messages:', error);
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
