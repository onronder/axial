/**
 * DLQ API Service
 *
 * Frontend service for interacting with Dead Letter Queue API endpoints.
 * Uses the axios api client for consistent auth handling and error formatting.
 */

import { api } from '@/lib/api';
import { AxiosError } from 'axios';

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
    try {
        const response = await api.get<FailedTask>(`/dlq/failed-tasks/${jobId}`);
        return response.data;
    } catch (error) {
        if (error instanceof AxiosError && error.response?.status === 404) {
            return null;
        }
        throw error;
    }
}

/**
 * Manually retry a failed task
 */
export async function manualRetryTask(
    taskId: string,
    reason?: string
): Promise<ManualRetryResponse> {
    const response = await api.post<ManualRetryResponse>(`/dlq/retry/${taskId}`, { reason });
    return response.data;
}

/**
 * Get DLQ statistics for current user
 */
export async function getDLQStats(): Promise<DLQStats> {
    const response = await api.get<DLQStats>('/dlq/stats');
    return response.data;
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
    const params = new URLSearchParams({
        page: page.toString(),
        page_size: pageSize.toString(),
    });

    if (statusFilter) {
        params.append('status_filter', statusFilter);
    }

    const response = await api.get(`/dlq/my-tasks?${params}`);
    return response.data;
}
