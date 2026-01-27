
'use client';

/**
 * Feedback Buttons Component
 * 
 * Provides thumbs up/down rating buttons for AI chat responses.
 * Shows optional comment input modal for negative feedback.
 * 
 * Related Files:
 * - frontend-new/hooks/useFeedback.ts (data hook)
 * - frontend-new/components/chat/MessageBubble.tsx (parent component)
 * - backend/api/v1/feedback.py (API endpoints)
 * 
 * States:
 * - default: Both buttons shown, neither selected
 * - positive: Thumbs up highlighted (green)
 * - negative: Thumbs down highlighted (red), shows thank you or comment modal
 * - submitting: Buttons disabled, loading state
 */

import { useState, useCallback, useEffect } from 'react';
import { ThumbsUp, ThumbsDown, Check } from "lucide-react";
import { Spinner } from "@/components/ui/spinner";

import { cn } from '@/lib/utils';
import { Button } from '@/components/ui/button';
import {
    Dialog,
    DialogContent,
    DialogDescription,
    DialogFooter,
    DialogHeader,
    DialogTitle,
} from '@/components/ui/dialog';
import { Textarea } from '@/components/ui/textarea';
import { type SourceSnapshot, type FeedbackRating } from '@/hooks/useFeedback';

// =============================================================================
// Types
// =============================================================================

export interface FeedbackButtonsProps {
    /** UUID of the message being rated */
    messageId: string;
    
    /** Sources cited in the response */
    sources: SourceSnapshot[];
    
    /** The user's original question (from previous message) */
    queryText: string;
    
    /** First 500 chars of AI response */
    answerPreview: string;
    
    /** Current feedback state for this message */
    currentRating?: FeedbackRating;
    
    /** Callback when feedback is submitted */
    onSubmit: (
        messageId: string,
        rating: FeedbackRating,
        feedbackText?: string
    ) => Promise<void>;
    
    /** Whether submission is in progress */
    isSubmitting?: boolean;
    
    /** Disable buttons (e.g., during streaming) */
    disabled?: boolean;
    
    /** Additional class names */
    className?: string;
}

// =============================================================================
// Component
// =============================================================================

