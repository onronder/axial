/**
 * Unit Tests for useChatHistory Hook
 * 
 * Tests the chat history context provider and all its methods.
 */

import { describe, it, expect, beforeEach, vi, Mock } from 'vitest';
import { renderHook, act, waitFor } from '@testing-library/react';
import { ReactNode } from 'react';
import { ChatHistoryProvider, useChatHistory, groupConversationsByDate, ChatConversation } from '@/hooks/useChatHistory';

// Mock dependencies
const mockToast = vi.fn();
const mockApiGet = vi.fn();
const mockApiPost = vi.fn();
const mockApiPatch = vi.fn();
const mockApiDelete = vi.fn();

vi.mock('@/hooks/use-toast', () => ({
    useToast: () => ({ toast: mockToast }),
}));

vi.mock('@/lib/api', () => ({
    api: {
        get: (...args: any[]) => mockApiGet(...args),
        post: (...args: any[]) => mockApiPost(...args),
        patch: (...args: any[]) => mockApiPatch(...args),
        delete: (...args: any[]) => mockApiDelete(...args),
    },
}));

// Create QueryClient for tests
import { QueryClient, QueryClientProvider } from '@tanstack/react-query';

const createTestQueryClient = () => new QueryClient({
    defaultOptions: {
        queries: {
            retry: false,
        },
    },
});

// Test wrapper with all required providers
const wrapper = ({ children }: { children: ReactNode }) => {
    const queryClient = createTestQueryClient();
    return (
        <QueryClientProvider client={queryClient}>
            <ChatHistoryProvider>{children}</ChatHistoryProvider>
        </QueryClientProvider>
    );
};

describe('useChatHistory', () => {
    beforeEach(() => {
        vi.clearAllMocks();
        mockApiGet.mockResolvedValue({ data: [] });
    });

    describe('Initial State', () => {
        it('should start with loading state', () => {
            const { result } = renderHook(() => useChatHistory(), { wrapper });
            expect(result.current.isLoading).toBe(true);
        });

        it('should fetch conversations on mount', async () => {
            const mockConversations = [
                { id: '1', title: 'Chat 1', created_at: '2024-01-01', updated_at: '2024-01-01' },
            ];
            mockApiGet.mockResolvedValue({ data: mockConversations });

            const { result } = renderHook(() => useChatHistory(), { wrapper });

            await waitFor(() => {
                expect(result.current.isLoading).toBe(false);
            });

            expect(mockApiGet).toHaveBeenCalledWith('/conversations');
            expect(result.current.conversations).toEqual(mockConversations);
        });

        it('should handle fetch error gracefully', async () => {
            mockApiGet.mockRejectedValue(new Error('Network error'));

            const { result } = renderHook(() => useChatHistory(), { wrapper });

            await waitFor(() => {
                expect(result.current.isLoading).toBe(false);
            });

            expect(result.current.conversations).toEqual([]);
        });
    });

    describe('createNewChat', () => {
        it('should create a new chat and update state', async () => {
            const newChat = { id: 'new-1', title: 'New Chat', created_at: '2024-01-01', updated_at: '2024-01-01' };
            mockApiPost.mockResolvedValue({ data: newChat });

            const { result } = renderHook(() => useChatHistory(), { wrapper });

            await waitFor(() => expect(result.current.isLoading).toBe(false));

            let chatId: string;
            await act(async () => {
                chatId = await result.current.createNewChat('New Chat');
            });

            expect(chatId!).toBe('new-1');
            expect(mockApiPost).toHaveBeenCalledWith('/conversations', { title: 'New Chat' });

            await waitFor(() => {
                expect(result.current.conversations[0]).toEqual(newChat);
            });
        });

        it('should show error toast on create failure', async () => {
            mockApiPost.mockRejectedValue({ message: 'Create failed', response: { data: { detail: 'Server error' } } });

            const { result } = renderHook(() => useChatHistory(), { wrapper });

            await waitFor(() => expect(result.current.isLoading).toBe(false));

            await act(async () => {
                try {
                    await result.current.createNewChat();
                } catch (e) {
                    // Expected
                }
            });

            expect(mockToast).toHaveBeenCalledWith(
                expect.objectContaining({
                    title: 'Error',
                    variant: 'destructive',
                })
            );
        });
    });

    describe('deleteChat', () => {
        it('should delete a chat and update state', async () => {
            const existingConversations = [
                { id: '1', title: 'Chat 1', created_at: '2024-01-01', updated_at: '2024-01-01' },
                { id: '2', title: 'Chat 2', created_at: '2024-01-01', updated_at: '2024-01-01' },
            ];
            mockApiGet.mockResolvedValue({ data: existingConversations });
            mockApiDelete.mockResolvedValue({});

            const { result } = renderHook(() => useChatHistory(), { wrapper });

            await waitFor(() => expect(result.current.conversations.length).toBe(2));

            await act(async () => {
                await result.current.deleteChat('1');
            });

            expect(mockApiDelete).toHaveBeenCalledWith('/conversations/1');

            await waitFor(() => {
                expect(result.current.conversations).toHaveLength(1);
                expect(result.current.conversations[0].id).toBe('2');
            });

            expect(mockToast).toHaveBeenCalledWith(
                expect.objectContaining({ title: 'Chat deleted' })
            );
        });

        it('should show error toast on delete failure', async () => {
            mockApiDelete.mockRejectedValue({ message: 'Delete failed' });

            const { result } = renderHook(() => useChatHistory(), { wrapper });

            await waitFor(() => expect(result.current.isLoading).toBe(false));

            await act(async () => {
                try {
                    await result.current.deleteChat('nonexistent');
                } catch {
                    // Expected rejection
                }
            });

            await waitFor(() => expect(mockToast).toHaveBeenCalledWith(
                expect.objectContaining({
                    title: 'Error',
                    variant: 'destructive',
                })
            ));
        });
    });

    describe('renameChat', () => {
        it('should rename a chat and update state', async () => {
            const existingConversations = [
                { id: '1', title: 'Old Title', created_at: '2024-01-01', updated_at: '2024-01-01' },
            ];
            mockApiGet.mockResolvedValue({ data: existingConversations });
            mockApiPatch.mockResolvedValue({ data: { ...existingConversations[0], title: 'New Title' } });

            const { result } = renderHook(() => useChatHistory(), { wrapper });

            await waitFor(() => expect(result.current.conversations.length).toBe(1));

            await act(async () => {
                await result.current.renameChat('1', 'New Title');
            });

            expect(mockApiPatch).toHaveBeenCalledWith('/conversations/1', { title: 'New Title' });

            await waitFor(() => {
                expect(result.current.conversations[0].title).toBe('New Title');
            });

            expect(mockToast).toHaveBeenCalledWith(
                expect.objectContaining({ title: 'Chat renamed' })
            );
        });
    });

    describe('getMessagesById', () => {
        it('should fetch messages for a conversation', async () => {
            const messages = [
                { id: 'm1', role: 'user', content: 'Hello', created_at: '2024-01-01' },
                { id: 'm2', role: 'assistant', content: 'Hi!', created_at: '2024-01-01' },
            ];
            mockApiGet.mockImplementation((url: string) => {
                if (url.includes('messages')) {
                    return Promise.resolve({ data: messages });
                }
                return Promise.resolve({ data: [] });
            });

            const { result } = renderHook(() => useChatHistory(), { wrapper });

            await waitFor(() => expect(result.current.isLoading).toBe(false));

            let fetchedMessages;
            await act(async () => {
                fetchedMessages = await result.current.getMessagesById('conv-1');
            });

            expect(mockApiGet).toHaveBeenCalledWith('/conversations/conv-1/messages');
            expect(fetchedMessages).toEqual(messages);
        });

        it('should return empty array on error', async () => {
            mockApiGet.mockImplementation((url: string) => {
                if (url.includes('messages')) {
                    return Promise.reject(new Error('Network error'));
                }
                return Promise.resolve({ data: [] });
            });

            const { result } = renderHook(() => useChatHistory(), { wrapper });

            await waitFor(() => expect(result.current.isLoading).toBe(false));

            let fetchedMessages;
            await act(async () => {
                fetchedMessages = await result.current.getMessagesById('conv-1');
            });

            expect(fetchedMessages).toEqual([]);
        });
    });

    describe('refresh', () => {
        it('should re-fetch conversations', async () => {
            mockApiGet.mockResolvedValue({ data: [] });

            const { result } = renderHook(() => useChatHistory(), { wrapper });

            await waitFor(() => expect(result.current.isLoading).toBe(false));

            mockApiGet.mockResolvedValue({ data: [{ id: 'new', title: 'New', created_at: '', updated_at: '' }] });

            await act(async () => {
                await result.current.refresh();
            });

            await waitFor(() => {
                expect(result.current.conversations).toHaveLength(1);
            });
        });
    });
});

