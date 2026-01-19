/**
 * Unit Tests for ThinkingIndicator Component
 * 
 * Tests covering:
 * - Step visualization
 * - Animated progress
 * - Details display (source count, scope name)
 * - Different states (searching, analyzing, found, generating, complete)
 */

import { describe, it, expect } from 'vitest';
import { render, screen } from '@testing-library/react';
import { ThinkingIndicator, TypingIndicator, ThinkingStatus } from '@/components/chat/ThinkingIndicator';

describe('ThinkingIndicator Component', () => {
    describe('Rendering', () => {
        it('should render with searching status', () => {
            const status: ThinkingStatus = {
                step: 'searching',
                message: 'Searching knowledge base...',
            };

            render(<ThinkingIndicator status={status} />);

            expect(screen.getByText(/Searching knowledge base/)).toBeInTheDocument();
        });

        it('should render with found status and source count', () => {
            const status: ThinkingStatus = {
                step: 'found',
                message: 'Found 5 relevant sources',
                details: {
                    sourceCount: 5,
                },
            };

            render(<ThinkingIndicator status={status} />);

            expect(screen.getByText(/Found 5 relevant sources/)).toBeInTheDocument();
            expect(screen.getByText('5 sources')).toBeInTheDocument();
        });

        it('should render with generating status', () => {
            const status: ThinkingStatus = {
                step: 'generating',
                message: 'Generating response...',
            };

            render(<ThinkingIndicator status={status} />);

            expect(screen.getByText(/Generating response/)).toBeInTheDocument();
        });

        it('should render scope name when provided', () => {
            const status: ThinkingStatus = {
                step: 'found',
                message: 'Found relevant sources',
                details: {
                    sourceCount: 3,
                    scopeName: 'Project Documentation',
                },
            };

            render(<ThinkingIndicator status={status} />);

            expect(screen.getByText(/from Project Documentation/)).toBeInTheDocument();
        });

        it('should render with analyzing status', () => {
            const status: ThinkingStatus = {
                step: 'analyzing',
                message: 'Analyzing context...',
            };

            render(<ThinkingIndicator status={status} />);

            expect(screen.getByText(/Analyzing context/)).toBeInTheDocument();
        });

        it('should render complete status without animated dots', () => {
            const status: ThinkingStatus = {
                step: 'complete',
                message: 'Complete',
            };

            render(<ThinkingIndicator status={status} />);

            // Complete should show exact message without trailing dots
            expect(screen.getByText('Complete')).toBeInTheDocument();
        });
    });

    describe('Step Progress Visualization', () => {
        it('should show all four steps', () => {
            const status: ThinkingStatus = {
                step: 'searching',
                message: 'Searching...',
            };

            render(<ThinkingIndicator status={status} />);

            // Should have 4 step indicators (circles)
            const stepIndicators = document.querySelectorAll('[class*="rounded-full"]');
            // At least 4 step indicators (may have more circles for other UI elements)
            expect(stepIndicators.length).toBeGreaterThanOrEqual(4);
        });
    });

    describe('Custom className', () => {
        it('should apply custom className', () => {
            const status: ThinkingStatus = {
                step: 'searching',
                message: 'Searching...',
            };

            const { container } = render(
                <ThinkingIndicator status={status} className="custom-class" />
            );

            expect(container.firstChild).toHaveClass('custom-class');
        });
    });
});

describe('TypingIndicator Component', () => {
    it('should render bouncing dots', () => {
        render(<TypingIndicator />);

        // Should have 3 bouncing dots
        const dots = document.querySelectorAll('[class*="animate-bounce"]');
        expect(dots.length).toBe(3);
    });

    it('should apply custom className', () => {
        const { container } = render(<TypingIndicator className="my-custom-class" />);

        expect(container.firstChild).toHaveClass('my-custom-class');
    });
});
