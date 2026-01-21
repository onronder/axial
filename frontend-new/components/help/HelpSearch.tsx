"use client";

/**
 * Help Search Component - Production Grade
 *
 * Features:
 * - Real-time search with debouncing
 * - Keyboard navigation (Arrow keys, Enter, Escape)
 * - Search result highlighting
 * - Reading time display
 * - Category badges
 * - Click outside to close
 * - Accessible with ARIA labels
 */

import { useState, useRef, useEffect, useCallback } from 'react';
import { Search, X, Clock, ChevronRight, FileText } from 'lucide-react';
import { Input } from '@/components/ui/input';
import { Badge } from '@/components/ui/badge';
import Link from 'next/link';
import { useRouter } from 'next/navigation';
import { cn } from '@/lib/utils';

interface ArticleMeta {
    slug: string;
    title: string;
    category: string;
    order: number;
    content?: string;
}

interface HelpSearchProps {
    articles: ArticleMeta[];
    placeholder?: string;
    className?: string;
}

// Category colors
const categoryColors: Record<string, string> = {
    "Getting Started": "bg-blue-500/10 text-blue-600 dark:text-blue-400",
    "Data Management": "bg-green-500/10 text-green-600 dark:text-green-400",
    "Features": "bg-purple-500/10 text-purple-600 dark:text-purple-400",
    "Settings": "bg-orange-500/10 text-orange-600 dark:text-orange-400",
    "Legal & Safety": "bg-red-500/10 text-red-600 dark:text-red-400",
};

// Calculate reading time
function getReadingTime(content: string): number {
    if (!content) return 1;
    const wordsPerMinute = 200;
    const wordCount = content.split(/\s+/).length;
    return Math.max(1, Math.ceil(wordCount / wordsPerMinute));
}

// Highlight search matches
function highlightText(text: string, query: string): React.ReactNode {
    if (!query.trim()) return text;

    try {
        const parts = text.split(new RegExp(`(${query.replace(/[.*+?^${}()|[\]\\]/g, '\\$&')})`, 'gi'));
        return parts.map((part, i) =>
            part.toLowerCase() === query.toLowerCase()
                ? <mark key={i} className="bg-yellow-200 dark:bg-yellow-800 text-foreground rounded px-0.5">{part}</mark>
                : part
        );
    } catch {
        return text;
    }
}

