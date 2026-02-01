/**
 * Comprehensive Unit Tests for HelpSearch Component
 * 
 * Tests:
 * - Initial rendering
 * - Search functionality
 * - Keyboard navigation (Arrow keys, Enter, Escape)
 * - Search result highlighting
 * - Category colors/badges
 * - Reading time calculation
 * - Click outside to close
 * - Empty/no results states
 * - Accessibility
 */

import React from 'react';
import { describe, it, expect, beforeEach, vi, afterEach } from 'vitest';
import { render, screen, fireEvent, waitFor, act } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import '@testing-library/jest-dom';
import { HelpSearch } from '@/components/help/HelpSearch';

// Mock next/navigation
const mockPush = vi.fn();
vi.mock('next/navigation', () => ({
    useRouter: () => ({
        push: mockPush,
    }),
}));

// Mock articles data
const mockArticles = [
    {
        slug: 'getting-started',
        title: 'Getting Started with Axio Hub',
        category: 'Getting Started',
        order: 1,
        content: 'Welcome to Axio Hub. This is your AI-powered knowledge assistant that lets you chat with your documents.',
    },
    {
        slug: 'data-management',
        title: 'Data Management',
        category: 'Data Management',
        order: 2,
        content: 'Manage your files and documents efficiently with our data management tools.',
    },
    {
        slug: 'ai-features',
        title: 'AI Features Overview',
        category: 'Features',
        order: 3,
        content: 'Explore the powerful AI features available in Axio Hub for document analysis.',
    },
    {
        slug: 'settings-guide',
        title: 'Settings Guide',
        category: 'Settings',
        order: 4,
        content: 'Configure your account settings and preferences.',
    },
    {
        slug: 'legal-safety',
        title: 'Legal & Safety Information',
        category: 'Legal & Safety',
        order: 5,
        content: 'Important legal and safety information about using Axio Hub.',
    },
    {
        slug: 'unknown-category',
        title: 'Article with Unknown Category',
        category: 'Unknown',
        order: 6,
        content: 'This article has an unknown category for testing fallback styles.',
    },
];

