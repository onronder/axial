"use client";

/**
 * Help Modal Component - Production Grade
 *
 * Full-screen modal with:
 * - Collapsible sidebar navigation with category grouping
 * - Real-time search with highlighting
 * - Keyboard navigation (Escape, Arrow keys, Enter)
 * - Reading progress indicator
 * - Related articles
 * - Article feedback
 * - Responsive design
 */

import { useEffect, useMemo, useState, useRef, useCallback } from 'react';
import {
    X,
    Search,
    BookOpen,
    Zap,
    Users,
    CreditCard,
    HelpCircle,
    ChevronDown,
    ChevronRight,
    Clock,
    ArrowUp,
    Plug,
    AlertTriangle,
    ExternalLink,
    Keyboard
} from 'lucide-react';
import ReactMarkdown from 'react-markdown';
import remarkGfm from 'remark-gfm';
import { useHelpStore } from '@/store/useHelpStore';
import { HELP_ARTICLES, getCategories, type HelpArticle } from '@/data/helpArticles';
import { Dialog, DialogContent, DialogTitle, DialogDescription } from '@/components/ui/dialog';
import { Input } from '@/components/ui/input';
import { Button } from '@/components/ui/button';
import { ScrollArea } from '@/components/ui/scroll-area';
import { Badge } from '@/components/ui/badge';
import { cn } from '@/lib/utils';

// Category configuration with icons and colors
const categoryConfig: Record<string, { icon: React.ReactNode; color: string; bgColor: string }> = {
    'General': {
        icon: <BookOpen className="h-4 w-4" />,
        color: 'text-blue-600 dark:text-blue-400',
        bgColor: 'bg-blue-500/10'
    },
    'AI Features': {
        icon: <Zap className="h-4 w-4" />,
        color: 'text-purple-600 dark:text-purple-400',
        bgColor: 'bg-purple-500/10'
    },
    'Connectors': {
        icon: <Plug className="h-4 w-4" />,
        color: 'text-green-600 dark:text-green-400',
        bgColor: 'bg-green-500/10'
    },
    'Teams': {
        icon: <Users className="h-4 w-4" />,
        color: 'text-orange-600 dark:text-orange-400',
        bgColor: 'bg-orange-500/10'
    },
    'Billing': {
        icon: <CreditCard className="h-4 w-4" />,
        color: 'text-emerald-600 dark:text-emerald-400',
        bgColor: 'bg-emerald-500/10'
    },
    'Troubleshooting': {
        icon: <AlertTriangle className="h-4 w-4" />,
        color: 'text-red-600 dark:text-red-400',
        bgColor: 'bg-red-500/10'
    },
};

// Calculate reading time
function getReadingTime(content: string): number {
    const wordsPerMinute = 200;
    const wordCount = content.split(/\s+/).length;
    return Math.max(1, Math.ceil(wordCount / wordsPerMinute));
}

// Highlight search matches in text
function highlightMatches(text: string, query: string): React.ReactNode {
    if (!query.trim()) return text;

    const parts = text.split(new RegExp(`(${query})`, 'gi'));
    return parts.map((part, i) =>
        part.toLowerCase() === query.toLowerCase()
            ? <mark key={i} className="bg-yellow-200 dark:bg-yellow-800 text-foreground rounded px-0.5">{part}</mark>
            : part
    );
}

