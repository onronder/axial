/**
 * DLQ API Service
 * 
 * Frontend service for interacting with Dead Letter Queue API endpoints.
 */

import { createClient } from '@/lib/supabase/client';

export interface FailedTask {
    id: string;
    task_id: string;
    task_name: string;
    user_id: string;
    job_id: string | null;
    status: 'failed' | 'pending_retry' | 'retrying' | 'permanently_failed' | 'resolved';
    attempt_count: number;
    max_retries: number;
    next_retry_at: string | null;
    exception_type: string | null;
    exception_message: string | null;
    traceback: string | null;
    created_at: string;
    updated_at: string;
    resolved_at: string | null;
}

export interface DLQStats {
    total_failed: number;
    pending_retry: number;
    retrying: number;
    permanently_failed: number;
    resolved: number;
}

export interface ManualRetryResponse {
    success: boolean;
    message: string;
    task_id: string;
    new_status: string;
}

/**
 * Get failed task for a specific job
 */
export async function getFailedTaskForJob(jobId: string): Promise<FailedTask | null> {
    const supabase = createClient();

    const { data: { session } } = await supabase.auth.getSession();
    if (!session) {
        throw new Error('Not authenticated');
    }

    const response = await fetch(`/api/v1/dlq/failed-tasks/${jobId}`, {
        headers: {
            'Authorization': `Bearer ${session.access_token}`,
        },
    });

    if (!response.ok) {
        if (response.status === 404) {
            return null;
        }
        throw new Error('Failed to fetch failed task');
    }

    return response.json();
}

/**
 * Manually retry a failed task
 */
export async function manualRetryTask(
    taskId: string,
    reason?: string
): Promise<ManualRetryResponse> {
    const supabase = createClient();

    const { data: { session } } = await supabase.auth.getSession();
    if (!session) {
        throw new Error('Not authenticated');
    }

    const response = await fetch(`/api/v1/dlq/retry/${taskId}`, {
        method: 'POST',
        headers: {
            'Authorization': `Bearer ${session.access_token}`,
            'Content-Type': 'application/json',
        },
        body: JSON.stringify({ reason }),
    });

    if (!response.ok) {
        const error = await response.json();
        throw new Error(error.detail || 'Failed to retry task');
    }

    return response.json();
}

/**
 * Get DLQ statistics for current user
 */
export async function getDLQStats(): Promise<DLQStats> {
    const supabase = createClient();

    const { data: { session } } = await supabase.auth.getSession();
    if (!session) {
        throw new Error('Not authenticated');
    }

    const response = await fetch('/api/v1/dlq/stats', {
        headers: {
            'Authorization': `Bearer ${session.access_token}`,
        },
    });

    if (!response.ok) {
        throw new Error('Failed to fetch DLQ stats');
    }

    return response.json();
}

/**
 * Get all failed tasks for current user
 */
export async function getMyFailedTasks(
    page: number = 1,
    pageSize: number = 20,
    statusFilter?: string
): Promise<{
    tasks: FailedTask[];
    total: number;
    page: number;
    page_size: number;
}> {
    const supabase = createClient();

    const { data: { session } } = await supabase.auth.getSession();
    if (!session) {
        throw new Error('Not authenticated');
    }

    const params = new URLSearchParams({
        page: page.toString(),
        page_size: pageSize.toString(),
    });

    if (statusFilter) {
        params.append('status_filter', statusFilter);
    }

    const response = await fetch(`/api/v1/dlq/my-tasks?${params}`, {
        headers: {
            'Authorization': `Bearer ${session.access_token}`,
        },
    });

    if (!response.ok) {
        throw new Error('Failed to fetch failed tasks');
    }

    return response.json();
}