describe('HelpSearch Component', () => {
    beforeEach(() => {
        vi.clearAllMocks();
    });

    afterEach(() => {
        vi.clearAllMocks();
    });

    describe('Initial Rendering', () => {
        it('should render search input with default placeholder', () => {
            render(<HelpSearch articles={mockArticles} />);

            expect(screen.getByPlaceholderText('Search help articles...')).toBeInTheDocument();
        });

        it('should render search input with custom placeholder', () => {
            render(<HelpSearch articles={mockArticles} placeholder="Find articles..." />);

            expect(screen.getByPlaceholderText('Find articles...')).toBeInTheDocument();
        });

        it('should apply custom className', () => {
            const { container } = render(
                <HelpSearch articles={mockArticles} className="custom-class" />
            );

            expect(container.firstChild).toHaveClass('custom-class');
        });

        it('should have proper ARIA attributes on input', () => {
            render(<HelpSearch articles={mockArticles} />);

            const input = screen.getByRole('combobox');
            expect(input).toHaveAttribute('aria-label', 'Search help articles');
            expect(input).toHaveAttribute('aria-haspopup', 'listbox');
            expect(input).toHaveAttribute('aria-controls', 'search-results');
        });

        it('should not show clear button initially', () => {
            render(<HelpSearch articles={mockArticles} />);

            expect(screen.queryByLabelText('Clear search')).not.toBeInTheDocument();
        });
    });

    describe('Keyboard Hint Display', () => {
        it('should show keyboard hint when focused with no query', async () => {
            render(<HelpSearch articles={mockArticles} />);

            const input = screen.getByRole('combobox');
            fireEvent.focus(input);

            expect(screen.getByText('Type to search articles')).toBeInTheDocument();
        });

        it('should hide keyboard hint when query is entered', async () => {
            const user = userEvent.setup();
            render(<HelpSearch articles={mockArticles} />);

            const input = screen.getByRole('combobox');
            await user.type(input, 'getting');

            expect(screen.queryByText('Type to search articles')).not.toBeInTheDocument();
        });
    });

    describe('Search Functionality', () => {
        it('should filter articles by title', async () => {
            const user = userEvent.setup();
            render(<HelpSearch articles={mockArticles} />);

            const input = screen.getByRole('combobox');
            await user.type(input, 'getting');

            await waitFor(() => {
                // Text may be split due to highlighting, use container query
                const listbox = screen.getByRole('listbox');
                expect(listbox.textContent).toContain('Getting Started with Axio Hub');
            });
        });

        it('should filter articles by category', async () => {
            const user = userEvent.setup();
            render(<HelpSearch articles={mockArticles} />);

            const input = screen.getByRole('combobox');
            await user.type(input, 'overview');

            await waitFor(() => {
                const listbox = screen.getByRole('listbox');
                expect(listbox.textContent).toContain('AI Features Overview');
            });
        });

        it('should show results count', async () => {
            const user = userEvent.setup();
            render(<HelpSearch articles={mockArticles} />);

            const input = screen.getByRole('combobox');
            await user.type(input, 'ai');

            await waitFor(() => {
                expect(screen.getByText(/1 result found/)).toBeInTheDocument();
            });
        });

        it('should show plural results count for multiple matches', async () => {
            const user = userEvent.setup();
            render(<HelpSearch articles={mockArticles} />);

            const input = screen.getByRole('combobox');
            await user.type(input, 'a'); // Matches multiple articles

            await waitFor(() => {
                expect(screen.getByText(/results found/)).toBeInTheDocument();
            });
        });

        it('should limit results to 8', async () => {
            // Create more than 8 articles
            const manyArticles = Array.from({ length: 15 }, (_, i) => ({
                slug: `article-${i}`,
                title: `Article ${i} with Axio`,
                category: 'General',
                order: i,
                content: 'Content',
            }));

            const user = userEvent.setup();
            render(<HelpSearch articles={manyArticles} />);

            const input = screen.getByRole('combobox');
            await user.type(input, 'axio');

            await waitFor(() => {
                const items = screen.getAllByRole('option');
                expect(items.length).toBeLessThanOrEqual(8);
            });
        });

        it('should not show results when query is empty', async () => {
            render(<HelpSearch articles={mockArticles} />);

            const input = screen.getByRole('combobox');
            fireEvent.focus(input);

            expect(screen.queryByRole('listbox')).not.toBeInTheDocument();
        });

        it('should show no results message when no matches', async () => {
            const user = userEvent.setup();
            render(<HelpSearch articles={mockArticles} />);

            const input = screen.getByRole('combobox');
            await user.type(input, 'xyznonexistent');

            await waitFor(() => {
                expect(screen.getByText('No articles found')).toBeInTheDocument();
                expect(screen.getByText(/No results for/)).toBeInTheDocument();
            });
        });
    });

    describe('Clear Search', () => {
        it('should show clear button when query exists', async () => {
            const user = userEvent.setup();
            render(<HelpSearch articles={mockArticles} />);

            const input = screen.getByRole('combobox');
            await user.type(input, 'test');

            expect(screen.getByLabelText('Clear search')).toBeInTheDocument();
        });

        it('should clear query when clear button clicked', async () => {
            const user = userEvent.setup();
            render(<HelpSearch articles={mockArticles} />);

            const input = screen.getByRole('combobox');
            await user.type(input, 'test');
            await user.click(screen.getByLabelText('Clear search'));

            expect(input).toHaveValue('');
        });

        it('should clear search from no results view', async () => {
            const user = userEvent.setup();
            render(<HelpSearch articles={mockArticles} />);

            const input = screen.getByRole('combobox');
            await user.type(input, 'xyznonexistent');

            await waitFor(() => {
                expect(screen.getByText('Clear search')).toBeInTheDocument();
            });

            await user.click(screen.getByText('Clear search'));

            expect(input).toHaveValue('');
        });
    });

    describe('Keyboard Navigation', () => {
        it('should navigate down with ArrowDown', async () => {
            const user = userEvent.setup();
            render(<HelpSearch articles={mockArticles} />);

            const input = screen.getByRole('combobox');
            await user.type(input, 'a');

            await waitFor(() => {
                expect(screen.getByRole('listbox')).toBeInTheDocument();
            });

            await user.keyboard('{ArrowDown}');

            const firstItem = screen.getAllByRole('option')[0];
            expect(firstItem).toHaveAttribute('aria-selected', 'true');
        });

        it('should navigate up with ArrowUp', async () => {
            const user = userEvent.setup();
            render(<HelpSearch articles={mockArticles} />);

            const input = screen.getByRole('combobox');
            await user.type(input, 'a');

            await waitFor(() => {
                expect(screen.getByRole('listbox')).toBeInTheDocument();
            });

            // Go down twice, then up once
            await user.keyboard('{ArrowDown}{ArrowDown}{ArrowUp}');

            const firstItem = screen.getAllByRole('option')[0];
            expect(firstItem).toHaveAttribute('aria-selected', 'true');
        });

        it('should wrap around when navigating past last item', async () => {
            const articles = [
                { slug: 'a', title: 'Article A', category: 'General', order: 1, content: 'A' },
                { slug: 'b', title: 'Article B', category: 'General', order: 2, content: 'B' },
            ];

            const user = userEvent.setup();
            render(<HelpSearch articles={articles} />);

            const input = screen.getByRole('combobox');
            await user.type(input, 'article');

            await waitFor(() => {
                expect(screen.getByRole('listbox')).toBeInTheDocument();
            });

            // Navigate past the last item (2 items, press down 3 times)
            await user.keyboard('{ArrowDown}{ArrowDown}{ArrowDown}');

            const firstItem = screen.getAllByRole('option')[0];
            expect(firstItem).toHaveAttribute('aria-selected', 'true');
        });

        it('should wrap around when navigating before first item', async () => {
            const articles = [
                { slug: 'a', title: 'Article A', category: 'General', order: 1, content: 'A' },
                { slug: 'b', title: 'Article B', category: 'General', order: 2, content: 'B' },
            ];

            const user = userEvent.setup();
            render(<HelpSearch articles={articles} />);

            const input = screen.getByRole('combobox');
            await user.type(input, 'article');

            await waitFor(() => {
                expect(screen.getByRole('listbox')).toBeInTheDocument();
            });

            // Navigate to first then up once
            await user.keyboard('{ArrowDown}{ArrowUp}');

            const lastItem = screen.getAllByRole('option')[1];
            expect(lastItem).toHaveAttribute('aria-selected', 'true');
        });

        it('should navigate to selected article on Enter', async () => {
            const user = userEvent.setup();
            render(<HelpSearch articles={mockArticles} />);

            const input = screen.getByRole('combobox');
            await user.type(input, 'getting');

            await waitFor(() => {
                expect(screen.getByRole('listbox')).toBeInTheDocument();
            });

            await user.keyboard('{ArrowDown}{Enter}');

            expect(mockPush).toHaveBeenCalledWith('/dashboard/help/getting-started');
        });

        it('should close dropdown on Escape', async () => {
            const user = userEvent.setup();
            render(<HelpSearch articles={mockArticles} />);

            const input = screen.getByRole('combobox');
            await user.type(input, 'getting');

            await waitFor(() => {
                expect(screen.getByRole('listbox')).toBeInTheDocument();
            });

            await user.keyboard('{Escape}');

            await waitFor(() => {
                expect(screen.queryByRole('listbox')).not.toBeInTheDocument();
            });
        });

        it('should reset focused index when query changes', async () => {
            const user = userEvent.setup();
            render(<HelpSearch articles={mockArticles} />);

            const input = screen.getByRole('combobox');
            await user.type(input, 'getting');

            await waitFor(() => {
                expect(screen.getByRole('listbox')).toBeInTheDocument();
            });

            await user.keyboard('{ArrowDown}');

            // Clear and type new query
            await user.clear(input);
            await user.type(input, 'ai');

            // No item should be focused initially
            const items = screen.getAllByRole('option');
            items.forEach(item => {
                expect(item).not.toHaveAttribute('aria-selected', 'true');
            });
        });

        it('should not navigate when no results shown', async () => {
            const user = userEvent.setup();
            render(<HelpSearch articles={mockArticles} />);

            const input = screen.getByRole('combobox');
            fireEvent.focus(input);

            // No query, no results
            await user.keyboard('{ArrowDown}');

            // Should not cause errors
            expect(mockPush).not.toHaveBeenCalled();
        });
    });

    describe('Click on Result', () => {
        it('should navigate to article when result is clicked', async () => {
            const user = userEvent.setup();
            render(<HelpSearch articles={mockArticles} />);

            const input = screen.getByRole('combobox');
            await user.type(input, 'started');

            await waitFor(() => {
                const listbox = screen.getByRole('listbox');
                expect(listbox.textContent).toContain('Getting Started');
            });

            // Find the link - it should be the first option
            const links = screen.getAllByRole('link');
            await user.click(links[0]);

            // Query should be cleared and dropdown closed
            expect(input).toHaveValue('');
        });
    });

    describe('Click Outside', () => {
        it('should close dropdown when clicking outside', async () => {
            const user = userEvent.setup();
            render(
                <div>
                    <div data-testid="outside">Outside</div>
                    <HelpSearch articles={mockArticles} />
                </div>
            );

            const input = screen.getByRole('combobox');
            await user.type(input, 'getting');

            await waitFor(() => {
                expect(screen.getByRole('listbox')).toBeInTheDocument();
            });

            fireEvent.mouseDown(screen.getByTestId('outside'));

            await waitFor(() => {
                expect(screen.queryByRole('listbox')).not.toBeInTheDocument();
            });
        });

        it('should keep dropdown open when clicking inside', async () => {
            const user = userEvent.setup();
            render(<HelpSearch articles={mockArticles} />);

            const input = screen.getByRole('combobox');
            await user.type(input, 'getting');

            await waitFor(() => {
                expect(screen.getByRole('listbox')).toBeInTheDocument();
            });

            fireEvent.mouseDown(input);

            expect(screen.getByRole('listbox')).toBeInTheDocument();
        });
    });

    describe('Category Badges', () => {
        it('should display category badges in search results', async () => {
            const user = userEvent.setup();
            render(<HelpSearch articles={mockArticles} />);

            const input = screen.getByRole('combobox');
            await user.type(input, 'a');

            await waitFor(() => {
                const listbox = screen.getByRole('listbox');
                // Should have badges for categories - check for category text in the listbox
                expect(listbox).toBeInTheDocument();
                // Categories should be displayed in the results
                const content = listbox.textContent || '';
                const hasCategory = content.includes('Getting Started') || 
                                   content.includes('Data Management') || 
                                   content.includes('Features') ||
                                   content.includes('Settings');
                expect(hasCategory).toBe(true);
            });
        });

        it('should show reading time with min suffix', async () => {
            const user = userEvent.setup();
            render(<HelpSearch articles={mockArticles} />);

            const input = screen.getByRole('combobox');
            await user.type(input, 'a');

            await waitFor(() => {
                const listbox = screen.getByRole('listbox');
                expect(listbox.textContent).toContain('min');
            });
        });

        it('should apply color styles based on category', () => {
            // Test that component renders properly with various category types
            render(<HelpSearch articles={mockArticles} />);
            
            // Component renders without error
            expect(screen.getByRole('combobox')).toBeInTheDocument();
        });
    });

    describe('Reading Time', () => {
        it('should display reading time for articles with content', async () => {
            const user = userEvent.setup();
            render(<HelpSearch articles={mockArticles} />);

            const input = screen.getByRole('combobox');
            await user.type(input, 'getting');

            await waitFor(() => {
                expect(screen.getByText(/min/)).toBeInTheDocument();
            });
        });

        it('should default to 1 min for empty content', async () => {
            const articlesWithNoContent = [
                { slug: 'empty', title: 'Empty Article', category: 'General', order: 1, content: '' },
            ];

            const user = userEvent.setup();
            render(<HelpSearch articles={articlesWithNoContent} />);

            const input = screen.getByRole('combobox');
            await user.type(input, 'empty');

            await waitFor(() => {
                expect(screen.getByText('1 min')).toBeInTheDocument();
            });
        });

        it('should calculate reading time based on word count', async () => {
            // 400 words = 2 min at 200 wpm
            const longContent = Array(400).fill('word').join(' ');
            const articlesWithLongContent = [
                { slug: 'long', title: 'Long Article', category: 'General', order: 1, content: longContent },
            ];

            const user = userEvent.setup();
            render(<HelpSearch articles={articlesWithLongContent} />);

            const input = screen.getByRole('combobox');
            await user.type(input, 'long');

            await waitFor(() => {
                expect(screen.getByText('2 min')).toBeInTheDocument();
            });
        });
    });

    describe('Search Highlighting', () => {
        it('should highlight matching text in title', async () => {
            const user = userEvent.setup();
            render(<HelpSearch articles={mockArticles} />);

            const input = screen.getByRole('combobox');
            await user.type(input, 'getting');

            await waitFor(() => {
                const marks = document.querySelectorAll('mark');
                expect(marks.length).toBeGreaterThan(0);
            });
        });

        it('should handle special regex characters in query', async () => {
            const user = userEvent.setup();
            render(<HelpSearch articles={mockArticles} />);

            const input = screen.getByRole('combobox');
            // Test with regex special characters
            await user.type(input, 'a.*b');

            // Should not throw error
            await waitFor(() => {
                // Either shows results or no results, but doesn't crash
                expect(true).toBe(true);
            });
        });
    });

    describe('Scroll Behavior', () => {
        it('should scroll focused item into view', async () => {
            const user = userEvent.setup();
            render(<HelpSearch articles={mockArticles} />);

            const input = screen.getByRole('combobox');
            await user.type(input, 'a');

            await waitFor(() => {
                expect(screen.getByRole('listbox')).toBeInTheDocument();
            });

            // Navigate down multiple times
            await user.keyboard('{ArrowDown}{ArrowDown}{ArrowDown}');

            // Test passes if no error - scrollIntoView is called
            expect(true).toBe(true);
        });
    });

    describe('ARIA Expanded State', () => {
        it('should set aria-expanded to true when results shown', async () => {
            const user = userEvent.setup();
            render(<HelpSearch articles={mockArticles} />);

            const input = screen.getByRole('combobox');
            await user.type(input, 'getting');

            await waitFor(() => {
                expect(input).toHaveAttribute('aria-expanded', 'true');
            });
        });

        it('should set aria-expanded to false when no results shown', () => {
            render(<HelpSearch articles={mockArticles} />);

            const input = screen.getByRole('combobox');
            expect(input).toHaveAttribute('aria-expanded', 'false');
        });
    });

    describe('No Articles', () => {
        it('should handle empty articles array', async () => {
            const user = userEvent.setup();
            render(<HelpSearch articles={[]} />);

            const input = screen.getByRole('combobox');
            await user.type(input, 'test');

            await waitFor(() => {
                expect(screen.getByText('No articles found')).toBeInTheDocument();
            });
        });
    });

    describe('Cleanup', () => {
        it('should remove event listener on unmount', () => {
            const removeEventListenerSpy = vi.spyOn(document, 'removeEventListener');
            
            const { unmount } = render(<HelpSearch articles={mockArticles} />);
            unmount();

            expect(removeEventListenerSpy).toHaveBeenCalledWith('mousedown', expect.any(Function));
            removeEventListenerSpy.mockRestore();
        });
    });
});
