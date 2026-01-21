/**
 * Help Center Index Page - Production Grade
 *
 * Features:
 * - Hero section with animated search
 * - Category cards with article previews
 * - Popular articles section
 * - Quick links and contact support
 * - Responsive design
 * - Keyboard navigation
 */

import { getAllArticles, getCategories, getCategoryNames } from '@/lib/help';
import { HelpSearch } from '@/components/help/HelpSearch';
import { Card, CardContent, CardHeader } from '@/components/ui/card';
import { Badge } from '@/components/ui/badge';
import {
    BookOpen,
    FileText,
    Settings,
    Shield,
    Zap,
    ChevronRight,
    MessageCircle,
    Sparkles,
    ArrowRight
} from 'lucide-react';
import Link from 'next/link';

// Category configuration with icons and colors
const categoryConfig: Record<string, {
    icon: React.ReactNode;
    color: string;
    bgColor: string;
    borderColor: string;
    description: string;
}> = {
    "Getting Started": {
        icon: <Zap className="h-6 w-6" />,
        color: "text-blue-600 dark:text-blue-400",
        bgColor: "bg-blue-500/10",
        borderColor: "border-blue-500/20 hover:border-blue-500/40",
        description: "Quick guides to get up and running"
    },
    "Data Management": {
        icon: <FileText className="h-6 w-6" />,
        color: "text-green-600 dark:text-green-400",
        bgColor: "bg-green-500/10",
        borderColor: "border-green-500/20 hover:border-green-500/40",
        description: "Learn about uploading and managing data"
    },
    "Features": {
        icon: <Sparkles className="h-6 w-6" />,
        color: "text-purple-600 dark:text-purple-400",
        bgColor: "bg-purple-500/10",
        borderColor: "border-purple-500/20 hover:border-purple-500/40",
        description: "Explore all available features"
    },
    "Settings": {
        icon: <Settings className="h-6 w-6" />,
        color: "text-orange-600 dark:text-orange-400",
        bgColor: "bg-orange-500/10",
        borderColor: "border-orange-500/20 hover:border-orange-500/40",
        description: "Configure and customize your experience"
    },
    "Legal & Safety": {
        icon: <Shield className="h-6 w-6" />,
        color: "text-red-600 dark:text-red-400",
        bgColor: "bg-red-500/10",
        borderColor: "border-red-500/20 hover:border-red-500/40",
        description: "Privacy, security, and compliance"
    },
};

