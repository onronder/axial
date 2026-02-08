"use client";

/**
 * Article Feedback Component - Production Grade
 *
 * Collects user feedback on article helpfulness.
 * Includes thank you state after submission.
 */

import { useState } from 'react';
import { Button } from '@/components/ui/button';
import { ThumbsUp, ThumbsDown, CheckCircle } from 'lucide-react';
import { cn } from '@/lib/utils';

interface ArticleFeedbackProps {
    articleId?: string;
    articleSlug?: string;
    className?: string;
}

export function ArticleFeedback({ articleId, articleSlug, className }: ArticleFeedbackProps) {
    const [feedback, setFeedback] = useState<'helpful' | 'not-helpful' | null>(null);
    const [showThankYou, setShowThankYou] = useState(false);

    const handleFeedback = (type: 'helpful' | 'not-helpful') => {
        setFeedback(type);
        setShowThankYou(true);

        // In production, send this to analytics
        const identifier = articleId || articleSlug || 'unknown';
        if (process.env.NODE_ENV !== 'production') {
            console.log(`Article ${identifier} feedback: ${type}`);
        }
    };

    if (showThankYou) {
        return (
            <div className={cn("flex flex-col items-center gap-3 py-4", className)}>
                <div className="flex items-center gap-2 text-primary">
                    <CheckCircle className="h-5 w-5" />
                    <p className="text-sm font-medium">Thank you for your feedback!</p>
                </div>
                <p className="text-xs text-muted-foreground">
                    Your input helps us improve our documentation.
                </p>
            </div>
        );
    }

    return (
        <div className={cn("flex flex-col items-center gap-4", className)}>
            <p className="text-sm text-muted-foreground">Was this article helpful?</p>
            <div className="flex gap-3">
                <Button
                    variant={feedback === 'helpful' ? 'default' : 'outline'}
                    size="sm"
                    onClick={() => handleFeedback('helpful')}
                    className="gap-2 cursor-pointer"
                >
                    <ThumbsUp className="h-4 w-4" />
                    Yes, it helped
                </Button>
                <Button
                    variant={feedback === 'not-helpful' ? 'default' : 'outline'}
                    size="sm"
                    onClick={() => handleFeedback('not-helpful')}
                    className="gap-2 cursor-pointer"
                >
                    <ThumbsDown className="h-4 w-4" />
                    No, I need more help
                </Button>
            </div>
        </div>
    );
}
