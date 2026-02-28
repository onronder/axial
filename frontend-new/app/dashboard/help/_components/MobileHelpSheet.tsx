"use client";

import { useState } from "react";
import Link from "next/link";
import { usePathname } from "next/navigation";
import { Menu, BookOpen, ChevronRight, ChevronDown } from "lucide-react";
import { cn } from "@/lib/utils";
import { Button } from "@/components/ui/button";
import {
    Sheet,
    SheetContent,
    SheetHeader,
    SheetTitle,
    SheetTrigger,
} from "@/components/ui/sheet";
import type { HelpArticleMeta } from "@/lib/help";

interface MobileHelpSheetProps {
    articles: HelpArticleMeta[];
    categories: Record<string, HelpArticleMeta[]>;
    currentSlug?: string;
}

export default function MobileHelpSheet({ articles, categories, currentSlug }: MobileHelpSheetProps) {
    const pathname = usePathname();
    const [sheetOpen, setSheetOpen] = useState(false);
    const [expandedCategories, setExpandedCategories] = useState<Set<string>>(() => {
        if (currentSlug) {
            const currentArticle = articles.find(a => a.slug === currentSlug);
            if (currentArticle) {
                return new Set([currentArticle.category]);
            }
        }
        const firstCategory = Object.keys(categories)[0];
        return firstCategory ? new Set([firstCategory]) : new Set();
    });

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

    return (
        <div className="lg:hidden border-b border-white/10 bg-background/70 backdrop-blur-xl">
            <div className="flex items-center gap-3 p-4">
                <Sheet open={sheetOpen} onOpenChange={setSheetOpen}>
                    <SheetTrigger asChild>
                        <Button variant="ghost" size="icon" className="shrink-0">
                            <Menu className="h-5 w-5" />
                            <span className="sr-only">Toggle help menu</span>
                        </Button>
                    </SheetTrigger>
                    <SheetContent side="left" className="w-72 p-0 bg-card/95 backdrop-blur-xl">
                        <SheetHeader className="p-6 border-b border-white/10">
                            <div className="flex items-center gap-3">
                                <div className="flex h-10 w-10 items-center justify-center rounded-xl bg-primary/10">
                                    <BookOpen className="h-5 w-5 text-primary" />
                                </div>
                                <SheetTitle className="font-display text-lg font-bold">
                                    Help Center
                                </SheetTitle>
                            </div>
                        </SheetHeader>
                        <div className="overflow-y-auto max-h-[calc(100vh-120px)]">
                            <nav className="flex flex-col gap-2 p-3">
                                {/* All Categories link */}
                                <Link
                                    href="/dashboard/help"
                                    onClick={() => setSheetOpen(false)}
                                    className={cn(
                                        "flex items-center gap-2 px-4 py-2.5 text-sm font-medium rounded-lg transition-all",
                                        pathname === "/dashboard/help"
                                            ? "bg-primary/10 text-primary"
                                            : "text-muted-foreground hover:bg-muted/80 hover:text-foreground"
                                    )}
                                >
                                    <BookOpen className="h-4 w-4 shrink-0" />
                                    All Categories
                                </Link>

                                {/* Category sections */}
                                {Object.entries(categories).map(([category, categoryArticles]) => {
                                    const isExpanded = expandedCategories.has(category);
                                    const hasActiveArticle = categoryArticles.some(
                                        a => pathname === `/dashboard/help/${a.slug}`
                                    );

                                    return (
                                        <div key={category} className="rounded-lg border border-border/50 overflow-hidden">
                                            <button
                                                onClick={() => toggleCategory(category)}
                                                className="w-full flex items-center justify-between p-3 hover:bg-accent/30 transition-colors cursor-pointer"
                                            >
                                                <span className={cn(
                                                    "font-medium text-sm",
                                                    hasActiveArticle && "text-primary"
                                                )}>
                                                    {category}
                                                </span>
                                                {isExpanded ? (
                                                    <ChevronDown className="h-4 w-4 text-muted-foreground" />
                                                ) : (
                                                    <ChevronRight className="h-4 w-4 text-muted-foreground" />
                                                )}
                                            </button>

                                            {isExpanded && (
                                                <div className="border-t border-border/30 bg-background/30">
                                                    {categoryArticles.map((article) => {
                                                        const isActive = pathname === `/dashboard/help/${article.slug}`;
                                                        return (
                                                            <Link
                                                                key={article.slug}
                                                                href={`/dashboard/help/${article.slug}`}
                                                                onClick={() => setSheetOpen(false)}
                                                                className={cn(
                                                                    "flex items-center gap-2 px-4 py-2.5 text-sm transition-all border-l-2",
                                                                    isActive
                                                                        ? "bg-primary/10 border-l-primary text-primary font-medium"
                                                                        : "border-l-transparent text-muted-foreground hover:text-foreground hover:bg-accent/30"
                                                                )}
                                                            >
                                                                <ChevronRight className={cn(
                                                                    "h-3 w-3 shrink-0",
                                                                    isActive ? "text-primary" : "text-muted-foreground/50"
                                                                )} />
                                                                <span className="truncate">{article.title}</span>
                                                            </Link>
                                                        );
                                                    })}
                                                </div>
                                            )}
                                        </div>
                                    );
                                })}
                            </nav>
                        </div>
                    </SheetContent>
                </Sheet>

                <div className="flex h-10 w-10 items-center justify-center rounded-xl bg-primary/10">
                    <BookOpen className="h-5 w-5 text-primary" />
                </div>
                <div>
                    <h1 className="font-display text-lg font-bold text-foreground">
                        Help Center
                    </h1>
                    <p className="text-xs text-muted-foreground">
                        {articles.length} articles
                    </p>
                </div>
            </div>
        </div>
    );
}
