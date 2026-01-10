import { describe, it, expect, beforeEach } from 'vitest';
import { useHelpStore } from '@/store/useHelpStore';
import { HELP_ARTICLES } from '@/data/helpArticles';

describe('useHelpStore', () => {
    beforeEach(() => {
        useHelpStore.getState().reset();
    });

    it('opens and closes help modal', () => {
        expect(useHelpStore.getState().isOpen).toBe(false);
        useHelpStore.getState().openHelp();
        expect(useHelpStore.getState().isOpen).toBe(true);
        useHelpStore.getState().closeHelp();
        expect(useHelpStore.getState().isOpen).toBe(false);
    });

    it('updates search query and selected article', () => {
        useHelpStore.getState().setSearchQuery('billing');
        expect(useHelpStore.getState().searchQuery).toBe('billing');

        useHelpStore.getState().setSelectedArticle(HELP_ARTICLES[0]);
        expect(useHelpStore.getState().selectedArticle?.id).toBe(HELP_ARTICLES[0].id);
    });

    it('updates selected category and resets article selection', () => {
        useHelpStore.getState().setSelectedArticle(HELP_ARTICLES[1]);
        useHelpStore.getState().setSelectedCategory('Billing');

        expect(useHelpStore.getState().selectedCategory).toBe('Billing');
        expect(useHelpStore.getState().selectedArticle).toBeNull();
    });

    it('reset returns to initial state', () => {
        useHelpStore.getState().openHelp();
        useHelpStore.getState().setSearchQuery('test');
        useHelpStore.getState().reset();

        expect(useHelpStore.getState().isOpen).toBe(false);
        expect(useHelpStore.getState().searchQuery).toBe('');
    });
});
