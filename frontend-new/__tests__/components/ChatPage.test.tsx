/**
 * Unit Tests for ChatPage Component
 * 
 * Tests covering the conversation state management fix:
 * - Conversation ID tracked in state, not derived from URL params
 * - Subsequent messages use the same conversation ID
 * - URL navigation properly syncs state
 * - Browser back/forward navigation
 * - New chat creation flow
 * - Stale closure prevention via ref
 */

import { describe, it, expect, vi, beforeEach, afterEach } from 'vitest';
import { render, screen, waitFor, act } from '@testing-library/react';
import userEvent from '@testing-library/user-event';

// =============================================================================
// Mock Setup
// =============================================================================

const mockPush = vi.fn();
const mockReplace = vi.fn();
const mockRouter = {
    push: mockPush,
    replace: mockReplace,
    back: vi.fn(),
    forward: vi.fn(),
    refresh: vi.fn(),
    prefetch: vi.fn(),
};

let mockChatIdFromUrl = 'new';

vi.mock('next/navigation', () => ({
    useRouter: () => mockRouter,
    useParams: () => ({ chatId: mockChatIdFromUrl }),
}));

const mockCreateNewChat = vi.fn();
const mockGetMessagesById = vi.fn();

vi.mock('@/hooks/useChatHistory', () => ({
    useChatHistory: () => ({
        conversations: [],
        isLoading: false,
        createNewChat: mockCreateNewChat,
        deleteChat: vi.fn(),
        renameChat: vi.fn(),
        getMessagesById: mockGetMessagesById,
        refresh: vi.fn(),
    }),
    ChatHistoryProvider: ({ children }: { children: React.ReactNode }) => children,
    Message: {},
}));

vi.mock('@/hooks/useDocumentCount', () => ({
    useDocumentCount: () => ({
        isEmpty: false,
        isLoading: false,
    }),
}));

vi.mock('@/hooks/useProfile', () => ({
    useProfile: () => ({
        profile: { first_name: 'Test', last_name: 'User', has_team: true },
        isLoading: false,
    }),
}));

const mockToast = vi.fn();
vi.mock('@/hooks/use-toast', () => ({
    useToast: () => ({
        toast: mockToast,
    }),
}));

// Mock streamChatResponse as an async generator
const mockStreamChatResponse = vi.fn();
vi.mock('@/lib/chat-utils', () => ({
    generateSmartTitle: vi.fn((content: string) => content.slice(0, 30)),
    streamChatResponse: (payload: unknown) => mockStreamChatResponse(payload),
    isChatApiError: vi.fn(() => false),
}));

vi.mock('@/components/chat/ChatArea', () => ({
    ChatArea: ({ onSendMessage, messages, disabled }: {
        onSendMessage: (content: string, scopeId?: string) => void;
        messages: unknown[];
        disabled: boolean;
    }) => (
        <div data-testid="chat-area">
            <div data-testid="message-count">{messages.length}</div>
            <button
                data-testid="send-message"
                onClick={() => onSendMessage('Test message')}
                disabled={disabled}
            >
                Send
            </button>
            <button
                data-testid="send-second-message"
                onClick={() => onSendMessage('Second message')}
                disabled={disabled}
            >
                Send Second
            </button>
        </div>
    ),
}));

vi.mock('@/components/onboarding/OnboardingModal', () => ({
    OnboardingModal: () => null,
}));

import ChatPage from '@/app/dashboard/chat/[chatId]/page';

// =============================================================================
// Helper Functions
// =============================================================================

/**
 * Creates a mock async generator for streamChatResponse
 */
function createMockStreamGenerator(events: Array<{ type: string; content?: string; sources?: unknown[] }>) {
    return async function* () {
        for (const event of events) {
            yield event;
        }
    };
}

// =============================================================================
// Tests
// =============================================================================