export function HelpModal() {
    const {
        isOpen,
        searchQuery,
        selectedArticle,
        selectedCategory,
        closeHelp,
        setSearchQuery,
        setSelectedArticle,
        setSelectedCategory,
    } = useHelpStore();

    // Local state
    const [expandedCategories, setExpandedCategories] = useState<Set<string>>(new Set(['General']));
    const [readingProgress, setReadingProgress] = useState(0);
    const [showBackToTop, setShowBackToTop] = useState(false);
    const [focusedIndex, setFocusedIndex] = useState(-1);
    const [showKeyboardHints, setShowKeyboardHints] = useState(false);

    // Refs
    const contentRef = useRef<HTMLDivElement>(null);
    const searchInputRef = useRef<HTMLInputElement>(null);
    const articleListRef = useRef<HTMLDivElement>(null);

    // Filter articles based on search and category
    const filteredArticles = useMemo(() => {
        let articles = HELP_ARTICLES;

        // Filter by category
        if (selectedCategory !== 'All') {
            articles = articles.filter(a => a.category === selectedCategory);
        }

        // Filter by search
        if (searchQuery.trim()) {
            const query = searchQuery.toLowerCase();
            articles = articles.filter(
                a => a.title.toLowerCase().includes(query) ||
                    a.content.toLowerCase().includes(query) ||
                    a.keywords?.some(k => k.toLowerCase().includes(query))
            );
        }

        return articles;
    }, [selectedCategory, searchQuery]);

    // Group articles by category
    const groupedArticles = useMemo(() => {
        const groups: Record<string, HelpArticle[]> = {};
        filteredArticles.forEach(article => {
            if (!groups[article.category]) {
                groups[article.category] = [];
            }
            groups[article.category].push(article);
        });
        return groups;
    }, [filteredArticles]);

    const categories = ['All', ...getCategories()] as const;

    // Toggle category expansion
    const toggleCategory = useCallback((category: string) => {
        setExpandedCategories(prev => {
            const next = new Set(prev);
            if (next.has(category)) {
                next.delete(category);
            } else {
                next.add(category);
            }
            return next;
        });
    }, []);

    // Handle scroll for reading progress and back-to-top
    const handleContentScroll = useCallback((e: React.UIEvent<HTMLDivElement>) => {
        const target = e.target as HTMLDivElement;
        const scrollTop = target.scrollTop;
        const scrollHeight = target.scrollHeight - target.clientHeight;

        if (scrollHeight > 0) {
            const progress = Math.min(100, (scrollTop / scrollHeight) * 100);
            setReadingProgress(progress);
            setShowBackToTop(scrollTop > 300);
        }
    }, []);

    // Scroll to top
    const scrollToTop = useCallback(() => {
        contentRef.current?.scrollTo({ top: 0, behavior: 'smooth' });
    }, []);

    // Auto-select first article when filter changes
    useEffect(() => {
        if (filteredArticles.length > 0 && !selectedArticle) {
            setSelectedArticle(filteredArticles[0]);
        }
    }, [filteredArticles, selectedArticle, setSelectedArticle]);

    // Expand category when article is selected
    useEffect(() => {
        if (selectedArticle) {
            setExpandedCategories(prev => new Set([...prev, selectedArticle.category]));
        }
    }, [selectedArticle]);

    // Reset reading progress when article changes
    useEffect(() => {
        setReadingProgress(0);
        setShowBackToTop(false);
        contentRef.current?.scrollTo({ top: 0 });
    }, [selectedArticle]);

    // Keyboard navigation
    useEffect(() => {
        if (!isOpen) return;

        const handleKeyDown = (e: KeyboardEvent) => {
            // Escape to close
            if (e.key === 'Escape') {
                closeHelp();
                return;
            }

            // Cmd/Ctrl + K to focus search
            if ((e.metaKey || e.ctrlKey) && e.key === 'k') {
                e.preventDefault();
                searchInputRef.current?.focus();
                return;
            }

            // Arrow keys for navigation when search is focused
            if (document.activeElement === searchInputRef.current && filteredArticles.length > 0) {
                if (e.key === 'ArrowDown') {
                    e.preventDefault();
                    setFocusedIndex(prev => Math.min(prev + 1, filteredArticles.length - 1));
                } else if (e.key === 'ArrowUp') {
                    e.preventDefault();
                    setFocusedIndex(prev => Math.max(prev - 1, 0));
                } else if (e.key === 'Enter' && focusedIndex >= 0) {
                    e.preventDefault();
                    setSelectedArticle(filteredArticles[focusedIndex]);
                    setFocusedIndex(-1);
                }
            }

            // ? to show keyboard hints
            if (e.key === '?' && !e.shiftKey && document.activeElement?.tagName !== 'INPUT') {
                setShowKeyboardHints(prev => !prev);
            }
        };

        window.addEventListener('keydown', handleKeyDown);
        return () => window.removeEventListener('keydown', handleKeyDown);
    }, [isOpen, closeHelp, filteredArticles, focusedIndex, setSelectedArticle]);

    // Reset focused index when search changes
    useEffect(() => {
        setFocusedIndex(-1);
    }, [searchQuery]);

    // Get related articles
    const relatedArticles = useMemo(() => {
        if (!selectedArticle) return [];
        return HELP_ARTICLES
            .filter(a =>
                a.id !== selectedArticle.id &&
                (a.category === selectedArticle.category ||
                 a.keywords?.some(k => selectedArticle.keywords?.includes(k)))
            )
            .slice(0, 3);
    }, [selectedArticle]);

    return (
        <Dialog open={isOpen} onOpenChange={(open) => !open && closeHelp()}>
            <DialogContent className="max-w-6xl h-[90vh] p-0 gap-0 overflow-hidden border-border/50 shadow-2xl">
                <DialogTitle className="sr-only">Help Center</DialogTitle>
                <DialogDescription className="sr-only">
                    Browse help articles and documentation for Axio Hub.
                </DialogDescription>

                {/* Reading Progress Bar */}
                {selectedArticle && (
                    <div className="absolute top-0 left-0 right-0 h-1 bg-muted z-50">
                        <div
                            className="h-full bg-primary transition-all duration-150 ease-out"
                            style={{ width: `${readingProgress}%` }}
                        />
                    </div>
                )}

                <div className="flex h-full min-h-0">
                    {/* Sidebar */}
                    <div className="w-80 border-r border-border bg-muted/30 flex flex-col min-h-0">
                        {/* Header */}
                        <div className="p-4 border-b border-border">
                            <div className="flex items-center justify-between mb-4">
                                <div className="flex items-center gap-3">
                                    <div className="flex h-10 w-10 items-center justify-center rounded-xl bg-primary/10">
                                        <BookOpen className="h-5 w-5 text-primary" />
                                    </div>
                                    <div>
                                        <h2 className="font-semibold text-lg">Help Center</h2>
                                        <p className="text-xs text-muted-foreground">
                                            {HELP_ARTICLES.length} articles
                                        </p>
                                    </div>
                                </div>
                                <Button
                                    variant="ghost"
                                    size="icon"
                                    onClick={() => setShowKeyboardHints(prev => !prev)}
                                    className="h-8 w-8 text-muted-foreground hover:text-foreground"
                                >
                                    <Keyboard className="h-4 w-4" />
                                </Button>
                            </div>

                            {/* Search */}
                            <div className="relative">
                                <Search className="absolute left-3 top-1/2 -translate-y-1/2 h-4 w-4 text-muted-foreground" />
                                <Input
                                    ref={searchInputRef}
                                    placeholder="Search articles... (⌘K)"
                                    value={searchQuery}
                                    onChange={(e) => setSearchQuery(e.target.value)}
                                    className="pl-10 pr-4 h-10 bg-background/50"
                                />
                                {searchQuery && (
                                    <button
                                        onClick={() => setSearchQuery('')}
                                        className="absolute right-3 top-1/2 -translate-y-1/2 text-muted-foreground hover:text-foreground transition-colors"
                                    >
                                        <X className="h-4 w-4" />
                                    </button>
                                )}
                            </div>

                            {/* Keyboard Hints */}
                            {showKeyboardHints && (
                                <div className="mt-3 p-3 rounded-lg bg-background/50 border border-border/50 text-xs space-y-1.5">
                                    <div className="flex justify-between">
                                        <span className="text-muted-foreground">Search</span>
                                        <kbd className="px-1.5 py-0.5 rounded bg-muted text-muted-foreground">⌘K</kbd>
                                    </div>
                                    <div className="flex justify-between">
                                        <span className="text-muted-foreground">Navigate</span>
                                        <kbd className="px-1.5 py-0.5 rounded bg-muted text-muted-foreground">↑↓</kbd>
                                    </div>
                                    <div className="flex justify-between">
                                        <span className="text-muted-foreground">Select</span>
                                        <kbd className="px-1.5 py-0.5 rounded bg-muted text-muted-foreground">Enter</kbd>
                                    </div>
                                    <div className="flex justify-between">
                                        <span className="text-muted-foreground">Close</span>
                                        <kbd className="px-1.5 py-0.5 rounded bg-muted text-muted-foreground">Esc</kbd>
                                    </div>
                                </div>
                            )}
                        </div>

                        {/* Category Filters */}
                        <div className="px-3 py-2 border-b border-border/50 flex flex-wrap gap-1.5">
                            {categories.map((category) => {
                                const config = category !== 'All' ? categoryConfig[category] : null;
                                const count = category === 'All'
                                    ? HELP_ARTICLES.length
                                    : HELP_ARTICLES.filter(a => a.category === category).length;

                                return (
                                    <button
                                        key={category}
                                        onClick={() => {
                                            setSelectedCategory(category as HelpArticle['category'] | 'All');
                                            setSelectedArticle(null);
                                        }}
                                        className={cn(
                                            "inline-flex items-center gap-1.5 px-2.5 py-1 rounded-full text-xs font-medium transition-all cursor-pointer",
                                            selectedCategory === category
                                                ? "bg-primary text-primary-foreground"
                                                : "bg-muted hover:bg-muted/80 text-muted-foreground hover:text-foreground"
                                        )}
                                    >
                                        {config?.icon}
                                        {category === 'All' ? 'All' : category.split(' ')[0]}
                                        <span className={cn(
                                            "text-[10px] px-1.5 rounded-full",
                                            selectedCategory === category
                                                ? "bg-primary-foreground/20"
                                                : "bg-background/50"
                                        )}>
                                            {count}
                                        </span>
                                    </button>
                                );
                            })}
                        </div>

                        {/* Article List */}
                        <ScrollArea className="flex-1">
                            <div ref={articleListRef} className="p-3 space-y-3">
                                {searchQuery.trim() ? (
                                    // Flat list when searching
                                    <div className="space-y-1">
                                        <p className="px-2 text-xs text-muted-foreground mb-2">
                                            {filteredArticles.length} result{filteredArticles.length !== 1 ? 's' : ''} for "{searchQuery}"
                                        </p>
                                        {filteredArticles.map((article, index) => {
                                            const config = categoryConfig[article.category];
                                            return (
                                                <button
                                                    key={article.id}
                                                    onClick={() => setSelectedArticle(article)}
                                                    className={cn(
                                                        "w-full text-left p-3 rounded-lg transition-all cursor-pointer",
                                                        selectedArticle?.id === article.id
                                                            ? "bg-primary/10 border border-primary/20"
                                                            : focusedIndex === index
                                                            ? "bg-accent border border-accent"
                                                            : "hover:bg-accent/50 border border-transparent"
                                                    )}
                                                >
                                                    <div className="flex items-start gap-2">
                                                        <div className={cn("mt-0.5 p-1 rounded", config?.bgColor)}>
                                                            <span className={config?.color}>
                                                                {config?.icon}
                                                            </span>
                                                        </div>
                                                        <div className="flex-1 min-w-0">
                                                            <p className="text-sm font-medium truncate">
                                                                {highlightMatches(article.title, searchQuery)}
                                                            </p>
                                                            <div className="flex items-center gap-2 mt-1">
                                                                <span className="text-xs text-muted-foreground">
                                                                    {article.category}
                                                                </span>
                                                                <span className="text-muted-foreground/50">•</span>
                                                                <span className="text-xs text-muted-foreground flex items-center gap-1">
                                                                    <Clock className="h-3 w-3" />
                                                                    {getReadingTime(article.content)} min
                                                                </span>
                                                            </div>
                                                        </div>
                                                    </div>
                                                </button>
                                            );
                                        })}
                                    </div>
                                ) : (
                                    // Grouped by category
                                    Object.entries(groupedArticles).map(([category, articles]) => {
                                        const config = categoryConfig[category];
                                        const isExpanded = expandedCategories.has(category);

                                        return (
                                            <div key={category} className="rounded-lg border border-border/50 overflow-hidden">
                                                <button
                                                    onClick={() => toggleCategory(category)}
                                                    className="w-full flex items-center justify-between p-3 hover:bg-accent/50 transition-colors cursor-pointer"
                                                >
                                                    <div className="flex items-center gap-2">
                                                        <div className={cn("p-1.5 rounded-lg", config?.bgColor)}>
                                                            <span className={config?.color}>
                                                                {config?.icon}
                                                            </span>
                                                        </div>
                                                        <span className="font-medium text-sm">{category}</span>
                                                        <Badge variant="secondary" className="text-xs">
                                                            {articles.length}
                                                        </Badge>
                                                    </div>
                                                    {isExpanded ? (
                                                        <ChevronDown className="h-4 w-4 text-muted-foreground" />
                                                    ) : (
                                                        <ChevronRight className="h-4 w-4 text-muted-foreground" />
                                                    )}
                                                </button>

                                                {isExpanded && (
                                                    <div className="border-t border-border/50 bg-background/30">
                                                        {articles.map((article) => (
                                                            <button
                                                                key={article.id}
                                                                onClick={() => setSelectedArticle(article)}
                                                                className={cn(
                                                                    "w-full text-left px-3 py-2.5 transition-all cursor-pointer flex items-center gap-2 border-l-2",
                                                                    selectedArticle?.id === article.id
                                                                        ? "bg-primary/5 border-l-primary"
                                                                        : "border-l-transparent hover:bg-accent/30 hover:border-l-muted-foreground/30"
                                                                )}
                                                            >
                                                                <ChevronRight className={cn(
                                                                    "h-3 w-3 transition-colors",
                                                                    selectedArticle?.id === article.id
                                                                        ? "text-primary"
                                                                        : "text-muted-foreground/50"
                                                                )} />
                                                                <span className={cn(
                                                                    "text-sm truncate flex-1",
                                                                    selectedArticle?.id === article.id
                                                                        ? "text-primary font-medium"
                                                                        : "text-muted-foreground"
                                                                )}>
                                                                    {article.title}
                                                                </span>
                                                                <span className="text-xs text-muted-foreground/50 flex items-center gap-1">
                                                                    <Clock className="h-3 w-3" />
                                                                    {getReadingTime(article.content)}m
                                                                </span>
                                                            </button>
                                                        ))}
                                                    </div>
                                                )}
                                            </div>
                                        );
                                    })
                                )}

                                {filteredArticles.length === 0 && (
                                    <div className="text-center py-8">
                                        <div className="inline-flex items-center justify-center w-12 h-12 rounded-full bg-muted mb-3">
                                            <Search className="h-5 w-5 text-muted-foreground" />
                                        </div>
                                        <p className="text-sm font-medium text-muted-foreground">No articles found</p>
                                        <p className="text-xs text-muted-foreground/80 mt-1">
                                            Try different keywords or browse categories
                                        </p>
                                        <Button
                                            variant="ghost"
                                            size="sm"
                                            onClick={() => {
                                                setSearchQuery('');
                                                setSelectedCategory('All');
                                            }}
                                            className="mt-3"
                                        >
                                            Clear filters
                                        </Button>
                                    </div>
                                )}
                            </div>
                        </ScrollArea>

                        {/* Footer */}
                        <div className="p-3 border-t border-border bg-background/50">
                            <a
                                href="mailto:support@axiohub.io"
                                className="flex items-center justify-center gap-2 px-4 py-2.5 rounded-lg bg-muted hover:bg-muted/80 transition-colors text-sm font-medium cursor-pointer"
                            >
                                <HelpCircle className="h-4 w-4" />
                                Contact Support
                                <ExternalLink className="h-3 w-3 text-muted-foreground" />
                            </a>
                        </div>
                    </div>

                    {/* Content Area */}
                    <div className="flex-1 flex flex-col min-w-0 min-h-0 bg-background">
                        {/* Header with close button */}
                        <div className="flex items-center justify-between px-6 py-3 border-b border-border/50">
                            {selectedArticle && (
                                <nav className="flex items-center gap-2 text-sm">
                                    <button
                                        onClick={() => setSelectedCategory('All')}
                                        className="text-muted-foreground hover:text-foreground transition-colors cursor-pointer"
                                    >
                                        Help Center
                                    </button>
                                    <ChevronRight className="h-4 w-4 text-muted-foreground/50" />
                                    <button
                                        onClick={() => setSelectedCategory(selectedArticle.category)}
                                        className="text-muted-foreground hover:text-foreground transition-colors cursor-pointer"
                                    >
                                        {selectedArticle.category}
                                    </button>
                                    <ChevronRight className="h-4 w-4 text-muted-foreground/50" />
                                    <span className="text-foreground font-medium truncate max-w-[200px]">
                                        {selectedArticle.title}
                                    </span>
                                </nav>
                            )}
                        </div>

                        {/* Article Content */}
                        <div
                            ref={contentRef}
                            onScroll={handleContentScroll}
                            className="flex-1 overflow-y-auto scroll-smooth"
                        >
                            {selectedArticle ? (
                                <article className="max-w-3xl mx-auto px-8 py-8">
                                    {/* Article Header */}
                                    <header className="mb-8 pb-6 border-b border-border/50">
                                        <div className="flex items-center gap-3 mb-4">
                                            <div className={cn(
                                                "inline-flex items-center gap-2 px-3 py-1.5 rounded-full text-xs font-medium",
                                                categoryConfig[selectedArticle.category]?.bgColor,
                                                categoryConfig[selectedArticle.category]?.color
                                            )}>
                                                {categoryConfig[selectedArticle.category]?.icon}
                                                {selectedArticle.category}
                                            </div>
                                            <div className="flex items-center gap-1.5 text-xs text-muted-foreground">
                                                <Clock className="h-3.5 w-3.5" />
                                                {getReadingTime(selectedArticle.content)} min read
                                            </div>
                                        </div>
                                        <h1 className="text-3xl font-bold tracking-tight">
                                            {selectedArticle.title}
                                        </h1>
                                    </header>

                                    {/* Markdown Content */}
                                    <div className="prose prose-slate max-w-none dark:prose-invert
                                        prose-headings:font-semibold prose-headings:tracking-tight
                                        prose-h2:text-xl prose-h2:mt-8 prose-h2:mb-4 prose-h2:pb-2 prose-h2:border-b prose-h2:border-border/30
                                        prose-h3:text-lg prose-h3:mt-6 prose-h3:mb-3
                                        prose-p:text-muted-foreground prose-p:leading-7
                                        prose-li:text-muted-foreground prose-li:leading-7
                                        prose-strong:text-foreground prose-strong:font-semibold
                                        prose-code:text-primary prose-code:bg-primary/10 prose-code:px-1.5 prose-code:py-0.5 prose-code:rounded prose-code:text-sm prose-code:before:content-[''] prose-code:after:content-['']
                                        prose-pre:bg-muted prose-pre:border prose-pre:border-border/50 prose-pre:rounded-lg
                                        prose-table:text-sm prose-th:text-left prose-th:px-4 prose-th:py-3 prose-th:bg-muted prose-th:font-semibold prose-td:px-4 prose-td:py-3 prose-td:border-b prose-td:border-border/30
                                        prose-blockquote:border-l-primary prose-blockquote:bg-primary/5 prose-blockquote:py-1 prose-blockquote:px-6 prose-blockquote:rounded-r-lg prose-blockquote:not-italic
                                        prose-a:text-primary prose-a:no-underline hover:prose-a:underline
                                        prose-img:rounded-lg prose-img:border prose-img:border-border/50"
                                    >
                                        <ReactMarkdown remarkPlugins={[remarkGfm]}>
                                            {selectedArticle.content}
                                        </ReactMarkdown>
                                    </div>

                                    {/* Article Feedback */}
                                    <div className="mt-12 pt-8 border-t border-border/50">
                                        <ArticleFeedback articleId={selectedArticle.id} />
                                    </div>

                                    {/* Related Articles */}
                                    {relatedArticles.length > 0 && (
                                        <div className="mt-8 pt-8 border-t border-border/50">
                                            <h3 className="text-lg font-semibold mb-4">Related Articles</h3>
                                            <div className="grid gap-3">
                                                {relatedArticles.map((article) => {
                                                    const config = categoryConfig[article.category];
                                                    return (
                                                        <button
                                                            key={article.id}
                                                            onClick={() => setSelectedArticle(article)}
                                                            className="flex items-center gap-3 p-4 rounded-lg border border-border/50 hover:border-border hover:bg-accent/30 transition-all text-left cursor-pointer"
                                                        >
                                                            <div className={cn("p-2 rounded-lg", config?.bgColor)}>
                                                                <span className={config?.color}>
                                                                    {config?.icon}
                                                                </span>
                                                            </div>
                                                            <div className="flex-1 min-w-0">
                                                                <p className="font-medium truncate">{article.title}</p>
                                                                <p className="text-xs text-muted-foreground mt-0.5">
                                                                    {article.category} • {getReadingTime(article.content)} min read
                                                                </p>
                                                            </div>
                                                            <ChevronRight className="h-4 w-4 text-muted-foreground shrink-0" />
                                                        </button>
                                                    );
                                                })}
                                            </div>
                                        </div>
                                    )}
                                </article>
                            ) : (
                                <div className="flex flex-col items-center justify-center h-full text-center px-8">
                                    <div className="w-20 h-20 rounded-2xl bg-muted/50 flex items-center justify-center mb-6">
                                        <BookOpen className="h-10 w-10 text-muted-foreground/50" />
                                    </div>
                                    <h3 className="text-xl font-semibold text-foreground mb-2">
                                        Welcome to Help Center
                                    </h3>
                                    <p className="text-muted-foreground max-w-md mb-6">
                                        Browse articles by category or search for specific topics.
                                        Use keyboard shortcuts for faster navigation.
                                    </p>
                                    <div className="flex flex-wrap gap-2 justify-center">
                                        {Object.entries(categoryConfig).slice(0, 4).map(([category, config]) => (
                                            <button
                                                key={category}
                                                onClick={() => {
                                                    setSelectedCategory(category as HelpArticle['category']);
                                                    setExpandedCategories(new Set([category]));
                                                }}
                                                className={cn(
                                                    "inline-flex items-center gap-2 px-4 py-2 rounded-lg border border-border/50 hover:border-border transition-all cursor-pointer",
                                                    config.bgColor
                                                )}
                                            >
                                                <span className={config.color}>{config.icon}</span>
                                                <span className="text-sm font-medium">{category}</span>
                                            </button>
                                        ))}
                                    </div>
                                </div>
                            )}
                        </div>

                        {/* Back to Top Button */}
                        {showBackToTop && (
                            <button
                                onClick={scrollToTop}
                                className="absolute bottom-6 right-6 p-3 rounded-full bg-primary text-primary-foreground shadow-lg hover:bg-primary/90 transition-all cursor-pointer animate-in fade-in slide-in-from-bottom-4"
                            >
                                <ArrowUp className="h-5 w-5" />
                            </button>
                        )}
                    </div>
                </div>
            </DialogContent>
        </Dialog>
    );
}

