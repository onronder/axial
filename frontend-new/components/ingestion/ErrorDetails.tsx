/**
 * Error Details Component
 * 
 * Displays detailed error information for failed files.
 * Shows error type, message, timestamp, and attempt count.
 */

import React from 'react';
import { AlertCircle, Clock, RotateCw } from 'lucide-react';

interface ErrorDetailsProps {
    error: {
        type: string;
        message: string;
        timestamp?: string;
        attemptCount?: number;
        maxAttempts?: number;
    };
    className?: string;
}

export function ErrorDetails({ error, className }: ErrorDetailsProps) {
    return (
        <div className={className}>
            {/* Header */}
            <div className="flex items-center gap-2 mb-2">
                <AlertCircle className="h-4 w-4 text-red-500" />
                <span className="text-sm font-medium text-red-700 dark:text-red-400">
                    Error Details
                </span>
            </div>

            {/* Error card */}
            <div className="rounded-lg border border-red-200 dark:border-red-800 bg-red-50 dark:bg-red-950 p-4 space-y-3">
                {/* Error type */}
                <div>
                    <span className="text-xs font-medium text-red-600 dark:text-red-400 font-mono">
                        {error.type}
                    </span>
                </div>

                {/* Error message */}
                <p className="text-sm text-red-700 dark:text-red-300 leading-relaxed">
                    {error.message}
                </p>

                {/* Metadata */}
                {(error.timestamp || error.attemptCount) && (
                    <div className="flex items-center gap-4 text-xs text-red-600/80 dark:text-red-400/80 pt-2 border-t border-red-200 dark:border-red-800">
                        {error.timestamp && (
                            <div className="flex items-center gap-1">
                                <Clock className="h-3 w-3" />
                                <span className="tabular-nums">
                                    {new Date(error.timestamp).toLocaleTimeString()}
                                </span>
                            </div>
                        )}
                        {error.attemptCount && error.maxAttempts && (
                            <div className="flex items-center gap-1">
                                <RotateCw className="h-3 w-3" />
                                <span className="tabular-nums">
                                    Attempt {error.attemptCount}/{error.maxAttempts}
                                </span>
                            </div>
                        )}
                    </div>
                )}
            </div>
        </div>
    );
}
