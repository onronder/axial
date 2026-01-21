"use client";

/**
 * Help Sidebar Component - Production Grade
 *
 * Features:
 * - Collapsible category sections
 * - Active state highlighting with smooth transitions
 * - Reading time display
 * - Search integration
 * - Responsive design
 * - Keyboard accessible
 */

import { useState, useMemo } from 'react';
import Link from 'next/link';
import { usePathname } from 'next/navigation';
import { cn } from '@/lib/utils';
import {
    BookOpen,
    ChevronRight,
    ChevronDown,
    Search,
    Clock,
    Zap,
    FileText,
    Settings,
    Shield,
    Sparkles,
    Home,
    X
} from 'lucide-react';
import { Input } from '@/components/ui/input';
import { ScrollArea } from '@/components/ui/scroll-area';
import { Badge } from '@/components/ui/badge';

interface ArticleMeta {
    slug: string;
    title: string;
    category: string;
    order: number;
    content?: string;
}

interface HelpSidebarProps {
    articles: ArticleMeta[];
    categories: Record<string, ArticleMeta[]>;
    currentSlug?: string;
}

// Category configuration
const categoryConfig: Record<string, {
    icon: React.ReactNode;
    color: string;
    bgColor: string;
}> = {
    "Getting Started": {
        icon: <Zap className="h-4 w-4" />,
        color: "text-blue-600 dark:text-blue-400",
        bgColor: "bg-blue-500/10"
    },
    "Data Management": {
        icon: <FileText className="h-4 w-4" />,
        color: "text-green-600 dark:text-green-400",
        bgColor: "bg-green-500/10"
    },
    "Features": {
        icon: <Sparkles className="h-4 w-4" />,
        color: "text-purple-600 dark:text-purple-400",
        bgColor: "bg-purple-500/10"
    },
    "Settings": {
        icon: <Settings className="h-4 w-4" />,
        color: "text-orange-600 dark:text-orange-400",
        bgColor: "bg-orange-500/10"
    },
    "Legal & Safety": {
        icon: <Shield className="h-4 w-4" />,
        color: "text-red-600 dark:text-red-400",
        bgColor: "bg-red-500/10"
    },
};

// Calculate reading time
function getReadingTime(content: string): number {
    if (!content) return 1;
    const wordsPerMinute = 200;
    const wordCount = content.split(/\s+/).length;
    return Math.max(1, Math.ceil(wordCount / wordsPerMinute));
}

