/**
 * Help Article Detail Page
 * 
 * Dynamic route for viewing individual help articles.
 */

import { getArticleBySlug, getAllArticles, getCategories } from '@/lib/help';
import { HelpSidebar } from '@/components/help/HelpSidebar';
import { ArticleViewer } from '@/components/help/ArticleViewer';
import { notFound } from 'next/navigation';
import { ChevronLeft, ChevronRight } from 'lucide-react';
import Link from 'next/link';

interface PageProps {
    params: Promise<{ slug: string }>;
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

    return (
        <div className="flex min-h-screen">
            {/* Sidebar */}
            <HelpSidebar articles={articles} categories={categories} />

            {/* Main Content */}
            <main className="flex-1 overflow-y-auto">
                <div className="max-w-4xl mx-auto py-10 px-8">
                    {/* Breadcrumb */}
                    <nav className="mb-8">
                        <ol className="flex items-center gap-2 text-sm text-muted-foreground">
                            <li>
                                <Link href="/dashboard/help" className="hover:text-primary transition-colors">
                                    Help Center
                                </Link>
                            </li>
                            <li>
                                <ChevronRight className="h-4 w-4" />
                            </li>
                            <li>
                                <span className="text-foreground">{article.category}</span>
                            </li>
                        </ol>
                    </nav>

                    {/* Article Content */}
                    <ArticleViewer
                        title={article.title}
                        category={article.category}
                        content={article.content}
                    />

                    {/* Navigation Footer */}
                    <nav className="mt-12 pt-8 border-t border-border/50">
                        <div className="flex justify-between items-center">
                            {prevArticle ? (
                                <Link
                                    href={`/dashboard/help/${prevArticle.slug}`}
                                    className="flex items-center gap-2 text-sm text-muted-foreground hover:text-primary transition-colors"
                                >
                                    <ChevronLeft className="h-4 w-4" />
                                    <span>{prevArticle.title}</span>
                                </Link>
                            ) : (
                                <div />
                            )}

                            {nextArticle ? (
                                <Link
                                    href={`/dashboard/help/${nextArticle.slug}`}
                                    className="flex items-center gap-2 text-sm text-muted-foreground hover:text-primary transition-colors"
                                >
                                    <span>{nextArticle.title}</span>
                                    <ChevronRight className="h-4 w-4" />
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
                            className="inline-flex items-center gap-2 text-sm text-primary hover:underline"
                        >
                            <ChevronLeft className="h-4 w-4" />
                            Back to Help Center
                        </Link>
                    </div>
                </div>
            </main>
        </div>
    );
}
