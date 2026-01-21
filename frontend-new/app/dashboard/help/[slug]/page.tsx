/**
 * Help Article Detail Page - Production Grade
 *
 * Features:
 * - Reading progress indicator
 * - Improved sidebar with collapsible categories
 * - Article feedback
 * - Related articles
 * - Responsive design
 */

import { getArticleBySlug, getAllArticles, getCategories } from '@/lib/help';
import { HelpSidebar } from '@/components/help/HelpSidebar';
import { ArticleViewer } from '@/components/help/ArticleViewer';
import { ArticleFeedback } from '@/components/help/ArticleFeedback';
import { ReadingProgressBar } from '@/components/help/ReadingProgressBar';
import { notFound } from 'next/navigation';
import {
    ChevronLeft,
    ChevronRight,
    BookOpen,
    Clock,
    ArrowLeft
} from 'lucide-react';
import Link from 'next/link';

interface PageProps {
    params: Promise<{ slug: string }>;
}

// Calculate reading time
function getReadingTime(content: string): number {
    const wordsPerMinute = 200;
    const wordCount = content.split(/\s+/).length;
    return Math.max(1, Math.ceil(wordCount / wordsPerMinute));
}

// Generate static params for all articles
export async function generateStaticParams() {
    const articles = getAllArticles();
    return articles.map((article) => ({
        slug: article.slug,
    }));
}

export default async function HelpArticlePage({ params }: PageProps) {
    const { slug } = await params;
    const article = getArticleBySlug(slug);

    if (!article) {
        notFound();
    }

    const articles = getAllArticles();
    const categories = getCategories();

    // Find previous and next articles
    const currentIndex = articles.findIndex((a) => a.slug === slug);
    const prevArticle = currentIndex > 0 ? articles[currentIndex - 1] : null;
    const nextArticle = currentIndex < articles.length - 1 ? articles[currentIndex + 1] : null;

    // Find related articles (same category, different article)
    const relatedArticles = articles
        .filter(a => a.category === article.category && a.slug !== slug)
        .slice(0, 3);

    return (
        <div className="flex min-h-screen bg-background">
            {/* Sidebar */}
            <HelpSidebar articles={articles} categories={categories} currentSlug={slug} />

            {/* Main Content */}
            <main className="flex-1 min-w-0">
                {/* Reading Progress Bar */}
                <ReadingProgressBar />

                <div className="max-w-4xl mx-auto py-8 px-6 md:px-8">
                    {/* Breadcrumb */}
                    <nav className="mb-8">
                        <ol className="flex items-center gap-2 text-sm">
                            <li>
                                <Link
                                    href="/dashboard/help"
                                    className="inline-flex items-center gap-1.5 text-muted-foreground hover:text-primary transition-colors"
                                >
                                    <ArrowLeft className="h-3.5 w-3.5" />
                                    Help Center
                                </Link>
                            </li>
                            <li>
                                <ChevronRight className="h-4 w-4 text-muted-foreground/50" />
                            </li>
                            <li>
                                <span className="text-muted-foreground">{article.category}</span>
                            </li>
                            <li>
                                <ChevronRight className="h-4 w-4 text-muted-foreground/50" />
                            </li>
                            <li>
                                <span className="text-foreground font-medium truncate max-w-[200px] inline-block">
                                    {article.title}
                                </span>
                            </li>
                        </ol>
                    </nav>

                    {/* Article Meta */}
                    <div className="flex items-center gap-3 mb-6">
                        <div className="flex items-center gap-1.5 text-sm text-muted-foreground">
                            <Clock className="h-4 w-4" />
                            <span>{getReadingTime(article.content)} min read</span>
                        </div>
                    </div>

                    {/* Article Content */}
                    <ArticleViewer
                        title={article.title}
                        category={article.category}
                        content={article.content}
                    />

                    {/* Article Feedback */}
                    <div className="mt-12 pt-8 border-t border-border/50">
                        <ArticleFeedback articleSlug={slug} />
                    </div>

                    {/* Related Articles */}
                    {relatedArticles.length > 0 && (
                        <div className="mt-8 pt-8 border-t border-border/50">
                            <h3 className="text-lg font-semibold mb-4 flex items-center gap-2">
                                <BookOpen className="h-5 w-5 text-primary" />
                                Related Articles
                            </h3>
                            <div className="grid gap-3">
                                {relatedArticles.map((relatedArticle) => (
                                    <Link
                                        key={relatedArticle.slug}
                                        href={`/dashboard/help/${relatedArticle.slug}`}
                                        className="group flex items-center gap-3 p-4 rounded-lg border border-border/50 hover:border-border hover:bg-accent/30 transition-all"
                                    >
                                        <div className="flex-1 min-w-0">
                                            <p className="font-medium group-hover:text-primary transition-colors truncate">
                                                {relatedArticle.title}
                                            </p>
                                            <p className="text-xs text-muted-foreground mt-1">
                                                {relatedArticle.category}
                                            </p>
                                        </div>
                                        <ChevronRight className="h-4 w-4 text-muted-foreground group-hover:text-primary group-hover:translate-x-0.5 transition-all shrink-0" />
                                    </Link>
                                ))}
                            </div>
                        </div>
                    )}

                    {/* Navigation Footer */}
                    <nav className="mt-12 pt-8 border-t border-border/50">
                        <div className="grid grid-cols-2 gap-4">
                            {prevArticle ? (
                                <Link
                                    href={`/dashboard/help/${prevArticle.slug}`}
                                    className="group flex flex-col p-4 rounded-lg border border-border/50 hover:border-border hover:bg-accent/30 transition-all"
                                >
                                    <span className="text-xs text-muted-foreground mb-1 flex items-center gap-1">
                                        <ChevronLeft className="h-3 w-3" />
                                        Previous
                                    </span>
                                    <span className="font-medium text-sm group-hover:text-primary transition-colors line-clamp-2">
                                        {prevArticle.title}
                                    </span>
                                </Link>
                            ) : (
                                <div />
                            )}

                            {nextArticle ? (
                                <Link
                                    href={`/dashboard/help/${nextArticle.slug}`}
                                    className="group flex flex-col items-end text-right p-4 rounded-lg border border-border/50 hover:border-border hover:bg-accent/30 transition-all"
                                >
                                    <span className="text-xs text-muted-foreground mb-1 flex items-center gap-1">
                                        Next
                                        <ChevronRight className="h-3 w-3" />
                                    </span>
                                    <span className="font-medium text-sm group-hover:text-primary transition-colors line-clamp-2">
                                        {nextArticle.title}
                                    </span>
                                </Link>
                            ) : (
                                <div />
                            )}
                        </div>
                    </nav>

                    {/* Back to Help Center */}
                    <div className="mt-8 text-center">
                        <Link
                            href="/dashboard/help"
                            className="inline-flex items-center gap-2 px-4 py-2 rounded-lg text-sm text-muted-foreground hover:text-foreground hover:bg-accent transition-all"
                        >
                            <ArrowLeft className="h-4 w-4" />
                            Back to Help Center
                        </Link>
                    </div>
                </div>
            </main>
        </div>
    );
}
