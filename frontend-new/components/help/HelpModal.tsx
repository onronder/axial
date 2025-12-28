"use client";

/**
 * Help Modal Component
 * 
 * Full-screen modal with sidebar navigation, search, and markdown rendering.
 */

import { useEffect, useMemo } from 'react';
import { X, Search, BookOpen, Zap, Users, CreditCard, HelpCircle } from 'lucide-react';
import ReactMarkdown from 'react-markdown';
import remarkGfm from 'remark-gfm';
import { useHelpStore } from '@/store/useHelpStore';
import { HELP_ARTICLES, getCategories, type HelpArticle } from '@/data/helpArticles';
import { Dialog, DialogContent } from '@/components/ui/dialog';
import { Input } from '@/components/ui/input';
import { Button } from '@/components/ui/button';
import { ScrollArea } from '@/components/ui/scroll-area';
import { cn } from '@/lib/utils';

const categoryIcons: Record<string, React.ReactNode> = {
    'General': <HelpCircle className="h-4 w-4" />,
    'AI Features': <Zap className="h-4 w-4" />,
    'Teams': <Users className="h-4 w-4" />,
    'Billing': <CreditCard className="h-4 w-4" />,
};

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
                    a.content.toLowerCase().includes(query)
            );
        }

        return articles;
    }, [selectedCategory, searchQuery]);

    // Auto-select first article when filter changes
    useEffect(() => {
        if (filteredArticles.length > 0 && !selectedArticle) {
            setSelectedArticle(filteredArticles[0]);
        }
    }, [filteredArticles, selectedArticle, setSelectedArticle]);

    // Keyboard shortcut to open help
    useEffect(() => {
        const handleKeyDown = (e: KeyboardEvent) => {
            if (e.key === 'Escape' && isOpen) {
                closeHelp();
            }
        };
        window.addEventListener('keydown', handleKeyDown);
        return () => window.removeEventListener('keydown', handleKeyDown);
    }, [isOpen, closeHelp]);

    const categories = ['All', ...getCategories()] as const;

    return (
        <Dialog open={isOpen} onOpenChange={(open) => !open && closeHelp()}>
            <DialogContent className="max-w-5xl h-[85vh] p-0 gap-0 overflow-hidden">
                <div className="flex h-full">
                    {/* Sidebar */}
                    <div className="w-64 border-r border-border bg-muted/30 flex flex-col">
                        {/* Header */}
                        <div className="p-4 border-b border-border">
                            <div className="flex items-center gap-2 mb-4">
                                <div className="flex h-8 w-8 items-center justify-center rounded-lg bg-primary/10">
                                    <BookOpen className="h-4 w-4 text-primary" />
                                </div>
                                <h2 className="font-semibold text-lg">Help Center</h2>
                            </div>
                            {/* Search */}
                            <div className="relative">
                                <Search className="absolute left-3 top-1/2 -translate-y-1/2 h-4 w-4 text-muted-foreground" />
                                <Input
                                    placeholder="Search articles..."
                                    value={searchQuery}
                                    onChange={(e) => setSearchQuery(e.target.value)}
                                    className="pl-9 h-9"
                                />
                            </div>
                        </div>

                        {/* Categories */}
                        <ScrollArea className="flex-1 p-3">
                            <div className="space-y-1 mb-4">
                                {categories.map((category) => (
                                    <Button
                                        key={category}
                                        variant={selectedCategory === category ? "secondary" : "ghost"}
                                        size="sm"
                                        className={cn(
                                            "w-full justify-start gap-2",
                                            selectedCategory === category && "bg-primary/10 text-primary"
                                        )}
                                        onClick={() => {
                                            setSelectedCategory(category as HelpArticle['category'] | 'All');
                                            setSelectedArticle(null);
                                        }}
                                    >
                                        {category !== 'All' && categoryIcons[category]}
                                        {category === 'All' && <BookOpen className="h-4 w-4" />}
                                        {category}
                                    </Button>
                                ))}
                            </div>

                            {/* Article List */}
                            <div className="space-y-1">
                                <h3 className="px-2 mb-2 text-xs font-semibold uppercase tracking-wider text-muted-foreground">
                                    Articles ({filteredArticles.length})
                                </h3>
                                {filteredArticles.map((article) => (
                                    <Button
                                        key={article.id}
                                        variant="ghost"
                                        size="sm"
                                        className={cn(
                                            "w-full justify-start text-left h-auto py-2 px-2",
                                            selectedArticle?.id === article.id && "bg-accent"
                                        )}
                                        onClick={() => setSelectedArticle(article)}
                                    >
                                        <div className="flex flex-col items-start gap-0.5">
                                            <span className="text-sm line-clamp-1">{article.title}</span>
                                            <span className="text-xs text-muted-foreground">{article.category}</span>
                                        </div>
                                    </Button>
                                ))}
                                {filteredArticles.length === 0 && (
                                    <p className="text-sm text-muted-foreground text-center py-4">
                                        No articles found
                                    </p>
                                )}
                            </div>
                        </ScrollArea>
                    </div>

                    {/* Content Area */}
                    <div className="flex-1 flex flex-col">
                        {/* Close Button */}
                        <div className="flex justify-end p-2 border-b border-border">
                            <Button
                                variant="ghost"
                                size="icon"
                                onClick={closeHelp}
                                className="h-8 w-8"
                            >
                                <X className="h-4 w-4" />
                            </Button>
                        </div>

                        {/* Article Content */}
                        <ScrollArea className="flex-1 p-6">
                            {selectedArticle ? (
                                <article className="max-w-3xl mx-auto">
                                    {/* Article Header */}
                                    <header className="mb-6 pb-4 border-b border-border/50">
                                        <div className="inline-flex items-center gap-2 px-3 py-1 rounded-full bg-primary/10 text-primary text-xs font-medium mb-3">
                                            {categoryIcons[selectedArticle.category]}
                                            {selectedArticle.category}
                                        </div>
                                        <h1 className="text-2xl font-bold tracking-tight">
                                            {selectedArticle.title}
                                        </h1>
                                    </header>

                                    {/* Markdown Content */}
                                    <div className="prose prose-slate max-w-none dark:prose-invert prose-headings:font-semibold prose-headings:tracking-tight prose-h2:text-xl prose-h2:mt-6 prose-h2:mb-3 prose-p:text-muted-foreground prose-p:leading-relaxed prose-li:text-muted-foreground prose-strong:text-foreground prose-code:text-primary prose-code:bg-muted prose-code:px-1.5 prose-code:py-0.5 prose-code:rounded prose-code:before:content-[''] prose-code:after:content-[''] prose-table:text-sm prose-th:text-left prose-th:px-3 prose-th:py-2 prose-th:bg-muted prose-td:px-3 prose-td:py-2 prose-td:border-b prose-blockquote:border-l-primary prose-blockquote:bg-muted/50 prose-blockquote:py-1 prose-blockquote:px-4 prose-pre:bg-muted prose-pre:text-foreground">
                                        <ReactMarkdown remarkPlugins={[remarkGfm]}>
                                            {selectedArticle.content}
                                        </ReactMarkdown>
                                    </div>
                                </article>
                            ) : (
                                <div className="flex flex-col items-center justify-center h-full text-center">
                                    <BookOpen className="h-12 w-12 text-muted-foreground/50 mb-4" />
                                    <h3 className="text-lg font-medium text-muted-foreground">
                                        Select an article to read
                                    </h3>
                                    <p className="text-sm text-muted-foreground/80 mt-1">
                                        Browse categories or search for help topics
                                    </p>
                                </div>
                            )}
                        </ScrollArea>
                    </div>
                </div>
            </DialogContent>
        </Dialog>
    );
}
