"use client";

/**
 * Article Viewer Component - Production Grade
 *
 * Features:
 * - Enhanced markdown rendering with Tailwind Typography
 * - Category badge with icon
 * - Syntax highlighting for code blocks
 * - Responsive typography
 * - Accessible heading structure
 */

import ReactMarkdown from 'react-markdown';
import remarkGfm from 'remark-gfm';
import {
    BookOpen,
    Zap,
    FileText,
    Settings,
    Shield,
    Sparkles,
    Plug,
    Users,
    CreditCard,
    AlertTriangle
} from 'lucide-react';
import { cn } from '@/lib/utils';

interface ArticleViewerProps {
    title: string;
    category: string;
    content: string;
}

// Category configuration
const categoryConfig: Record<string, {
    icon: React.ReactNode;
    color: string;
    bgColor: string;
}> = {
    "General": {
        icon: <BookOpen className="h-4 w-4" />,
        color: "text-blue-600 dark:text-blue-400",
        bgColor: "bg-blue-500/10"
    },
    "Getting Started": {
        icon: <Zap className="h-4 w-4" />,
        color: "text-blue-600 dark:text-blue-400",
        bgColor: "bg-blue-500/10"
    },
    "Data Management": {
        icon: <FileText className="h-4 w-4" />,
        color: "text-green-600 dark:text-green-400",
        bgColor: "bg-green-500/10"
    },
    "AI Features": {
        icon: <Sparkles className="h-4 w-4" />,
        color: "text-purple-600 dark:text-purple-400",
        bgColor: "bg-purple-500/10"
    },
    "Features": {
        icon: <Sparkles className="h-4 w-4" />,
        color: "text-purple-600 dark:text-purple-400",
        bgColor: "bg-purple-500/10"
    },
    "Connectors": {
        icon: <Plug className="h-4 w-4" />,
        color: "text-green-600 dark:text-green-400",
        bgColor: "bg-green-500/10"
    },
    "Teams": {
        icon: <Users className="h-4 w-4" />,
        color: "text-orange-600 dark:text-orange-400",
        bgColor: "bg-orange-500/10"
    },
    "Settings": {
        icon: <Settings className="h-4 w-4" />,
        color: "text-orange-600 dark:text-orange-400",
        bgColor: "bg-orange-500/10"
    },
    "Billing": {
        icon: <CreditCard className="h-4 w-4" />,
        color: "text-emerald-600 dark:text-emerald-400",
        bgColor: "bg-emerald-500/10"
    },
    "Legal & Safety": {
        icon: <Shield className="h-4 w-4" />,
        color: "text-red-600 dark:text-red-400",
        bgColor: "bg-red-500/10"
    },
    "Troubleshooting": {
        icon: <AlertTriangle className="h-4 w-4" />,
        color: "text-red-600 dark:text-red-400",
        bgColor: "bg-red-500/10"
    },
};

export function ArticleViewer({ title, category, content }: ArticleViewerProps) {
    const config = categoryConfig[category];

    return (
        <article className="max-w-3xl mx-auto">
            {/* Article Header */}
            <header className="mb-8 pb-6 border-b border-border/50">
                <div className={cn(
                    "inline-flex items-center gap-2 px-3 py-1.5 rounded-full text-xs font-medium mb-4",
                    config?.bgColor || "bg-muted",
                    config?.color || "text-muted-foreground"
                )}>
                    {config?.icon || <FileText className="h-4 w-4" />}
                    {category}
                </div>
                <h1 className="text-3xl md:text-4xl font-bold tracking-tight text-foreground">
                    {title}
                </h1>
            </header>

            {/* Article Content */}
            <div className={cn(
                "prose prose-slate max-w-none dark:prose-invert",
                // Headings
                "prose-headings:font-semibold prose-headings:tracking-tight prose-headings:scroll-mt-20",
                "prose-h1:text-3xl prose-h1:mb-6",
                "prose-h2:text-xl prose-h2:mt-10 prose-h2:mb-4 prose-h2:pb-2 prose-h2:border-b prose-h2:border-border/30",
                "prose-h3:text-lg prose-h3:mt-8 prose-h3:mb-3",
                "prose-h4:text-base prose-h4:mt-6 prose-h4:mb-2",
                // Paragraphs
                "prose-p:text-muted-foreground prose-p:leading-7",
                // Lists
                "prose-li:text-muted-foreground prose-li:leading-7 prose-li:marker:text-muted-foreground/50",
                "prose-ul:my-4 prose-ol:my-4",
                // Strong and emphasis
                "prose-strong:text-foreground prose-strong:font-semibold",
                "prose-em:text-muted-foreground",
                // Code
                "prose-code:text-primary prose-code:bg-primary/10 prose-code:px-1.5 prose-code:py-0.5 prose-code:rounded-md prose-code:text-sm prose-code:font-medium prose-code:before:content-[''] prose-code:after:content-['']",
                // Pre (code blocks)
                "prose-pre:bg-muted prose-pre:border prose-pre:border-border/50 prose-pre:rounded-xl prose-pre:p-4 prose-pre:overflow-x-auto",
                "prose-pre:text-sm prose-pre:leading-relaxed",
                // Tables
                "prose-table:text-sm prose-table:w-full prose-table:border-collapse prose-table:overflow-hidden prose-table:rounded-lg prose-table:border prose-table:border-border/50",
                "prose-thead:bg-muted/50",
                "prose-th:text-left prose-th:px-4 prose-th:py-3 prose-th:font-semibold prose-th:text-foreground prose-th:border-b prose-th:border-border/30",
                "prose-td:px-4 prose-td:py-3 prose-td:border-b prose-td:border-border/30 prose-td:text-muted-foreground",
                "prose-tr:last:border-0",
                // Blockquotes
                "prose-blockquote:border-l-4 prose-blockquote:border-l-primary prose-blockquote:bg-primary/5 prose-blockquote:py-3 prose-blockquote:px-6 prose-blockquote:rounded-r-lg prose-blockquote:not-italic prose-blockquote:text-muted-foreground",
                // Links
                "prose-a:text-primary prose-a:font-medium prose-a:no-underline hover:prose-a:underline prose-a:transition-colors",
                // Images
                "prose-img:rounded-xl prose-img:border prose-img:border-border/50 prose-img:shadow-sm",
                // Horizontal rules
                "prose-hr:border-border/50 prose-hr:my-8"
            )}>
                <ReactMarkdown
                    remarkPlugins={[remarkGfm]}
                    components={{
                        // Custom rendering for specific elements
                        a: ({ node: _node, ...props }) => (
                            <a {...props} target={props.href?.startsWith('http') ? '_blank' : undefined} rel={props.href?.startsWith('http') ? 'noopener noreferrer' : undefined} />
                        ),
                        // Add copy button to code blocks in the future
                        pre: ({ node: _node, ...props }) => (
                            <div className="relative group">
                                <pre {...props} />
                            </div>
                        ),
                    }}
                >
                    {content}
                </ReactMarkdown>
            </div>
        </article>
    );
}
