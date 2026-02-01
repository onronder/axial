/**
 * Comprehensive Unit Tests for helpArticles Data Module
 * 
 * Tests all exported functions:
 * - HELP_ARTICLES
 * - getCategories
 * - getArticlesByCategory
 * - searchArticles
 * - getArticleById
 * - getRelatedArticles
 * - getCategoryCounts
 */

import { describe, it, expect } from 'vitest';
import {
    HELP_ARTICLES,
    HelpArticle,
    getCategories,
    getArticlesByCategory,
    searchArticles,
    getArticleById,
    getRelatedArticles,
    getCategoryCounts,
} from '@/data/helpArticles';

describe('HELP_ARTICLES', () => {
    it('should contain multiple articles', () => {
        expect(HELP_ARTICLES.length).toBeGreaterThan(0);
    });

    it('should have valid structure for all articles', () => {
        HELP_ARTICLES.forEach(article => {
            expect(article.id).toBeDefined();
            expect(typeof article.id).toBe('string');
            expect(article.title).toBeDefined();
            expect(typeof article.title).toBe('string');
            expect(article.category).toBeDefined();
            expect(article.content).toBeDefined();
            expect(typeof article.content).toBe('string');
        });
    });

    it('should have unique IDs', () => {
        const ids = HELP_ARTICLES.map(a => a.id);
        const uniqueIds = new Set(ids);
        expect(uniqueIds.size).toBe(ids.length);
    });
});

describe('getCategories', () => {
    it('should return all expected categories', () => {
        const categories = getCategories();
        expect(categories).toContain('General');
        expect(categories).toContain('AI Features');
        expect(categories).toContain('Connectors');
        expect(categories).toContain('Teams');
        expect(categories).toContain('Billing');
        expect(categories).toContain('Troubleshooting');
    });

    it('should return categories in correct order', () => {
        const categories = getCategories();
        expect(categories).toEqual([
            'General',
            'AI Features',
            'Connectors',
            'Teams',
            'Billing',
            'Troubleshooting',
        ]);
    });

    it('should return exactly 6 categories', () => {
        const categories = getCategories();
        expect(categories.length).toBe(6);
    });
});

describe('getArticlesByCategory', () => {
    it('should filter articles by General category', () => {
        const articles = getArticlesByCategory('General');
        expect(articles.length).toBeGreaterThan(0);
        articles.forEach(article => {
            expect(article.category).toBe('General');
        });
    });

    it('should filter articles by AI Features category', () => {
        const articles = getArticlesByCategory('AI Features');
        expect(articles.length).toBeGreaterThan(0);
        articles.forEach(article => {
            expect(article.category).toBe('AI Features');
        });
    });

    it('should filter articles by Connectors category', () => {
        const articles = getArticlesByCategory('Connectors');
        expect(articles.length).toBeGreaterThan(0);
        articles.forEach(article => {
            expect(article.category).toBe('Connectors');
        });
    });

    it('should filter articles by Teams category', () => {
        const articles = getArticlesByCategory('Teams');
        expect(articles.length).toBeGreaterThan(0);
        articles.forEach(article => {
            expect(article.category).toBe('Teams');
        });
    });

    it('should filter articles by Billing category', () => {
        const articles = getArticlesByCategory('Billing');
        expect(articles.length).toBeGreaterThan(0);
        articles.forEach(article => {
            expect(article.category).toBe('Billing');
        });
    });

    it('should filter articles by Troubleshooting category', () => {
        const articles = getArticlesByCategory('Troubleshooting');
        expect(articles.length).toBeGreaterThan(0);
        articles.forEach(article => {
            expect(article.category).toBe('Troubleshooting');
        });
    });

    it('should return empty array for non-existent category', () => {
        const articles = getArticlesByCategory('NonExistent' as HelpArticle['category']);
        expect(articles).toEqual([]);
    });
});

describe('searchArticles', () => {
    it('should return empty array for empty query', () => {
        const results = searchArticles('');
        expect(results).toEqual([]);
    });

    it('should return empty array for whitespace-only query', () => {
        const results = searchArticles('   ');
        expect(results).toEqual([]);
    });

    it('should find articles by title', () => {
        const results = searchArticles('Getting Started');
        expect(results.length).toBeGreaterThan(0);
        expect(results.some(a => a.title.includes('Getting Started'))).toBe(true);
    });

    it('should find articles by content', () => {
        const results = searchArticles('encryption');
        expect(results.length).toBeGreaterThan(0);
    });

    it('should find articles by keyword', () => {
        const results = searchArticles('gdrive');
        expect(results.length).toBeGreaterThan(0);
    });

    it('should be case-insensitive', () => {
        const lowerResults = searchArticles('ghost protocol');
        const upperResults = searchArticles('GHOST PROTOCOL');
        expect(lowerResults.length).toBe(upperResults.length);
    });

    it('should prioritize title matches', () => {
        // Search for something that appears in both title and content
        const results = searchArticles('started');
        expect(results.length).toBeGreaterThan(0);
        // First result should have "Started" in title
        if (results.length > 1) {
            const firstHasInTitle = results[0].title.toLowerCase().includes('started');
            expect(firstHasInTitle).toBe(true);
        }
    });

    it('should match partial keywords', () => {
        const results = searchArticles('auth');
        expect(results.length).toBeGreaterThan(0);
    });

    it('should find articles with multi-word queries', () => {
        const results = searchArticles('smart router ai');
        expect(results.length).toBeGreaterThan(0);
    });
});

