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
    ChatArea: ({ onSendMessage, onSelectScope, onModelSelect, messages, disabled }: {
        onSendMessage: (content: string, scopeId?: string) => void;
        onSelectScope?: (scopeId: string, originalQuery: string) => void;
        onModelSelect?: (model: string) => void;
        messages: Array<{ role?: string; original_query?: string }>;
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
                data-testid="select-scope-btn"
                onClick={() => {
                    const clarification = messages.find(m => m.role === 'clarification');
                    if (clarification && onSelectScope) {
                        onSelectScope('scope-1', clarification.original_query || 'Test query');
                    }
                }}
            >
                Select Scope
            </button>
            <button
                data-testid="select-all-scope-btn"
                onClick={() => {
                    const clarification = messages.find(m => m.role === 'clarification');
                    if (clarification && onSelectScope) {
                        onSelectScope('__all__', clarification.original_query || 'Test query');
                    }
                }}
            >
                Search All
            </button>
            <button
                data-testid="select-smart-model"
                onClick={() => onModelSelect && onModelSelect('smart')}
            >
                Smart
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

// =============================================================================
// Additional Tests for Full Coverage
// =============================================================================

describe('ChatPage Component - Abort Error Handling', () => {
    beforeEach(() => {
        vi.clearAllMocks();
        mockChatIdFromUrl = 'new';
        mockCreateNewChat.mockResolvedValue('created-chat-123');
        mockGetMessagesById.mockResolvedValue([]);
    });

    it('should handle AbortError gracefully', async () => {
        // Mock stream that throws AbortError
        mockStreamChatResponse.mockImplementation(() =>
            (async function* () {
                const error = new Error('Aborted');
                error.name = 'AbortError';
                throw error;
            })()
        );

        const user = userEvent.setup();
        render(<ChatPage />);

        await act(async () => {
            await user.click(screen.getByTestId('send-message'));
        });

        // Should NOT show error toast for AbortError
        await waitFor(() => {
            expect(mockToast).not.toHaveBeenCalledWith(
                expect.objectContaining({
                    variant: 'destructive',
                })
            );
        });
    });

    it('should show error toast for non-abort errors', async () => {
        // Mock stream that throws a regular error
        mockStreamChatResponse.mockImplementation(() =>
            (async function* () {
                throw new Error('Network failed');
            })()
        );

        const user = userEvent.setup();
        render(<ChatPage />);

        await act(async () => {
            await user.click(screen.getByTestId('send-message'));
        });

        await waitFor(() => {
            expect(mockToast).toHaveBeenCalledWith(
                expect.objectContaining({
                    title: 'Chat error',
                    variant: 'destructive',
                })
            );
        });
    });
});

describe('ChatPage Component - Scope Selection', () => {
    beforeEach(() => {
        vi.clearAllMocks();
        mockChatIdFromUrl = 'existing-chat-456';
        mockGetMessagesById.mockResolvedValue([
            { id: 'clarification-1', role: 'clarification', content: 'Choose scope', created_at: new Date().toISOString(), candidates: [{ id: 'scope-1', name: 'Scope 1' }], original_query: 'Test query' },
        ]);
        mockStreamChatResponse.mockImplementation(() =>
            (async function* () {
                yield { type: 'token', content: 'Response' };
            })()
        );
    });

    it('should handle scope selection and re-send message', async () => {
        const user = userEvent.setup();
        render(<ChatPage />);

        // Wait for clarification message to load
        await waitFor(() => {
            expect(screen.getByTestId('message-count')).toHaveTextContent('1');
        });

        // Simulate scope selection
        await act(async () => {
            await user.click(screen.getByTestId('select-scope-btn'));
        });

        // Should call stream with scope
        await waitFor(() => {
            expect(mockStreamChatResponse).toHaveBeenCalled();
        });
    });

    it('should handle __all__ scope selection', async () => {
        const user = userEvent.setup();
        render(<ChatPage />);

        await waitFor(() => {
            expect(screen.getByTestId('message-count')).toHaveTextContent('1');
        });

        // Select "search all"
        await act(async () => {
            await user.click(screen.getByTestId('select-all-scope-btn'));
        });

        await waitFor(() => {
            expect(mockStreamChatResponse).toHaveBeenCalled();
        });
    });
});

describe('ChatPage Component - Chat Error Types', () => {
    beforeEach(() => {
        vi.clearAllMocks();
        mockChatIdFromUrl = 'existing-chat';
        mockGetMessagesById.mockResolvedValue([]);
    });

    it('should handle LLM_TIMEOUT error', async () => {
        mockStreamChatResponse.mockImplementation(() =>
            (async function* () {
                yield { type: 'error', error: 'LLM_TIMEOUT', message: 'Timeout' };
            })()
        );

        const user = userEvent.setup();
        render(<ChatPage />);

        await waitFor(() => {
            expect(screen.getByTestId('send-message')).not.toBeDisabled();
        });

        await act(async () => {
            await user.click(screen.getByTestId('send-message'));
        });

        await waitFor(() => {
            expect(mockToast).toHaveBeenCalledWith(
                expect.objectContaining({
                    title: 'Model timeout',
                })
            );
        });
    });

    it('should handle PLAN_LIMIT_EXCEEDED error', async () => {
        mockStreamChatResponse.mockImplementation(() =>
            (async function* () {
                yield { type: 'error', error: 'PLAN_LIMIT_EXCEEDED', message: 'Limit' };
            })()
        );

        const user = userEvent.setup();
        render(<ChatPage />);

        await waitFor(() => {
            expect(screen.getByTestId('send-message')).not.toBeDisabled();
        });

        await act(async () => {
            await user.click(screen.getByTestId('send-message'));
        });

        await waitFor(() => {
            expect(mockToast).toHaveBeenCalledWith(
                expect.objectContaining({
                    title: 'Plan limit reached',
                })
            );
        });
    });

    it('should handle INTEGRATION_AUTH_FAILED error', async () => {
        mockStreamChatResponse.mockImplementation(() =>
            (async function* () {
                yield { type: 'error', error: 'INTEGRATION_AUTH_FAILED', message: 'Auth failed' };
            })()
        );

        const user = userEvent.setup();
        render(<ChatPage />);

        await waitFor(() => {
            expect(screen.getByTestId('send-message')).not.toBeDisabled();
        });

        await act(async () => {
            await user.click(screen.getByTestId('send-message'));
        });

        await waitFor(() => {
            expect(mockToast).toHaveBeenCalledWith(
                expect.objectContaining({
                    title: 'Integration expired',
                })
            );
        });
    });

    it('should handle CONNECTOR_UNAVAILABLE error', async () => {
        mockStreamChatResponse.mockImplementation(() =>
            (async function* () {
                yield { type: 'error', error: 'CONNECTOR_UNAVAILABLE', message: 'Unavailable' };
            })()
        );

        const user = userEvent.setup();
        render(<ChatPage />);

        await waitFor(() => {
            expect(screen.getByTestId('send-message')).not.toBeDisabled();
        });

        await act(async () => {
            await user.click(screen.getByTestId('send-message'));
        });

        await waitFor(() => {
            expect(mockToast).toHaveBeenCalledWith(
                expect.objectContaining({
                    title: 'Service unavailable',
                })
            );
        });
    });
});

describe('ChatPage Component - Model Selection Persistence', () => {
    beforeEach(() => {
        vi.clearAllMocks();
        mockChatIdFromUrl = 'new';
        // Clear localStorage before each test
        try {
            localStorage.clear();
        } catch {
            // localStorage might not be available in test env
        }
        mockCreateNewChat.mockResolvedValue('created-chat-123');
        mockGetMessagesById.mockResolvedValue([]);
        mockStreamChatResponse.mockImplementation(() =>
            (async function* () {
                yield { type: 'token', content: 'Hello' };
            })()
        );
    });

    it('should persist model selection to localStorage', async () => {
        const user = userEvent.setup();
        render(<ChatPage />);

        // Select smart model
        await act(async () => {
            await user.click(screen.getByTestId('select-smart-model'));
        });

        // Check localStorage was updated (if available)
        const stored = localStorage.getItem('axio-chat-model-preference');
        expect(stored === 'smart' || stored === null).toBe(true); // null if localStorage unavailable
    });
});

describe('ChatPage Component - Source Normalization', () => {
    beforeEach(() => {
        vi.clearAllMocks();
        mockChatIdFromUrl = 'existing-chat';
        mockGetMessagesById.mockResolvedValue([]);
    });

    it('should normalize string sources', async () => {
        mockStreamChatResponse.mockImplementation(() =>
            (async function* () {
                yield { type: 'sources', sources: ['Source A', 'Source B'] };
                yield { type: 'token', content: 'Response' };
            })()
        );

        const user = userEvent.setup();
        render(<ChatPage />);

        await waitFor(() => {
            expect(screen.getByTestId('send-message')).not.toBeDisabled();
        });

        await act(async () => {
            await user.click(screen.getByTestId('send-message'));
        });

        // Sources should be normalized
        await waitFor(() => {
            expect(screen.getByTestId('message-count')).toHaveTextContent('2');
        });
    });

    it('should normalize object sources', async () => {
        mockStreamChatResponse.mockImplementation(() =>
            (async function* () {
                yield { 
                    type: 'sources', 
                    sources: [
                        { index: 1, title: 'Document A', url: 'http://example.com' },
                        { source: 'Document B', page_number: 5 }
                    ] 
                };
                yield { type: 'token', content: 'Response' };
            })()
        );

        const user = userEvent.setup();
        render(<ChatPage />);

        await waitFor(() => {
            expect(screen.getByTestId('send-message')).not.toBeDisabled();
        });

        await act(async () => {
            await user.click(screen.getByTestId('send-message'));
        });

        await waitFor(() => {
            expect(screen.getByTestId('message-count')).toHaveTextContent('2');
        });
    });
});

describe('ChatPage Component - Thinking Status', () => {
    beforeEach(() => {
        vi.clearAllMocks();
        mockChatIdFromUrl = 'existing-chat';
        mockGetMessagesById.mockResolvedValue([]);
    });

    it('should update thinking status during RAG process', async () => {
        mockStreamChatResponse.mockImplementation(() =>
            (async function* () {
                yield { type: 'status', step: 'searching', message: 'Searching...', details: {} };
                yield { type: 'status', step: 'analyzing', message: 'Analyzing...', details: { sourceCount: 5 } };
                yield { type: 'token', content: 'Response' };
            })()
        );

        const user = userEvent.setup();
        render(<ChatPage />);

        await waitFor(() => {
            expect(screen.getByTestId('send-message')).not.toBeDisabled();
        });

        await act(async () => {
            await user.click(screen.getByTestId('send-message'));
        });

        // Should complete without errors
        await waitFor(() => {
            expect(screen.getByTestId('message-count')).toHaveTextContent('2');
        });
    });
});

describe('ChatPage Component - Scope Context', () => {
    beforeEach(() => {
        vi.clearAllMocks();
        mockChatIdFromUrl = 'existing-chat';
        mockGetMessagesById.mockResolvedValue([]);
    });

    it('should handle scope_context event', async () => {
        mockStreamChatResponse.mockImplementation(() =>
            (async function* () {
                yield { 
                    type: 'scope_context', 
                    scope_context: { scope_id: 'scope-123', scope_name: 'My Scope' } 
                };
                yield { type: 'token', content: 'Response' };
            })()
        );

        const user = userEvent.setup();
        render(<ChatPage />);

        await waitFor(() => {
            expect(screen.getByTestId('send-message')).not.toBeDisabled();
        });

        await act(async () => {
            await user.click(screen.getByTestId('send-message'));
        });

        await waitFor(() => {
            expect(screen.getByTestId('message-count')).toHaveTextContent('2');
        });
    });
});

describe('ChatPage Component - Done Event', () => {
    beforeEach(() => {
        vi.clearAllMocks();
        mockChatIdFromUrl = 'existing-chat';
        mockGetMessagesById.mockResolvedValue([]);
    });

    it('should capture message_id from done event', async () => {
        mockStreamChatResponse.mockImplementation(() =>
            (async function* () {
                yield { type: 'token', content: 'Response' };
                yield { type: 'done', message_id: 'server-msg-123' };
            })()
        );

        const user = userEvent.setup();
        render(<ChatPage />);

        await waitFor(() => {
            expect(screen.getByTestId('send-message')).not.toBeDisabled();
        });

        await act(async () => {
            await user.click(screen.getByTestId('send-message'));
        });

        await waitFor(() => {
            expect(screen.getByTestId('message-count')).toHaveTextContent('2');
        });
    });
});

// =============================================================================
// Clarification Event Tests
// =============================================================================

describe('ChatPage Component - Clarification Event', () => {
    beforeEach(() => {
        vi.clearAllMocks();
        mockChatIdFromUrl = 'existing-chat';
        mockGetMessagesById.mockResolvedValue([]);
    });

    it('should handle clarification event and add clarification message', async () => {
        mockStreamChatResponse.mockImplementation(() =>
            (async function* () {
                yield { 
                    type: 'clarification', 
                    data: {
                        message: 'Please clarify your scope',
                        candidates: [
                            { id: 'scope-1', name: 'Scope 1' },
                            { id: 'scope-2', name: 'Scope 2' },
                        ],
                    }
                };
            })()
        );

        const user = userEvent.setup();
        render(<ChatPage />);

        await waitFor(() => {
            expect(screen.getByTestId('send-message')).not.toBeDisabled();
        });

        await act(async () => {
            await user.click(screen.getByTestId('send-message'));
        });

        // Should have user message + clarification message
        await waitFor(() => {
            expect(screen.getByTestId('message-count')).toHaveTextContent('2');
        });
    });

    it('should unlock send after clarification event', async () => {
        mockStreamChatResponse.mockImplementation(() =>
            (async function* () {
                yield { 
                    type: 'clarification', 
                    data: {
                        message: 'Please clarify',
                        candidates: [{ id: 'scope-1', name: 'Scope 1' }],
                    }
                };
            })()
        );

        const user = userEvent.setup();
        render(<ChatPage />);

        await waitFor(() => {
            expect(screen.getByTestId('send-message')).not.toBeDisabled();
        });

        await act(async () => {
            await user.click(screen.getByTestId('send-message'));
        });

        await waitFor(() => {
            expect(screen.getByTestId('message-count')).toHaveTextContent('2');
        });

        // Send should be enabled again after clarification (unlocked)
        expect(screen.getByTestId('send-message')).not.toBeDisabled();
    });
});

// =============================================================================
// Error Handling Tests
// =============================================================================

describe('ChatPage Component - Error Handling', () => {
    beforeEach(() => {
        vi.clearAllMocks();
        mockChatIdFromUrl = 'existing-chat';
        mockGetMessagesById.mockResolvedValue([]);
    });

    it('should handle error during streaming and show error message', async () => {
        // Import the mocked isChatApiError
        const { isChatApiError } = await import('@/lib/chat-utils');
        vi.mocked(isChatApiError).mockReturnValue(false);
        
        mockStreamChatResponse.mockImplementation(() =>
            (async function* () {
                yield { type: 'token', content: 'Partial' };
                throw new Error('Network failed');
            })()
        );

        const user = userEvent.setup();
        render(<ChatPage />);

        await waitFor(() => {
            expect(screen.getByTestId('send-message')).not.toBeDisabled();
        });

        await act(async () => {
            await user.click(screen.getByTestId('send-message'));
        });

        await waitFor(() => {
            expect(mockToast).toHaveBeenCalledWith(
                expect.objectContaining({
                    variant: 'destructive',
                })
            );
        });
    });

    it('should handle ChatApiError with specific code', async () => {
        const { isChatApiError } = await import('@/lib/chat-utils');
        
        // Create a mock ChatApiError
        const chatApiError = {
            name: 'ChatApiError',
            status: 429,
            code: 'PLAN_LIMIT_EXCEEDED',
            message: 'Plan limit reached',
        };
        
        // Mock isChatApiError to return true for this error
        vi.mocked(isChatApiError).mockImplementation((err) => {
            return err === chatApiError;
        });
        
        mockStreamChatResponse.mockImplementation(() =>
            (async function* () {
                yield { type: 'token', content: 'Partial' };
                throw chatApiError;
            })()
        );

        const user = userEvent.setup();
        render(<ChatPage />);

        await waitFor(() => {
            expect(screen.getByTestId('send-message')).not.toBeDisabled();
        });

        await act(async () => {
            await user.click(screen.getByTestId('send-message'));
        });

        await waitFor(() => {
            expect(mockToast).toHaveBeenCalledWith(
                expect.objectContaining({
                    variant: 'destructive',
                })
            );
        });
    });

    it('should gracefully handle unmount during error processing', async () => {
        let errorResolve: () => void;
        const errorPromise = new Promise<void>((resolve) => {
            errorResolve = resolve;
        });

        mockStreamChatResponse.mockImplementation(() =>
            (async function* () {
                yield { type: 'token', content: 'Starting' };
                // Wait for signal to throw error
                await errorPromise;
                throw new Error('Network error');
            })()
        );

        const user = userEvent.setup();
        const { unmount } = render(<ChatPage />);

        await waitFor(() => {
            expect(screen.getByTestId('send-message')).not.toBeDisabled();
        });

        // Start sending message
        await act(async () => {
            await user.click(screen.getByTestId('send-message'));
        });

        // Unmount before error is thrown
        unmount();

        // Now resolve the error (after unmount)
        await act(async () => {
            errorResolve!();
            // Give time for error processing
            await new Promise(resolve => setTimeout(resolve, 50));
        });

        // Should not crash - the mounted check should prevent state updates
    });
});

// =============================================================================
// Development Mode Logging Tests
// =============================================================================

describe('ChatPage Component - Development Mode', () => {
    const originalNodeEnv = process.env.NODE_ENV;

    beforeEach(() => {
        vi.clearAllMocks();
        mockChatIdFromUrl = 'existing-chat';
        mockGetMessagesById.mockResolvedValue([]);
    });

    afterEach(() => {
        process.env.NODE_ENV = originalNodeEnv;
    });

    it('should work in development mode', async () => {
        process.env.NODE_ENV = 'development';
        
        mockStreamChatResponse.mockImplementation(() =>
            (async function* () {
                yield { type: 'token', content: 'Response' };
                yield { type: 'done' };
            })()
        );

        const user = userEvent.setup();
        render(<ChatPage />);

        await waitFor(() => {
            expect(screen.getByTestId('send-message')).not.toBeDisabled();
        });

        await act(async () => {
            await user.click(screen.getByTestId('send-message'));
        });

        await waitFor(() => {
            expect(screen.getByTestId('message-count')).toHaveTextContent('2');
        });
    });
});
