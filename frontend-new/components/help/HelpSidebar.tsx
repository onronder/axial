"use client";

/**
 * Help Sidebar Component
 * 
 * Displays categorized list of help articles with active state.
 */

import Link from 'next/link';
import { usePathname } from 'next/navigation';
import { cn } from '@/lib/utils';
import { BookOpen, ChevronRight } from 'lucide-react';

interface ArticleMeta {
    slug: string;
    title: string;
    category: string;
    order: number;
}

interface HelpSidebarProps {
    articles: ArticleMeta[];
    categories: Record<string, ArticleMeta[]>;
}

export function HelpSidebar({ articles, categories }: HelpSidebarProps) {
    const pathname = usePathname();

    return (
        <aside className="w-64 shrink-0 border-r border-border/50 bg-muted/20">
            <div className="sticky top-0 h-screen overflow-y-auto p-4">
                <div className="flex items-center gap-2 mb-6 px-2">
                    <div className="flex h-8 w-8 items-center justify-center rounded-lg bg-primary/10">
                        <BookOpen className="h-4 w-4 text-primary" />
                    </div>
                    <h2 className="font-semibold text-lg">Help Center</h2>
                </div>

                <nav className="space-y-6">
                    {Object.entries(categories).map(([category, categoryArticles]) => (
                        <div key={category}>
                            <h3 className="px-2 mb-2 text-xs font-semibold uppercase tracking-wider text-muted-foreground">
                                {category}
                            </h3>
                            <ul className="space-y-1">
                                {categoryArticles.map((article) => {
                                    const isActive = pathname === `/dashboard/help/${article.slug}`;
                                    return (
                                        <li key={article.slug}>
                                            <Link
                                                href={`/dashboard/help/${article.slug}`}
                                                className={cn(
                                                    "flex items-center gap-2 rounded-lg px-2 py-2 text-sm transition-colors",
                                                    isActive
                                                        ? "bg-primary/10 text-primary font-medium"
                                                        : "text-muted-foreground hover:bg-muted hover:text-foreground"
                                                )}
                                            >
                                                <ChevronRight className={cn(
                                                    "h-3 w-3 transition-transform",
                                                    isActive && "text-primary"
                                                )} />
                                                {article.title}
                                            </Link>
                                        </li>
                                    );
                                })}
                            </ul>
                        </div>
                    ))}
                </nav>
            </div>
        </aside>
    );
}
