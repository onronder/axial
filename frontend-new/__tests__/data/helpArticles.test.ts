import { describe, it, expect } from 'vitest';
import {
    HELP_ARTICLES,
    getCategories,
    getArticlesByCategory,
    searchArticles,
    getArticleById,
} from '@/data/helpArticles';

describe('helpArticles data helpers', () => {
    it('returns all categories', () => {
        const categories = getCategories();
        expect(categories).toContain('General');
        expect(categories).toContain('AI Features');
    });

    it('filters articles by category', () => {
        const billingArticles = getArticlesByCategory('Billing');
        expect(billingArticles.length).toBeGreaterThan(0);
        expect(billingArticles.every(a => a.category === 'Billing')).toBe(true);
    });

    it('searches articles by title or content', () => {
        const results = searchArticles('smart router');
        expect(results.length).toBeGreaterThan(0);
    });

    it('finds article by ID', () => {
        const article = getArticleById(HELP_ARTICLES[0].id);
        expect(article?.id).toBe(HELP_ARTICLES[0].id);
    });
});
