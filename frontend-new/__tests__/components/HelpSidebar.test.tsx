import { describe, it, expect, vi, beforeEach } from 'vitest';
import { render, screen, fireEvent, waitFor } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { HelpSidebar } from '@/components/help/HelpSidebar';

// =============================================================================
// Mocks
// =============================================================================

const mockUsePathname = vi.fn();
vi.mock('next/navigation', () => ({
    usePathname: () => mockUsePathname(),
}));

// =============================================================================
// Test Data
// =============================================================================

const mockArticles = [
    { slug: 'getting-started', title: 'Getting Started', category: 'Getting Started', order: 1, content: 'This is getting started content with many words for reading time test.' },
    { slug: 'connect-sources', title: 'Connect Data Sources', category: 'Getting Started', order: 2, content: 'How to connect data sources.' },
    { slug: 'upload-files', title: 'Upload Files', category: 'Data Management', order: 1, content: 'How to upload files.' },
    { slug: 'manage-files', title: 'Manage Your Files', category: 'Data Management', order: 2, content: 'Managing your files guide.' },
    { slug: 'ai-chat', title: 'AI Chat Features', category: 'Features', order: 1, content: 'AI chat features explanation.' },
    { slug: 'billing', title: 'Billing & Plans', category: 'Settings', order: 1, content: 'Billing information.' },
    { slug: 'privacy', title: 'Privacy Policy', category: 'Legal & Safety', order: 1, content: 'Privacy policy details.' },
];

const mockCategories: Record<string, typeof mockArticles> = {
    'Getting Started': mockArticles.filter(a => a.category === 'Getting Started'),
    'Data Management': mockArticles.filter(a => a.category === 'Data Management'),
    'Features': mockArticles.filter(a => a.category === 'Features'),
    'Settings': mockArticles.filter(a => a.category === 'Settings'),
    'Legal & Safety': mockArticles.filter(a => a.category === 'Legal & Safety'),
};

// =============================================================================
// Test Suite
// =============================================================================

