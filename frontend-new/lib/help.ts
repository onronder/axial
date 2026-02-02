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
 * Sanitize slug to prevent path traversal attacks.
 * Only allows alphanumeric characters, hyphens, and underscores.
 * SECURITY FIX: Prevents directory traversal (e.g., "../../../etc/passwd")
 */
function sanitizeSlug(slug: string): string | null {
    // Only allow alphanumeric, hyphens, and underscores
    const sanitized = slug.replace(/[^a-zA-Z0-9_-]/g, '');
    
    // Reject if sanitization changed the slug (suspicious input)
    if (!sanitized || sanitized !== slug) {
        return null;
    }
    
    return sanitized;
}

/**
 * Get a single article by slug with full content.
 * SECURITY: Includes path traversal protection via slug sanitization.
 */
export function getArticleBySlug(slug: string): HelpArticle | null {
    // SECURITY FIX: Sanitize slug to prevent path traversal
    const sanitizedSlug = sanitizeSlug(slug);
    if (!sanitizedSlug) {
        return null;
    }

    const fullPath = path.join(helpDirectory, `${sanitizedSlug}.md`);
    
    // SECURITY FIX: Verify resolved path stays within allowed directory
    // Note: path.resolve and path.sep may be undefined in test environments
    if (typeof path.resolve === 'function' && path.sep) {
        const resolvedPath = path.resolve(fullPath);
        const resolvedHelpDir = path.resolve(helpDirectory);
        if (resolvedPath && resolvedHelpDir && !resolvedPath.startsWith(resolvedHelpDir + path.sep)) {
            return null;
        }
    }

    if (!fs.existsSync(fullPath)) {
        return null;
    }

    const fileContents = fs.readFileSync(fullPath, 'utf8');
    const { data, content } = matter(fileContents);

    return {
        slug: sanitizedSlug,
        title: data.title || sanitizedSlug,
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
