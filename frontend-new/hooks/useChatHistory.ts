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
        console.log('💬 [useChatHistory] Starting fetchConversations...');
        setIsLoading(true);
        try {
            console.log('💬 [useChatHistory] Making GET request to /api/v1/conversations');
            const { data } = await api.get('/api/v1/conversations');
            console.log('💬 [useChatHistory] ✅ Conversations fetched:', data?.length || 0, 'items');
            console.log('💬 [useChatHistory] Data:', data);
            setConversations(data);
        } catch (error: any) {
            console.error('💬 [useChatHistory] ❌ Failed to fetch conversations:', error);
            console.error('💬 [useChatHistory] Error response:', error.response?.data);
            console.error('💬 [useChatHistory] Error status:', error.response?.status);
            // Don't show toast on initial load failure - might just be empty
        } finally {
            setIsLoading(false);
            console.log('💬 [useChatHistory] fetchConversations complete');
        }
    }, []);

    useEffect(() => {
        console.log('💬 [useChatHistory] Hook mounted, calling fetchConversations');
        fetchConversations();
    }, [fetchConversations]);

    /**
     * Create a new conversation
     */
    const createNewChat = async (title: string = 'New Chat'): Promise<string> => {
        console.log('💬 [useChatHistory] Creating new chat with title:', title);
        try {
            console.log('💬 [useChatHistory] Making POST request to /api/v1/conversations');
            const { data } = await api.post('/api/v1/conversations', { title });
            console.log('💬 [useChatHistory] ✅ Chat created successfully:', data);
            setConversations(prev => [data, ...prev]);
            return data.id;
        } catch (error: any) {
            console.error('💬 [useChatHistory] ❌ Failed to create conversation:', error);
            console.error('💬 [useChatHistory] Error response:', error.response?.data);
            console.error('💬 [useChatHistory] Error status:', error.response?.status);
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
            console.log('💬 [useChatHistory] ✅ Chat deleted successfully');
            setConversations(prev => prev.filter(c => c.id !== id));
            toast({
                title: 'Chat deleted',
                description: 'The conversation has been removed.',
            });
        } catch (error: any) {
            console.error('💬 [useChatHistory] ❌ Failed to delete conversation:', error);
            console.error('💬 [useChatHistory] Error response:', error.response?.data);
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
        console.log('💬 [useChatHistory] Renaming chat:', id, 'to:', title);
        try {
            const { data } = await api.patch(`/api/v1/conversations/${id}`, { title });
            console.log('💬 [useChatHistory] ✅ Chat renamed successfully:', data);
            setConversations(prev =>
                prev.map(c => (c.id === id ? { ...c, title: data.title } : c))
            );
        } catch (error: any) {
            console.error('💬 [useChatHistory] ❌ Failed to rename conversation:', error);
            console.error('💬 [useChatHistory] Error response:', error.response?.data);
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
        console.log('💬 [useChatHistory] Fetching messages for conversation:', conversationId);
        try {
            const { data } = await api.get(`/api/v1/conversations/${conversationId}/messages`);
            console.log('💬 [useChatHistory] ✅ Messages fetched:', data?.length || 0, 'items');
            return data;
        } catch (error: any) {
            console.error('💬 [useChatHistory] ❌ Failed to fetch messages:', error);
            console.error('💬 [useChatHistory] Error response:', error.response?.data);
            console.error('💬 [useChatHistory] Error status:', error.response?.status);
            return [];
        }
    };

    // Log current state
    console.log('💬 [useChatHistory] Current state:', {
        conversationCount: conversations.length,
        isLoading
    });

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
