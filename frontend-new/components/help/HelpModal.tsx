"use client";

/**
 * Help Modal Component - Premium Redesign
 * 
 * Design System:
 * - Glassmorphism with subtle backdrop blur
 * - Premium gradients and shadows
 * - Refined typography with proper hierarchy
 * - Sophisticated color palette
 * - Smooth micro-interactions
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
    Keyboard,
    Sparkles
} from 'lucide-react';
import ReactMarkdown from 'react-markdown';
import remarkGfm from 'remark-gfm';
import { useHelpStore } from '@/store/useHelpStore';
import { HELP_ARTICLES, getCategories, type HelpArticle } from '@/data/helpArticles';
import { Dialog, DialogContent, DialogTitle, DialogDescription } from '@/components/ui/dialog';
import { Input } from '@/components/ui/input';
import { Button } from '@/components/ui/button';
import { ScrollArea } from '@/components/ui/scroll-area';
import { cn } from '@/lib/utils';

// Premium category configuration with gradients
const categoryConfig: Record<string, {
    icon: React.ReactNode;
    gradient: string;
    iconBg: string;
    activeRing: string;
    textColor: string;
}> = {
    'General': {
        icon: <BookOpen className="h-4 w-4" />,
        gradient: 'from-sky-500 to-blue-600',
        iconBg: 'bg-gradient-to-br from-sky-500/20 to-blue-600/20',
        activeRing: 'ring-sky-500/30',
        textColor: 'text-sky-400'
    },
    'AI Features': {
        icon: <Sparkles className="h-4 w-4" />,
        gradient: 'from-violet-500 to-purple-600',
        iconBg: 'bg-gradient-to-br from-violet-500/20 to-purple-600/20',
        activeRing: 'ring-violet-500/30',
        textColor: 'text-violet-400'
    },
    'Connectors': {
        icon: <Plug className="h-4 w-4" />,
        gradient: 'from-emerald-500 to-teal-600',
        iconBg: 'bg-gradient-to-br from-emerald-500/20 to-teal-600/20',
        activeRing: 'ring-emerald-500/30',
        textColor: 'text-emerald-400'
    },
    'Teams': {
        icon: <Users className="h-4 w-4" />,
        gradient: 'from-amber-500 to-orange-600',
        iconBg: 'bg-gradient-to-br from-amber-500/20 to-orange-600/20',
        activeRing: 'ring-amber-500/30',
        textColor: 'text-amber-400'
    },
    'Billing': {
        icon: <CreditCard className="h-4 w-4" />,
        gradient: 'from-cyan-500 to-blue-600',
        iconBg: 'bg-gradient-to-br from-cyan-500/20 to-blue-600/20',
        activeRing: 'ring-cyan-500/30',
        textColor: 'text-cyan-400'
    },
    'Troubleshooting': {
        icon: <AlertTriangle className="h-4 w-4" />,
        gradient: 'from-rose-500 to-red-600',
        iconBg: 'bg-gradient-to-br from-rose-500/20 to-red-600/20',
        activeRing: 'ring-rose-500/30',
        textColor: 'text-rose-400'
    },
};

function getReadingTime(content: string): number {
    const wordsPerMinute = 200;
    const wordCount = content.split(/\s+/).length;
    return Math.max(1, Math.ceil(wordCount / wordsPerMinute));
}

function highlightMatches(text: string, query: string): React.ReactNode {
    if (!query.trim()) return text;
    const parts = text.split(new RegExp(`(${query})`, 'gi'));
    return parts.map((part, i) =>
        part.toLowerCase() === query.toLowerCase()
            ? <mark key={i} className="bg-amber-400/30 text-amber-200 rounded px-0.5">{part}</mark>
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

    const [expandedCategories, setExpandedCategories] = useState<Set<string>>(new Set(['General']));
    const [readingProgress, setReadingProgress] = useState(0);
    const [showBackToTop, setShowBackToTop] = useState(false);
    const [focusedIndex, setFocusedIndex] = useState(-1);
    const [showKeyboardHints, setShowKeyboardHints] = useState(false);

    const contentRef = useRef<HTMLDivElement>(null);
    const searchInputRef = useRef<HTMLInputElement>(null);

    const filteredArticles = useMemo(() => {
        let articles = HELP_ARTICLES;
        if (selectedCategory !== 'All') {
            articles = articles.filter(a => a.category === selectedCategory);
        }
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

    const scrollToTop = useCallback(() => {
        contentRef.current?.scrollTo({ top: 0, behavior: 'smooth' });
    }, []);

    useEffect(() => {
        if (filteredArticles.length > 0 && !selectedArticle) {
            setSelectedArticle(filteredArticles[0]);
        }
    }, [filteredArticles, selectedArticle, setSelectedArticle]);

    useEffect(() => {
        if (selectedArticle) {
            setExpandedCategories(prev => new Set([...prev, selectedArticle.category]));
        }
    }, [selectedArticle]);

    useEffect(() => {
        setReadingProgress(0);
        setShowBackToTop(false);
        contentRef.current?.scrollTo({ top: 0 });
    }, [selectedArticle]);

    useEffect(() => {
        if (!isOpen) return;
        const handleKeyDown = (e: KeyboardEvent) => {
            if (e.key === 'Escape') { closeHelp(); return; }
            if ((e.metaKey || e.ctrlKey) && e.key === 'k') {
                e.preventDefault();
                searchInputRef.current?.focus();
                return;
            }
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
            if (e.key === '?' && !e.shiftKey && document.activeElement?.tagName !== 'INPUT') {
                setShowKeyboardHints(prev => !prev);
            }
        };
        window.addEventListener('keydown', handleKeyDown);
        return () => window.removeEventListener('keydown', handleKeyDown);
    }, [isOpen, closeHelp, filteredArticles, focusedIndex, setSelectedArticle]);

    useEffect(() => { setFocusedIndex(-1); }, [searchQuery]);

    const relatedArticles = useMemo(() => {
        if (!selectedArticle) return [];
        return HELP_ARTICLES
            .filter(a => a.id !== selectedArticle.id &&
                (a.category === selectedArticle.category ||
                 a.keywords?.some(k => selectedArticle.keywords?.includes(k))))
            .slice(0, 3);
    }, [selectedArticle]);

    return (
        <Dialog open={isOpen} onOpenChange={(open) => !open && closeHelp()}>
            <DialogContent className="max-w-6xl h-[90vh] p-0 gap-0 overflow-hidden bg-[#0a0a0f]/95 backdrop-blur-2xl border-white/[0.08] shadow-[0_0_80px_rgba(0,0,0,0.8)]">
                <DialogTitle className="sr-only">Help Center</DialogTitle>
                <DialogDescription className="sr-only">Browse help articles and documentation.</DialogDescription>

                {/* Premium Reading Progress Bar */}
                {selectedArticle && (
                    <div className="absolute top-0 left-0 right-0 h-[2px] bg-white/[0.03] z-50">
                        <div
                            className="h-full bg-gradient-to-r from-violet-500 via-purple-500 to-fuchsia-500 transition-all duration-150 ease-out shadow-[0_0_20px_rgba(139,92,246,0.5)]"
                            style={{ width: `${readingProgress}%` }}
                        />
                    </div>
                )}

                <div className="flex h-full min-h-0">
                    {/* Premium Sidebar */}
                    <div className="w-80 border-r border-white/[0.06] bg-gradient-to-b from-white/[0.02] to-transparent flex flex-col min-h-0">
                        {/* Header with Glass Effect */}
                        <div className="p-5 border-b border-white/[0.06]">
                            <div className="flex items-center justify-between mb-5">
                                <div className="flex items-center gap-3">
                                    <div className="relative">
                                        <div className="absolute inset-0 bg-gradient-to-br from-violet-500 to-purple-600 rounded-xl blur-lg opacity-40" />
                                        <div className="relative flex h-11 w-11 items-center justify-center rounded-xl bg-gradient-to-br from-violet-500/20 to-purple-600/20 border border-violet-500/20">
                                            <BookOpen className="h-5 w-5 text-violet-400" />
                                        </div>
                                    </div>
                                    <div>
                                        <h2 className="font-semibold text-lg text-white tracking-tight">Help Center</h2>
                                        <p className="text-xs text-white/40 font-medium">
                                            {HELP_ARTICLES.length} articles
                                        </p>
                                    </div>
                                </div>
                                <button
                                    onClick={() => setShowKeyboardHints(prev => !prev)}
                                    className="h-9 w-9 flex items-center justify-center rounded-lg bg-white/[0.03] hover:bg-white/[0.06] border border-white/[0.06] text-white/40 hover:text-white/60 transition-all cursor-pointer"
                                >
                                    <Keyboard className="h-4 w-4" />
                                </button>
                            </div>

                            {/* Premium Search Input */}
                            <div className="relative group">
                                <div className="absolute inset-0 bg-gradient-to-r from-violet-500/20 to-purple-500/20 rounded-xl blur-xl opacity-0 group-focus-within:opacity-100 transition-opacity" />
                                <div className="relative">
                                    <Search className="absolute left-3.5 top-1/2 -translate-y-1/2 h-4 w-4 text-white/30" />
                                    <Input
                                        ref={searchInputRef}
                                        placeholder="Search articles..."
                                        value={searchQuery}
                                        onChange={(e) => setSearchQuery(e.target.value)}
                                        className="pl-10 pr-12 h-11 bg-white/[0.03] border-white/[0.08] text-white placeholder:text-white/30 focus:border-violet-500/50 focus:ring-violet-500/20 rounded-xl"
                                    />
                                    <kbd className="absolute right-3 top-1/2 -translate-y-1/2 text-[10px] text-white/20 font-mono bg-white/[0.05] px-1.5 py-0.5 rounded border border-white/[0.08]">
                                        ⌘K
                                    </kbd>
                                </div>
                            </div>

                            {/* Keyboard Hints Panel */}
                            {showKeyboardHints && (
                                <div className="mt-4 p-4 rounded-xl bg-white/[0.02] border border-white/[0.06] space-y-2">
                                    {[
                                        ['Search', '⌘K'],
                                        ['Navigate', '↑↓'],
                                        ['Select', '↵'],
                                        ['Close', 'Esc']
                                    ].map(([action, key]) => (
                                        <div key={action} className="flex justify-between text-xs">
                                            <span className="text-white/40">{action}</span>
                                            <kbd className="px-1.5 py-0.5 rounded bg-white/[0.05] text-white/50 font-mono border border-white/[0.08]">{key}</kbd>
                                        </div>
                                    ))}
                                </div>
                            )}
                        </div>

                        {/* Premium Category Pills */}
                        <div className="px-4 py-3 border-b border-white/[0.06] flex flex-wrap gap-2">
                            {categories.map((category) => {
                                const config = category !== 'All' ? categoryConfig[category] : null;
                                const count = category === 'All'
                                    ? HELP_ARTICLES.length
                                    : HELP_ARTICLES.filter(a => a.category === category).length;
                                const isActive = selectedCategory === category;

                                return (
                                    <button
                                        key={category}
                                        onClick={() => {
                                            setSelectedCategory(category as HelpArticle['category'] | 'All');
                                            setSelectedArticle(null);
                                        }}
                                        className={cn(
                                            "inline-flex items-center gap-1.5 px-3 py-1.5 rounded-lg text-xs font-medium transition-all cursor-pointer",
                                            isActive
                                                ? "bg-gradient-to-r from-violet-500/20 to-purple-500/20 text-violet-300 border border-violet-500/30 shadow-[0_0_20px_rgba(139,92,246,0.15)]"
                                                : "bg-white/[0.03] text-white/50 border border-white/[0.06] hover:bg-white/[0.06] hover:text-white/70"
                                        )}
                                    >
                                        {config?.icon && <span className={isActive ? config.textColor : ''}>{config.icon}</span>}
                                        {category === 'All' ? 'All' : category.split(' ')[0]}
                                        <span className={cn(
                                            "text-[10px] px-1.5 py-0.5 rounded-md font-semibold",
                                            isActive ? "bg-violet-500/20 text-violet-300" : "bg-white/[0.05] text-white/40"
                                        )}>
                                            {count}
                                        </span>
                                    </button>
                                );
                            })}
                        </div>

                        {/* Article List */}
                        <ScrollArea className="flex-1">
                            <div className="p-3 space-y-2">
                                {searchQuery.trim() ? (
                                    <div className="space-y-1">
                                        <p className="px-3 py-2 text-xs text-white/40 font-medium">
                                            {filteredArticles.length} result{filteredArticles.length !== 1 ? 's' : ''} for &quot;{searchQuery}&quot;
                                        </p>
                                        {filteredArticles.map((article, index) => {
                                            const config = categoryConfig[article.category];
                                            const isActive = selectedArticle?.id === article.id;
                                            return (
                                                <button
                                                    key={article.id}
                                                    onClick={() => setSelectedArticle(article)}
                                                    className={cn(
                                                        "w-full text-left p-3 rounded-xl transition-all cursor-pointer",
                                                        isActive
                                                            ? `bg-gradient-to-r ${config?.gradient} bg-opacity-10 border border-white/10 shadow-lg`
                                                            : focusedIndex === index
                                                            ? "bg-white/[0.05] border border-white/[0.08]"
                                                            : "hover:bg-white/[0.03] border border-transparent"
                                                    )}
                                                >
                                                    <div className="flex items-start gap-3">
                                                        <div className={cn("mt-0.5 p-2 rounded-lg", config?.iconBg)}>
                                                            <span className={config?.textColor}>{config?.icon}</span>
                                                        </div>
                                                        <div className="flex-1 min-w-0">
                                                            <p className={cn("text-sm font-medium truncate", isActive ? "text-white" : "text-white/80")}>
                                                                {highlightMatches(article.title, searchQuery)}
                                                            </p>
                                                            <div className="flex items-center gap-2 mt-1.5">
                                                                <span className="text-xs text-white/40">{article.category}</span>
                                                                <span className="w-1 h-1 rounded-full bg-white/20" />
                                                                <span className="text-xs text-white/30 flex items-center gap-1">
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
                                    Object.entries(groupedArticles).map(([category, articles]) => {
                                        const config = categoryConfig[category];
                                        const isExpanded = expandedCategories.has(category);
                                        const hasActiveArticle = articles.some(a => selectedArticle?.id === a.id);

                                        return (
                                            <div
                                                key={category}
                                                className={cn(
                                                    "rounded-xl border overflow-hidden transition-all",
                                                    hasActiveArticle
                                                        ? `border-white/10 ${config?.iconBg} shadow-lg`
                                                        : "border-white/[0.06] hover:border-white/[0.1]"
                                                )}
                                            >
                                                <button
                                                    onClick={() => toggleCategory(category)}
                                                    className="w-full flex items-center justify-between p-3 hover:bg-white/[0.02] transition-colors cursor-pointer"
                                                >
                                                    <div className="flex items-center gap-3">
                                                        <div className={cn("p-2 rounded-lg", config?.iconBg)}>
                                                            <span className={config?.textColor}>{config?.icon}</span>
                                                        </div>
                                                        <span className={cn("font-medium text-sm", hasActiveArticle ? "text-white" : "text-white/70")}>
                                                            {category}
                                                        </span>
                                                        <span className="text-[10px] px-2 py-0.5 rounded-md bg-white/[0.05] text-white/40 font-semibold">
                                                            {articles.length}
                                                        </span>
                                                    </div>
                                                    <ChevronDown className={cn(
                                                        "h-4 w-4 text-white/30 transition-transform",
                                                        !isExpanded && "-rotate-90"
                                                    )} />
                                                </button>

                                                {isExpanded && (
                                                    <div className="border-t border-white/[0.04] bg-black/20">
                                                        {articles.map((article) => {
                                                            const isActive = selectedArticle?.id === article.id;
                                                            return (
                                                                <button
                                                                    key={article.id}
                                                                    onClick={() => setSelectedArticle(article)}
                                                                    className={cn(
                                                                        "w-full text-left px-4 py-2.5 transition-all cursor-pointer flex items-center gap-2 border-l-2",
                                                                        isActive
                                                                            ? `border-l-violet-500 bg-violet-500/10 ${config?.textColor}`
                                                                            : "border-l-transparent hover:bg-white/[0.02] hover:border-l-white/20 text-white/50 hover:text-white/70"
                                                                    )}
                                                                >
                                                                    <ChevronRight className={cn("h-3 w-3", isActive ? config?.textColor : "text-white/30")} />
                                                                    <span className="text-sm truncate flex-1">{article.title}</span>
                                                                    <span className="text-[10px] text-white/30 flex items-center gap-1">
                                                                        <Clock className="h-3 w-3" />
                                                                        {getReadingTime(article.content)}m
                                                                    </span>
                                                                </button>
                                                            );
                                                        })}
                                                    </div>
                                                )}
                                            </div>
                                        );
                                    })
                                )}

                                {filteredArticles.length === 0 && (
                                    <div className="text-center py-12">
                                        <div className="inline-flex items-center justify-center w-14 h-14 rounded-2xl bg-white/[0.03] border border-white/[0.06] mb-4">
                                            <Search className="h-6 w-6 text-white/30" />
                                        </div>
                                        <p className="text-sm font-medium text-white/50">No articles found</p>
                                        <p className="text-xs text-white/30 mt-1.5">
                                            Try different keywords or browse categories
                                        </p>
                                        <Button
                                            variant="ghost"
                                            size="sm"
                                            onClick={() => {
                                                setSearchQuery('');
                                                setSelectedCategory('All');
                                            }}
                                            className="mt-4 text-violet-400 hover:text-violet-300 hover:bg-violet-500/10"
                                        >
                                            Clear filters
                                        </Button>
                                    </div>
                                )}
                            </div>
                        </ScrollArea>

                        {/* Premium Footer */}
                        <div className="p-4 border-t border-white/[0.06]">
                            <a
                                href="mailto:support@axiohub.io"
                                className="flex items-center justify-center gap-2 px-4 py-3 rounded-xl bg-gradient-to-r from-violet-500/10 to-purple-500/10 border border-violet-500/20 hover:border-violet-500/40 text-violet-300 text-sm font-medium transition-all cursor-pointer group"
                            >
                                <HelpCircle className="h-4 w-4" />
                                Contact Support
                                <ExternalLink className="h-3 w-3 opacity-50 group-hover:opacity-100 transition-opacity" />
                            </a>
                        </div>
                    </div>

                    {/* Content Area */}
                    <div className="flex-1 flex flex-col min-w-0 min-h-0 bg-[#08080c]">
                        {/* Breadcrumb Header */}
                        <div className="flex items-center justify-between px-6 py-4 border-b border-white/[0.06] bg-white/[0.01]">
                            {selectedArticle ? (
                                <nav className="flex items-center gap-2 text-sm">
                                    <button onClick={() => setSelectedCategory('All')} className="text-white/40 hover:text-white/70 transition-colors cursor-pointer">
                                        Help Center
                                    </button>
                                    <ChevronRight className="h-4 w-4 text-white/20" />
                                    <button
                                        onClick={() => setSelectedCategory(selectedArticle.category)}
                                        className={cn("hover:text-white/70 transition-colors cursor-pointer", categoryConfig[selectedArticle.category]?.textColor || "text-white/40")}
                                    >
                                        {selectedArticle.category}
                                    </button>
                                    <ChevronRight className="h-4 w-4 text-white/20" />
                                    <span className="text-white font-medium truncate max-w-[300px]">{selectedArticle.title}</span>
                                </nav>
                            ) : (
                                <div />
                            )}
                            <button
                                onClick={closeHelp}
                                className="h-8 w-8 flex items-center justify-center rounded-lg bg-white/[0.03] hover:bg-white/[0.08] border border-white/[0.06] text-white/40 hover:text-white/70 transition-all cursor-pointer"
                            >
                                <X className="h-4 w-4" />
                            </button>
                        </div>

                        {/* Article Content */}
                        <div ref={contentRef} onScroll={handleContentScroll} className="flex-1 overflow-y-auto scroll-smooth">
                            {selectedArticle ? (
                                <article className="max-w-3xl mx-auto px-8 py-10">
                                    {/* Article Header */}
                                    <header className="mb-10">
                                        <div className="flex items-center gap-3 mb-5">
                                            <div className={cn(
                                                "inline-flex items-center gap-2 px-3.5 py-2 rounded-xl text-xs font-semibold border",
                                                categoryConfig[selectedArticle.category]?.iconBg,
                                                categoryConfig[selectedArticle.category]?.textColor,
                                                "border-white/10"
                                            )}>
                                                {categoryConfig[selectedArticle.category]?.icon}
                                                {selectedArticle.category}
                                            </div>
                                            <div className="flex items-center gap-1.5 text-xs text-white/40">
                                                <Clock className="h-3.5 w-3.5" />
                                                {getReadingTime(selectedArticle.content)} min read
                                            </div>
                                        </div>
                                        <h1 className="text-4xl font-bold tracking-tight text-white leading-tight">
                                            {selectedArticle.title}
                                        </h1>
                                    </header>

                                    {/* Premium Markdown Content */}
                                    <div className="prose prose-invert max-w-none
                                        prose-headings:font-semibold prose-headings:tracking-tight prose-headings:text-white
                                        prose-h2:text-2xl prose-h2:mt-12 prose-h2:mb-5 prose-h2:pb-3 prose-h2:border-b prose-h2:border-white/[0.06]
                                        prose-h3:text-xl prose-h3:mt-8 prose-h3:mb-4 prose-h3:text-white/90
                                        prose-p:text-white/60 prose-p:leading-relaxed prose-p:text-[15px]
                                        prose-li:text-white/60 prose-li:leading-relaxed prose-li:text-[15px]
                                        prose-strong:text-white prose-strong:font-semibold
                                        prose-code:text-violet-300 prose-code:bg-violet-500/10 prose-code:px-2 prose-code:py-1 prose-code:rounded-md prose-code:text-sm prose-code:before:content-[''] prose-code:after:content-[''] prose-code:border prose-code:border-violet-500/20
                                        prose-pre:bg-[#0c0c14] prose-pre:border prose-pre:border-white/[0.06] prose-pre:rounded-xl
                                        prose-table:text-sm
                                        prose-th:text-left prose-th:px-5 prose-th:py-4 prose-th:bg-white/[0.03] prose-th:font-semibold prose-th:text-white/70 prose-th:border-b prose-th:border-white/[0.08]
                                        prose-td:px-5 prose-td:py-4 prose-td:border-b prose-td:border-white/[0.04] prose-td:text-white/50
                                        prose-blockquote:border-l-violet-500 prose-blockquote:bg-violet-500/5 prose-blockquote:py-2 prose-blockquote:px-6 prose-blockquote:rounded-r-xl prose-blockquote:not-italic prose-blockquote:text-white/60
                                        prose-a:text-violet-400 prose-a:no-underline hover:prose-a:text-violet-300 hover:prose-a:underline
                                        prose-img:rounded-xl prose-img:border prose-img:border-white/[0.06]"
                                    >
                                        <ReactMarkdown remarkPlugins={[remarkGfm]}>
                                            {selectedArticle.content}
                                        </ReactMarkdown>
                                    </div>

                                    {/* Article Feedback */}
                                    <div className="mt-16 pt-10 border-t border-white/[0.06]">
                                        <ArticleFeedback articleId={selectedArticle.id} />
                                    </div>

                                    {/* Related Articles with Premium Cards */}
                                    {relatedArticles.length > 0 && (
                                        <div className="mt-10 pt-10 border-t border-white/[0.06]">
                                            <h3 className="text-lg font-semibold text-white mb-5">Related Articles</h3>
                                            <div className="grid gap-3">
                                                {relatedArticles.map((article) => {
                                                    const config = categoryConfig[article.category];
                                                    return (
                                                        <button
                                                            key={article.id}
                                                            onClick={() => setSelectedArticle(article)}
                                                            className="flex items-center gap-4 p-4 rounded-xl border border-white/[0.06] hover:border-white/[0.12] hover:bg-white/[0.02] transition-all text-left cursor-pointer group"
                                                        >
                                                            <div className={cn("p-2.5 rounded-xl", config?.iconBg)}>
                                                                <span className={config?.textColor}>{config?.icon}</span>
                                                            </div>
                                                            <div className="flex-1 min-w-0">
                                                                <p className="font-medium text-white/80 group-hover:text-white truncate transition-colors">{article.title}</p>
                                                                <p className="text-xs text-white/40 mt-1">
                                                                    {article.category} • {getReadingTime(article.content)} min read
                                                                </p>
                                                            </div>
                                                            <ChevronRight className="h-4 w-4 text-white/20 group-hover:text-white/40 group-hover:translate-x-0.5 transition-all shrink-0" />
                                                        </button>
                                                    );
                                                })}
                                            </div>
                                        </div>
                                    )}
                                </article>
                            ) : (
                                <div className="flex flex-col items-center justify-center h-full text-center px-8">
                                    <div className="relative mb-8">
                                        <div className="absolute inset-0 bg-gradient-to-br from-violet-500 to-purple-600 rounded-3xl blur-2xl opacity-20" />
                                        <div className="relative w-24 h-24 rounded-3xl bg-gradient-to-br from-violet-500/20 to-purple-600/20 border border-violet-500/20 flex items-center justify-center">
                                            <BookOpen className="h-12 w-12 text-violet-400" />
                                        </div>
                                    </div>
                                    <h3 className="text-2xl font-bold text-white mb-3">Welcome to Help Center</h3>
                                    <p className="text-white/50 max-w-md mb-8 leading-relaxed">
                                        Browse articles by category or search for specific topics.
                                        Use keyboard shortcuts for faster navigation.
                                    </p>
                                    <div className="flex flex-wrap gap-3 justify-center">
                                        {Object.entries(categoryConfig).slice(0, 4).map(([category, config]) => (
                                            <button
                                                key={category}
                                                onClick={() => {
                                                    setSelectedCategory(category as HelpArticle['category']);
                                                    setExpandedCategories(new Set([category]));
                                                }}
                                                className={cn(
                                                    "inline-flex items-center gap-2 px-5 py-2.5 rounded-xl border border-white/[0.08] hover:border-white/[0.15] transition-all cursor-pointer",
                                                    config.iconBg
                                                )}
                                            >
                                                <span className={config.textColor}>{config.icon}</span>
                                                <span className="text-sm font-medium text-white/70">{category}</span>
                                            </button>
                                        ))}
                                    </div>
                                </div>
                            )}
                        </div>

                        {/* Premium Back to Top */}
                        {showBackToTop && (
                            <button
                                onClick={scrollToTop}
                                className="absolute bottom-6 right-6 p-3 rounded-xl bg-gradient-to-r from-violet-500 to-purple-600 text-white shadow-[0_0_30px_rgba(139,92,246,0.4)] hover:shadow-[0_0_40px_rgba(139,92,246,0.6)] transition-all cursor-pointer animate-in fade-in slide-in-from-bottom-4"
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

// Premium Article Feedback Component
function ArticleFeedback({ articleId }: { articleId: string }) {
    const [feedback, setFeedback] = useState<'helpful' | 'not-helpful' | null>(null);
    const [showThankYou, setShowThankYou] = useState(false);

    const handleFeedback = (type: 'helpful' | 'not-helpful') => {
        setFeedback(type);
        setShowThankYou(true);
        console.log(`Article ${articleId} feedback: ${type}`);
    };

    if (showThankYou) {
        return (
            <div className="flex flex-col items-center gap-3 py-6">
                <div className="w-12 h-12 rounded-full bg-emerald-500/10 border border-emerald-500/20 flex items-center justify-center">
                    <Sparkles className="h-5 w-5 text-emerald-400" />
                </div>
                <p className="text-sm text-white/60">
                    Thank you for your feedback!
                </p>
            </div>
        );
    }

    return (
        <div className="flex flex-col items-center gap-4">
            <p className="text-sm text-white/50">Was this article helpful?</p>
            <div className="flex gap-3">
                <button
                    onClick={() => handleFeedback('helpful')}
                    className={cn(
                        "px-5 py-2.5 rounded-xl text-sm font-medium transition-all cursor-pointer",
                        feedback === 'helpful'
                            ? "bg-emerald-500/20 text-emerald-300 border border-emerald-500/30"
                            : "bg-white/[0.03] text-white/60 border border-white/[0.08] hover:bg-white/[0.06] hover:text-white/80"
                    )}
                >
                    Yes, it helped
                </button>
                <button
                    onClick={() => handleFeedback('not-helpful')}
                    className={cn(
                        "px-5 py-2.5 rounded-xl text-sm font-medium transition-all cursor-pointer",
                        feedback === 'not-helpful'
                            ? "bg-rose-500/20 text-rose-300 border border-rose-500/30"
                            : "bg-white/[0.03] text-white/60 border border-white/[0.08] hover:bg-white/[0.06] hover:text-white/80"
                    )}
                >
                    No, I need more help
                </button>
            </div>
        </div>
    );
}
