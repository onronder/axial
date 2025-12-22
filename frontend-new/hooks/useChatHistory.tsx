'use client';

import { createContext, useContext, useState, useEffect, useCallback, useRef, ReactNode } from 'react';
import { api } from '@/lib/api';
import { useToast } from '@/hooks/use-toast';

export interface Message {
    id: string;
    role: 'user' | 'assistant' | 'system';
    content: string;
    sources?: string[];
    created_at: string;
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

interface ChatHistoryContextType {
    conversations: ChatConversation[];
    isLoading: boolean;
    createNewChat: (title?: string) => Promise<string>;
    deleteChat: (id: string) => Promise<void>;
    renameChat: (id: string, title: string) => Promise<void>;
    getMessagesById: (conversationId: string) => Promise<Message[]>;
    refresh: () => Promise<void>;
}

const ChatHistoryContext = createContext<ChatHistoryContextType | null>(null);

/**
 * Provider component that wraps the app and provides chat history state.
 * This ensures only ONE fetch happens regardless of how many components use the hook.
 */
export function ChatHistoryProvider({ children }: { children: ReactNode }) {
    const { toast } = useToast();
    const [conversations, setConversations] = useState<ChatConversation[]>([]);
    const [isLoading, setIsLoading] = useState(true);
    const hasFetched = useRef(false);

    const fetchConversations = useCallback(async () => {
        console.log('💬 [ChatHistory] Fetching conversations...');
        setIsLoading(true);
        try {
            const { data } = await api.get('/api/v1/conversations');
            console.log('💬 [ChatHistory] ✅ Got', data?.length || 0, 'conversations');
            setConversations(data || []);
        } catch (error: any) {
            console.error('💬 [ChatHistory] ❌ Fetch failed:', error.message);
        } finally {
            setIsLoading(false);
        }
    }, []);

    // Fetch once on mount
    useEffect(() => {
        if (!hasFetched.current) {
            hasFetched.current = true;
            fetchConversations();
        }
    }, [fetchConversations]);

    const createNewChat = useCallback(async (title: string = 'New Chat'): Promise<string> => {
        console.log('💬 [ChatHistory] Creating chat:', title);
        try {
            const { data } = await api.post('/api/v1/conversations', { title });
            console.log('💬 [ChatHistory] ✅ Created:', data.id);
            setConversations(prev => [data, ...prev]);
            return data.id;
        } catch (error: any) {
            console.error('💬 [ChatHistory] ❌ Create failed:', error.message);
            toast({
                title: 'Error',
                description: error.response?.data?.detail || 'Failed to create new chat.',
                variant: 'destructive',
            });
            throw error;
        }
    }, [toast]);

    const deleteChat = useCallback(async (id: string): Promise<void> => {
        console.log('💬 [ChatHistory] Deleting chat:', id);
        try {
            await api.delete(`/api/v1/conversations/${id}`);
            console.log('💬 [ChatHistory] ✅ Deleted');
            setConversations(prev => prev.filter(c => c.id !== id));
            toast({
                title: 'Chat deleted',
                description: 'The conversation has been removed.',
            });
        } catch (error: any) {
            console.error('💬 [ChatHistory] ❌ Delete failed:', error.message);
            toast({
                title: 'Error',
                description: error.response?.data?.detail || 'Failed to delete chat.',
                variant: 'destructive',
            });
        }
    }, [toast]);

    const renameChat = useCallback(async (id: string, title: string): Promise<void> => {
        console.log('💬 [ChatHistory] Renaming chat:', id);
        try {
            const { data } = await api.patch(`/api/v1/conversations/${id}`, { title });
            console.log('💬 [ChatHistory] ✅ Renamed');
            setConversations(prev =>
                prev.map(c => (c.id === id ? { ...c, title: data.title } : c))
            );
        } catch (error: any) {
            console.error('💬 [ChatHistory] ❌ Rename failed:', error.message);
            toast({
                title: 'Error',
                description: error.response?.data?.detail || 'Failed to rename chat.',
                variant: 'destructive',
            });
        }
    }, [toast]);

    const getMessagesById = useCallback(async (conversationId: string): Promise<Message[]> => {
        console.log('💬 [ChatHistory] Getting messages for:', conversationId);
        try {
            const { data } = await api.get(`/api/v1/conversations/${conversationId}/messages`);
            console.log('💬 [ChatHistory] ✅ Got', data?.length || 0, 'messages');
            return data;
        } catch (error: any) {
            console.error('💬 [ChatHistory] ❌ Get messages failed:', error.message);
            return [];
        }
    }, []);

    const value: ChatHistoryContextType = {
        conversations,
        isLoading,
        createNewChat,
        deleteChat,
        renameChat,
        getMessagesById,
        refresh: fetchConversations,
    };

    return (
        <ChatHistoryContext.Provider value={value}>
            {children}
        </ChatHistoryContext.Provider>
    );
}

/**
 * Hook for accessing chat history from anywhere in the app.
 * All consumers share the same state - no duplicate API calls.
 */
export const useChatHistory = (): ChatHistoryContextType => {
    const context = useContext(ChatHistoryContext);
    if (!context) {
        throw new Error('useChatHistory must be used within a ChatHistoryProvider');
    }
    return context;
};

/**
 * Group conversations by date for sidebar display
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