export function FeedbackButtons({
    messageId,
    sources: _sources,      // Passed for type safety, used by parent for context
    queryText: _queryText,  // Passed for type safety, used by parent for context
    answerPreview: _answerPreview, // Passed for type safety, used by parent for context
    currentRating,
    onSubmit,
    isSubmitting = false,
    disabled = false,
    className,
}: FeedbackButtonsProps) {
    // These props are intentionally passed but unused in this component.
    // They exist in the interface so the parent can provide full context.
    void _sources;
    void _queryText;
    void _answerPreview;
    // Local state
    const [showCommentModal, setShowCommentModal] = useState(false);
    const [comment, setComment] = useState('');
    const [showThankYou, setShowThankYou] = useState(false);
    const [localRating, setLocalRating] = useState<FeedbackRating | undefined>(currentRating);
    
    // Sync with prop changes
    useEffect(() => {
        setLocalRating(currentRating);
    }, [currentRating]);
    
    // Reset thank you state after delay
    useEffect(() => {
        if (showThankYou) {
            const timer = setTimeout(() => setShowThankYou(false), 2000);
            return () => clearTimeout(timer);
        }
    }, [showThankYou]);
    
    /**
     * Handle positive feedback (thumbs up).
     * Submits immediately without comment.
     */
    const handlePositive = useCallback(async () => {
        if (disabled || isSubmitting) return;
        
        // If already positive, do nothing (or could toggle off)
        if (localRating === 'positive') return;
        
        setLocalRating('positive');
        setShowThankYou(true);
        
        try {
            await onSubmit(messageId, 'positive');
        } catch {
            // Revert on error
            setLocalRating(currentRating);
            setShowThankYou(false);
        }
    }, [disabled, isSubmitting, localRating, currentRating, messageId, onSubmit]);
    
    /**
     * Handle negative feedback (thumbs down).
     * Opens comment modal for optional feedback.
     */
    const handleNegative = useCallback(() => {
        if (disabled || isSubmitting) return;
        
        // If already negative, allow changing comment via modal
        setShowCommentModal(true);
    }, [disabled, isSubmitting]);
    
    /**
     * Submit negative feedback with optional comment.
     */
    const submitNegativeFeedback = useCallback(async () => {
        setShowCommentModal(false);
        setLocalRating('negative');
        setShowThankYou(true);
        
        try {
            await onSubmit(messageId, 'negative', comment.trim() || undefined);
            setComment(''); // Clear for next time
        } catch {
            // Revert on error
            setLocalRating(currentRating);
            setShowThankYou(false);
        }
    }, [messageId, comment, currentRating, onSubmit]);
    
    /**
     * Close modal without submitting.
     */
    const cancelNegativeFeedback = useCallback(() => {
        setShowCommentModal(false);
        setComment('');
    }, []);
    
    // Determine button states
    const isPositiveSelected = localRating === 'positive';
    const isNegativeSelected = localRating === 'negative';
    const hasRating = localRating !== undefined;
    
    return (
        <>
            {/* Feedback Buttons */}
            <div 
                className={cn(
                    "flex items-center gap-1 mt-2",
                    className
                )}
            >
                {/* Thank you message (briefly shown after feedback) */}
                {showThankYou && (
                    <span className="text-xs text-muted-foreground flex items-center gap-1 mr-2 animate-fade-in">
                        <Check className="h-3 w-3 text-green-500" />
                        Thanks!
                    </span>
                )}
                
                {/* Thumbs Up Button */}
                <Button
                    variant="ghost"
                    size="sm"
                    className={cn(
                        "h-7 w-7 p-0 rounded-full transition-all",
                        isPositiveSelected 
                            ? "bg-green-100 dark:bg-green-900/30 text-green-600 dark:text-green-400" 
                            : "text-muted-foreground hover:text-foreground hover:bg-muted",
                        hasRating && !isPositiveSelected && "opacity-40",
                        (disabled || isSubmitting) && "cursor-not-allowed opacity-50"
                    )}
                    onClick={handlePositive}
                    disabled={disabled || isSubmitting}
                    title={isPositiveSelected ? "Marked as helpful" : "Mark as helpful"}
                >
                    {isSubmitting && isPositiveSelected ? (
                        <Spinner className="h-3.5 w-3.5 animate-spin" />
                    ) : (
                        <ThumbsUp className={cn(
                            "h-3.5 w-3.5",
                            isPositiveSelected && "fill-current"
                        )} />
                    )}
                </Button>
                
                {/* Thumbs Down Button */}
                <Button
                    variant="ghost"
                    size="sm"
                    className={cn(
                        "h-7 w-7 p-0 rounded-full transition-all",
                        isNegativeSelected 
                            ? "bg-red-100 dark:bg-red-900/30 text-red-600 dark:text-red-400" 
                            : "text-muted-foreground hover:text-foreground hover:bg-muted",
                        hasRating && !isNegativeSelected && "opacity-40",
                        (disabled || isSubmitting) && "cursor-not-allowed opacity-50"
                    )}
                    onClick={handleNegative}
                    disabled={disabled || isSubmitting}
                    title={isNegativeSelected ? "Marked as not helpful" : "Mark as not helpful"}
                >
                    {isSubmitting && isNegativeSelected ? (
                        <Spinner className="h-3.5 w-3.5 animate-spin" />
                    ) : (
                        <ThumbsDown className={cn(
                            "h-3.5 w-3.5",
                            isNegativeSelected && "fill-current"
                        )} />
                    )}
                </Button>
            </div>
            
            {/* Comment Modal for Negative Feedback */}
            <Dialog open={showCommentModal} onOpenChange={setShowCommentModal}>
                <DialogContent className="sm:max-w-[425px]">
                    <DialogHeader>
                        <DialogTitle>Help us improve</DialogTitle>
                        <DialogDescription>
                            What was wrong with this response? Your feedback helps us improve our AI.
                        </DialogDescription>
                    </DialogHeader>
                    
                    <div className="grid gap-4 py-4">
                        <Textarea
                            placeholder="Optional: Tell us what went wrong (max 100 characters)"
                            value={comment}
                            onChange={(e) => setComment(e.target.value.slice(0, 100))}
                            maxLength={100}
                            rows={3}
                            className="resize-none"
                        />
                        <p className="text-xs text-muted-foreground text-right">
                            {comment.length}/100
                        </p>
                    </div>
                    
                    <DialogFooter>
                        <Button
                            variant="outline"
                            onClick={cancelNegativeFeedback}
                        >
                            Cancel
                        </Button>
                        <Button
                            onClick={submitNegativeFeedback}
                            disabled={isSubmitting}
                        >
                            {isSubmitting ? (
                                <>
                                    <Spinner className="mr-2 h-4 w-4 animate-spin" />
                                    Submitting...
                                </>
                            ) : (
                                'Submit Feedback'
                            )}
                        </Button>
                    </DialogFooter>
                </DialogContent>
            </Dialog>
        </>
    );
}
