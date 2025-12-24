/**
 * Help Center Data Utility
 * 
 * Reads and parses markdown files from content/help directory.
 * Uses gray-matter for frontmatter parsing.
 */

import fs from 'fs';
import path from 'path';
import matter from 'gray-matter';

const helpDirectory = path.join(process.cwd(), 'content/help');

export interface HelpArticle {
    slug: string;
    title: string;
    category: string;
    order: number;
    content: string;
}

export interface HelpArticleMeta {
    slug: string;
    title: string;
    category: string;
    order: number;
}

/**
 * Get all help articles sorted by order.
 */
export function getAllArticles(): HelpArticleMeta[] {
    // Ensure directory exists
    if (!fs.existsSync(helpDirectory)) {
        return [];
    }

    const fileNames = fs.readdirSync(helpDirectory);

    const articles = fileNames
        .filter((fileName) => fileName.endsWith('.md'))
        .map((fileName) => {
            const slug = fileName.replace(/\.md$/, '');
            const fullPath = path.join(helpDirectory, fileName);
            const fileContents = fs.readFileSync(fullPath, 'utf8');
            const { data } = matter(fileContents);

            return {
                slug,
                title: data.title || slug,
                category: data.category || 'General',
                order: data.order || 999,
            };
        });

    // Sort by order
    return articles.sort((a, b) => a.order - b.order);
}

/**
 * Get a single article by slug with full content.
 */
export function getArticleBySlug(slug: string): HelpArticle | null {
    const fullPath = path.join(helpDirectory, `${slug}.md`);

    if (!fs.existsSync(fullPath)) {
        return null;
    }

    const fileContents = fs.readFileSync(fullPath, 'utf8');
    const { data, content } = matter(fileContents);

    return {
        slug,
        title: data.title || slug,
        category: data.category || 'General',
        order: data.order || 999,
        content,
    };
}

/**
 * Get all articles grouped by category.
 */
export function getCategories(): Record<string, HelpArticleMeta[]> {
    const articles = getAllArticles();

    return articles.reduce((acc, article) => {
        const category = article.category;
        if (!acc[category]) {
            acc[category] = [];
        }
        acc[category].push(article);
        return acc;
    }, {} as Record<string, HelpArticleMeta[]>);
}

/**
 * Get all unique category names in order of first appearance.
 */
export function getCategoryNames(): string[] {
    const articles = getAllArticles();
    const seen = new Set<string>();
    const categories: string[] = [];

    for (const article of articles) {
        if (!seen.has(article.category)) {
            seen.add(article.category);
            categories.push(article.category);
        }
    }

    return categories;
}
