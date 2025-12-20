'use client';

import { useState, useEffect, useCallback } from 'react';
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

    /**
     * Fetch all conversations for the current user
     */
    const fetchConversations = useCallback(async () => {
        setIsLoading(true);
        try {
            const { data } = await api.get('/api/v1/conversations');
            setConversations(data);
        } catch (error) {
            console.error('Failed to fetch conversations:', error);
            // Don't show toast on initial load failure - might just be empty
        } finally {
            setIsLoading(false);
        }
    }, []);

    useEffect(() => {
        fetchConversations();
    }, [fetchConversations]);

    /**
     * Create a new conversation
     */
    const createNewChat = async (title: string = 'New Chat'): Promise<string> => {
        try {
            const { data } = await api.post('/api/v1/conversations', { title });
            setConversations(prev => [data, ...prev]);
            return data.id;
        } catch (error) {
            console.error('Failed to create conversation:', error);
            toast({
                title: 'Error',
                description: 'Failed to create new chat.',
                variant: 'destructive',
            });
            throw error;
        }
    };

    /**
     * Delete a conversation
     */
    const deleteChat = async (id: string): Promise<void> => {
        try {
            await api.delete(`/api/v1/conversations/${id}`);
            setConversations(prev => prev.filter(c => c.id !== id));
            toast({
                title: 'Chat deleted',
                description: 'The conversation has been removed.',
            });
        } catch (error) {
            console.error('Failed to delete conversation:', error);
            toast({
                title: 'Error',
                description: 'Failed to delete chat.',
                variant: 'destructive',
            });
        }
    };

    /**
     * Rename a conversation
     */
    const renameChat = async (id: string, title: string): Promise<void> => {
        try {
            const { data } = await api.patch(`/api/v1/conversations/${id}`, { title });
            setConversations(prev =>
                prev.map(c => (c.id === id ? { ...c, title: data.title } : c))
            );
        } catch (error) {
            console.error('Failed to rename conversation:', error);
            toast({
                title: 'Error',
                description: 'Failed to rename chat.',
                variant: 'destructive',
            });
        }
    };

    /**
     * Get messages for a specific conversation
     */
    const getMessagesById = async (conversationId: string): Promise<Message[]> => {
        try {
            const { data } = await api.get(`/api/v1/conversations/${conversationId}/messages`);
            return data;
        } catch (error) {
            console.error('Failed to fetch messages:', error);
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
