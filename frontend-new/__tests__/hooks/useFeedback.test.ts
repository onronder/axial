import { describe, it, expect, vi, beforeEach, afterEach } from 'vitest';
import { renderHook, act, waitFor } from '@testing-library/react';
import { useFeedback } from '@/hooks/useFeedback';

// =============================================================================
// Mocks
// =============================================================================

const mockApiPost = vi.fn();
const mockApiGet = vi.fn();
const mockToast = vi.fn();

vi.mock('@/lib/api', () => ({
    api: {
        post: (...args: unknown[]) => mockApiPost(...args),
        get: (...args: unknown[]) => mockApiGet(...args),
    },
    clearAuthCache: vi.fn(),
}));

vi.mock('@/hooks/use-toast', () => ({
    useToast: () => ({ toast: mockToast }),
}));

// =============================================================================
// Test Setup
// =============================================================================

beforeEach(() => {
    vi.clearAllMocks();
    
    // Default successful responses
    mockApiPost.mockResolvedValue({
        data: {
            id: 'feedback-123',
            message_id: 'msg-123',
            rating: 'positive',
            is_update: false,
        },
    });
    
    mockApiGet.mockResolvedValue({
        data: { feedback: {} },
    });
});

afterEach(() => {
    vi.clearAllMocks();
});

// =============================================================================
// Tests
// =============================================================================