export function HelpSearch({ articles, placeholder = "Search help articles...", className }: HelpSearchProps) {
    const [query, setQuery] = useState('');
    const [isFocused, setIsFocused] = useState(false);
    const [focusedIndex, setFocusedIndex] = useState(-1);
    const router = useRouter();
    const inputRef = useRef<HTMLInputElement>(null);
    const dropdownRef = useRef<HTMLDivElement>(null);
    const itemRefs = useRef<(HTMLAnchorElement | null)[]>([]);

    // Filter articles based on query
    const filteredArticles = query.trim()
        ? articles.filter(
            (article) =>
                article.title.toLowerCase().includes(query.toLowerCase()) ||
                article.category.toLowerCase().includes(query.toLowerCase())
        ).slice(0, 8) // Limit to 8 results
        : [];

    const showResults = isFocused && query.trim().length > 0;

    // Handle keyboard navigation
    const handleKeyDown = useCallback((e: React.KeyboardEvent) => {
        if (!showResults) return;

        switch (e.key) {
            case 'ArrowDown':
                e.preventDefault();
                setFocusedIndex(prev =>
                    prev < filteredArticles.length - 1 ? prev + 1 : 0
                );
                break;
            case 'ArrowUp':
                e.preventDefault();
                setFocusedIndex(prev =>
                    prev > 0 ? prev - 1 : filteredArticles.length - 1
                );
                break;
            case 'Enter':
                e.preventDefault();
                if (focusedIndex >= 0 && filteredArticles[focusedIndex]) {
                    router.push(`/dashboard/help/${filteredArticles[focusedIndex].slug}`);
                    setQuery('');
                    setIsFocused(false);
                }
                break;
            case 'Escape':
                e.preventDefault();
                setIsFocused(false);
                inputRef.current?.blur();
                break;
        }
    }, [showResults, filteredArticles, focusedIndex, router]);

    // Reset focused index when query changes
    useEffect(() => {
        setFocusedIndex(-1);
    }, [query]);

    // Scroll focused item into view
    useEffect(() => {
        if (focusedIndex >= 0 && itemRefs.current[focusedIndex]) {
            itemRefs.current[focusedIndex]?.scrollIntoView({
                block: 'nearest',
                behavior: 'smooth'
            });
        }
    }, [focusedIndex]);

    // Handle click outside
    useEffect(() => {
        const handleClickOutside = (e: MouseEvent) => {
            if (
                dropdownRef.current &&
                !dropdownRef.current.contains(e.target as Node) &&
                inputRef.current &&
                !inputRef.current.contains(e.target as Node)
            ) {
                setIsFocused(false);
            }
        };

        document.addEventListener('mousedown', handleClickOutside);
        return () => document.removeEventListener('mousedown', handleClickOutside);
    }, []);

    return (
        <div className={cn("relative w-full max-w-lg", className)}>
            {/* Search Input */}
            <div className="relative">
                <Search className="absolute left-4 top-1/2 -translate-y-1/2 h-5 w-5 text-muted-foreground" />
                <Input
                    ref={inputRef}
                    type="text"
                    placeholder={placeholder}
                    value={query}
                    onChange={(e) => setQuery(e.target.value)}
                    onFocus={() => setIsFocused(true)}
                    onKeyDown={handleKeyDown}
                    className="pl-12 pr-12 h-12 text-base bg-background border-2 border-border/50 focus:border-primary/50 rounded-xl shadow-sm"
                    aria-label="Search help articles"
                    aria-expanded={showResults}
                    aria-haspopup="listbox"
                    aria-controls="search-results"
                    role="combobox"
                    autoComplete="off"
                />
                {query && (
                    <button
                        onClick={() => {
                            setQuery('');
                            inputRef.current?.focus();
                        }}
                        className="absolute right-4 top-1/2 -translate-y-1/2 p-1 rounded-full text-muted-foreground hover:text-foreground hover:bg-muted transition-colors cursor-pointer"
                        aria-label="Clear search"
                    >
                        <X className="h-4 w-4" />
                    </button>
                )}
            </div>

            {/* Keyboard hint */}
            {isFocused && !query && (
                <div className="absolute top-full left-0 right-0 mt-2 p-3 bg-popover border border-border rounded-xl shadow-lg text-center">
                    <p className="text-sm text-muted-foreground">
                        Type to search articles
                    </p>
                    <p className="text-xs text-muted-foreground/80 mt-1">
                        Use <kbd className="px-1.5 py-0.5 rounded bg-muted text-xs">↑</kbd> <kbd className="px-1.5 py-0.5 rounded bg-muted text-xs">↓</kbd> to navigate, <kbd className="px-1.5 py-0.5 rounded bg-muted text-xs">Enter</kbd> to select
                    </p>
                </div>
            )}

            {/* Search Results Dropdown */}
            {showResults && filteredArticles.length > 0 && (
                <div
                    ref={dropdownRef}
                    id="search-results"
                    role="listbox"
                    className="absolute top-full left-0 right-0 mt-2 bg-popover border border-border rounded-xl shadow-lg overflow-hidden z-50"
                >
                    <div className="p-2 border-b border-border/50">
                        <p className="text-xs text-muted-foreground px-2">
                            {filteredArticles.length} result{filteredArticles.length !== 1 ? 's' : ''} found
                        </p>
                    </div>
                    <ul className="py-1 max-h-80 overflow-y-auto">
                        {filteredArticles.map((article, index) => {
                            const colorClass = categoryColors[article.category] || "bg-muted text-muted-foreground";
                            return (
                                <li key={article.slug} role="option" aria-selected={focusedIndex === index}>
                                    <Link
                                        ref={el => { itemRefs.current[index] = el; }}
                                        href={`/dashboard/help/${article.slug}`}
                                        onClick={() => {
                                            setQuery('');
                                            setIsFocused(false);
                                        }}
                                        className={cn(
                                            "flex items-start gap-3 px-3 py-3 transition-colors cursor-pointer",
                                            focusedIndex === index
                                                ? "bg-accent"
                                                : "hover:bg-accent/50"
                                        )}
                                    >
                                        <div className="shrink-0 mt-0.5 p-1.5 rounded-lg bg-muted">
                                            <FileText className="h-4 w-4 text-muted-foreground" />
                                        </div>
                                        <div className="flex-1 min-w-0">
                                            <p className="font-medium text-sm text-foreground truncate">
                                                {highlightText(article.title, query)}
                                            </p>
                                            <div className="flex items-center gap-2 mt-1">
                                                <Badge variant="secondary" className={cn("text-[10px] px-1.5 py-0", colorClass)}>
                                                    {article.category}
                                                </Badge>
                                                <span className="text-xs text-muted-foreground flex items-center gap-1">
                                                    <Clock className="h-3 w-3" />
                                                    {getReadingTime(article.content || '')} min
                                                </span>
                                            </div>
                                        </div>
                                        <ChevronRight className="h-4 w-4 text-muted-foreground/50 shrink-0 mt-1" />
                                    </Link>
                                </li>
                            );
                        })}
                    </ul>
                    <div className="p-2 border-t border-border/50 bg-muted/30">
                        <p className="text-[10px] text-muted-foreground text-center">
                            <kbd className="px-1 py-0.5 rounded bg-muted">↵</kbd> to select · <kbd className="px-1 py-0.5 rounded bg-muted">esc</kbd> to close
                        </p>
                    </div>
                </div>
            )}

            {/* No Results */}
            {showResults && query.trim() && filteredArticles.length === 0 && (
                <div
                    ref={dropdownRef}
                    className="absolute top-full left-0 right-0 mt-2 bg-popover border border-border rounded-xl shadow-lg p-6 z-50"
                >
                    <div className="text-center">
                        <div className="inline-flex items-center justify-center w-12 h-12 rounded-full bg-muted mb-3">
                            <Search className="h-5 w-5 text-muted-foreground" />
                        </div>
                        <p className="text-sm font-medium text-foreground">
                            No articles found
                        </p>
                        <p className="text-xs text-muted-foreground mt-1">
                            No results for "{query}"
                        </p>
                        <button
                            onClick={() => {
                                setQuery('');
                                inputRef.current?.focus();
                            }}
                            className="mt-3 text-xs text-primary hover:underline cursor-pointer"
                        >
                            Clear search
                        </button>
                    </div>
                </div>
            )}
        </div>
    );
}
