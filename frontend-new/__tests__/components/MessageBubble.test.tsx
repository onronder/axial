/**
 * Test Suite: MessageBubble Component
 *
 * Comprehensive tests for:
 * - User vs assistant message styling
 * - Citation parsing and rendering
 * - Source pills rendering
 * - Streaming cursor display
 * - Markdown-like formatting (headings, bullets)
 * - Feedback buttons integration
 */

import { describe, it, expect, vi, beforeEach, afterEach } from 'vitest';
import { render, screen, fireEvent, cleanup } from '@testing-library/react';
import { MessageBubble } from '@/components/chat/MessageBubble';

// =============================================================================
// Test Setup
// =============================================================================

const createUserMessage = (content: string, overrides = {}) => ({
    id: 'user-1',
    role: 'user' as const,
    content,
    created_at: '2024-01-01T00:00:00Z',
    ...overrides,
});

const createAssistantMessage = (content: string, overrides = {}) => ({
    id: 'assistant-1',
    role: 'assistant' as const,
    content,
    created_at: '2024-01-01T00:00:00Z',
    ...overrides,
});

describe('MessageBubble Component', () => {
    beforeEach(() => {
        vi.clearAllMocks();
    });

    afterEach(() => {
        cleanup();
    });

    describe('User Message Rendering', () => {
        it('renders user message correctly', () => {
            render(<MessageBubble message={createUserMessage('Hello, AI!')} />);

            expect(screen.getByText('Hello, AI!')).toBeInTheDocument();
        });

        it('renders user message with correct styling (gradient background)', () => {
            const { container } = render(<MessageBubble message={createUserMessage('Hello')} />);

            const messageWrapper = container.querySelector('.flex-row-reverse');
            expect(messageWrapper).toBeInTheDocument();
        });

        it('shows user icon for user messages', () => {
            const { container } = render(<MessageBubble message={createUserMessage('Hello')} />);

            // User icon should be in a gradient background container
            const iconContainer = container.querySelector('.bg-axio-gradient');
            expect(iconContainer).toBeInTheDocument();
        });

        it('does not show sources for user messages', () => {
            render(
                <MessageBubble
                    message={createUserMessage('Hello', {
                        sources: [{ index: 1, type: 'web', label: 'Source 1' }],
                    })}
                />
            );

            expect(screen.queryByText('Source 1')).not.toBeInTheDocument();
        });

        it('does not show feedback buttons for user messages', () => {
            const onFeedbackSubmit = vi.fn();
            render(
                <MessageBubble
                    message={createUserMessage('Hello')}
                    onFeedbackSubmit={onFeedbackSubmit}
                />
            );

            expect(screen.queryByRole('button', { name: /helpful/i })).not.toBeInTheDocument();
        });
    });

    describe('Assistant Message Rendering', () => {
        it('renders assistant message correctly', () => {
            render(<MessageBubble message={createAssistantMessage('Hello, human!')} />);

            expect(screen.getByText('Hello, human!')).toBeInTheDocument();
        });

        it('renders assistant message with muted background', () => {
            const { container } = render(
                <MessageBubble message={createAssistantMessage('Hello')} />
            );

            const bubble = container.querySelector('.bg-muted\\/50');
            expect(bubble).toBeInTheDocument();
        });

        it('does not reverse row direction for assistant messages', () => {
            const { container } = render(
                <MessageBubble message={createAssistantMessage('Hello')} />
            );

            const messageWrapper = container.querySelector('.flex-row-reverse');
            expect(messageWrapper).not.toBeInTheDocument();
        });

        it('renders amber faithfulness warning banner when provided', () => {
            render(
                <MessageBubble
                    message={createAssistantMessage('Answer', {
                        faithfulness_warning: 'Some claims may not be fully supported',
                    })}
                />
            );

            expect(screen.getByTestId('faithfulness-warning-banner')).toBeInTheDocument();
            expect(screen.getByTestId('faithfulness-warning-icon')).toBeInTheDocument();
            expect(
                screen.getByText('Some claims may not be fully supported')
            ).toBeInTheDocument();
        });

        it('does not render warning banner when faithfulness warning is absent', () => {
            render(<MessageBubble message={createAssistantMessage('Answer')} />);

            expect(screen.queryByTestId('faithfulness-warning-banner')).not.toBeInTheDocument();
        });
    });

    describe('Citation Parsing', () => {
        it('parses single citation [1]', () => {
            render(
                <MessageBubble
                    message={createAssistantMessage('This is a fact [1].')}
                />
            );

            // Citation should be rendered as a badge/span
            expect(screen.getByText('1')).toBeInTheDocument();
        });

        it('parses multiple citations [1] [2] [3]', () => {
            const { container } = render(
                <MessageBubble
                    message={createAssistantMessage('First [1], second [2], third [3].')}
                />
            );

            // Find citation buttons by role and title
            expect(container.querySelector('[title="Source 1"]')).toBeInTheDocument();
            expect(container.querySelector('[title="Source 2"]')).toBeInTheDocument();
            expect(container.querySelector('[title="Source 3"]')).toBeInTheDocument();
        });

        it('renders citation as interactive element', () => {
            const { container } = render(
                <MessageBubble
                    message={createAssistantMessage('Reference [1] here.')}
                />
            );

            const citationBadge = container.querySelector('.cursor-pointer');
            expect(citationBadge).toBeInTheDocument();
        });

        it('highlights citation on hover', () => {
            const { container } = render(
                <MessageBubble
                    message={createAssistantMessage('Reference [1] here.')}
                />
            );

            const citationBadge = container.querySelector('[title="Source 1"]');
            expect(citationBadge).toBeInTheDocument();

            // Simulate hover
            fireEvent.mouseEnter(citationBadge!);

            // Check for highlight class
            expect(citationBadge).toHaveClass('ring-2');
        });
    });

    describe('Source Pills', () => {
        it('renders source pills for assistant messages', () => {
            render(
                <MessageBubble
                    message={createAssistantMessage('Answer', {
                        sources: [
                            { index: 1, type: 'web', label: 'Source Document' },
                        ],
                    })}
                />
            );

            // Source pills may have type appended like "Source Document (Web Crawl)"
            expect(screen.getByText(/Source Document/)).toBeInTheDocument();
        });

        it('renders multiple source pills', () => {
            render(
                <MessageBubble
                    message={createAssistantMessage('Answer', {
                        sources: [
                            { index: 1, type: 'web', label: 'Source 1' },
                            { index: 2, type: 'file', label: 'Source 2' },
                            { index: 3, type: 'notion', label: 'Source 3' },
                        ],
                    })}
                />
            );

            expect(screen.getByText(/Source 1/)).toBeInTheDocument();
            expect(screen.getByText(/Source 2/)).toBeInTheDocument();
            expect(screen.getByText(/Source 3/)).toBeInTheDocument();
        });

        it('normalizes string sources', () => {
            render(
                <MessageBubble
                    message={createAssistantMessage('Answer', {
                        sources: ['https://example.com', 'document.pdf'],
                    })}
                />
            );

            expect(screen.getByText(/example\.com/)).toBeInTheDocument();
            expect(screen.getByText(/document\.pdf/)).toBeInTheDocument();
        });

        it('handles empty sources array', () => {
            const { container } = render(
                <MessageBubble
                    message={createAssistantMessage('Answer', { sources: [] })}
                />
            );

            // Should not render source nav section
            const sourceNav = container.querySelector('nav[aria-label="Source citations"]');
            expect(sourceNav).not.toBeInTheDocument();
        });
    });

    describe('Streaming Cursor', () => {
        it('shows streaming cursor when isStreaming is true', () => {
            const { container } = render(
                <MessageBubble
                    message={createAssistantMessage('Typing...')}
                    isStreaming={true}
                />
            );

            const cursor = container.querySelector('.animate-pulse');
            expect(cursor).toBeInTheDocument();
        });

        it('hides streaming cursor when isStreaming is false', () => {
            const { container } = render(
                <MessageBubble
                    message={createAssistantMessage('Done typing')}
                    isStreaming={false}
                />
            );

            const cursor = container.querySelector('.animate-pulse');
            expect(cursor).not.toBeInTheDocument();
        });

        it('shows streaming cursor for any message when isStreaming is true', () => {
            // Note: In practice, user messages wouldn't be streamed,
            // but the component renders cursor based on isStreaming prop regardless of role
            const { container } = render(
                <MessageBubble
                    message={createUserMessage('User message')}
                    isStreaming={true}
                />
            );

            // Cursor is rendered based on isStreaming prop, not role
            const cursor = container.querySelector('[aria-label="AI is typing"]');
            expect(cursor).toBeInTheDocument();
        });
    });

    describe('Markdown-like Formatting', () => {
        it('renders headings with **bold** markers', () => {
            const { container } = render(
                <MessageBubble
                    message={createAssistantMessage('**Section Title**')}
                />
            );

            const heading = container.querySelector('.font-semibold');
            expect(heading).toBeInTheDocument();
            expect(heading?.textContent).toBe('Section Title');
        });

        it('renders bullet points', () => {
            const { container } = render(
                <MessageBubble
                    message={createAssistantMessage('- First item\n- Second item')}
                />
            );

            const bullets = container.querySelectorAll('.list-disc');
            expect(bullets.length).toBe(2);
        });

        it('renders blank lines as line breaks', () => {
            render(
                <MessageBubble
                    message={createAssistantMessage('Line 1\n\nLine 3')}
                />
            );

            expect(screen.getByText('Line 1')).toBeInTheDocument();
            expect(screen.getByText('Line 3')).toBeInTheDocument();
        });

        it('renders regular text in paragraphs', () => {
            const { container } = render(
                <MessageBubble
                    message={createAssistantMessage('Regular paragraph text.')}
                />
            );

            const paragraph = container.querySelector('.leading-relaxed');
            expect(paragraph).toBeInTheDocument();
        });
    });

    describe('Feedback Buttons', () => {
        it('renders feedback buttons for assistant messages', () => {
            const onFeedbackSubmit = vi.fn();
            render(
                <MessageBubble
                    message={createAssistantMessage('Answer')}
                    onFeedbackSubmit={onFeedbackSubmit}
                />
            );

            expect(screen.getByTitle('Mark as helpful')).toBeInTheDocument();
            expect(screen.getByTitle('Mark as not helpful')).toBeInTheDocument();
        });

        it('does not render feedback buttons during streaming', () => {
            const onFeedbackSubmit = vi.fn();
            render(
                <MessageBubble
                    message={createAssistantMessage('Streaming...')}
                    onFeedbackSubmit={onFeedbackSubmit}
                    isStreaming={true}
                />
            );

            expect(screen.queryByTitle('Mark as helpful')).not.toBeInTheDocument();
        });

        it('does not render feedback buttons without onFeedbackSubmit', () => {
            render(<MessageBubble message={createAssistantMessage('Answer')} />);

            expect(screen.queryByTitle('Mark as helpful')).not.toBeInTheDocument();
        });

        it('passes correct props to feedback buttons', () => {
            const onFeedbackSubmit = vi.fn();
            render(
                <MessageBubble
                    message={createAssistantMessage('Answer', {
                        sources: [{ index: 1, type: 'web', label: 'Source' }],
                    })}
                    onFeedbackSubmit={onFeedbackSubmit}
                    previousUserQuery="What is X?"
                    feedbackRating="positive"
                    isFeedbackSubmitting={true}
                />
            );

            // Feedback buttons should be rendered
            const thumbsUpButton = screen.getByTitle('Marked as helpful');
            expect(thumbsUpButton).toBeInTheDocument();
        });
    });

    describe('Source Normalization', () => {
        it('normalizes source with legacy fields', () => {
            render(
                <MessageBubble
                    message={createAssistantMessage('Answer', {
                        sources: [
                            {
                                source: 'web',
                                source_type: 'web',
                                title: 'Legacy Title',
                                source_url: 'https://example.com',
                            },
                        ],
                    })}
                />
            );

            expect(screen.getByText(/Legacy Title/)).toBeInTheDocument();
        });

        it('prefers label over title', () => {
            render(
                <MessageBubble
                    message={createAssistantMessage('Answer', {
                        sources: [
                            {
                                index: 1,
                                type: 'web',
                                label: 'Primary Label',
                                title: 'Secondary Title',
                            },
                        ],
                    })}
                />
            );

            expect(screen.getByText(/Primary Label/)).toBeInTheDocument();
        });

        it('assigns sequential index to sources without index', () => {
            render(
                <MessageBubble
                    message={createAssistantMessage('Check [1] and [2]', {
                        sources: [
                            { type: 'web', label: 'First Source' },
                            { type: 'web', label: 'Second Source' },
                        ],
                    })}
                />
            );

            // Both sources should be rendered (with type suffix)
            expect(screen.getByText(/First Source/)).toBeInTheDocument();
            expect(screen.getByText(/Second Source/)).toBeInTheDocument();
        });
    });

    describe('Citation-Source Highlight Sync', () => {
        it('highlights source when citation is hovered', () => {
            const { container } = render(
                <MessageBubble
                    message={createAssistantMessage('Reference [1]', {
                        sources: [{ index: 1, type: 'web', label: 'Source 1' }],
                    })}
                />
            );

            // Find citation badge (inline citation [1])
            const citationBadge = container.querySelector('[role="button"][title="Source 1"]');
            expect(citationBadge).toBeInTheDocument();

            fireEvent.mouseEnter(citationBadge!);

            // Citation should have highlight class after hover
            expect(citationBadge).toHaveClass('ring-2');
        });

        it('removes highlight when mouse leaves citation', () => {
            const { container } = render(
                <MessageBubble
                    message={createAssistantMessage('Reference [1]', {
                        sources: [{ index: 1, type: 'web', label: 'Source 1' }],
                    })}
                />
            );

            const citationBadge = container.querySelector('[role="button"][title="Source 1"]');
            fireEvent.mouseEnter(citationBadge!);
            fireEvent.mouseLeave(citationBadge!);

            // Highlight should be removed (no ring-offset-1)
            expect(citationBadge).not.toHaveClass('ring-offset-1');
        });
    });

    describe('Edge Cases', () => {
        it('handles empty content', () => {
            const { container } = render(<MessageBubble message={createAssistantMessage('')} />);

            // Should render without crashing - article container should exist
            expect(container.querySelector('[role="article"]')).toBeInTheDocument();
        });

        it('handles message without id', () => {
            const onFeedbackSubmit = vi.fn();
            const { container } = render(
                <MessageBubble
                    message={{ ...createAssistantMessage('Test'), id: '' }}
                    onFeedbackSubmit={onFeedbackSubmit}
                />
            );

            // Should not render feedback buttons without valid id (empty string is falsy)
            expect(container.querySelector('[title="Mark as helpful"]')).not.toBeInTheDocument();
        });

        it('handles very long content', () => {
            const longContent = 'A'.repeat(10000);
            const { getByText } = render(<MessageBubble message={createAssistantMessage(longContent)} />);

            // Should render without crashing
            expect(getByText(longContent)).toBeInTheDocument();
        });
    });
});
