/**
 * Unit Tests for Help Center Components
 * 
 * Tests HelpSidebar, ArticleViewer, and HelpSearch components.
 */

import React from 'react';
import { describe, it, expect, vi, beforeEach } from 'vitest';
import { render, screen, fireEvent } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import '@testing-library/jest-dom';

// Mock next/navigation
const mockUsePathname = vi.fn();
vi.mock('next/navigation', () => ({
    usePathname: () => mockUsePathname(),
}));

// Import components after mocks
import { HelpSidebar } from '@/components/help/HelpSidebar';
import { ArticleViewer } from '@/components/help/ArticleViewer';
import { HelpSearch } from '@/components/help/HelpSearch';

const mockArticles = [
    { slug: '01-getting-started', title: 'Getting Started', category: 'Basics', order: 1 },
    { slug: '02-uploading', title: 'Uploading Files', category: 'Basics', order: 2 },
    { slug: '03-chat', title: 'Using Chat', category: 'Features', order: 3 },
];

const mockCategories = {
    'Basics': [mockArticles[0], mockArticles[1]],
    'Features': [mockArticles[2]],
};

describe('HelpSidebar', () => {
    beforeEach(() => {
        mockUsePathname.mockReturnValue('/dashboard/help');
    });

    it('should render Help Center title', () => {
        render(<HelpSidebar articles={mockArticles} categories={mockCategories} />);
        expect(screen.getByText('Help Center')).toBeInTheDocument();
    });

    it('should render all categories', () => {
        render(<HelpSidebar articles={mockArticles} categories={mockCategories} />);
        expect(screen.getByText('Basics')).toBeInTheDocument();
        expect(screen.getByText('Features')).toBeInTheDocument();
    });

    it('should render all article titles', () => {
        render(<HelpSidebar articles={mockArticles} categories={mockCategories} />);
        expect(screen.getByText('Getting Started')).toBeInTheDocument();
        expect(screen.getByText('Uploading Files')).toBeInTheDocument();
        expect(screen.getByText('Using Chat')).toBeInTheDocument();
    });

    it('should highlight active article', () => {
        mockUsePathname.mockReturnValue('/dashboard/help/01-getting-started');

        render(<HelpSidebar articles={mockArticles} categories={mockCategories} />);

        const activeLink = screen.getByText('Getting Started').closest('a');
        expect(activeLink).toHaveClass('bg-primary/10');
    });

    it('should have correct links', () => {
        render(<HelpSidebar articles={mockArticles} categories={mockCategories} />);

        const link = screen.getByText('Getting Started').closest('a');
        expect(link).toHaveAttribute('href', '/dashboard/help/01-getting-started');
    });
});

describe('ArticleViewer', () => {
    const mockContent = `
# Test Heading

This is a paragraph with **bold** and *italic* text.

## Subheading

- List item 1
- List item 2
`;

    it('should render article title', () => {
        render(
            <ArticleViewer
                title="Test Article"
                category="Test Category"
                content={mockContent}
            />
        );
        expect(screen.getByText('Test Article')).toBeInTheDocument();
    });

    it('should render category badge', () => {
        render(
            <ArticleViewer
                title="Test Article"
                category="Test Category"
                content={mockContent}
            />
        );
        expect(screen.getByText('Test Category')).toBeInTheDocument();
    });

    it('should render markdown content', () => {
        render(
            <ArticleViewer
                title="Test Article"
                category="Test Category"
                content={mockContent}
            />
        );
        expect(screen.getByText('Test Heading')).toBeInTheDocument();
        expect(screen.getByText('Subheading')).toBeInTheDocument();
    });

    it('should render lists', () => {
        render(
            <ArticleViewer
                title="Test Article"
                category="Test Category"
                content={mockContent}
            />
        );
        expect(screen.getByText('List item 1')).toBeInTheDocument();
        expect(screen.getByText('List item 2')).toBeInTheDocument();
    });

    it('should have prose styling class', () => {
        const { container } = render(
            <ArticleViewer
                title="Test Article"
                category="Test Category"
                content={mockContent}
            />
        );
        expect(container.querySelector('.prose')).toBeInTheDocument();
    });
});

describe('HelpSearch', () => {
    it('should render search input', () => {
        render(<HelpSearch articles={mockArticles} />);
        expect(screen.getByPlaceholderText('Search help articles...')).toBeInTheDocument();
    });

    it('should filter articles on input', async () => {
        render(<HelpSearch articles={mockArticles} />);

        const input = screen.getByPlaceholderText('Search help articles...');
        await userEvent.type(input, 'Getting');

        await new Promise(r => setTimeout(r, 100)); // Wait for focus state

        expect(screen.getByText('Getting Started')).toBeInTheDocument();
    });

    it('should show no results message', async () => {
        render(<HelpSearch articles={mockArticles} />);

        const input = screen.getByPlaceholderText('Search help articles...');
        await userEvent.type(input, 'nonexistent query');

        await new Promise(r => setTimeout(r, 100));

        expect(screen.getByText(/No articles found/i)).toBeInTheDocument();
    });

    it('should clear input on X click', async () => {
        render(<HelpSearch articles={mockArticles} />);

        const input = screen.getByPlaceholderText('Search help articles...');
        await userEvent.type(input, 'test');

        const clearButton = screen.getByRole('button');
        await userEvent.click(clearButton);

        expect(input).toHaveValue('');
    });

    it('should search by category', async () => {
        render(<HelpSearch articles={mockArticles} />);

        const input = screen.getByPlaceholderText('Search help articles...');
        await userEvent.type(input, 'Features');

        await new Promise(r => setTimeout(r, 100));

        expect(screen.getByText('Using Chat')).toBeInTheDocument();
    });
});
