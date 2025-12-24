/**
 * Help Center Index Page
 * 
 * Displays category cards with article listings.
 */

import { getAllArticles, getCategories, getCategoryNames } from '@/lib/help';
import { HelpSearch } from '@/components/help/HelpSearch';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { BookOpen, FileText, Settings, Shield, Zap } from 'lucide-react';
import Link from 'next/link';

// Category icons mapping
const categoryIcons: Record<string, React.ReactNode> = {
    "Getting Started": <Zap className="h-5 w-5" />,
    "Data Management": <FileText className="h-5 w-5" />,
    "Features": <BookOpen className="h-5 w-5" />,
    "Settings": <Settings className="h-5 w-5" />,
    "Legal & Safety": <Shield className="h-5 w-5" />,
};

// Category colors mapping
const categoryColors: Record<string, string> = {
    "Getting Started": "bg-blue-500/10 text-blue-600 dark:text-blue-400",
    "Data Management": "bg-green-500/10 text-green-600 dark:text-green-400",
    "Features": "bg-purple-500/10 text-purple-600 dark:text-purple-400",
    "Settings": "bg-orange-500/10 text-orange-600 dark:text-orange-400",
    "Legal & Safety": "bg-red-500/10 text-red-600 dark:text-red-400",
};

export default function HelpCenterPage() {
    const articles = getAllArticles();
    const categories = getCategories();
    const categoryNames = getCategoryNames();

    return (
        <div className="container max-w-5xl py-10 px-4">
            {/* Header */}
            <div className="text-center mb-12">
                <div className="inline-flex items-center justify-center w-16 h-16 rounded-2xl bg-primary/10 mb-6">
                    <BookOpen className="h-8 w-8 text-primary" />
                </div>
                <h1 className="text-4xl font-bold tracking-tight mb-4">Help Center</h1>
                <p className="text-lg text-muted-foreground max-w-2xl mx-auto mb-8">
                    Find answers to common questions and learn how to get the most out of Axio Hub.
                </p>

                {/* Search */}
                <div className="flex justify-center">
                    <HelpSearch articles={articles} />
                </div>
            </div>

            {/* Category Cards Grid */}
            <div className="grid gap-6 md:grid-cols-2 lg:grid-cols-3">
                {categoryNames.map((category) => {
                    const categoryArticles = categories[category] || [];
                    const icon = categoryIcons[category] || <FileText className="h-5 w-5" />;
                    const colorClass = categoryColors[category] || "bg-gray-500/10 text-gray-600";

                    return (
                        <Card key={category} className="group hover:shadow-lg transition-all duration-200 border-border/50">
                            <CardHeader className="pb-3">
                                <div className="flex items-center gap-3">
                                    <div className={`flex items-center justify-center w-10 h-10 rounded-lg ${colorClass}`}>
                                        {icon}
                                    </div>
                                    <CardTitle className="text-lg">{category}</CardTitle>
                                </div>
                            </CardHeader>
                            <CardContent>
                                <ul className="space-y-2">
                                    {categoryArticles.map((article) => (
                                        <li key={article.slug}>
                                            <Link
                                                href={`/dashboard/help/${article.slug}`}
                                                className="text-sm text-muted-foreground hover:text-primary transition-colors flex items-center gap-2"
                                            >
                                                <span className="w-1.5 h-1.5 rounded-full bg-muted-foreground/50" />
                                                {article.title}
                                            </Link>
                                        </li>
                                    ))}
                                </ul>
                            </CardContent>
                        </Card>
                    );
                })}
            </div>

            {/* Quick Links Footer */}
            <div className="mt-12 pt-8 border-t border-border/50 text-center">
                <p className="text-sm text-muted-foreground mb-4">
                    Can't find what you're looking for?
                </p>
                <div className="flex items-center justify-center gap-4">
                    <Link
                        href="mailto:support@axiohub.io"
                        className="text-sm text-primary hover:underline"
                    >
                        Contact Support
                    </Link>
                    <span className="text-muted-foreground">•</span>
                    <Link
                        href="/dashboard/settings"
                        className="text-sm text-primary hover:underline"
                    >
                        Go to Settings
                    </Link>
                </div>
            </div>
        </div>
    );
}