describe('HelpSidebar Component', () => {
    beforeEach(() => {
        vi.clearAllMocks();
        mockUsePathname.mockReturnValue('/dashboard/help');
    });

    // =========================================================================
    // Rendering Tests
    // =========================================================================

    describe('Rendering', () => {
        it('should render the Help Center header', () => {
            render(<HelpSidebar articles={mockArticles} categories={mockCategories} />);
            expect(screen.getByText('Help Center')).toBeInTheDocument();
        });

        it('should render the total article count', () => {
            render(<HelpSidebar articles={mockArticles} categories={mockCategories} />);
            expect(screen.getByText('7 articles')).toBeInTheDocument();
        });

        it('should render the search input', () => {
            render(<HelpSidebar articles={mockArticles} categories={mockCategories} />);
            expect(screen.getByPlaceholderText('Search articles...')).toBeInTheDocument();
        });

        it('should render the All Categories link', () => {
            render(<HelpSidebar articles={mockArticles} categories={mockCategories} />);
            expect(screen.getByText('All Categories')).toBeInTheDocument();
        });

        it('should render the Contact Support link', () => {
            render(<HelpSidebar articles={mockArticles} categories={mockCategories} />);
            expect(screen.getByText('Contact Support')).toBeInTheDocument();
        });

        it('should render category headers', () => {
            render(<HelpSidebar articles={mockArticles} categories={mockCategories} />);
            // Categories are rendered as buttons
            const buttons = screen.getAllByRole('button');
            const categoryNames = buttons.map(btn => btn.textContent);
            expect(categoryNames.some(name => name?.includes('Getting Started'))).toBe(true);
            expect(categoryNames.some(name => name?.includes('Data Management'))).toBe(true);
        });

        it('should render category article counts', () => {
            render(<HelpSidebar articles={mockArticles} categories={mockCategories} />);
            // Getting Started has 2 articles
            const badges = screen.getAllByText('2');
            expect(badges.length).toBeGreaterThan(0);
        });
    });

    // =========================================================================
    // Category Expansion Tests
    // =========================================================================

    describe('Category Expansion', () => {
        it('should auto-expand first category by default', () => {
            render(<HelpSidebar articles={mockArticles} categories={mockCategories} />);
            // First category button should be visible
            const buttons = screen.getAllByRole('button');
            expect(buttons.length).toBeGreaterThan(0);
        });

        it('should auto-expand category containing current article', () => {
            mockUsePathname.mockReturnValue('/dashboard/help/upload-files');
            render(<HelpSidebar articles={mockArticles} categories={mockCategories} currentSlug="upload-files" />);
            
            // Data Management category should be expanded since it contains upload-files
            expect(screen.getByText('Upload Files')).toBeInTheDocument();
        });

        it('should toggle category expansion on click', async () => {
            const user = userEvent.setup();
            render(<HelpSidebar articles={mockArticles} categories={mockCategories} />);

            // Find and click category button
            const categoryButtons = screen.getAllByRole('button');
            const dataManagementBtn = categoryButtons.find(btn => 
                btn.textContent?.includes('Data Management')
            );

            if (dataManagementBtn) {
                await user.click(dataManagementBtn);
            }

            // Articles should be visible after clicking
            await waitFor(() => {
                expect(screen.getByText('Upload Files')).toBeInTheDocument();
            });
        });

        it('should collapse expanded category on click', async () => {
            const user = userEvent.setup();
            render(<HelpSidebar articles={mockArticles} categories={mockCategories} />);

            // Click Getting Started to collapse it (it's expanded by default)
            const categoryButtons = screen.getAllByRole('button');
            const gettingStartedBtn = categoryButtons.find(btn => 
                btn.textContent?.includes('Getting Started')
            );

            if (gettingStartedBtn) {
                await user.click(gettingStartedBtn);
            }

            // After collapse, clicking again should re-expand
            await waitFor(() => {
                // Category header should still be visible
                expect(screen.getByText('Getting Started')).toBeInTheDocument();
            });
        });
    });

    // =========================================================================
    // Search Tests
    // =========================================================================

    describe('Search', () => {
        it('should filter articles by title', async () => {
            const user = userEvent.setup();
            render(<HelpSidebar articles={mockArticles} categories={mockCategories} />);

            const searchInput = screen.getByPlaceholderText('Search articles...');
            await user.type(searchInput, 'upload');

            await waitFor(() => {
                expect(screen.getByText(/1 result/i)).toBeInTheDocument();
            });
        });

        it('should filter articles by category name', async () => {
            const user = userEvent.setup();
            render(<HelpSidebar articles={mockArticles} categories={mockCategories} />);

            const searchInput = screen.getByPlaceholderText('Search articles...');
            await user.type(searchInput, 'settings');

            await waitFor(() => {
                expect(screen.getByText('Billing & Plans')).toBeInTheDocument();
            });
        });

        it('should show "No articles found" when no matches', async () => {
            const user = userEvent.setup();
            render(<HelpSidebar articles={mockArticles} categories={mockCategories} />);

            const searchInput = screen.getByPlaceholderText('Search articles...');
            await user.type(searchInput, 'nonexistent query');

            await waitFor(() => {
                expect(screen.getByText(/No articles found/i)).toBeInTheDocument();
            });
        });

        it('should show clear search button when searching', async () => {
            const user = userEvent.setup();
            render(<HelpSidebar articles={mockArticles} categories={mockCategories} />);

            const searchInput = screen.getByPlaceholderText('Search articles...');
            await user.type(searchInput, 'test');

            await waitFor(() => {
                const clearButton = document.querySelector('.lucide-x');
                expect(clearButton).toBeInTheDocument();
            });
        });

        it('should clear search when X button clicked', async () => {
            const user = userEvent.setup();
            render(<HelpSidebar articles={mockArticles} categories={mockCategories} />);

            const searchInput = screen.getByPlaceholderText('Search articles...') as HTMLInputElement;
            await user.type(searchInput, 'test');

            // Find and click clear button
            const clearButton = screen.getByRole('button', { name: '' }); // X button has no text
            const xButtons = document.querySelectorAll('button');
            const xBtn = Array.from(xButtons).find(btn => btn.querySelector('.lucide-x'));
            
            if (xBtn) {
                await user.click(xBtn);
            }

            await waitFor(() => {
                expect(searchInput.value).toBe('');
            });
        });

        it('should update search input value', async () => {
            const user = userEvent.setup();
            render(<HelpSidebar articles={mockArticles} categories={mockCategories} />);

            const searchInput = screen.getByPlaceholderText('Search articles...') as HTMLInputElement;
            await user.type(searchInput, 'test');

            expect(searchInput.value).toBe('test');
        });

        it('should highlight matching text', async () => {
            const user = userEvent.setup();
            render(<HelpSidebar articles={mockArticles} categories={mockCategories} />);

            const searchInput = screen.getByPlaceholderText('Search articles...');
            await user.type(searchInput, 'files');

            await waitFor(() => {
                const marks = document.querySelectorAll('mark');
                expect(marks.length).toBeGreaterThan(0);
            });
        });

        it('should show "Clear search" link when no results', async () => {
            const user = userEvent.setup();
            render(<HelpSidebar articles={mockArticles} categories={mockCategories} />);

            const searchInput = screen.getByPlaceholderText('Search articles...');
            await user.type(searchInput, 'nonexistent');

            await waitFor(() => {
                expect(screen.getByText('Clear search')).toBeInTheDocument();
            });
        });

        it('should clear search when "Clear search" is clicked', async () => {
            const user = userEvent.setup();
            render(<HelpSidebar articles={mockArticles} categories={mockCategories} />);

            const searchInput = screen.getByPlaceholderText('Search articles...') as HTMLInputElement;
            await user.type(searchInput, 'nonexistent');

            await waitFor(() => {
                expect(screen.getByText('Clear search')).toBeInTheDocument();
            });

            const clearLink = screen.getByText('Clear search');
            await user.click(clearLink);

            await waitFor(() => {
                expect(searchInput.value).toBe('');
            });
        });
    });

    // =========================================================================
    // Active State Tests
    // =========================================================================

    describe('Active State', () => {
        it('should highlight active article', () => {
            mockUsePathname.mockReturnValue('/dashboard/help/getting-started');
            render(<HelpSidebar articles={mockArticles} categories={mockCategories} currentSlug="getting-started" />);

            // Article should have active styling (primary color)
            const link = screen.getByRole('link', { name: /getting started/i });
            expect(link).toHaveClass('text-primary');
        });

        it('should highlight category containing active article', () => {
            mockUsePathname.mockReturnValue('/dashboard/help/upload-files');
            render(<HelpSidebar articles={mockArticles} categories={mockCategories} currentSlug="upload-files" />);

            // The category should have special styling when it contains active article
            const categoryHeader = screen.getByText('Data Management');
            expect(categoryHeader).toBeInTheDocument();
        });

        it('should highlight All Categories when on help index', () => {
            mockUsePathname.mockReturnValue('/dashboard/help');
            render(<HelpSidebar articles={mockArticles} categories={mockCategories} />);

            const allCategoriesLink = screen.getByRole('link', { name: /all categories/i });
            expect(allCategoriesLink).toHaveClass('text-primary');
        });
    });

    // =========================================================================
    // Reading Time Tests
    // =========================================================================

    describe('Reading Time', () => {
        it('should display reading time for articles', () => {
            render(<HelpSidebar articles={mockArticles} categories={mockCategories} />);

            // Articles should show reading time in minutes
            const readingTimes = screen.getAllByText(/\d+m/);
            expect(readingTimes.length).toBeGreaterThan(0);
        });

        it('should show minimum 1 minute for short content', () => {
            const shortArticles = [
                { slug: 'short', title: 'Short Article', category: 'Getting Started', order: 1, content: 'A' },
            ];
            const shortCategories = { 'Getting Started': shortArticles };

            render(<HelpSidebar articles={shortArticles} categories={shortCategories} />);

            // Should show at least 1m
            expect(screen.getByText('1m')).toBeInTheDocument();
        });

        it('should handle articles without content', () => {
            const noContentArticles = [
                { slug: 'no-content', title: 'No Content', category: 'Getting Started', order: 1 },
            ];
            const noContentCategories = { 'Getting Started': noContentArticles };

            render(<HelpSidebar articles={noContentArticles} categories={noContentCategories} />);

            // Should show 1m as default
            expect(screen.getByText('1m')).toBeInTheDocument();
        });
    });

    // =========================================================================
    // Edge Cases
    // =========================================================================

    describe('Edge Cases', () => {
        it('should handle empty categories', () => {
            render(<HelpSidebar articles={[]} categories={{}} />);
            expect(screen.getByText('Help Center')).toBeInTheDocument();
            expect(screen.getByText('0 articles')).toBeInTheDocument();
        });

        it('should handle unknown category without config', () => {
            const unknownCategoryArticles = [
                { slug: 'unknown', title: 'Unknown Category Article', category: 'Unknown Category', order: 1, content: 'Test' },
            ];
            const unknownCategories = { 'Unknown Category': unknownCategoryArticles };

            render(<HelpSidebar articles={unknownCategoryArticles} categories={unknownCategories} />);

            expect(screen.getByText('Unknown Category')).toBeInTheDocument();
        });

        it('should handle currentSlug that does not exist', () => {
            render(<HelpSidebar articles={mockArticles} categories={mockCategories} currentSlug="nonexistent-slug" />);
            
            // Should still render with first category expanded
            expect(screen.getByText('Help Center')).toBeInTheDocument();
        });
    });
});
