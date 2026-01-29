/**
 * Test Suite: FeedbackButtons Component
 *
 * Comprehensive tests for:
 * - Thumbs up/down button rendering
 * - Positive feedback submission
 * - Negative feedback with comment modal
 * - Thank you message display
 * - Error handling with rollback
 * - Disabled state
 * - Current rating state display
 */

import { describe, it, expect, vi, beforeEach, afterEach } from 'vitest';
import { render, screen, fireEvent, waitFor, act, cleanup } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { FeedbackButtons } from '@/components/chat/FeedbackButtons';

// =============================================================================
// Test Setup
// =============================================================================

const defaultProps = {
    messageId: 'msg-123',
    sources: [{ index: 1, type: 'web', label: 'Source 1' }],
    queryText: 'What is the answer?',
    answerPreview: 'The answer is 42.',
    onSubmit: vi.fn().mockResolvedValue(undefined),
};

describe('FeedbackButtons Component', () => {
    beforeEach(() => {
        vi.clearAllMocks();
        vi.useFakeTimers({ shouldAdvanceTime: true });
    });

    afterEach(() => {
        cleanup();
        vi.useRealTimers();
    });

    describe('Rendering', () => {
        it('renders thumbs up and thumbs down buttons', () => {
            render(<FeedbackButtons {...defaultProps} />);

            expect(screen.getByTitle('Mark as helpful')).toBeInTheDocument();
            expect(screen.getByTitle('Mark as not helpful')).toBeInTheDocument();
        });

        it('renders buttons with correct initial state (unselected)', () => {
            const { container } = render(<FeedbackButtons {...defaultProps} />);

            // Both buttons should have muted text color (not selected)
            const buttons = container.querySelectorAll('.text-muted-foreground');
            expect(buttons.length).toBeGreaterThan(0);
        });

        it('accepts custom className', () => {
            const { container } = render(
                <FeedbackButtons {...defaultProps} className="custom-class" />
            );

            expect(container.querySelector('.custom-class')).toBeInTheDocument();
        });
    });

    describe('Positive Feedback (Thumbs Up)', () => {
        it('calls onSubmit with positive rating when thumbs up is clicked', async () => {
            const onSubmit = vi.fn().mockResolvedValue(undefined);
            const user = userEvent.setup({ advanceTimers: vi.advanceTimersByTime });
            const { container } = render(<FeedbackButtons {...defaultProps} onSubmit={onSubmit} />);

            const thumbsUp = container.querySelector('[title="Mark as helpful"]') as HTMLElement;
            await user.click(thumbsUp);

            expect(onSubmit).toHaveBeenCalledWith('msg-123', 'positive');
        });

        it('shows thank you message after positive feedback', async () => {
            const user = userEvent.setup({ advanceTimers: vi.advanceTimersByTime });
            const { container, getByText } = render(<FeedbackButtons {...defaultProps} />);

            const thumbsUp = container.querySelector('[title="Mark as helpful"]') as HTMLElement;
            await user.click(thumbsUp);

            expect(getByText('Thanks!')).toBeInTheDocument();
        });

        it('hides thank you message after 2 seconds', async () => {
            const user = userEvent.setup({ advanceTimers: vi.advanceTimersByTime });
            const { container, queryByText, getByText } = render(<FeedbackButtons {...defaultProps} />);

            const thumbsUp = container.querySelector('[title="Mark as helpful"]') as HTMLElement;
            await user.click(thumbsUp);

            expect(getByText('Thanks!')).toBeInTheDocument();

            // Advance timer by 2 seconds
            await act(async () => {
                vi.advanceTimersByTime(2100);
            });

            await waitFor(() => {
                expect(queryByText('Thanks!')).not.toBeInTheDocument();
            });
        });

        it('highlights thumbs up button after positive feedback', async () => {
            const user = userEvent.setup({ advanceTimers: vi.advanceTimersByTime });
            const { container } = render(<FeedbackButtons {...defaultProps} />);

            const thumbsUp = container.querySelector('[title="Mark as helpful"]') as HTMLElement;
            await user.click(thumbsUp);

            // Button should now show as selected (green styling)
            expect(container.querySelector('[title="Marked as helpful"]')).toBeInTheDocument();
        });

        it('does nothing if already rated positive', async () => {
            const onSubmit = vi.fn().mockResolvedValue(undefined);
            const user = userEvent.setup({ advanceTimers: vi.advanceTimersByTime });
            const { container } = render(
                <FeedbackButtons
                    {...defaultProps}
                    onSubmit={onSubmit}
                    currentRating="positive"
                />
            );

            const thumbsUp = container.querySelector('[title="Marked as helpful"]') as HTMLElement;
            await user.click(thumbsUp);

            // Should not call onSubmit again
            expect(onSubmit).not.toHaveBeenCalled();
        });
    });

    describe('Negative Feedback (Thumbs Down)', () => {
        it('opens comment modal when thumbs down is clicked', async () => {
            const user = userEvent.setup({ advanceTimers: vi.advanceTimersByTime });
            const { container } = render(<FeedbackButtons {...defaultProps} />);

            const thumbsDown = container.querySelector('[title="Mark as not helpful"]') as HTMLElement;
            await user.click(thumbsDown);

            expect(screen.getByText('Help us improve')).toBeInTheDocument();
        });

        it('shows textarea for comment in modal', async () => {
            const user = userEvent.setup({ advanceTimers: vi.advanceTimersByTime });
            const { container } = render(<FeedbackButtons {...defaultProps} />);

            const thumbsDown = container.querySelector('[title="Mark as not helpful"]') as HTMLElement;
            await user.click(thumbsDown);

            expect(screen.getByPlaceholderText(/Tell us what went wrong/)).toBeInTheDocument();
        });

        it('submits negative feedback with comment', async () => {
            const onSubmit = vi.fn().mockResolvedValue(undefined);
            const user = userEvent.setup({ advanceTimers: vi.advanceTimersByTime });
            const { container } = render(<FeedbackButtons {...defaultProps} onSubmit={onSubmit} />);

            const thumbsDown = container.querySelector('[title="Mark as not helpful"]') as HTMLElement;
            await user.click(thumbsDown);

            const textarea = screen.getByPlaceholderText(/Tell us what went wrong/);
            await user.type(textarea, 'Incorrect information');

            const submitButton = screen.getByRole('button', { name: /Submit Feedback/i });
            await user.click(submitButton);

            expect(onSubmit).toHaveBeenCalledWith('msg-123', 'negative', 'Incorrect information');
        });

        it('submits negative feedback without comment', async () => {
            const onSubmit = vi.fn().mockResolvedValue(undefined);
            const user = userEvent.setup({ advanceTimers: vi.advanceTimersByTime });
            const { container } = render(<FeedbackButtons {...defaultProps} onSubmit={onSubmit} />);

            const thumbsDown = container.querySelector('[title="Mark as not helpful"]') as HTMLElement;
            await user.click(thumbsDown);

            const submitButton = screen.getByRole('button', { name: /Submit Feedback/i });
            await user.click(submitButton);

            expect(onSubmit).toHaveBeenCalledWith('msg-123', 'negative', undefined);
        });

        it('closes modal on cancel', async () => {
            const user = userEvent.setup({ advanceTimers: vi.advanceTimersByTime });
            const { container } = render(<FeedbackButtons {...defaultProps} />);

            const thumbsDown = container.querySelector('[title="Mark as not helpful"]') as HTMLElement;
            await user.click(thumbsDown);

            expect(screen.getByText('Help us improve')).toBeInTheDocument();

            const cancelButton = screen.getByRole('button', { name: /Cancel/i });
            await user.click(cancelButton);

            await waitFor(() => {
                expect(screen.queryByText('Help us improve')).not.toBeInTheDocument();
            });
        });

        it('clears comment on cancel', async () => {
            const user = userEvent.setup({ advanceTimers: vi.advanceTimersByTime });
            const { container } = render(<FeedbackButtons {...defaultProps} />);

            const thumbsDown = container.querySelector('[title="Mark as not helpful"]') as HTMLElement;
            await user.click(thumbsDown);

            const textarea = screen.getByPlaceholderText(/Tell us what went wrong/);
            await user.type(textarea, 'Some comment');

            const cancelButton = screen.getByRole('button', { name: /Cancel/i });
            await user.click(cancelButton);

            // Re-open modal
            const thumbsDownAgain = container.querySelector('[title="Mark as not helpful"]') as HTMLElement;
            await user.click(thumbsDownAgain);

            // Comment should be cleared
            const newTextarea = screen.getByPlaceholderText(/Tell us what went wrong/);
            expect(newTextarea).toHaveValue('');
        });

        it('limits comment to 100 characters', async () => {
            const user = userEvent.setup({ advanceTimers: vi.advanceTimersByTime });
            const { container } = render(<FeedbackButtons {...defaultProps} />);

            const thumbsDown = container.querySelector('[title="Mark as not helpful"]') as HTMLElement;
            await user.click(thumbsDown);

            const textarea = screen.getByPlaceholderText(/Tell us what went wrong/);
            const longText = 'A'.repeat(150);
            await user.type(textarea, longText);

            expect(textarea).toHaveValue('A'.repeat(100));
        });

        it('shows character count', async () => {
            const user = userEvent.setup({ advanceTimers: vi.advanceTimersByTime });
            const { container } = render(<FeedbackButtons {...defaultProps} />);

            const thumbsDown = container.querySelector('[title="Mark as not helpful"]') as HTMLElement;
            await user.click(thumbsDown);

            expect(screen.getByText('0/100')).toBeInTheDocument();

            const textarea = screen.getByPlaceholderText(/Tell us what went wrong/);
            await user.type(textarea, 'Test comment');

            expect(screen.getByText('12/100')).toBeInTheDocument();
        });
    });

    describe('Error Handling', () => {
        it('reverts positive rating on submission error', async () => {
            const onSubmit = vi.fn().mockRejectedValue(new Error('Network error'));
            const user = userEvent.setup({ advanceTimers: vi.advanceTimersByTime });
            const { container } = render(<FeedbackButtons {...defaultProps} onSubmit={onSubmit} />);

            const thumbsUp = container.querySelector('[title="Mark as helpful"]') as HTMLElement;
            await user.click(thumbsUp);

            // Should revert to unselected state
            await waitFor(() => {
                expect(container.querySelector('[title="Mark as helpful"]')).toBeInTheDocument();
            });
        });

        it('reverts negative rating on submission error', async () => {
            const onSubmit = vi.fn().mockRejectedValue(new Error('Network error'));
            const user = userEvent.setup({ advanceTimers: vi.advanceTimersByTime });
            const { container } = render(<FeedbackButtons {...defaultProps} onSubmit={onSubmit} />);

            const thumbsDown = container.querySelector('[title="Mark as not helpful"]') as HTMLElement;
            await user.click(thumbsDown);

            const submitButton = screen.getByRole('button', { name: /Submit Feedback/i });
            await user.click(submitButton);

            // Should revert to unselected state
            await waitFor(() => {
                expect(container.querySelector('[title="Mark as not helpful"]')).toBeInTheDocument();
            });
        });

        it('hides thank you message on error', async () => {
            const onSubmit = vi.fn().mockRejectedValue(new Error('Network error'));
            const user = userEvent.setup({ advanceTimers: vi.advanceTimersByTime });
            const { container, queryByText } = render(<FeedbackButtons {...defaultProps} onSubmit={onSubmit} />);

            const thumbsUp = container.querySelector('[title="Mark as helpful"]') as HTMLElement;
            await user.click(thumbsUp);

            // Thank you message should be hidden after error
            await waitFor(() => {
                expect(queryByText('Thanks!')).not.toBeInTheDocument();
            });
        });
    });

    describe('Disabled State', () => {
        it('disables buttons when disabled prop is true', () => {
            const { container } = render(<FeedbackButtons {...defaultProps} disabled={true} />);

            const thumbsUp = container.querySelector('[title="Mark as helpful"]') as HTMLButtonElement;
            const thumbsDown = container.querySelector('[title="Mark as not helpful"]') as HTMLButtonElement;

            expect(thumbsUp).toBeDisabled();
            expect(thumbsDown).toBeDisabled();
        });

        it('disables buttons when submitting', async () => {
            const { container } = render(<FeedbackButtons {...defaultProps} isSubmitting={true} />);

            const thumbsUp = container.querySelector('[title="Mark as helpful"]') as HTMLButtonElement;
            expect(thumbsUp).toBeDisabled();
        });

        it('prevents interaction when disabled', async () => {
            const onSubmit = vi.fn();
            const user = userEvent.setup({ advanceTimers: vi.advanceTimersByTime });
            const { container } = render(<FeedbackButtons {...defaultProps} onSubmit={onSubmit} disabled={true} />);

            const thumbsUp = container.querySelector('[title="Mark as helpful"]') as HTMLElement;
            await user.click(thumbsUp);

            expect(onSubmit).not.toHaveBeenCalled();
        });
    });

    describe('Current Rating State', () => {
        it('shows positive state when currentRating is positive', () => {
            const { container } = render(<FeedbackButtons {...defaultProps} currentRating="positive" />);

            expect(container.querySelector('[title="Marked as helpful"]')).toBeInTheDocument();
        });

        it('shows negative state when currentRating is negative', () => {
            const { container } = render(<FeedbackButtons {...defaultProps} currentRating="negative" />);

            expect(container.querySelector('[title="Marked as not helpful"]')).toBeInTheDocument();
        });

        it('dims other button when one is selected', () => {
            const { container } = render(
                <FeedbackButtons {...defaultProps} currentRating="positive" />
            );

            // The negative button should be dimmed (opacity-40)
            const dimmedButton = container.querySelector('.opacity-40');
            expect(dimmedButton).toBeInTheDocument();
        });

        it('syncs local state with currentRating prop changes', async () => {
            const { rerender, container } = render(<FeedbackButtons {...defaultProps} />);

            // Initially unrated
            expect(container.querySelector('[title="Mark as helpful"]')).toBeInTheDocument();

            // Update prop to positive
            rerender(<FeedbackButtons {...defaultProps} currentRating="positive" />);

            expect(container.querySelector('[title="Marked as helpful"]')).toBeInTheDocument();
        });

        it('allows changing from negative to comment modal', async () => {
            const user = userEvent.setup({ advanceTimers: vi.advanceTimersByTime });
            const { container } = render(<FeedbackButtons {...defaultProps} currentRating="negative" />);

            // Should still be able to open modal to update comment
            const thumbsDown = container.querySelector('[title="Marked as not helpful"]') as HTMLElement;
            await user.click(thumbsDown);

            expect(screen.getByText('Help us improve')).toBeInTheDocument();
        });
    });

    describe('Accessibility', () => {
        it('has proper title attributes on buttons', () => {
            const { container } = render(<FeedbackButtons {...defaultProps} />);

            expect(container.querySelector('[title="Mark as helpful"]')).toBeInTheDocument();
            expect(container.querySelector('[title="Mark as not helpful"]')).toBeInTheDocument();
        });

        it('updates title when rating is selected', () => {
            const { container } = render(<FeedbackButtons {...defaultProps} currentRating="positive" />);

            expect(container.querySelector('[title="Marked as helpful"]')).toBeInTheDocument();
        });

        it('modal has proper dialog role', async () => {
            const user = userEvent.setup({ advanceTimers: vi.advanceTimersByTime });
            const { container } = render(<FeedbackButtons {...defaultProps} />);

            const thumbsDown = container.querySelector('[title="Mark as not helpful"]') as HTMLElement;
            await user.click(thumbsDown);

            expect(screen.getByRole('dialog')).toBeInTheDocument();
        });

        it('modal has descriptive title', async () => {
            const user = userEvent.setup({ advanceTimers: vi.advanceTimersByTime });
            const { container } = render(<FeedbackButtons {...defaultProps} />);

            const thumbsDown = container.querySelector('[title="Mark as not helpful"]') as HTMLElement;
            await user.click(thumbsDown);

            expect(screen.getByText('Help us improve')).toBeInTheDocument();
        });
    });
});