// Article Feedback Component
function ArticleFeedback({ articleId }: { articleId: string }) {
    const [feedback, setFeedback] = useState<'helpful' | 'not-helpful' | null>(null);
    const [showThankYou, setShowThankYou] = useState(false);

    const handleFeedback = (type: 'helpful' | 'not-helpful') => {
        setFeedback(type);
        setShowThankYou(true);
        // In production, send this to analytics
        console.log(`Article ${articleId} feedback: ${type}`);
    };

    if (showThankYou) {
        return (
            <div className="text-center py-4">
                <p className="text-sm text-muted-foreground">
                    Thank you for your feedback!
                </p>
            </div>
        );
    }

    return (
        <div className="flex flex-col items-center gap-3">
            <p className="text-sm text-muted-foreground">Was this article helpful?</p>
            <div className="flex gap-2">
                <Button
                    variant={feedback === 'helpful' ? 'default' : 'outline'}
                    size="sm"
                    onClick={() => handleFeedback('helpful')}
                    className="cursor-pointer"
                >
                    Yes, it helped
                </Button>
                <Button
                    variant={feedback === 'not-helpful' ? 'default' : 'outline'}
                    size="sm"
                    onClick={() => handleFeedback('not-helpful')}
                    className="cursor-pointer"
                >
                    No, I need more help
                </Button>
            </div>
        </div>
    );
}
