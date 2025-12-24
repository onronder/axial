"use client";

/**
 * Article Viewer Component
 * 
 * Renders markdown content with Tailwind Typography styling.
 */

import ReactMarkdown from 'react-markdown';

interface ArticleViewerProps {
    title: string;
    category: string;
    content: string;
}

export function ArticleViewer({ title, category, content }: ArticleViewerProps) {
    return (
        <article className="max-w-3xl mx-auto">
            {/* Article Header */}
            <header className="mb-8 pb-6 border-b border-border/50">
                <div className="inline-flex items-center gap-2 px-3 py-1 rounded-full bg-primary/10 text-primary text-xs font-medium mb-4">
                    {category}
                </div>
                <h1 className="text-3xl font-bold tracking-tight text-foreground">
                    {title}
                </h1>
            </header>

            {/* Article Content */}
            <div className="prose prose-slate max-w-none dark:prose-invert prose-headings:font-semibold prose-headings:tracking-tight prose-h2:text-xl prose-h2:mt-8 prose-h2:mb-4 prose-p:text-muted-foreground prose-p:leading-relaxed prose-li:text-muted-foreground prose-strong:text-foreground prose-code:text-primary prose-code:bg-muted prose-code:px-1.5 prose-code:py-0.5 prose-code:rounded prose-code:before:content-[''] prose-code:after:content-['']">
                <ReactMarkdown>{content}</ReactMarkdown>
            </div>
        </article>
    );
}
