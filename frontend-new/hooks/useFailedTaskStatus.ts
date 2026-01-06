/**
 * Frontend hook for tracking failed task status and retry information.
 * 
 * Provides realtime updates on task failures, retry schedules, and permanent failures.
 */

import { useState, useEffect } from 'react';
import { createClient } from '@/lib/supabase/client';

export interface FailedTask {
    id: string;
    task_id: string;
    task_name: string;
    user_id: string;
    job_id: string;
    status: 'failed' | 'pending_retry' | 'retrying' | 'permanently_failed' | 'resolved';
    attempt_count: number;
    max_retries: number;
    next_retry_at: string | null;
    exception_type: string;
    exception_message: string;
    traceback: string;
    created_at: string;
    updated_at: string;
    resolved_at: string | null;
}

export function useFailedTaskStatus(jobId: string | null) {
    const [failedTask, setFailedTask] = useState<FailedTask | null>(null);
    const [loading, setLoading] = useState(true);
    const [error, setError] = useState<Error | null>(null);

    useEffect(() => {
        if (!jobId) {
            setLoading(false);
            return;
        }

        const supabase = createClient();

        // Initial fetch
        const fetchFailedTask = async () => {
            try {
                const { data, error: fetchError } = await supabase
                    .from('failed_tasks')
                    .select('*')
                    .eq('job_id', jobId)
                    .order('created_at', { ascending: false })
                    .limit(1)
                    .maybeSingle();

                if (fetchError) throw fetchError;

                setFailedTask(data);
                setLoading(false);
            } catch (err) {
                console.error('Error fetching failed task:', err);
                setError(err as Error);
                setLoading(false);
            }
        };

        fetchFailedTask();

        // Subscribe to realtime updates
        const channel = supabase
            .channel(`failed-task-${jobId}`)
            .on(
                'postgres_changes',
                {
                    event: '*',
                    schema: 'public',
                    table: 'failed_tasks',
                    filter: `job_id=eq.${jobId}`
                },
                (payload: { eventType: string; new?: FailedTask; old?: Partial<FailedTask> }) => {
                    console.log('🔔 Failed task update:', payload);

                    if (payload.eventType === 'INSERT' || payload.eventType === 'UPDATE') {
                        if (payload.new) setFailedTask(payload.new);
                    } else if (payload.eventType === 'DELETE') {
                        setFailedTask(null);
                    }
                }
            )
            .subscribe((status: string) => {
                if (status === 'SUBSCRIBED') {
                    console.log('✅ Subscribed to failed task updates for job:', jobId);
                }
            });

        // ✅ CLEANUP - Prevent memory leaks
        return () => {
            channel.unsubscribe();
            supabase.removeChannel(channel);
        };
    }, [jobId]);

    return { failedTask, loading, error };
}

/**
 * Calculate time until retry in human-readable format
 */
export function getTimeUntilRetry(nextRetryAt: string | null): string {
    if (!nextRetryAt) return '';

    const now = new Date();
    const retryTime = new Date(nextRetryAt);
    const diffMs = retryTime.getTime() - now.getTime();

    if (diffMs <= 0) return 'retrying now';

    const diffMinutes = Math.floor(diffMs / 60000);
    const diffHours = Math.floor(diffMinutes / 60);

    if (diffHours > 0) {
        const remainingMinutes = diffMinutes % 60;
        return `${diffHours}h ${remainingMinutes}m`;
    }

    return `${diffMinutes}m`;
}

/**
 * Format retry time as readable date
 */
export function formatRetryTime(nextRetryAt: string | null): string {
    if (!nextRetryAt) return '';

    const retryTime = new Date(nextRetryAt);
    return retryTime.toLocaleString('en-US', {
        month: 'short',
        day: 'numeric',
        hour: '2-digit',
        minute: '2-digit'
    });
}