describe('groupConversationsByDate', () => {
    it('should group conversations correctly', () => {
        const now = new Date();
        const today = now.toISOString();
        const yesterday = new Date(now.getTime() - 24 * 60 * 60 * 1000).toISOString();
        const lastWeek = new Date(now.getTime() - 3 * 24 * 60 * 60 * 1000).toISOString();
        const older = new Date(now.getTime() - 30 * 24 * 60 * 60 * 1000).toISOString();

        const conversations: ChatConversation[] = [
            { id: '1', title: 'Today Chat', created_at: today, updated_at: today },
            { id: '2', title: 'Yesterday Chat', created_at: yesterday, updated_at: yesterday },
            { id: '3', title: 'Last Week Chat', created_at: lastWeek, updated_at: lastWeek },
            { id: '4', title: 'Old Chat', created_at: older, updated_at: older },
        ];

        const groups = groupConversationsByDate(conversations);

        expect(groups.length).toBeGreaterThan(0);
        expect(groups.some(g => g.label === 'Today')).toBe(true);
    });

    it('should return empty array for empty input', () => {
        const groups = groupConversationsByDate([]);
        expect(groups).toEqual([]);
    });

    it('should filter out empty groups', () => {
        const now = new Date();
        const today = now.toISOString();

        const conversations: ChatConversation[] = [
            { id: '1', title: 'Today Only', created_at: today, updated_at: today },
        ];

        const groups = groupConversationsByDate(conversations);

        expect(groups.length).toBe(1);
        expect(groups[0].label).toBe('Today');
    });
});

describe('useChatHistory outside provider', () => {
    it('should throw error when used outside provider', () => {
        expect(() => {
            renderHook(() => useChatHistory());
        }).toThrow('useChatHistory must be used within a ChatHistoryProvider');
    });
});