export function HelpSidebar({ articles, categories, currentSlug }: HelpSidebarProps) {
    const pathname = usePathname();
    const [searchQuery, setSearchQuery] = useState('');
    const [expandedCategories, setExpandedCategories] = useState<Set<string>>(() => {
        // Auto-expand the category of the current article
        if (currentSlug) {
            const currentArticle = articles.find(a => a.slug === currentSlug);
            if (currentArticle) {
                return new Set([currentArticle.category]);
            }
        }
        // Default: expand first category
        const firstCategory = Object.keys(categories)[0];
        return firstCategory ? new Set([firstCategory]) : new Set();
    });

    // Filter articles based on search
    const filteredCategories = useMemo(() => {
        if (!searchQuery.trim()) return categories;

        const query = searchQuery.toLowerCase();
        const filtered: Record<string, ArticleMeta[]> = {};

        Object.entries(categories).forEach(([category, categoryArticles]) => {
            const matchingArticles = categoryArticles.filter(article =>
                article.title.toLowerCase().includes(query) ||
                category.toLowerCase().includes(query)
            );
            if (matchingArticles.length > 0) {
                filtered[category] = matchingArticles;
            }
        });

        return filtered;
    }, [categories, searchQuery]);

    // Toggle category expansion
    const toggleCategory = (category: string) => {
        setExpandedCategories(prev => {
            const next = new Set(prev);
            if (next.has(category)) {
                next.delete(category);
            } else {
                next.add(category);
            }
            return next;
        });
    };

    // Expand all when searching
    const effectiveExpandedCategories = searchQuery.trim()
        ? new Set(Object.keys(filteredCategories))
        : expandedCategories;

    const totalArticles = articles.length;
    const filteredCount = Object.values(filteredCategories).flat().length;

    return (
        <aside className="w-72 shrink-0 border-r border-border/50 bg-muted/20 hidden lg:block">
            <div className="sticky top-0 h-screen flex flex-col">
                {/* Header */}
                <div className="p-4 border-b border-border/50">
                    <Link
                        href="/dashboard/help"
                        className="flex items-center gap-3 mb-4 group"
                    >
                        <div className="flex h-10 w-10 items-center justify-center rounded-xl bg-primary/10 group-hover:bg-primary/20 transition-colors">
                            <BookOpen className="h-5 w-5 text-primary" />
                        </div>
                        <div>
                            <h2 className="font-semibold text-lg group-hover:text-primary transition-colors">
                                Help Center
                            </h2>
                            <p className="text-xs text-muted-foreground">
                                {totalArticles} articles
                            </p>
                        </div>
                    </Link>

                    {/* Search */}
                    <div className="relative">
                        <Search className="absolute left-3 top-1/2 -translate-y-1/2 h-4 w-4 text-muted-foreground" />
                        <Input
                            placeholder="Search articles..."
                            value={searchQuery}
                            onChange={(e) => setSearchQuery(e.target.value)}
                            className="pl-10 pr-10 h-9 bg-background/50"
                        />
                        {searchQuery && (
                            <button
                                onClick={() => setSearchQuery('')}
                                className="absolute right-3 top-1/2 -translate-y-1/2 text-muted-foreground hover:text-foreground transition-colors cursor-pointer"
                            >
                                <X className="h-4 w-4" />
                            </button>
                        )}
                    </div>

                    {/* Search results count */}
                    {searchQuery.trim() && (
                        <p className="mt-2 text-xs text-muted-foreground">
                            {filteredCount} result{filteredCount !== 1 ? 's' : ''} found
                        </p>
                    )}
                </div>

                {/* Quick Links */}
                <div className="px-3 py-2 border-b border-border/50">
                    <Link
                        href="/dashboard/help"
                        className={cn(
                            "flex items-center gap-2 px-3 py-2 rounded-lg text-sm transition-all",
                            pathname === '/dashboard/help'
                                ? "bg-primary/10 text-primary font-medium"
                                : "text-muted-foreground hover:text-foreground hover:bg-accent/50"
                        )}
                    >
                        <Home className="h-4 w-4" />
                        All Categories
                    </Link>
                </div>

                {/* Categories Navigation */}
                <ScrollArea className="flex-1">
                    <nav className="p-3 space-y-2">
                        {Object.entries(filteredCategories).map(([category, categoryArticles]) => {
                            const config = categoryConfig[category];
                            const isExpanded = effectiveExpandedCategories.has(category);
                            const hasActiveArticle = categoryArticles.some(
                                a => pathname === `/dashboard/help/${a.slug}`
                            );

                            return (
                                <div
                                    key={category}
                                    className={cn(
                                        "rounded-lg border overflow-hidden transition-all",
                                        hasActiveArticle
                                            ? "border-primary/30 bg-primary/5"
                                            : "border-border/50 hover:border-border"
                                    )}
                                >
                                    {/* Category Header */}
                                    <button
                                        onClick={() => toggleCategory(category)}
                                        className="w-full flex items-center justify-between p-3 hover:bg-accent/30 transition-colors cursor-pointer"
                                    >
                                        <div className="flex items-center gap-2.5">
                                            <div className={cn("p-1.5 rounded-lg", config?.bgColor || "bg-muted")}>
                                                <span className={config?.color || "text-muted-foreground"}>
                                                    {config?.icon || <FileText className="h-4 w-4" />}
                                                </span>
                                            </div>
                                            <span className={cn(
                                                "font-medium text-sm",
                                                hasActiveArticle && "text-primary"
                                            )}>
                                                {category}
                                            </span>
                                            <Badge variant="secondary" className="text-[10px] px-1.5 py-0">
                                                {categoryArticles.length}
                                            </Badge>
                                        </div>
                                        {isExpanded ? (
                                            <ChevronDown className="h-4 w-4 text-muted-foreground" />
                                        ) : (
                                            <ChevronRight className="h-4 w-4 text-muted-foreground" />
                                        )}
                                    </button>

                                    {/* Category Articles */}
                                    {isExpanded && (
                                        <div className="border-t border-border/30 bg-background/30">
                                            {categoryArticles.map((article) => {
                                                const isActive = pathname === `/dashboard/help/${article.slug}`;
                                                const readingTime = getReadingTime(article.content || '');

                                                return (
                                                    <Link
                                                        key={article.slug}
                                                        href={`/dashboard/help/${article.slug}`}
                                                        className={cn(
                                                            "flex items-center gap-2 px-3 py-2.5 text-sm transition-all border-l-2",
                                                            isActive
                                                                ? "bg-primary/10 border-l-primary text-primary font-medium"
                                                                : "border-l-transparent text-muted-foreground hover:text-foreground hover:bg-accent/30 hover:border-l-muted-foreground/30"
                                                        )}
                                                    >
                                                        <ChevronRight className={cn(
                                                            "h-3 w-3 shrink-0 transition-colors",
                                                            isActive ? "text-primary" : "text-muted-foreground/50"
                                                        )} />
                                                        <span className="truncate flex-1">
                                                            {searchQuery.trim() ? (
                                                                highlightText(article.title, searchQuery)
                                                            ) : (
                                                                article.title
                                                            )}
                                                        </span>
                                                        <span className="text-[10px] text-muted-foreground/60 shrink-0 flex items-center gap-0.5">
                                                            <Clock className="h-2.5 w-2.5" />
                                                            {readingTime}m
                                                        </span>
                                                    </Link>
                                                );
                                            })}
                                        </div>
                                    )}
                                </div>
                            );
                        })}

                        {/* No results */}
                        {Object.keys(filteredCategories).length === 0 && searchQuery.trim() && (
                            <div className="text-center py-8">
                                <div className="inline-flex items-center justify-center w-12 h-12 rounded-full bg-muted mb-3">
                                    <Search className="h-5 w-5 text-muted-foreground" />
                                </div>
                                <p className="text-sm text-muted-foreground">
                                    No articles found for "{searchQuery}"
                                </p>
                                <button
                                    onClick={() => setSearchQuery('')}
                                    className="mt-2 text-xs text-primary hover:underline cursor-pointer"
                                >
                                    Clear search
                                </button>
                            </div>
                        )}
                    </nav>
                </ScrollArea>

                {/* Footer */}
                <div className="p-3 border-t border-border/50 bg-background/50">
                    <a
                        href="mailto:support@axiohub.io"
                        className="flex items-center justify-center gap-2 px-4 py-2.5 rounded-lg bg-muted hover:bg-muted/80 transition-colors text-sm font-medium cursor-pointer"
                    >
                        Contact Support
                    </a>
                </div>
            </div>
        </aside>
    );
}

// Helper function to highlight search matches
function highlightText(text: string, query: string): React.ReactNode {
    if (!query.trim()) return text;

    const parts = text.split(new RegExp(`(${query})`, 'gi'));
    return parts.map((part, i) =>
        part.toLowerCase() === query.toLowerCase()
            ? <mark key={i} className="bg-yellow-200 dark:bg-yellow-800 text-foreground rounded px-0.5">{part}</mark>
            : part
    );
}