export default function HelpCenterPage() {
    const articles = getAllArticles();
    const categories = getCategories();
    const categoryNames = getCategoryNames();

    // Get popular articles (first article from each category)
    const popularArticles = categoryNames
        .map(cat => categories[cat]?.[0])
        .filter(Boolean)
        .slice(0, 4);

    return (
        <div className="min-h-screen bg-gradient-to-b from-muted/30 to-background">
            {/* Hero Section */}
            <div className="relative overflow-hidden border-b border-border/50">
                {/* Background Pattern */}
                <div className="absolute inset-0 bg-grid-slate-100/50 dark:bg-grid-slate-900/50 [mask-image:radial-gradient(ellipse_at_center,white,transparent_75%)]" />

                <div className="container max-w-6xl py-16 px-4 relative">
                    <div className="text-center max-w-3xl mx-auto">
                        {/* Icon */}
                        <div className="inline-flex items-center justify-center w-16 h-16 rounded-2xl bg-primary/10 mb-6 ring-4 ring-primary/5">
                            <BookOpen className="h-8 w-8 text-primary" />
                        </div>

                        {/* Title */}
                        <h1 className="text-4xl md:text-5xl font-bold tracking-tight mb-4 bg-gradient-to-r from-foreground to-foreground/70 bg-clip-text">
                            Help Center
                        </h1>

                        {/* Subtitle */}
                        <p className="text-lg text-muted-foreground mb-8 max-w-xl mx-auto">
                            Find answers to common questions and learn how to get the most out of Axio Hub.
                        </p>

                        {/* Search */}
                        <div className="flex justify-center mb-6">
                            <HelpSearch articles={articles} />
                        </div>

                        {/* Quick Stats */}
                        <div className="flex items-center justify-center gap-6 text-sm text-muted-foreground">
                            <div className="flex items-center gap-2">
                                <FileText className="h-4 w-4" />
                                <span>{articles.length} articles</span>
                            </div>
                            <div className="w-1 h-1 rounded-full bg-muted-foreground/50" />
                            <div className="flex items-center gap-2">
                                <BookOpen className="h-4 w-4" />
                                <span>{categoryNames.length} categories</span>
                            </div>
                        </div>
                    </div>
                </div>
            </div>

            {/* Main Content */}
            <div className="container max-w-6xl py-12 px-4">
                {/* Popular Articles Section */}
                {popularArticles.length > 0 && (
                    <section className="mb-12">
                        <div className="flex items-center gap-2 mb-6">
                            <Sparkles className="h-5 w-5 text-primary" />
                            <h2 className="text-xl font-semibold">Popular Articles</h2>
                        </div>

                        <div className="grid gap-4 md:grid-cols-2">
                            {popularArticles.map((article) => {
                                const config = categoryConfig[article.category];
                                return (
                                    <Link
                                        key={article.slug}
                                        href={`/dashboard/help/${article.slug}`}
                                        className="group flex items-start gap-4 p-4 rounded-xl border border-border/50 bg-card hover:bg-accent/30 hover:border-border transition-all cursor-pointer"
                                    >
                                        <div className={`flex-shrink-0 p-3 rounded-lg ${config?.bgColor || 'bg-muted'}`}>
                                            <span className={config?.color || 'text-muted-foreground'}>
                                                {config?.icon || <FileText className="h-6 w-6" />}
                                            </span>
                                        </div>
                                        <div className="flex-1 min-w-0">
                                            <h3 className="font-medium text-foreground group-hover:text-primary transition-colors truncate">
                                                {article.title}
                                            </h3>
                                            <p className="text-sm text-muted-foreground mt-1">
                                                {article.category}
                                            </p>
                                            <p className="text-xs text-muted-foreground/80 mt-2">
                                                {article.category}
                                            </p>
                                        </div>
                                        <ChevronRight className="h-5 w-5 text-muted-foreground/50 group-hover:text-primary group-hover:translate-x-0.5 transition-all shrink-0" />
                                    </Link>
                                );
                            })}
                        </div>
                    </section>
                )}

                {/* Category Cards Grid */}
                <section className="mb-12">
                    <div className="flex items-center gap-2 mb-6">
                        <BookOpen className="h-5 w-5 text-primary" />
                        <h2 className="text-xl font-semibold">Browse by Category</h2>
                    </div>

                    <div className="grid gap-6 md:grid-cols-2 lg:grid-cols-3">
                        {categoryNames.map((category) => {
                            const categoryArticles = categories[category] || [];
                            const config = categoryConfig[category];

                            return (
                                <Card
                                    key={category}
                                    className={`group hover:shadow-lg transition-all duration-300 border-2 ${config?.borderColor || 'border-border/50 hover:border-border'} cursor-pointer`}
                                >
                                    <CardHeader className="pb-3">
                                        <div className="flex items-start justify-between">
                                            <div className="flex items-center gap-3">
                                                <div className={`flex items-center justify-center w-12 h-12 rounded-xl ${config?.bgColor || 'bg-muted'}`}>
                                                    <span className={config?.color || 'text-muted-foreground'}>
                                                        {config?.icon || <FileText className="h-6 w-6" />}
                                                    </span>
                                                </div>
                                                <div>
                                                    <h3 className="font-semibold text-lg">{category}</h3>
                                                    <p className="text-xs text-muted-foreground mt-0.5">
                                                        {config?.description || `${categoryArticles.length} articles`}
                                                    </p>
                                                </div>
                                            </div>
                                            <Badge variant="secondary" className="text-xs">
                                                {categoryArticles.length}
                                            </Badge>
                                        </div>
                                    </CardHeader>
                                    <CardContent>
                                        <ul className="space-y-2">
                                            {categoryArticles.slice(0, 4).map((article) => (
                                                <li key={article.slug}>
                                                    <Link
                                                        href={`/dashboard/help/${article.slug}`}
                                                        className="group/link flex items-center gap-3 py-2 px-3 -mx-3 rounded-lg text-sm text-muted-foreground hover:text-foreground hover:bg-accent/50 transition-all"
                                                    >
                                                        <div className={`w-2 h-2 rounded-full ${config?.bgColor || 'bg-muted'} group-hover/link:scale-125 transition-transform`} />
                                                        <span className="truncate flex-1">{article.title}</span>
                                                        <ChevronRight className="h-3.5 w-3.5 opacity-0 -translate-x-2 group-hover/link:opacity-100 group-hover/link:translate-x-0 transition-all" />
                                                    </Link>
                                                </li>
                                            ))}
                                        </ul>

                                        {categoryArticles.length > 4 && (
                                            <Link
                                                href={`/dashboard/help?category=${encodeURIComponent(category)}`}
                                                className="inline-flex items-center gap-1.5 mt-4 text-sm text-primary hover:underline font-medium"
                                            >
                                                View all {categoryArticles.length} articles
                                                <ArrowRight className="h-3.5 w-3.5" />
                                            </Link>
                                        )}
                                    </CardContent>
                                </Card>
                            );
                        })}
                    </div>
                </section>

                {/* Contact Support Section */}
                <section className="relative overflow-hidden rounded-2xl border border-border/50 bg-gradient-to-br from-primary/5 via-background to-primary/5">
                    <div className="absolute inset-0 bg-grid-slate-100/30 dark:bg-grid-slate-900/30" />

                    <div className="relative p-8 md:p-12">
                        <div className="max-w-2xl mx-auto text-center">
                            <div className="inline-flex items-center justify-center w-14 h-14 rounded-full bg-primary/10 mb-6">
                                <MessageCircle className="h-7 w-7 text-primary" />
                            </div>

                            <h2 className="text-2xl font-bold mb-3">
                                Can't find what you're looking for?
                            </h2>

                            <p className="text-muted-foreground mb-8">
                                Our support team is here to help. Get in touch and we'll get back to you as soon as possible.
                            </p>

                            <div className="flex flex-col sm:flex-row items-center justify-center gap-4">
                                <a
                                    href="mailto:support@axiohub.io"
                                    className="inline-flex items-center gap-2 px-6 py-3 rounded-lg bg-primary text-primary-foreground font-medium hover:bg-primary/90 transition-colors cursor-pointer"
                                >
                                    <MessageCircle className="h-4 w-4" />
                                    Contact Support
                                </a>

                                <Link
                                    href="/dashboard/settings"
                                    className="inline-flex items-center gap-2 px-6 py-3 rounded-lg border border-border bg-background hover:bg-accent transition-colors cursor-pointer"
                                >
                                    <Settings className="h-4 w-4" />
                                    Go to Settings
                                </Link>
                            </div>
                        </div>
                    </div>
                </section>

                {/* Keyboard Shortcut Hint */}
                <div className="mt-8 text-center">
                    <p className="text-sm text-muted-foreground">
                        <span className="inline-flex items-center gap-1.5">
                            Press
                            <kbd className="px-2 py-1 rounded bg-muted border border-border text-xs font-mono">
                                ?
                            </kbd>
                            anywhere in the Help Modal for keyboard shortcuts
                        </span>
                    </p>
                </div>
            </div>
        </div>
    );
}
