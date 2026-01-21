"use client";

/**
 * Reading Progress Bar Component - Production Grade
 *
 * Shows reading progress as user scrolls through article.
 * Sticks to top of viewport.
 */

import { useState, useEffect, useCallback } from 'react';
import { cn } from '@/lib/utils';

interface ReadingProgressBarProps {
    className?: string;
}

export function ReadingProgressBar({ className }: ReadingProgressBarProps) {
    const [progress, setProgress] = useState(0);

    const updateProgress = useCallback(() => {
        const scrollTop = window.scrollY;
        const docHeight = document.documentElement.scrollHeight - window.innerHeight;
        const newProgress = docHeight > 0 ? (scrollTop / docHeight) * 100 : 0;
        setProgress(Math.min(100, newProgress));
    }, []);

    useEffect(() => {
        // Initial calculation
        updateProgress();

        // Add scroll listener
        window.addEventListener('scroll', updateProgress, { passive: true });

        return () => {
            window.removeEventListener('scroll', updateProgress);
        };
    }, [updateProgress]);

    return (
        <div className={cn("sticky top-0 z-50", className)}>
            <div className="h-1 bg-muted">
                <div
                    className="h-full bg-primary transition-all duration-150 ease-out"
                    style={{ width: `${progress}%` }}
                    role="progressbar"
                    aria-valuenow={Math.round(progress)}
                    aria-valuemin={0}
                    aria-valuemax={100}
                    aria-label="Reading progress"
                />
            </div>
        </div>
    );
}
