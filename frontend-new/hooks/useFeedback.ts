'use client';

/**
 * Chat Feedback Hook
 * 
 * Provides functionality for submitting user feedback (thumbs up/down)
 * on AI chat responses.
 * 
 * Related Files:
 * - frontend-new/components/chat/FeedbackButtons.tsx (UI component)
 * - backend/api/v1/feedback.py (API endpoints)
 * - docs/ChatFeedback_Implementation_Spec.md (specification)
 * 
 * Usage:
 *   const { submitFeedback, isSubmitting, feedbackState } = useFeedback(conversationId);
 *   
 *   // Check if message has feedback
 *   const rating = feedbackState[messageId]; // 'positive' | 'negative' | undefined
 *   
 *   // Submit new feedback
 *   await submitFeedback({
 *     messageId: "...",
 *     rating: "negative",
 *     queryText: "User's question",
 *     answerPreview: "AI response preview...",
 *     sources: [...],
 *     feedbackText: "Optional comment"
 *   });
 */

import { useState, useCallback, useEffect } from 'react';
import { api } from '@/lib/api';
import { useToast } from '@/hooks/use-toast';

// =============================================================================
// Types
// =============================================================================

export type FeedbackRating = 'positive' | 'negative';

export interface SourceSnapshot {
    index?: number;
    type?: string;
    label?: string;
    url?: string;
    page?: number;
    section?: string;
}

export interface SubmitFeedbackParams {
    messageId: string;
    rating: FeedbackRating;
    queryText: string;
    answerPreview: string;
    sources: SourceSnapshot[];
    feedbackText?: string;
}

export interface FeedbackResponse {
    id: string;
    message_id: string;
    rating: FeedbackRating;
    created_at?: string;
    updated_at?: string;
    is_update: boolean;
}

export interface UseFeedbackReturn {
    /**
     * Submit feedback for a message.
     * Automatically updates local state on success.
     */
    submitFeedback: (params: SubmitFeedbackParams) => Promise<void>;
    
    /**
     * Whether a feedback submission is in progress.
     */
    isSubmitting: boolean;
    
    /**
     * Last error message (cleared on successful submit).
     */
    error: string | null;
    
    /**
     * Map of message_id -> rating for messages with feedback.
     * Use this to show the current feedback state in the UI.
     */
    feedbackState: Record<string, FeedbackRating>;
    
    /**
     * Manually refresh feedback state for the conversation.
     */
    refreshFeedback: () => Promise<void>;
}

// =============================================================================
// Hook Implementation
// =============================================================================

/**
 * Hook for managing chat feedback.
 * 
 * @param conversationId - ID of the current conversation (optional, for loading existing feedback)
 */
export function useFeedback(conversationId?: string): UseFeedbackReturn {
    const { toast } = useToast();
    
    // State
    const [isSubmitting, setIsSubmitting] = useState(false);
    const [error, setError] = useState<string | null>(null);
    const [feedbackState, setFeedbackState] = useState<Record<string, FeedbackRating>>({});
    
    /**
     * Fetch existing feedback for the conversation.
     */
    const refreshFeedback = useCallback(async () => {
        if (!conversationId) {
            return;
        }
        
        try {
            const response = await api.get(`/chat/feedback/conversation/${conversationId}`);
            const data = response.data as { feedback: Record<string, FeedbackRating> };
            setFeedbackState(data.feedback || {});
        } catch (err) {
            // Silently fail - feedback state is optional UI enhancement
            if (process.env.NODE_ENV !== 'production') {
                console.debug('[useFeedback] Failed to fetch feedback state:', err);
            }
        }
    }, [conversationId]);
    
    // Load existing feedback when conversation changes
    useEffect(() => {
        if (conversationId) {
            refreshFeedback();
        } else {
            // Clear state when no conversation
            setFeedbackState({});
        }
    }, [conversationId, refreshFeedback]);
    
    /**
     * Submit feedback for a message.
     */
    const submitFeedback = useCallback(async (params: SubmitFeedbackParams): Promise<void> => {
        const { messageId, rating, queryText, answerPreview, sources, feedbackText } = params;
        
        // Validate
        if (!messageId) {
            setError('Message ID is required');
            return;
        }
        
        if (!['positive', 'negative'].includes(rating)) {
            setError('Invalid rating');
            return;
        }

        // Skip if same rating already submitted for this message
        if (feedbackState[messageId] === rating) {
            return;
        }

        setIsSubmitting(true);
        setError(null);
        
        try {
            const response = await api.post('/chat/feedback', {
                message_id: messageId,
                rating,
                query_text: queryText || '',
                answer_preview: answerPreview?.slice(0, 500) || '',
                sources: sources.map(s => ({
                    index: s.index,
                    type: s.type,
                    label: s.label,
                    url: s.url,
                    page: s.page,
                    section: s.section,
                })),
                feedback_text: feedbackText?.slice(0, 100) || null,
            });
            
            const data = response.data as FeedbackResponse;
            
            // Update local state
            setFeedbackState(prev => ({
                ...prev,
                [messageId]: rating,
            }));
            
            // Show success feedback (subtle, no toast for positive to reduce noise)
            if (rating === 'negative' && feedbackText) {
                toast({
                    title: 'Feedback submitted',
                    description: 'Thank you for helping us improve.',
                    duration: 2000,
                });
            }
            
            // Log for debugging
            if (process.env.NODE_ENV !== 'production') {
                console.debug(
                    `[useFeedback] Submitted ${rating} feedback for message ${messageId.slice(0, 8)}...`,
                    data.is_update ? '(updated)' : '(new)'
                );
            }
            
        } catch (err) {
            const errorMessage = getErrorMessage(err);
            setError(errorMessage);
            
            toast({
                title: 'Failed to submit feedback',
                description: errorMessage,
                variant: 'destructive',
                duration: 4000,
            });
            
            if (process.env.NODE_ENV !== 'production') {
                console.error('[useFeedback] Submit failed:', err);
            }
        } finally {
            setIsSubmitting(false);
        }
    }, [toast, feedbackState]);
    
    return {
        submitFeedback,
        isSubmitting,
        error,
        feedbackState,
        refreshFeedback,
    };
}

// =============================================================================
// Helpers
// =============================================================================

type ApiError = {
    response?: {
        data?: {
            detail?: string | { message?: string };
        };
    };
    message?: string;
};

function getErrorMessage(error: unknown): string {
    const apiError = error as ApiError;
    
    const detail = apiError.response?.data?.detail;
    if (typeof detail === 'string') {
        return detail;
    }
    if (typeof detail === 'object' && detail?.message) {
        return detail.message;
    }
    if (apiError.message) {
        return apiError.message;
    }
    
    return 'Something went wrong. Please try again.';
}
