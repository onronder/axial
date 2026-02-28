
/**
 * ThinkingIndicator - Shows RAG processing status with animated steps
 * 
 * Displays what the system is doing during the RAG pipeline:
 * - Searching knowledge base
 * - Analyzing context
 * - Found relevant sources
 * - Generating response
 */

"use client";

import { useEffect, useState } from "react";
import { cn } from "@/lib/utils";
import { AxioLogo } from "@/components/branding/AxioLogo";
import { Search, FileSearch, CheckCircle2, Sparkles, Database, Brain } from "lucide-react";
import { Spinner } from "@/components/ui/spinner";

export interface ThinkingStatus {
    step: 'searching' | 'analyzing' | 'found' | 'generating' | 'complete';
    message: string;
    details?: {
        sourceCount?: number;
        scopeName?: string;
        model?: string;      // 'fast' or 'smart' - from backend
        isComplex?: boolean; // Whether query is complex
    };
}

interface ThinkingIndicatorProps {
    status: ThinkingStatus;
    className?: string;
}

/**
 * Step configuration with icons and colors
 */
const STEP_CONFIG = {
    searching: {
        icon: Search,
        color: 'text-blue-500',
        bgColor: 'bg-blue-500/10',
        borderColor: 'border-blue-500/20',
        label: 'Searching',
    },
    analyzing: {
        icon: Brain,
        color: 'text-purple-500',
        bgColor: 'bg-purple-500/10',
        borderColor: 'border-purple-500/20',
        label: 'Analyzing',
    },
    found: {
        icon: FileSearch,
        color: 'text-emerald-500',
        bgColor: 'bg-emerald-500/10',
        borderColor: 'border-emerald-500/20',
        label: 'Found',
    },
    generating: {
        icon: Sparkles,
        color: 'text-amber-500',
        bgColor: 'bg-amber-500/10',
        borderColor: 'border-amber-500/20',
        label: 'Generating',
    },
    complete: {
        icon: CheckCircle2,
        color: 'text-green-500',
        bgColor: 'bg-green-500/10',
        borderColor: 'border-green-500/20',
        label: 'Complete',
    },
};

/**
 * All steps in order for the progress visualization
 */
const STEPS_ORDER: ThinkingStatus['step'][] = ['searching', 'analyzing', 'found', 'generating'];

