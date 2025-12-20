'use client';

import { useState, useEffect, useCallback, useRef } from 'react';
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

/**
 * Hook for managing chat conversations and messages.
 * Connects to real backend API endpoints.
 */
export const useChatHistory = () => {
    const { toast } = useToast();
    const [conversations, setConversations] = useState<ChatConversation[]>([]);
    const [isLoading, setIsLoading] = useState(true);
    const hasFetched = useRef(false);

    /**
     * Fetch all conversations for the current user
     */
    const fetchConversations = useCallback(async () => {
        console.log('💬 [useChatHistory] Fetching conversations...');
        setIsLoading(true);
        try {
            const { data } = await api.get('/api/v1/conversations');
            console.log('💬 [useChatHistory] ✅ Got', data?.length || 0, 'conversations');
            setConversations(data);
        } catch (error: any) {
            console.error('💬 [useChatHistory] ❌ Fetch failed:', error.message);
        } finally {
            setIsLoading(false);
        }
    }, []);

    // Only fetch once on mount
    useEffect(() => {
        if (!hasFetched.current) {
            hasFetched.current = true;
            fetchConversations();
        }
    }, [fetchConversations]);

    /**
     * Create a new conversation
     */
    const createNewChat = async (title: string = 'New Chat'): Promise<string> => {
        console.log('💬 [useChatHistory] Creating chat:', title);
        try {
            const { data } = await api.post('/api/v1/conversations', { title });
            console.log('💬 [useChatHistory] ✅ Created:', data.id);
            setConversations(prev => [data, ...prev]);
            return data.id;
        } catch (error: any) {
            console.error('💬 [useChatHistory] ❌ Create failed:', error.message);
            toast({
                title: 'Error',
                description: error.response?.data?.detail || 'Failed to create new chat.',
                variant: 'destructive',
            });
            throw error;
        }
    };

    /**
     * Delete a conversation
     */
    const deleteChat = async (id: string): Promise<void> => {
        console.log('💬 [useChatHistory] Deleting chat:', id);
        try {
            await api.delete(`/api/v1/conversations/${id}`);
            console.log('💬 [useChatHistory] ✅ Deleted');
            setConversations(prev => prev.filter(c => c.id !== id));
            toast({
                title: 'Chat deleted',
                description: 'The conversation has been removed.',
            });
        } catch (error: any) {
            console.error('💬 [useChatHistory] ❌ Delete failed:', error.message);
            toast({
                title: 'Error',
                description: error.response?.data?.detail || 'Failed to delete chat.',
                variant: 'destructive',
            });
        }
    };

    /**
     * Rename a conversation
     */
    const renameChat = async (id: string, title: string): Promise<void> => {
        console.log('💬 [useChatHistory] Renaming chat:', id);
        try {
            const { data } = await api.patch(`/api/v1/conversations/${id}`, { title });
            console.log('💬 [useChatHistory] ✅ Renamed');
            setConversations(prev =>
                prev.map(c => (c.id === id ? { ...c, title: data.title } : c))
            );
        } catch (error: any) {
            console.error('💬 [useChatHistory] ❌ Rename failed:', error.message);
            toast({
                title: 'Error',
                description: error.response?.data?.detail || 'Failed to rename chat.',
                variant: 'destructive',
            });
        }
    };

    /**
     * Get messages for a specific conversation
     */
    const getMessagesById = async (conversationId: string): Promise<Message[]> => {
        console.log('💬 [useChatHistory] Getting messages for:', conversationId);
        try {
            const { data } = await api.get(`/api/v1/conversations/${conversationId}/messages`);
            console.log('💬 [useChatHistory] ✅ Got', data?.length || 0, 'messages');
            return data;
        } catch (error: any) {
            console.error('💬 [useChatHistory] ❌ Get messages failed:', error.message);
            return [];
        }
    };

    return {
        conversations,
        isLoading,
        createNewChat,
        deleteChat,
        renameChat,
        getMessagesById,
        refresh: fetchConversations,
    };
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

    // Filter out empty groups
    return groups.filter(g => g.conversations.length > 0);
};