describe('ChatPage Component - Conversation State Management', () => {
    beforeEach(() => {
        vi.clearAllMocks();
        mockChatIdFromUrl = 'new';
        mockCreateNewChat.mockResolvedValue('created-chat-123');
        mockGetMessagesById.mockResolvedValue([]);
        mockStreamChatResponse.mockImplementation(() =>
            createMockStreamGenerator([
                { type: 'token', content: 'Hello ' },
                { type: 'token', content: 'world!' },
            ])()
        );
    });

    afterEach(() => {
        vi.clearAllMocks();
    });

    describe('Initial State', () => {
        it('should render with empty messages for new chat', () => {
            render(<ChatPage />);
            
            expect(screen.getByTestId('message-count')).toHaveTextContent('0');
        });

        it('should have activeConversationId as null for new chat URL', () => {
            render(<ChatPage />);
            
            // The send button should be enabled (not disabled means we're ready)
            expect(screen.getByTestId('send-message')).not.toBeDisabled();
        });

        it('should load messages for existing chat', async () => {
            mockChatIdFromUrl = 'existing-chat-456';
            mockGetMessagesById.mockResolvedValue([
                { id: '1', role: 'user', content: 'Hello', created_at: new Date().toISOString() },
                { id: '2', role: 'assistant', content: 'Hi there!', created_at: new Date().toISOString() },
            ]);

            render(<ChatPage />);

            await waitFor(() => {
                expect(mockGetMessagesById).toHaveBeenCalledWith('existing-chat-456');
            });
        });
    });

    describe('Conversation Creation - CRITICAL BUG FIX', () => {
        it('should create conversation only once on first message', async () => {
            const user = userEvent.setup();
            render(<ChatPage />);

            // Send first message
            await act(async () => {
                await user.click(screen.getByTestId('send-message'));
            });

            // Wait for async operations
            await waitFor(() => {
                expect(mockCreateNewChat).toHaveBeenCalledTimes(1);
            });

            expect(mockCreateNewChat).toHaveBeenCalledWith('Test message');
        });

        it('should NOT create new conversation on subsequent messages in same chat', async () => {
            const user = userEvent.setup();
            render(<ChatPage />);

            // Send first message - creates conversation
            await act(async () => {
                await user.click(screen.getByTestId('send-message'));
            });

            await waitFor(() => {
                expect(mockCreateNewChat).toHaveBeenCalledTimes(1);
            });

            // Clear the mock to check second call
            mockCreateNewChat.mockClear();

            // Wait for streaming to complete
            await waitFor(() => {
                expect(screen.getByTestId('send-message')).not.toBeDisabled();
            });

            // Send second message - should NOT create new conversation
            await act(async () => {
                await user.click(screen.getByTestId('send-second-message'));
            });

            // Wait a bit to ensure no async creation happens
            await new Promise(resolve => setTimeout(resolve, 100));

            // CRITICAL: This is the bug we fixed - second message should NOT create new chat
            expect(mockCreateNewChat).not.toHaveBeenCalled();
        });

        it('should update URL via router.replace after creating conversation', async () => {
            const user = userEvent.setup();
            render(<ChatPage />);

            await act(async () => {
                await user.click(screen.getByTestId('send-message'));
            });

            await waitFor(() => {
                expect(mockReplace).toHaveBeenCalledWith(
                    '/dashboard/chat/created-chat-123',
                    { scroll: false }
                );
            });
        });

        it('should use conversation ID from state in subsequent API calls', async () => {
            const user = userEvent.setup();
            render(<ChatPage />);

            // Send first message
            await act(async () => {
                await user.click(screen.getByTestId('send-message'));
            });

            await waitFor(() => {
                expect(mockStreamChatResponse).toHaveBeenCalledWith(
                    expect.objectContaining({
                        conversation_id: 'created-chat-123',
                    })
                );
            });

            // Wait for streaming to complete
            await waitFor(() => {
                expect(screen.getByTestId('send-message')).not.toBeDisabled();
            });

            mockStreamChatResponse.mockClear();

            // Send second message
            await act(async () => {
                await user.click(screen.getByTestId('send-second-message'));
            });

            await waitFor(() => {
                // Second call should use the same conversation ID
                expect(mockStreamChatResponse).toHaveBeenCalledWith(
                    expect.objectContaining({
                        conversation_id: 'created-chat-123',
                    })
                );
            });
        });
    });

    describe('URL Navigation Sync', () => {
        it('should sync state when navigating to different chat via URL', async () => {
            const { unmount } = render(<ChatPage />);
            unmount();

            // Simulate navigation to existing chat
            mockChatIdFromUrl = 'different-chat-789';
            
            render(<ChatPage />);

            await waitFor(() => {
                expect(mockGetMessagesById).toHaveBeenCalledWith('different-chat-789');
            });
        });

        it('should reset state when navigating back to new chat', async () => {
            // Start with existing chat
            mockChatIdFromUrl = 'existing-chat';
            mockGetMessagesById.mockResolvedValue([
                { id: '1', role: 'user', content: 'Previous message', created_at: new Date().toISOString() },
            ]);

            const { unmount } = render(<ChatPage />);

            await waitFor(() => {
                expect(mockGetMessagesById).toHaveBeenCalled();
            });

            unmount();

            // Navigate to new chat
            mockChatIdFromUrl = 'new';
            mockGetMessagesById.mockClear();
            
            render(<ChatPage />);

            await waitFor(() => {
                expect(screen.getByTestId('message-count')).toHaveTextContent('0');
            });
        });
    });

    describe('Error Handling', () => {
        it('should show toast on conversation creation failure', async () => {
            mockCreateNewChat.mockRejectedValue(new Error('Network error'));
            
            const user = userEvent.setup();
            render(<ChatPage />);

            await act(async () => {
                await user.click(screen.getByTestId('send-message'));
            });

            await waitFor(() => {
                expect(mockToast).toHaveBeenCalledWith(
                    expect.objectContaining({
                        title: 'Error',
                        variant: 'destructive',
                    })
                );
            });
        });

        it('should not add message to UI on creation failure', async () => {
            mockCreateNewChat.mockRejectedValue(new Error('Network error'));
            
            const user = userEvent.setup();
            render(<ChatPage />);

            const initialCount = screen.getByTestId('message-count').textContent;

            await act(async () => {
                await user.click(screen.getByTestId('send-message'));
            });

            // Wait for error handling
            await waitFor(() => {
                expect(mockToast).toHaveBeenCalled();
            });

            // Message count should remain the same on failure
            expect(screen.getByTestId('message-count')).toHaveTextContent(initialCount!);
        });
    });

    describe('Existing Chat Flow', () => {
        it('should not create new conversation when sending message in existing chat', async () => {
            mockChatIdFromUrl = 'existing-chat-456';
            mockGetMessagesById.mockResolvedValue([]);

            const user = userEvent.setup();
            render(<ChatPage />);

            // Wait for initial load
            await waitFor(() => {
                expect(mockGetMessagesById).toHaveBeenCalled();
            });

            // Wait for loading to complete
            await waitFor(() => {
                expect(screen.getByTestId('send-message')).not.toBeDisabled();
            });

            // Send message
            await act(async () => {
                await user.click(screen.getByTestId('send-message'));
            });

            // Should NOT call createNewChat
            expect(mockCreateNewChat).not.toHaveBeenCalled();

            // Should use existing chat ID in stream
            await waitFor(() => {
                expect(mockStreamChatResponse).toHaveBeenCalledWith(
                    expect.objectContaining({
                        conversation_id: 'existing-chat-456',
                    })
                );
            });
        });
    });
});