export function ThinkingIndicator({ status, className }: ThinkingIndicatorProps) {
    const [animatedDots, setAnimatedDots] = useState('');
    const [isTimedOut, setIsTimedOut] = useState(false);

    // Animate dots for active status
    useEffect(() => {
        if (status.step === 'complete') return;

        const interval = setInterval(() => {
            setAnimatedDots(prev => {
                if (prev.length >= 3) return '';
                return prev + '.';
            });
        }, 400);

        return () => clearInterval(interval);
    }, [status.step]);

    // Timeout fallback - if thinking for too long, show message
    useEffect(() => {
        if (status.step === 'complete' || status.step === 'generating') {
            setIsTimedOut(false);
            return;
        }

        setIsTimedOut(false);
        const timer = setTimeout(() => setIsTimedOut(true), 60000);
        return () => clearTimeout(timer);
    }, [status.step]);
    
    const currentStepIndex = STEPS_ORDER.indexOf(status.step);
    const config = STEP_CONFIG[status.step];
    const StepIcon = config.icon;
    
    return (
        <div className={cn("flex items-start gap-3 animate-fade-in", className)}>
            {/* Avatar */}
            <div className="flex h-8 w-8 shrink-0 items-center justify-center rounded-lg bg-muted border border-border">
                <AxioLogo variant="icon" size="sm" />
            </div>
            
            {/* Thinking Card */}
            <div className={cn(
                "flex-1 rounded-2xl border px-4 py-3 transition-all duration-300",
                config.bgColor,
                config.borderColor
            )}>
                {/* Current Status */}
                <div className="flex items-center gap-2 mb-3">
                    <div className={cn(
                        "flex items-center justify-center w-6 h-6 rounded-full",
                        config.bgColor
                    )}>
                        {status.step === 'complete' ? (
                            <StepIcon className={cn("h-4 w-4", config.color)} />
                        ) : (
                            <Spinner className={cn("h-4 w-4 animate-spin", config.color)} />
                        )}
                    </div>
                    <span className={cn("text-sm font-medium", config.color)}>
                        {status.message}{status.step !== 'complete' && animatedDots}
                    </span>
                </div>
                
                {/* Progress Steps */}
                <div className="flex items-center gap-1">
                    {STEPS_ORDER.map((step, index) => {
                        const stepConfig = STEP_CONFIG[step];
                        const Icon = stepConfig.icon;
                        const isActive = index === currentStepIndex;
                        const isCompleted = index < currentStepIndex;
                        const isPending = index > currentStepIndex;
                        
                        return (
                            <div key={step} className="flex items-center">
                                {/* Step indicator */}
                                <div className={cn(
                                    "flex items-center justify-center w-7 h-7 rounded-full border transition-all duration-300",
                                    isCompleted && "bg-primary/20 border-primary/40",
                                    isActive && cn(stepConfig.bgColor, stepConfig.borderColor, "ring-2 ring-offset-1 ring-offset-background", `ring-${stepConfig.color.replace('text-', '')}`),
                                    isPending && "bg-muted/50 border-border/50"
                                )}>
                                    {isCompleted ? (
                                        <CheckCircle2 className="h-4 w-4 text-primary" />
                                    ) : (
                                        <Icon className={cn(
                                            "h-3.5 w-3.5 transition-colors",
                                            isActive && stepConfig.color,
                                            isPending && "text-muted-foreground/50"
                                        )} />
                                    )}
                                </div>
                                
                                {/* Connector line */}
                                {index < STEPS_ORDER.length - 1 && (
                                    <div className={cn(
                                        "w-4 h-0.5 mx-0.5 transition-colors duration-300",
                                        isCompleted ? "bg-primary/40" : "bg-border/50"
                                    )} />
                                )}
                            </div>
                        );
                    })}
                </div>
                
                {/* Details (source count, scope name) */}
                {status.details && (status.details.sourceCount || status.details.scopeName) && (
                    <div className="mt-3 pt-2 border-t border-border/30">
                        <div className="flex items-center gap-3 text-xs text-muted-foreground">
                            {status.details.sourceCount && (
                                <div className="flex items-center gap-1">
                                    <Database className="h-3 w-3" />
                                    <span>{status.details.sourceCount} sources</span>
                                </div>
                            )}
                            {status.details.scopeName && (
                                <div className="flex items-center gap-1">
                                    <FileSearch className="h-3 w-3" />
                                    <span>from {status.details.scopeName}</span>
                                </div>
                            )}
                        </div>
                    </div>
                )}

                {/* Timeout fallback */}
                {isTimedOut && (
                    <div className="mt-3 pt-2 border-t border-border/30">
                        <p className="text-xs text-muted-foreground">
                            This is taking longer than expected. The response is still processing.
                        </p>
                    </div>
                )}
            </div>
        </div>
    );
}

/**
 * Simple typing indicator (bouncing dots) - used as fallback
 */
export function TypingIndicator({ className }: { className?: string }) {
    return (
        <div className={cn("flex items-start gap-3 animate-fade-in", className)}>
            <div className="flex h-8 w-8 shrink-0 items-center justify-center rounded-lg bg-muted border border-border">
                <AxioLogo variant="icon" size="sm" />
            </div>
            <div className="rounded-2xl bg-muted border border-border px-4 py-3">
                <div className="flex items-center gap-1.5">
                    <span className="h-2 w-2 rounded-full bg-primary animate-bounce" style={{ animationDelay: "0ms" }} />
                    <span className="h-2 w-2 rounded-full bg-primary animate-bounce" style={{ animationDelay: "150ms" }} />
                    <span className="h-2 w-2 rounded-full bg-primary animate-bounce" style={{ animationDelay: "300ms" }} />
                </div>
            </div>
        </div>
    );
}