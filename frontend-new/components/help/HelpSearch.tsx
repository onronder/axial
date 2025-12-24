"use client";

/**
 * Help Search Component
 * 
 * Client-side search input to filter help articles.
 */

import { useState } from 'react';
import { Search, X } from 'lucide-react';
import { Input } from '@/components/ui/input';
import Link from 'next/link';
import { cn } from '@/lib/utils';

interface ArticleMeta {
    slug: string;
    title: string;
    category: string;
    order: number;
}

interface HelpSearchProps {
    articles: ArticleMeta[];
}

export function HelpSearch({ articles }: HelpSearchProps) {
    const [query, setQuery] = useState('');
    const [isFocused, setIsFocused] = useState(false);

    const filteredArticles = query.trim()
        ? articles.filter(
            (article) =>
                article.title.toLowerCase().includes(query.toLowerCase()) ||
                article.category.toLowerCase().includes(query.toLowerCase())
        )
        : [];

    const showResults = isFocused && query.trim() && filteredArticles.length > 0;

    return (
        <div className="relative w-full max-w-md">
            <div className="relative">
                <Search className="absolute left-3 top-1/2 -translate-y-1/2 h-4 w-4 text-muted-foreground" />
                <Input
                    type="text"
                    placeholder="Search help articles..."
                    value={query}
                    onChange={(e) => setQuery(e.target.value)}
                    onFocus={() => setIsFocused(true)}
                    onBlur={() => setTimeout(() => setIsFocused(false), 200)}
                    className="pl-10 pr-10"
                />
                {query && (
                    <button
                        onClick={() => setQuery('')}
                        className="absolute right-3 top-1/2 -translate-y-1/2 text-muted-foreground hover:text-foreground"
                    >
                        <X className="h-4 w-4" />
                    </button>
                )}
            </div>

            {/* Search Results Dropdown */}
            {showResults && (
                <div className="absolute top-full left-0 right-0 mt-2 bg-popover border border-border rounded-lg shadow-lg overflow-hidden z-50">
                    <ul className="py-2">
                        {filteredArticles.map((article) => (
                            <li key={article.slug}>
                                <Link
                                    href={`/dashboard/help/${article.slug}`}
                                    className="flex flex-col px-4 py-2 hover:bg-muted transition-colors"
                                    onClick={() => {
                                        setQuery('');
                                        setIsFocused(false);
                                    }}
                                >
                                    <span className="text-sm font-medium text-foreground">
                                        {article.title}
                                    </span>
                                    <span className="text-xs text-muted-foreground">
                                        {article.category}
                                    </span>
                                </Link>
                            </li>
                        ))}
                    </ul>
                </div>
            )}

            {/* No Results */}
            {isFocused && query.trim() && filteredArticles.length === 0 && (
                <div className="absolute top-full left-0 right-0 mt-2 bg-popover border border-border rounded-lg shadow-lg p-4 z-50">
                    <p className="text-sm text-muted-foreground text-center">
                        No articles found for "{query}"
                    </p>
                </div>
            )}
        </div>
    );
}