describe('useFeedback', () => {
    // =========================================================================
    // Initial State Tests
    // =========================================================================
    
    describe('Initial State', () => {
        it('should have empty feedback state initially', () => {
            const { result } = renderHook(() => useFeedback());
            
            expect(result.current.feedbackState).toEqual({});
        });

        it('should not be submitting initially', () => {
            const { result } = renderHook(() => useFeedback());
            
            expect(result.current.isSubmitting).toBe(false);
        });

        it('should have no error initially', () => {
            const { result } = renderHook(() => useFeedback());
            
            expect(result.current.error).toBeNull();
        });
    });

    // =========================================================================
    // Feedback Submission Tests
    // =========================================================================
    
    describe('Feedback Submission', () => {
        it('should submit positive feedback', async () => {
            const { result } = renderHook(() => useFeedback());

            await act(async () => {
                await result.current.submitFeedback({
                    messageId: 'msg-123',
                    rating: 'positive',
                    queryText: 'What is AI?',
                    answerPreview: 'AI is artificial intelligence...',
                    sources: [],
                });
            });

            expect(mockApiPost).toHaveBeenCalledWith('/chat/feedback', {
                message_id: 'msg-123',
                rating: 'positive',
                query_text: 'What is AI?',
                answer_preview: 'AI is artificial intelligence...',
                sources: [],
                feedback_text: null,
            });
        });

        it('should submit negative feedback', async () => {
            mockApiPost.mockResolvedValue({
                data: {
                    id: 'feedback-456',
                    message_id: 'msg-456',
                    rating: 'negative',
                    is_update: false,
                },
            });

            const { result } = renderHook(() => useFeedback());

            await act(async () => {
                await result.current.submitFeedback({
                    messageId: 'msg-456',
                    rating: 'negative',
                    queryText: 'Why is this wrong?',
                    answerPreview: 'Some incorrect answer...',
                    sources: [],
                    feedbackText: 'This answer is incorrect',
                });
            });

            expect(mockApiPost).toHaveBeenCalledWith('/chat/feedback', expect.objectContaining({
                rating: 'negative',
                feedback_text: 'This answer is incorrect',
            }));
        });

        it('should update local state on success', async () => {
            const { result } = renderHook(() => useFeedback());

            await act(async () => {
                await result.current.submitFeedback({
                    messageId: 'msg-123',
                    rating: 'positive',
                    queryText: 'Test',
                    answerPreview: 'Test',
                    sources: [],
                });
            });

            expect(result.current.feedbackState['msg-123']).toBe('positive');
        });

        it('should show toast for negative feedback with comment', async () => {
            mockApiPost.mockResolvedValue({
                data: { is_update: false, rating: 'negative' },
            });

            const { result } = renderHook(() => useFeedback());

            await act(async () => {
                await result.current.submitFeedback({
                    messageId: 'msg-123',
                    rating: 'negative',
                    queryText: 'Test',
                    answerPreview: 'Test',
                    sources: [],
                    feedbackText: 'This is wrong',
                });
            });

            expect(mockToast).toHaveBeenCalledWith(
                expect.objectContaining({
                    title: 'Feedback submitted',
                })
            );
        });

        it('should not show toast for positive feedback', async () => {
            const { result } = renderHook(() => useFeedback());

            await act(async () => {
                await result.current.submitFeedback({
                    messageId: 'msg-123',
                    rating: 'positive',
                    queryText: 'Test',
                    answerPreview: 'Test',
                    sources: [],
                });
            });

            // Should not show success toast for positive feedback
            expect(mockToast).not.toHaveBeenCalledWith(
                expect.objectContaining({
                    title: 'Feedback submitted',
                })
            );
        });

        it('should include sources in submission', async () => {
            const { result } = renderHook(() => useFeedback());

            const sources = [
                { index: 0, type: 'document', label: 'Doc 1', url: 'http://example.com' },
                { index: 1, type: 'web', label: 'Web 1', page: 5 },
            ];

            await act(async () => {
                await result.current.submitFeedback({
                    messageId: 'msg-123',
                    rating: 'positive',
                    queryText: 'Test',
                    answerPreview: 'Test',
                    sources,
                });
            });

            expect(mockApiPost).toHaveBeenCalledWith('/chat/feedback', expect.objectContaining({
                sources: expect.arrayContaining([
                    expect.objectContaining({ index: 0, label: 'Doc 1' }),
                    expect.objectContaining({ index: 1, label: 'Web 1' }),
                ]),
            }));
        });
    });

    // =========================================================================
    // Validation Tests
    // =========================================================================
    
    describe('Validation', () => {
        it('should reject empty message ID', async () => {
            const { result } = renderHook(() => useFeedback());

            await act(async () => {
                await result.current.submitFeedback({
                    messageId: '',
                    rating: 'positive',
                    queryText: 'Test',
                    answerPreview: 'Test',
                    sources: [],
                });
            });

            expect(result.current.error).toBe('Message ID is required');
            expect(mockApiPost).not.toHaveBeenCalled();
        });

        it('should reject invalid rating', async () => {
            const { result } = renderHook(() => useFeedback());

            await act(async () => {
                await result.current.submitFeedback({
                    messageId: 'msg-123',
                    rating: 'invalid' as 'positive',
                    queryText: 'Test',
                    answerPreview: 'Test',
                    sources: [],
                });
            });

            expect(result.current.error).toBe('Invalid rating');
            expect(mockApiPost).not.toHaveBeenCalled();
        });

        it('should truncate long answer previews', async () => {
            const { result } = renderHook(() => useFeedback());

            const longAnswer = 'A'.repeat(1000);

            await act(async () => {
                await result.current.submitFeedback({
                    messageId: 'msg-123',
                    rating: 'positive',
                    queryText: 'Test',
                    answerPreview: longAnswer,
                    sources: [],
                });
            });

            expect(mockApiPost).toHaveBeenCalledWith('/chat/feedback', expect.objectContaining({
                answer_preview: expect.any(String),
            }));

            const calledWith = mockApiPost.mock.calls[0][1];
            expect(calledWith.answer_preview.length).toBeLessThanOrEqual(500);
        });

        it('should truncate long feedback text', async () => {
            const { result } = renderHook(() => useFeedback());

            const longFeedback = 'F'.repeat(200);

            await act(async () => {
                await result.current.submitFeedback({
                    messageId: 'msg-123',
                    rating: 'negative',
                    queryText: 'Test',
                    answerPreview: 'Test',
                    sources: [],
                    feedbackText: longFeedback,
                });
            });

            const calledWith = mockApiPost.mock.calls[0][1];
            expect(calledWith.feedback_text.length).toBeLessThanOrEqual(100);
        });
    });

    // =========================================================================
    // Error Handling Tests
    // =========================================================================
    
    describe('Error Handling', () => {
        it('should handle API errors', async () => {
            mockApiPost.mockRejectedValue({
                response: {
                    data: {
                        detail: 'Server error',
                    },
                },
            });

            const { result } = renderHook(() => useFeedback());

            await act(async () => {
                await result.current.submitFeedback({
                    messageId: 'msg-123',
                    rating: 'positive',
                    queryText: 'Test',
                    answerPreview: 'Test',
                    sources: [],
                });
            });

            expect(result.current.error).toBe('Server error');
        });

        it('should show error toast on failure', async () => {
            mockApiPost.mockRejectedValue({
                response: {
                    data: {
                        detail: 'Validation error',
                    },
                },
            });

            const { result } = renderHook(() => useFeedback());

            await act(async () => {
                await result.current.submitFeedback({
                    messageId: 'msg-123',
                    rating: 'positive',
                    queryText: 'Test',
                    answerPreview: 'Test',
                    sources: [],
                });
            });

            expect(mockToast).toHaveBeenCalledWith(
                expect.objectContaining({
                    title: 'Failed to submit feedback',
                    variant: 'destructive',
                })
            );
        });

        it('should clear error on successful submit', async () => {
            // First call fails
            mockApiPost.mockRejectedValueOnce({
                response: { data: { detail: 'Error' } },
            });

            const { result } = renderHook(() => useFeedback());

            // First submission fails
            await act(async () => {
                await result.current.submitFeedback({
                    messageId: 'msg-123',
                    rating: 'positive',
                    queryText: 'Test',
                    answerPreview: 'Test',
                    sources: [],
                });
            });

            expect(result.current.error).toBe('Error');

            // Second call succeeds
            mockApiPost.mockResolvedValueOnce({
                data: { is_update: false },
            });

            await act(async () => {
                await result.current.submitFeedback({
                    messageId: 'msg-456',
                    rating: 'positive',
                    queryText: 'Test',
                    answerPreview: 'Test',
                    sources: [],
                });
            });

            expect(result.current.error).toBeNull();
        });
    });

    // =========================================================================
    // Conversation Feedback Tests
    // =========================================================================
    
    describe('Conversation Feedback', () => {
        it('should load existing feedback for conversation', async () => {
            mockApiGet.mockResolvedValue({
                data: {
                    feedback: {
                        'msg-1': 'positive',
                        'msg-2': 'negative',
                    },
                },
            });

            const { result } = renderHook(() => useFeedback('conv-123'));

            await waitFor(() => {
                expect(result.current.feedbackState).toEqual({
                    'msg-1': 'positive',
                    'msg-2': 'negative',
                });
            });

            expect(mockApiGet).toHaveBeenCalledWith('/chat/feedback/conversation/conv-123');
        });

        it('should clear feedback when conversation changes to undefined', async () => {
            mockApiGet.mockResolvedValue({
                data: {
                    feedback: {
                        'msg-1': 'positive',
                    },
                },
            });

            const { result, rerender } = renderHook(
                ({ conversationId }) => useFeedback(conversationId),
                { initialProps: { conversationId: 'conv-123' } }
            );

            await waitFor(() => {
                expect(result.current.feedbackState).toEqual({
                    'msg-1': 'positive',
                });
            });

            // Change conversation to undefined
            rerender({ conversationId: undefined as unknown as string });

            await waitFor(() => {
                expect(result.current.feedbackState).toEqual({});
            });
        });

        it('should refresh feedback when conversation changes', async () => {
            mockApiGet.mockResolvedValueOnce({
                data: { feedback: { 'msg-1': 'positive' } },
            });

            const { result, rerender } = renderHook(
                ({ conversationId }) => useFeedback(conversationId),
                { initialProps: { conversationId: 'conv-123' } }
            );

            await waitFor(() => {
                expect(mockApiGet).toHaveBeenCalledWith('/chat/feedback/conversation/conv-123');
            });

            mockApiGet.mockResolvedValueOnce({
                data: { feedback: { 'msg-2': 'negative' } },
            });

            // Change to different conversation
            rerender({ conversationId: 'conv-456' });

            await waitFor(() => {
                expect(mockApiGet).toHaveBeenCalledWith('/chat/feedback/conversation/conv-456');
            });
        });
    });

    // =========================================================================
    // Loading State Tests
    // =========================================================================
    
    describe('Loading State', () => {
        it('should set isSubmitting during submission', async () => {
            let resolvePromise: (value: unknown) => void;
            mockApiPost.mockImplementation(() => new Promise((resolve) => {
                resolvePromise = resolve;
            }));

            const { result } = renderHook(() => useFeedback());

            // Start submission
            let submitPromise: Promise<void>;
            act(() => {
                submitPromise = result.current.submitFeedback({
                    messageId: 'msg-123',
                    rating: 'positive',
                    queryText: 'Test',
                    answerPreview: 'Test',
                    sources: [],
                });
            });

            // Check loading state
            expect(result.current.isSubmitting).toBe(true);

            // Resolve the API call
            await act(async () => {
                resolvePromise!({ data: { is_update: false } });
                await submitPromise;
            });

            // Check loading state cleared
            expect(result.current.isSubmitting).toBe(false);
        });
    });

    // =========================================================================
    // Refresh Tests
    // =========================================================================
    
    describe('Refresh', () => {
        it('should manually refresh feedback via refreshFeedback', async () => {
            mockApiGet.mockResolvedValue({
                data: { feedback: { 'msg-1': 'positive' } },
            });

            const { result } = renderHook(() => useFeedback('conv-123'));

            // Initial load
            await waitFor(() => {
                expect(mockApiGet).toHaveBeenCalledTimes(1);
            });

            // Manual refresh
            await act(async () => {
                await result.current.refreshFeedback();
            });

            expect(mockApiGet).toHaveBeenCalledTimes(2);
        });

        it('should not refresh without conversation ID', async () => {
            const { result } = renderHook(() => useFeedback());

            await act(async () => {
                await result.current.refreshFeedback();
            });

            expect(mockApiGet).not.toHaveBeenCalled();
        });
    });

    // =========================================================================
    // Error Message Extraction Tests
    // =========================================================================
    
    describe('Error Message Extraction', () => {
        it('should extract nested message from detail object', async () => {
            mockApiPost.mockRejectedValue({
                response: {
                    data: {
                        detail: { message: 'Nested error message' },
                    },
                },
            });

            const { result } = renderHook(() => useFeedback());

            await act(async () => {
                await result.current.submitFeedback({
                    messageId: 'msg-123',
                    rating: 'positive',
                    queryText: 'Test',
                    answerPreview: 'Test',
                    sources: [],
                });
            });

            expect(result.current.error).toBe('Nested error message');
        });

        it('should use error.message when detail is not available', async () => {
            mockApiPost.mockRejectedValue({
                message: 'Direct error message',
            });

            const { result } = renderHook(() => useFeedback());

            await act(async () => {
                await result.current.submitFeedback({
                    messageId: 'msg-123',
                    rating: 'positive',
                    queryText: 'Test',
                    answerPreview: 'Test',
                    sources: [],
                });
            });

            expect(result.current.error).toBe('Direct error message');
        });

        it('should use default message when no error details available', async () => {
            mockApiPost.mockRejectedValue({});

            const { result } = renderHook(() => useFeedback());

            await act(async () => {
                await result.current.submitFeedback({
                    messageId: 'msg-123',
                    rating: 'positive',
                    queryText: 'Test',
                    answerPreview: 'Test',
                    sources: [],
                });
            });

            expect(result.current.error).toBe('Something went wrong. Please try again.');
        });
    });

    // =========================================================================
    // Refresh Feedback Error Handling Tests
    // =========================================================================
    
    describe('Refresh Feedback Error', () => {
        it('should silently handle refresh feedback failure', async () => {
            const debugSpy = vi.spyOn(console, 'debug').mockImplementation(() => {});
            
            mockApiGet.mockRejectedValue(new Error('Network error'));

            const { result } = renderHook(() => useFeedback('conv-123'));

            await waitFor(() => {
                // Should have attempted to fetch
                expect(mockApiGet).toHaveBeenCalled();
            });

            // Should have logged debug message
            expect(debugSpy).toHaveBeenCalledWith(
                '[useFeedback] Failed to fetch feedback state:',
                expect.any(Error)
            );

            // State should remain empty (no crash)
            expect(result.current.feedbackState).toEqual({});

            debugSpy.mockRestore();
        });

        it('should handle empty feedback response', async () => {
            mockApiGet.mockResolvedValue({
                data: { feedback: null },
            });

            const { result } = renderHook(() => useFeedback('conv-123'));

            await waitFor(() => {
                expect(mockApiGet).toHaveBeenCalled();
            });

            // Should default to empty object
            expect(result.current.feedbackState).toEqual({});
        });
    });

    // =========================================================================
    // Debug Logging Tests
    // =========================================================================
    
    describe('Debug Logging', () => {
        it('should log successful feedback submission', async () => {
            const debugSpy = vi.spyOn(console, 'debug').mockImplementation(() => {});
            
            mockApiPost.mockResolvedValue({
                data: {
                    id: 'feedback-123',
                    message_id: 'msg-123',
                    rating: 'positive',
                    is_update: false,
                },
            });

            const { result } = renderHook(() => useFeedback());

            await act(async () => {
                await result.current.submitFeedback({
                    messageId: 'msg-123',
                    rating: 'positive',
                    queryText: 'Test',
                    answerPreview: 'Test',
                    sources: [],
                });
            });

            expect(debugSpy).toHaveBeenCalledWith(
                expect.stringContaining('[useFeedback] Submitted positive feedback'),
                '(new)'
            );

            debugSpy.mockRestore();
        });

        it('should log updated feedback submission', async () => {
            const debugSpy = vi.spyOn(console, 'debug').mockImplementation(() => {});
            
            mockApiPost.mockResolvedValue({
                data: {
                    id: 'feedback-123',
                    message_id: 'msg-123',
                    rating: 'negative',
                    is_update: true,
                },
            });

            const { result } = renderHook(() => useFeedback());

            await act(async () => {
                await result.current.submitFeedback({
                    messageId: 'msg-123',
                    rating: 'negative',
                    queryText: 'Test',
                    answerPreview: 'Test',
                    sources: [],
                });
            });

            expect(debugSpy).toHaveBeenCalledWith(
                expect.stringContaining('[useFeedback] Submitted negative feedback'),
                '(updated)'
            );

            debugSpy.mockRestore();
        });
    });

    // =========================================================================
    // Source Snapshot Edge Cases
    // =========================================================================
    
    describe('Source Snapshot Edge Cases', () => {
        it('should handle sources with all fields', async () => {
            const { result } = renderHook(() => useFeedback());

            const fullSource = {
                index: 0,
                type: 'document',
                label: 'Document Title',
                url: 'http://example.com/doc',
                page: 5,
                section: 'Introduction',
            };

            await act(async () => {
                await result.current.submitFeedback({
                    messageId: 'msg-123',
                    rating: 'positive',
                    queryText: 'Test',
                    answerPreview: 'Test',
                    sources: [fullSource],
                });
            });

            expect(mockApiPost).toHaveBeenCalledWith('/chat/feedback', expect.objectContaining({
                sources: [fullSource],
            }));
        });

        it('should handle sources with minimal fields', async () => {
            const { result } = renderHook(() => useFeedback());

            const minimalSource = {
                label: 'Minimal',
            };

            await act(async () => {
                await result.current.submitFeedback({
                    messageId: 'msg-123',
                    rating: 'positive',
                    queryText: 'Test',
                    answerPreview: 'Test',
                    sources: [minimalSource],
                });
            });

            expect(mockApiPost).toHaveBeenCalledWith('/chat/feedback', expect.objectContaining({
                sources: expect.arrayContaining([
                    expect.objectContaining({ label: 'Minimal' }),
                ]),
            }));
        });
    });
});