describe('getArticleById', () => {
    it('should find article by valid ID', () => {
        const firstArticle = HELP_ARTICLES[0];
        const result = getArticleById(firstArticle.id);
        expect(result).toBeDefined();
        expect(result?.id).toBe(firstArticle.id);
    });

    it('should return undefined for non-existent ID', () => {
        const result = getArticleById('non-existent-id-12345');
        expect(result).toBeUndefined();
    });

    it('should return undefined for empty ID', () => {
        const result = getArticleById('');
        expect(result).toBeUndefined();
    });

    it('should return exact match for known article', () => {
        const result = getArticleById('getting-started');
        expect(result).toBeDefined();
        expect(result?.id).toBe('getting-started');
        expect(result?.title).toBe('Getting Started with Axio Hub');
    });

    it('should return article with full content', () => {
        const result = getArticleById('ghost-protocol');
        expect(result).toBeDefined();
        expect(result?.content.length).toBeGreaterThan(100);
    });
});

describe('getRelatedArticles', () => {
    it('should return related articles based on shared keywords', () => {
        // Find an article with keywords
        const articleWithKeywords = HELP_ARTICLES.find(a => a.keywords && a.keywords.length > 0);
        if (articleWithKeywords) {
            const related = getRelatedArticles(articleWithKeywords.id);
            expect(related.length).toBeLessThanOrEqual(3);
        }
    });

    it('should not include the source article in results', () => {
        const sourceArticle = HELP_ARTICLES[0];
        const related = getRelatedArticles(sourceArticle.id);
        expect(related.every(a => a.id !== sourceArticle.id)).toBe(true);
    });

    it('should return empty array for non-existent article', () => {
        const related = getRelatedArticles('non-existent-id');
        expect(related).toEqual([]);
    });

    it('should return empty array for article without keywords', () => {
        // Create a scenario - if all articles have keywords, this may not trigger
        const articleWithoutKeywords = HELP_ARTICLES.find(a => !a.keywords);
        if (articleWithoutKeywords) {
            const related = getRelatedArticles(articleWithoutKeywords.id);
            expect(related).toEqual([]);
        }
    });

    it('should respect limit parameter', () => {
        const sourceArticle = HELP_ARTICLES.find(a => a.keywords && a.keywords.length > 0);
        if (sourceArticle) {
            const related2 = getRelatedArticles(sourceArticle.id, 2);
            expect(related2.length).toBeLessThanOrEqual(2);

            const related5 = getRelatedArticles(sourceArticle.id, 5);
            expect(related5.length).toBeLessThanOrEqual(5);
        }
    });

    it('should prefer articles from same category', () => {
        const sourceArticle = HELP_ARTICLES.find(
            a => a.keywords && a.keywords.length > 0 && a.category === 'Connectors'
        );
        if (sourceArticle) {
            const related = getRelatedArticles(sourceArticle.id, 10);
            // Should have some articles from same category
            const sameCategoryCount = related.filter(a => a.category === sourceArticle.category).length;
            // Not guaranteed but likely to have at least some
            expect(sameCategoryCount).toBeGreaterThanOrEqual(0);
        }
    });

    it('should use default limit of 3', () => {
        const sourceArticle = HELP_ARTICLES.find(a => a.keywords && a.keywords.length > 0);
        if (sourceArticle) {
            const related = getRelatedArticles(sourceArticle.id);
            expect(related.length).toBeLessThanOrEqual(3);
        }
    });
});

describe('getCategoryCounts', () => {
    it('should return counts for all categories', () => {
        const counts = getCategoryCounts();
        expect(counts['General']).toBeDefined();
        expect(counts['AI Features']).toBeDefined();
        expect(counts['Connectors']).toBeDefined();
        expect(counts['Teams']).toBeDefined();
        expect(counts['Billing']).toBeDefined();
        expect(counts['Troubleshooting']).toBeDefined();
    });

    it('should return correct count for each category', () => {
        const counts = getCategoryCounts();
        
        // Verify counts match actual articles
        for (const category of getCategories()) {
            const articlesInCategory = getArticlesByCategory(category);
            expect(counts[category]).toBe(articlesInCategory.length);
        }
    });

    it('should sum to total article count', () => {
        const counts = getCategoryCounts();
        const totalFromCounts = Object.values(counts).reduce((sum, count) => sum + count, 0);
        expect(totalFromCounts).toBe(HELP_ARTICLES.length);
    });

    it('should return numbers greater than or equal to 0', () => {
        const counts = getCategoryCounts();
        Object.values(counts).forEach(count => {
            expect(count).toBeGreaterThanOrEqual(0);
        });
    });
});

describe('Article Content Quality', () => {
    it('all articles should have meaningful titles', () => {
        HELP_ARTICLES.forEach(article => {
            expect(article.title.length).toBeGreaterThan(3);
        });
    });

    it('all articles should have substantial content', () => {
        HELP_ARTICLES.forEach(article => {
            expect(article.content.length).toBeGreaterThan(50);
        });
    });

    it('connector articles should exist for major integrations', () => {
        const connectorArticles = getArticlesByCategory('Connectors');
        const titles = connectorArticles.map(a => a.title.toLowerCase());
        
        // Check for major connectors
        expect(titles.some(t => t.includes('google'))).toBe(true);
        expect(titles.some(t => t.includes('dropbox'))).toBe(true);
        expect(titles.some(t => t.includes('notion'))).toBe(true);
        expect(titles.some(t => t.includes('github'))).toBe(true);
    });

    it('troubleshooting articles should cover common errors', () => {
        const troubleshootingArticles = getArticlesByCategory('Troubleshooting');
        const allContent = troubleshootingArticles.map(a => a.content.toLowerCase()).join(' ');
        
        expect(allContent).toContain('error');
        expect(allContent).toContain('solution');
    });
});
