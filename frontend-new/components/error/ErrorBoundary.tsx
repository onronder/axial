/**
 * Error Boundary Component
 * 
 * Production-grade error boundary for graceful error handling.
 * Catches React errors and displays fallback UI.
 */

"use client";

import React, { Component, ReactNode } from 'react';

interface ErrorBoundaryProps {
    children: ReactNode;
    fallback?: ReactNode;
    onError?: (error: Error, errorInfo: React.ErrorInfo) => void;
}

interface ErrorBoundaryState {
    hasError: boolean;
    error: Error | null;
}

export class ErrorBoundary extends Component<ErrorBoundaryProps, ErrorBoundaryState> {
    constructor(props: ErrorBoundaryProps) {
        super(props);
        this.state = {
            hasError: false,
            error: null,
        };
    }

    static getDerivedStateFromError(error: Error): ErrorBoundaryState {
        return {
            hasError: true,
            error,
        };
    }

    componentDidCatch(error: Error, errorInfo: React.ErrorInfo) {
        // Log error to console in development
        console.error('Error caught by boundary:', error, errorInfo);

        // Call custom error handler if provided
        this.props.onError?.(error, errorInfo);

        // TODO: Log to error tracking service (Sentry)
        // if (typeof window !== 'undefined' && window.Sentry) {
        //   window.Sentry.captureException(error, { contexts: { react: errorInfo } });
        // }
    }

    handleReset = () => {
        this.setState({
            hasError: false,
            error: null,
        });
    };

    render() {
        if (this.state.hasError) {
            // Use custom fallback if provided
            if (this.props.fallback) {
                return this.props.fallback;
            }

            // Default fallback UI
            return (
                <div className="flex items-center justify-center min-h-[400px] p-8">
                    <div className="text-center space-y-4 max-w-md">
                        <div className="text-6xl">⚠️</div>
                        <h2 className="text-2xl font-bold text-foreground">Something went wrong</h2>
                        <p className="text-muted-foreground">
                            {this.state.error?.message || 'An unexpected error occurred'}
                        </p>
                        <button
                            onClick={this.handleReset}
                            className="px-4 py-2 bg-primary text-primary-foreground rounded-md hover:bg-primary/90 transition-colors"
                        >
                            Try again
                        </button>
                    </div>
                </div>
            );
        }

        return this.props.children;
    }
}
