import React from 'react';
import { describe, it, expect, beforeEach } from 'vitest';
import { render, screen, fireEvent, act } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { HelpModal } from '@/components/help/HelpModal';
import { HelpTrigger } from '@/components/help/HelpTrigger';
import { useHelpStore } from '@/store/useHelpStore';
import { HELP_ARTICLES } from '@/data/helpArticles';

describe('HelpModal', () => {
    beforeEach(() => {
        act(() => {
            useHelpStore.getState().reset();
        });
    });

    it('auto-selects the first article when opened', () => {
        render(<HelpModal />);

        act(() => {
            useHelpStore.getState().openHelp();
        });

        expect(screen.getAllByText('Help Center').length).toBeGreaterThan(0);
        expect(screen.getAllByText(HELP_ARTICLES[0].title).length).toBeGreaterThan(0);
    });

    it('filters articles by category and search query', () => {
        render(<HelpModal />);

        act(() => {
            useHelpStore.getState().openHelp();
            useHelpStore.getState().setSelectedCategory('Billing');
            useHelpStore.getState().setSearchQuery('limit');
        });

        expect(screen.getAllByText('What happens when I hit my limit?').length).toBeGreaterThan(0);
    });

    it('shows empty state when no articles match search', () => {
        render(<HelpModal />);

        act(() => {
            useHelpStore.getState().openHelp();
            useHelpStore.getState().setSearchQuery('nope');
            useHelpStore.getState().setSelectedArticle(null);
        });

        expect(screen.getByText('No articles found')).toBeInTheDocument();
        expect(screen.getByText('Select an article to read')).toBeInTheDocument();
    });

    it('updates search query when typing in the search input', async () => {
        const user = userEvent.setup();
        render(<HelpModal />);

        act(() => {
            useHelpStore.getState().openHelp();
        });

        const input = screen.getByPlaceholderText('Search articles...');
        await user.type(input, 'billing');

        expect(input).toHaveValue('billing');
    });

    it('updates selected category when clicking a category button', async () => {
        const user = userEvent.setup();
        render(<HelpModal />);

        act(() => {
            useHelpStore.getState().openHelp();
        });

        await user.click(screen.getByRole('button', { name: 'Billing' }));

        expect(useHelpStore.getState().selectedCategory).toBe('Billing');
    });

    it('updates selected article when clicking an article', async () => {
        const user = userEvent.setup();
        render(<HelpModal />);

        act(() => {
            useHelpStore.getState().openHelp();
            useHelpStore.getState().setSelectedArticle(null);
        });

        await user.click(screen.getByRole('button', { name: new RegExp(HELP_ARTICLES[0].title) }));

        expect(useHelpStore.getState().selectedArticle?.id).toBe(HELP_ARTICLES[0].id);
    });

    it('closes when dialog close button is clicked', async () => {
        const user = userEvent.setup();
        render(<HelpModal />);

        act(() => {
            useHelpStore.getState().openHelp();
        });

        await user.click(screen.getByText('Close'));

        expect(useHelpStore.getState().isOpen).toBe(false);
    });

    it('closes on Escape key', () => {
        render(<HelpModal />);

        act(() => {
            useHelpStore.getState().openHelp();
        });

        fireEvent.keyDown(window, { key: 'Escape' });

        expect(useHelpStore.getState().isOpen).toBe(false);
    });
});

describe('HelpTrigger', () => {
    beforeEach(() => {
        act(() => {
            useHelpStore.getState().reset();
        });
    });

    it('opens help modal from sidebar trigger', async () => {
        const user = userEvent.setup();
        render(<HelpTrigger />);

        await user.click(screen.getByRole('button', { name: /Help & Support/i }));

        expect(useHelpStore.getState().isOpen).toBe(true);
    });

    it('opens help modal from icon trigger', async () => {
        const user = userEvent.setup();
        render(<HelpTrigger variant="icon" />);

        await user.click(screen.getByRole('button'));

        expect(useHelpStore.getState().isOpen).toBe(true);
    });

    it('opens help modal from fab trigger', async () => {
        const user = userEvent.setup();
        render(<HelpTrigger variant="fab" />);

        await user.click(screen.getByRole('button'));

        expect(useHelpStore.getState().isOpen).toBe(true);
    });
});