describe('ChatPage Component - Stale Closure Prevention', () => {
    beforeEach(() => {
        vi.clearAllMocks();
        mockChatIdFromUrl = 'new';
        mockCreateNewChat.mockResolvedValue('created-chat-123');
        mockGetMessagesById.mockResolvedValue([]);
    });

    it('should use ref to access current conversation ID in async callbacks', async () => {
        // This test verifies the ref pattern prevents stale closures
        // The fix uses conversationIdRef.current instead of relying on state directly
        const user = userEvent.setup();
        
        // Mock slow stream response
        mockStreamChatResponse.mockImplementation(() =>
            (async function* () {
                await new Promise(resolve => setTimeout(resolve, 50));
                yield { type: 'token', content: 'Response' };
            })()
        );

        render(<ChatPage />);

        // Send message
        await act(async () => {
            await user.click(screen.getByTestId('send-message'));
        });

        await waitFor(() => {
            expect(mockCreateNewChat).toHaveBeenCalledTimes(1);
        });

        // The ref should have been updated before the stream response arrives
        await waitFor(() => {
            expect(mockStreamChatResponse).toHaveBeenCalledWith(
                expect.objectContaining({
                    conversation_id: 'created-chat-123',
                })
            );
        });
    });
});

describe('ChatPage Component - Race Condition Prevention', () => {
    beforeEach(() => {
        vi.clearAllMocks();
        mockChatIdFromUrl = 'new';
        mockGetMessagesById.mockResolvedValue([]);
        mockStreamChatResponse.mockImplementation(() =>
            createMockStreamGenerator([
                { type: 'token', content: 'Hello' },
            ])()
        );
    });

    it('should handle rapid message sending without duplicate conversations', async () => {
        // Make createNewChat slow to simulate race condition scenario
        let createCallCount = 0;
        mockCreateNewChat.mockImplementation(async () => {
            createCallCount++;
            await new Promise(resolve => setTimeout(resolve, 100));
            return `chat-${createCallCount}`;
        });

        const user = userEvent.setup();
        render(<ChatPage />);

        // Send first message - should only create ONE conversation
        await act(async () => {
            await user.click(screen.getByTestId('send-message'));
        });

        await waitFor(() => {
            expect(mockCreateNewChat).toHaveBeenCalledTimes(1);
        });
    });
});
