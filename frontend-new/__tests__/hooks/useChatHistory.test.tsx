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

vi.mock('@/hooks/useUsage', () => ({
    useUsage: () => ({ plan: 'pro' }),
}));

vi.mock('@/lib/api', () => ({
    api: {
        get: (...args: any[]) => mockApiGet(...args),
        post: (...args: any[]) => mockApiPost(...args),
        patch: (...args: any[]) => mockApiPatch(...args),
        delete: (...args: any[]) => mockApiDelete(...args),
    },
    clearAuthCache: vi.fn(),
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

const createDisabledQueryClient = () => new QueryClient({
    defaultOptions: {
        queries: {
            retry: false,
            enabled: false,
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

            expect(mockApiGet).toHaveBeenCalledWith('/conversations', expect.objectContaining({ signal: expect.any(AbortSignal) }));
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

        it('should default to empty array when API returns null data', async () => {
            mockApiGet.mockResolvedValue({ data: null });

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

        it('should handle createNewChat when cache is empty', async () => {
            const queryClient = createDisabledQueryClient();
            const disabledWrapper = ({ children }: { children: ReactNode }) => (
                <QueryClientProvider client={queryClient}>
                    <ChatHistoryProvider>{children}</ChatHistoryProvider>
                </QueryClientProvider>
            );

            const newChat = { id: 'new-empty', title: 'New Chat', created_at: '2024-01-01', updated_at: '2024-01-01' };
            mockApiPost.mockResolvedValue({ data: newChat });

            const { result } = renderHook(() => useChatHistory(), { wrapper: disabledWrapper });

            await act(async () => {
                await result.current.createNewChat('New Chat');
            });

            await waitFor(() => {
                expect(result.current.conversations[0]).toEqual(newChat);
            });
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

        it('should handle delete when cache is empty', async () => {
            const queryClient = createDisabledQueryClient();
            const disabledWrapper = ({ children }: { children: ReactNode }) => (
                <QueryClientProvider client={queryClient}>
                    <ChatHistoryProvider>{children}</ChatHistoryProvider>
                </QueryClientProvider>
            );

            mockApiDelete.mockResolvedValue({});

            const { result } = renderHook(() => useChatHistory(), { wrapper: disabledWrapper });

            await act(async () => {
                await result.current.deleteChat('missing');
            });

            expect(mockApiDelete).toHaveBeenCalledWith('/conversations/missing');
            expect(result.current.conversations).toEqual([]);
        });
    });

    describe('renameChat', () => {
        it('should rename a chat and update state', async () => {
            const existingConversations = [
                { id: '1', title: 'Old Title', created_at: '2024-01-01', updated_at: '2024-01-01' },
                { id: '2', title: 'Other Chat', created_at: '2024-01-01', updated_at: '2024-01-01' },
            ];
            mockApiGet.mockResolvedValue({ data: existingConversations });
            mockApiPatch.mockResolvedValue({ data: { ...existingConversations[0], title: 'New Title' } });

            const { result } = renderHook(() => useChatHistory(), { wrapper });

            await waitFor(() => expect(result.current.conversations.length).toBe(2));

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

            expect(result.current.conversations.find(c => c.id === '2')?.title).toBe('Other Chat');
        });

        it('should show error toast on rename failure', async () => {
            mockApiPatch.mockRejectedValue({ message: 'Rename failed', response: { data: { detail: 'Server error' } } });

            const { result } = renderHook(() => useChatHistory(), { wrapper });

            await waitFor(() => expect(result.current.isLoading).toBe(false));

            await act(async () => {
                try {
                    await result.current.renameChat('1', 'New Title');
                } catch {
                    // Expected rejection
                }
            });

            expect(mockToast).toHaveBeenCalledWith(
                expect.objectContaining({
                    title: 'Error',
                    variant: 'destructive',
                })
            );
        });

        it('should handle rename when cache is empty', async () => {
            const queryClient = createDisabledQueryClient();
            const disabledWrapper = ({ children }: { children: ReactNode }) => (
                <QueryClientProvider client={queryClient}>
                    <ChatHistoryProvider>{children}</ChatHistoryProvider>
                </QueryClientProvider>
            );

            mockApiPatch.mockResolvedValue({ data: { id: 'missing', title: 'New', created_at: '', updated_at: '' } });

            const { result } = renderHook(() => useChatHistory(), { wrapper: disabledWrapper });

            await act(async () => {
                await result.current.renameChat('missing', 'New');
            });

            expect(result.current.conversations).toEqual([]);
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

// =============================================================================
// MESSAGE CACHING HOOKS TESTS
// =============================================================================

import { 
    useChatAccessCheck, 
    useConversationMessages, 
    useInvalidateMessages, 
    useOptimisticMessageUpdate,
    prefetchConversationMessages,
    chatKeys 
} from '@/hooks/useChatHistory';

describe('useChatAccessCheck', () => {
    it('should return hasChatAccess true for pro plan', () => {
        const { result } = renderHook(() => useChatAccessCheck());
        expect(result.current.hasChatAccess).toBe(true);
        expect(result.current.planReady).toBe(true);
    });
});

describe('useConversationMessages', () => {
    it('should fetch messages when conversationId is provided', async () => {
        const messages = [
            { id: 'm1', role: 'user', content: 'Hello', created_at: '2024-01-01' },
        ];
        mockApiGet.mockResolvedValue({ data: messages });

        const queryClient = createTestQueryClient();
        const messagesWrapper = ({ children }: { children: ReactNode }) => (
            <QueryClientProvider client={queryClient}>
                {children}
            </QueryClientProvider>
        );

        const { result } = renderHook(() => useConversationMessages('conv-123'), { wrapper: messagesWrapper });

        await waitFor(() => {
            expect(result.current.isLoading).toBe(false);
        });

        expect(result.current.data).toEqual(messages);
    });

    it('should not fetch when conversationId is null', async () => {
        mockApiGet.mockClear();

        const queryClient = createTestQueryClient();
        const messagesWrapper = ({ children }: { children: ReactNode }) => (
            <QueryClientProvider client={queryClient}>
                {children}
            </QueryClientProvider>
        );

        const { result } = renderHook(() => useConversationMessages(null), { wrapper: messagesWrapper });

        // Should not trigger API call
        expect(result.current.isLoading).toBe(false);
        expect(result.current.data).toBeUndefined();
    });

    it('should return empty array when API returns null', async () => {
        mockApiGet.mockResolvedValue({ data: null });

        const queryClient = createTestQueryClient();
        const messagesWrapper = ({ children }: { children: ReactNode }) => (
            <QueryClientProvider client={queryClient}>
                {children}
            </QueryClientProvider>
        );

        const { result } = renderHook(() => useConversationMessages('conv-123'), { wrapper: messagesWrapper });

        await waitFor(() => {
            expect(result.current.isLoading).toBe(false);
        });

        expect(result.current.data).toEqual([]);
    });
});

describe('useInvalidateMessages', () => {
    it('should invalidate messages query for a conversation', async () => {
        const queryClient = createTestQueryClient();
        const invalidateSpy = vi.spyOn(queryClient, 'invalidateQueries');

        const messagesWrapper = ({ children }: { children: ReactNode }) => (
            <QueryClientProvider client={queryClient}>
                {children}
            </QueryClientProvider>
        );

        const { result } = renderHook(() => useInvalidateMessages(), { wrapper: messagesWrapper });

        await act(async () => {
            result.current('conv-456');
        });

        expect(invalidateSpy).toHaveBeenCalledWith({ queryKey: chatKeys.message('conv-456') });
    });
});

describe('useOptimisticMessageUpdate', () => {
    it('should add message to cache optimistically', async () => {
        const queryClient = createTestQueryClient();
        const setQueryDataSpy = vi.spyOn(queryClient, 'setQueryData');

        const messagesWrapper = ({ children }: { children: ReactNode }) => (
            <QueryClientProvider client={queryClient}>
                {children}
            </QueryClientProvider>
        );

        const { result } = renderHook(() => useOptimisticMessageUpdate(), { wrapper: messagesWrapper });

        const newMessage = { 
            id: 'new-msg', 
            role: 'user' as const, 
            content: 'Test message', 
            created_at: '2024-01-01' 
        };

        await act(async () => {
            result.current('conv-789', newMessage);
        });

        expect(setQueryDataSpy).toHaveBeenCalledWith(
            chatKeys.message('conv-789'),
            expect.any(Function)
        );
    });

    it('should handle empty cache when adding message', async () => {
        const queryClient = createTestQueryClient();

        const messagesWrapper = ({ children }: { children: ReactNode }) => (
            <QueryClientProvider client={queryClient}>
                {children}
            </QueryClientProvider>
        );

        const { result } = renderHook(() => useOptimisticMessageUpdate(), { wrapper: messagesWrapper });

        const newMessage = { 
            id: 'new-msg', 
            role: 'assistant' as const, 
            content: 'Response', 
            created_at: '2024-01-01' 
        };

        await act(async () => {
            result.current('conv-empty', newMessage);
        });

        // Get the updated cache
        const cached = queryClient.getQueryData(chatKeys.message('conv-empty'));
        expect(cached).toEqual([newMessage]);
    });
});

describe('prefetchConversationMessages', () => {
    it('should prefetch messages for a conversation', async () => {
        const messages = [
            { id: 'm1', role: 'user', content: 'Prefetched', created_at: '2024-01-01' },
        ];
        mockApiGet.mockResolvedValue({ data: messages });

        const queryClient = createTestQueryClient();

        await prefetchConversationMessages(queryClient, 'conv-prefetch');

        const cached = queryClient.getQueryData(chatKeys.message('conv-prefetch'));
        expect(cached).toEqual(messages);
    });

    it('should return empty array when API returns null during prefetch', async () => {
        mockApiGet.mockResolvedValue({ data: null });

        const queryClient = createTestQueryClient();

        await prefetchConversationMessages(queryClient, 'conv-null');

        const cached = queryClient.getQueryData(chatKeys.message('conv-null'));
        expect(cached).toEqual([]);
    });
});

describe('chatKeys factory', () => {
    it('should generate correct query keys', () => {
        expect(chatKeys.all).toEqual(['chat']);
        expect(chatKeys.lists()).toEqual(['chat', 'list']);
        expect(chatKeys.list('filter')).toEqual(['chat', 'list', 'filter']);
        expect(chatKeys.messages()).toEqual(['chat', 'messages']);
        expect(chatKeys.message('id-123')).toEqual(['chat', 'messages', 'id-123']);
    });
});

// =============================================================================
// PLAN-BASED ACCESS CONTROL TESTS  
// =============================================================================

describe('useChatAccessCheck hook', () => {
    it('should return correct values for pro plan', () => {
        const { result } = renderHook(() => useChatAccessCheck());
        expect(result.current.hasChatAccess).toBe(true);
        expect(result.current.planReady).toBe(true);
    });
});

// =============================================================================
// FREE PLAN ACCESS DENIAL TESTS
// =============================================================================

describe('Access denial for free plan', () => {
    // Create a separate mock for useUsage that returns free plan
    const createFreePlanWrapper = () => {
        // We need to test with free plan mock
        const queryClient = createTestQueryClient();
        function FreePlanWrapper({ children }: { children: ReactNode }) {
            return (
                <QueryClientProvider client={queryClient}>
                    <ChatHistoryProvider>{children}</ChatHistoryProvider>
                </QueryClientProvider>
            );
        }
        FreePlanWrapper.displayName = 'FreePlanWrapper';
        return FreePlanWrapper;
    };

    it('should show toast when createNewChat is called without chat access', async () => {
        // Mock useUsage to return free plan for this test
        vi.doMock('@/hooks/useUsage', () => ({
            useUsage: () => ({ plan: 'free' }),
        }));
        
        // Re-import to get new mock
        vi.resetModules();
        
        const { ChatHistoryProvider: FreeChatHistoryProvider, useChatHistory: useFreeChatHistory } = await import('@/hooks/useChatHistory');
        const { QueryClientProvider } = await import('@tanstack/react-query');
        
        const freePlanWrapper = ({ children }: { children: ReactNode }) => {
            const queryClient = createTestQueryClient();
            return (
                <QueryClientProvider client={queryClient}>
                    <FreeChatHistoryProvider>{children}</FreeChatHistoryProvider>
                </QueryClientProvider>
            );
        };

        const { result } = renderHook(() => useFreeChatHistory(), { wrapper: freePlanWrapper });

        await act(async () => {
            try {
                await result.current.createNewChat();
            } catch (e) {
                // Expected to throw
            }
        });

        expect(mockToast).toHaveBeenCalledWith(
            expect.objectContaining({
                title: 'Subscription required',
            })
        );
        
        // Reset mock
        vi.doMock('@/hooks/useUsage', () => ({
            useUsage: () => ({ plan: 'pro' }),
        }));
    });
});

// =============================================================================
// Additional Edge Case Tests
// =============================================================================

describe('Chat History Edge Cases', () => {
    beforeEach(() => {
        vi.clearAllMocks();
        mockApiGet.mockResolvedValue({ data: [] });
    });

    it('should handle getMessagesById returning empty on API failure', async () => {
        const errorSpy = vi.spyOn(console, 'error').mockImplementation(() => {});
        
        mockApiGet.mockImplementation((url: string) => {
            if (url.includes('messages')) {
                return Promise.reject(new Error('Failed to fetch messages'));
            }
            return Promise.resolve({ data: [] });
        });

        const { result } = renderHook(() => useChatHistory(), { wrapper });

        await waitFor(() => expect(result.current.isLoading).toBe(false));

        let messages;
        await act(async () => {
            messages = await result.current.getMessagesById('conv-error');
        });

        expect(messages).toEqual([]);
        expect(errorSpy).toHaveBeenCalledWith('Failed to get messages:', expect.any(Error));
        
        errorSpy.mockRestore();
    });

    it('should use fallback error message in delete mutation', async () => {
        const existingConversations = [
            { id: '1', title: 'Chat 1', created_at: '2024-01-01', updated_at: '2024-01-01' },
        ];
        mockApiGet.mockResolvedValue({ data: existingConversations });
        mockApiDelete.mockRejectedValue({}); // Error without message

        const { result } = renderHook(() => useChatHistory(), { wrapper });

        await waitFor(() => expect(result.current.conversations.length).toBe(1));

        await act(async () => {
            try {
                await result.current.deleteChat('1');
            } catch {
                // Expected rejection
            }
        });

        await waitFor(() => expect(mockToast).toHaveBeenCalledWith(
            expect.objectContaining({
                description: 'Failed to delete chat.',
            })
        ));
    });

    it('should use fallback error message in create mutation', async () => {
        mockApiPost.mockRejectedValue({}); // Error without details

        const { result } = renderHook(() => useChatHistory(), { wrapper });

        await waitFor(() => expect(result.current.isLoading).toBe(false));

        await act(async () => {
            try {
                await result.current.createNewChat();
            } catch {
                // Expected rejection
            }
        });

        expect(mockToast).toHaveBeenCalledWith(
            expect.objectContaining({
                description: 'Failed to create new chat.',
            })
        );
    });

    it('should use fallback error message in rename mutation', async () => {
        mockApiPatch.mockRejectedValue({}); // Error without details

        const { result } = renderHook(() => useChatHistory(), { wrapper });

        await waitFor(() => expect(result.current.isLoading).toBe(false));

        await act(async () => {
            try {
                await result.current.renameChat('1', 'New Title');
            } catch {
                // Expected rejection
            }
        });

        expect(mockToast).toHaveBeenCalledWith(
            expect.objectContaining({
                description: 'Failed to rename chat.',
            })
        );
    });
});

// =============================================================================
// groupConversationsByDate Additional Tests
// =============================================================================

describe('groupConversationsByDate edge cases', () => {
    it('should correctly categorize conversations in Yesterday bucket', () => {
        const now = new Date();
        // Create a date that's exactly 36 hours ago (should be yesterday or last week depending on time)
        const almostYesterday = new Date(now.getTime() - 36 * 60 * 60 * 1000);

        const conversations: ChatConversation[] = [
            { id: '1', title: 'Yesterday Chat', created_at: almostYesterday.toISOString(), updated_at: almostYesterday.toISOString() },
        ];

        const groups = groupConversationsByDate(conversations);

        // Should be in Yesterday or Previous 7 Days depending on current time
        expect(groups.length).toBeGreaterThan(0);
        expect(groups.some(g => g.label === 'Yesterday' || g.label === 'Previous 7 Days')).toBe(true);
    });

    it('should correctly categorize conversations in Previous 7 Days bucket', () => {
        const now = new Date();
        const fiveDaysAgo = new Date(now.getTime() - 5 * 24 * 60 * 60 * 1000);

        const conversations: ChatConversation[] = [
            { id: '1', title: 'Recent Chat', created_at: fiveDaysAgo.toISOString(), updated_at: fiveDaysAgo.toISOString() },
        ];

        const groups = groupConversationsByDate(conversations);

        expect(groups.some(g => g.label === 'Previous 7 Days')).toBe(true);
    });

    it('should correctly categorize conversations in Older bucket', () => {
        const now = new Date();
        const thirtyDaysAgo = new Date(now.getTime() - 30 * 24 * 60 * 60 * 1000);

        const conversations: ChatConversation[] = [
            { id: '1', title: 'Old Chat', created_at: thirtyDaysAgo.toISOString(), updated_at: thirtyDaysAgo.toISOString() },
        ];

        const groups = groupConversationsByDate(conversations);

        expect(groups.some(g => g.label === 'Older')).toBe(true);
    });

    it('should handle conversations spanning all time periods', () => {
        const now = new Date();
        const today = now.toISOString();
        const yesterday = new Date(now.getTime() - 24 * 60 * 60 * 1000).toISOString();
        const fiveDaysAgo = new Date(now.getTime() - 5 * 24 * 60 * 60 * 1000).toISOString();
        const thirtyDaysAgo = new Date(now.getTime() - 30 * 24 * 60 * 60 * 1000).toISOString();

        const conversations: ChatConversation[] = [
            { id: '1', title: 'Today', created_at: today, updated_at: today },
            { id: '2', title: 'Yesterday', created_at: yesterday, updated_at: yesterday },
            { id: '3', title: 'Last Week', created_at: fiveDaysAgo, updated_at: fiveDaysAgo },
            { id: '4', title: 'Old', created_at: thirtyDaysAgo, updated_at: thirtyDaysAgo },
        ];

        const groups = groupConversationsByDate(conversations);

        // Should have at least 3-4 groups
        expect(groups.length).toBeGreaterThanOrEqual(3);
    });
});
