/**
 * Unit Tests for Help Library Utility
 * 
 * Tests markdown parsing, article sorting, and category retrieval.
 */

import { describe, it, expect, vi, beforeEach } from 'vitest';
import * as fs from 'fs';
import * as path from 'path';

// Mock fs and path
vi.mock('fs');
vi.mock('path');

// Mock gray-matter
vi.mock('gray-matter', () => ({
    default: vi.fn((content: string) => {
        // Parse mock frontmatter
        const match = content.match(/---\n([\s\S]*?)\n---\n([\s\S]*)/);
        if (match) {
            const frontmatterLines = match[1].split('\n');
            const data: Record<string, any> = {};
            frontmatterLines.forEach(line => {
                const [key, ...valueParts] = line.split(':');
                if (key && valueParts.length) {
                    const value = valueParts.join(':').trim().replace(/^["']|["']$/g, '');
                    if (key.trim() === 'order') {
                        data[key.trim()] = parseInt(value);
                    } else {
                        data[key.trim()] = value;
                    }
                }
            });
            return { data, content: match[2] };
        }
        return { data: {}, content };
    }),
}));

describe('Help Library', () => {
    beforeEach(() => {
        vi.clearAllMocks();

        // Mock path.join
        (path.join as any).mockImplementation((...args: string[]) => args.join('/'));

        // Mock process.cwd
        vi.spyOn(process, 'cwd').mockReturnValue('/app');
    });

    describe('getAllArticles', () => {
        it('should return empty array if directory does not exist', async () => {
            (fs.existsSync as any).mockReturnValue(false);

            // Dynamic import to get fresh module
            const { getAllArticles } = await import('@/lib/help');
            const articles = getAllArticles();

            expect(articles).toEqual([]);
        });

        it('should return articles sorted by order', async () => {
            (fs.existsSync as any).mockReturnValue(true);
            (fs.readdirSync as any).mockReturnValue(['02-second.md', '01-first.md']);
            (fs.readFileSync as any).mockImplementation((filePath: string) => {
                if (filePath.includes('01-first')) {
                    return `---
title: "First Article"
category: "Getting Started"
order: 1
---
Content here`;
                }
                return `---
title: "Second Article"
category: "Features"
order: 2
---
Content here`;
            });

            const { getAllArticles } = await import('@/lib/help');
            const articles = getAllArticles();

            expect(articles[0].order).toBeLessThan(articles[1].order);
        });

        it('should filter non-markdown files', async () => {
            (fs.existsSync as any).mockReturnValue(true);
            (fs.readdirSync as any).mockReturnValue(['article.md', 'readme.txt', 'image.png']);
            (fs.readFileSync as any).mockReturnValue(`---
title: "Test"
category: "Test"
order: 1
---
Content`);

            const { getAllArticles } = await import('@/lib/help');
            const articles = getAllArticles();

            expect(articles).toHaveLength(1);
        });
    });

    describe('getArticleBySlug', () => {
        it('should return null for non-existent slug', async () => {
            (fs.existsSync as any).mockReturnValue(false);

            const { getArticleBySlug } = await import('@/lib/help');
            const article = getArticleBySlug('nonexistent');

            expect(article).toBeNull();
        });

        it('should return full article with content', async () => {
            (fs.existsSync as any).mockReturnValue(true);
            (fs.readFileSync as any).mockReturnValue(`---
title: "Test Article"
category: "Test Category"
order: 1
---

# Full Content

This is the article body.`);

            const { getArticleBySlug } = await import('@/lib/help');
            const article = getArticleBySlug('test-article');

            expect(article).not.toBeNull();
            expect(article?.title).toBe('Test Article');
            expect(article?.category).toBe('Test Category');
            expect(article?.content).toContain('Full Content');
        });
    });

    describe('getCategories', () => {
        it('should group articles by category', async () => {
            (fs.existsSync as any).mockReturnValue(true);
            (fs.readdirSync as any).mockReturnValue(['01.md', '02.md', '03.md']);

            let callCount = 0;
            (fs.readFileSync as any).mockImplementation(() => {
                callCount++;
                const categories = ['Basics', 'Basics', 'Advanced'];
                return `---
title: "Article ${callCount}"
category: "${categories[callCount - 1]}"
order: ${callCount}
---
Content`;
            });

            const { getCategories } = await import('@/lib/help');
            const categories = getCategories();

            expect(Object.keys(categories)).toContain('Basics');
            expect(Object.keys(categories)).toContain('Advanced');
        });
    });

    describe('getCategoryNames', () => {
        it('should return unique category names in order', async () => {
            (fs.existsSync as any).mockReturnValue(true);
            (fs.readdirSync as any).mockReturnValue(['01.md', '02.md']);

            let callCount = 0;
            (fs.readFileSync as any).mockImplementation(() => {
                callCount++;
                return `---
title: "Article ${callCount}"
category: "Category ${callCount}"
order: ${callCount}
---
Content`;
            });

            const { getCategoryNames } = await import('@/lib/help');
            const names = getCategoryNames();

            expect(names.length).toBe(2);
        });
    });
});
