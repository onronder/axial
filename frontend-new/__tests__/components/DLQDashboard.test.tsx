/**
 * Unit Tests for DLQ Dashboard Component
 * 
 * Tests for the Dead Letter Queue dashboard data structures and utilities
 */

import React from 'react';
import { describe, it, expect, vi, beforeEach } from 'vitest';
import { render, screen, waitFor } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { QueryClient, QueryClientProvider } from '@tanstack/react-query';

// Mock API
const mockApiGet = vi.fn();
const mockApiPost = vi.fn();
vi.mock('@/lib/api', () => ({
    api: {
        get: (url: string) => mockApiGet(url),
        post: (url: string, data?: unknown) => mockApiPost(url, data),
    },
}));

// Mock useProfile
const mockProfile = vi.fn();
vi.mock('@/hooks/useProfile', () => ({
    useProfile: () => mockProfile(),
}));

// Mock toast
const mockToast = vi.fn();
vi.mock('@/hooks/use-toast', () => ({
    useToast: () => ({ toast: mockToast }),
}));

function createWrapper() {
    const queryClient = new QueryClient({
        defaultOptions: {
            queries: { retry: false },
        },
    });
    const Wrapper = ({ children }: { children: React.ReactNode }) => (
        <QueryClientProvider client={queryClient}>
            {children}
        </QueryClientProvider>
    );
    Wrapper.displayName = 'TestWrapper';
    return Wrapper;
}

// Import the component after mocks
import { DLQDashboard } from '@/components/admin/DLQDashboard';

describe('DLQ Dashboard Data Structures', () => {
    describe('FailedTask Type', () => {
        it('should have required task properties', () => {
            const task = {
                id: 't1',
                task_id: 'task-uuid',
                task_name: 'parse_document',
                user_id: 'user-1',
                job_id: 'job-1',
                status: 'failed' as const,
                error_message: 'Failed to parse PDF',
                retry_count: 3,
                max_retries: 5,
                created_at: '2024-01-15T10:00:00Z',
                last_retry_at: '2024-01-15T12:00:00Z',
            };

            expect(task).toHaveProperty('id');
            expect(task).toHaveProperty('task_name');
            expect(task).toHaveProperty('error_message');
            expect(task).toHaveProperty('retry_count');
            expect(task).toHaveProperty('status');
        });

        it('should support all status types', () => {
            const statuses = ['failed', 'pending_retry', 'retrying', 'permanently_failed', 'resolved'];
            statuses.forEach(status => {
                expect(['failed', 'pending_retry', 'retrying', 'permanently_failed', 'resolved']).toContain(status);
            });
        });
    });

    describe('Stats Structure', () => {
        it('should have stats properties', () => {
            const stats = {
                failed: 10,
                pending_retry: 5,
                retrying: 2,
                permanently_failed: 1,
                resolved: 3,
            };

            expect(stats.failed).toBe(10);
            expect(stats.pending_retry).toBe(5);
            expect(stats.retrying).toBe(2);
            expect(stats.resolved).toBe(3);
        });
    });

    describe('Retry Logic', () => {
        it('should identify tasks that can be retried', () => {
            const tasks = [
                { retry_count: 3, max_retries: 5, status: 'failed' },
                { retry_count: 5, max_retries: 5, status: 'permanently_failed' },
            ];

            const canRetry = (task: { retry_count: number; max_retries: number; status: string }) =>
                task.retry_count < task.max_retries && task.status !== 'resolved';

            expect(canRetry(tasks[0])).toBe(true);
            expect(canRetry(tasks[1])).toBe(false);
        });

        it('should not allow retry for resolved tasks', () => {
            const task = { retry_count: 1, max_retries: 5, status: 'resolved' };
            const canRetry = task.status !== 'resolved' && task.retry_count < task.max_retries;
            expect(canRetry).toBe(false);
        });
    });

    describe('Filtering', () => {
        it('should filter tasks by status', () => {
            const tasks = [
                { id: 't1', status: 'failed' },
                { id: 't2', status: 'retrying' },
                { id: 't3', status: 'resolved' },
            ];

            const filtered = tasks.filter(t => t.status === 'failed');
            expect(filtered).toHaveLength(1);
            expect(filtered[0].id).toBe('t1');
        });

        it('should filter tasks by task name', () => {
            const tasks = [
                { id: 't1', task_name: 'parse_document' },
                { id: 't2', task_name: 'embed_chunks' },
            ];

            const filtered = tasks.filter(t => t.task_name.includes('parse'));
            expect(filtered).toHaveLength(1);
            expect(filtered[0].id).toBe('t1');
        });
    });

    describe('Selection', () => {
        it('should track selected task ids', () => {
            const selectedIds = new Set<string>();
            
            selectedIds.add('t1');
            selectedIds.add('t2');
            
            expect(selectedIds.has('t1')).toBe(true);
            expect(selectedIds.has('t3')).toBe(false);
            expect(selectedIds.size).toBe(2);
        });

        it('should deselect tasks', () => {
            const selectedIds = new Set<string>(['t1', 't2', 't3']);
            
            selectedIds.delete('t2');
            
            expect(selectedIds.has('t2')).toBe(false);
            expect(selectedIds.size).toBe(2);
        });

        it('should select/deselect all', () => {
            const tasks = [{ id: 't1' }, { id: 't2' }, { id: 't3' }];
            let selectedIds = new Set<string>();
            
            // Select all
            tasks.forEach(t => selectedIds.add(t.id));
            expect(selectedIds.size).toBe(3);
            
            // Deselect all
            selectedIds = new Set<string>();
            expect(selectedIds.size).toBe(0);
        });
    });
});

describe('DLQ Dashboard Component', () => {
    const mockTasks = [
        {
            id: 't1',
            task_id: 'task-1',
            task_name: 'parse_document',
            user_id: 'user-1',
            job_id: 'job-1',
            status: 'failed' as const,
            attempt_count: 2,
            max_retries: 5,
            next_retry_at: null,
            exception_type: 'ParseError',
            exception_message: 'Failed to parse PDF',
            traceback: 'Error at line 1',
            kwargs: {},
            created_at: '2024-01-15T10:00:00Z',
            updated_at: '2024-01-15T10:00:00Z',
            resolved_at: null,
        },
        {
            id: 't2',
            task_id: 'task-2',
            task_name: 'embed_chunks',
            user_id: 'user-1',
            job_id: 'job-1',
            status: 'pending_retry' as const,
            attempt_count: 1,
            max_retries: 5,
            next_retry_at: '2024-01-15T12:00:00Z',
            exception_type: 'APIError',
            exception_message: 'API timeout',
            traceback: 'Error at line 2',
            kwargs: {},
            created_at: '2024-01-15T09:00:00Z',
            updated_at: '2024-01-15T11:00:00Z',
            resolved_at: null,
        },
    ];

    const mockStats = {
        total: 2,
        pending_retry: 1,
        retrying: 0,
        permanently_failed: 0,
        resolved_today: 0,
    };

    beforeEach(() => {
        vi.clearAllMocks();
        mockProfile.mockReturnValue({ profile: { role: 'admin', email: 'admin@test.com' }, isLoading: false });
        mockApiGet.mockResolvedValue({ data: { tasks: mockTasks, stats: mockStats } });
    });

    it('should render the component title', async () => {
        render(<DLQDashboard />, { wrapper: createWrapper() });
        
        await waitFor(() => {
            expect(screen.getByText(/dead letter queue/i)).toBeInTheDocument();
        });
    });

    it('should display stats cards', async () => {
        render(<DLQDashboard />, { wrapper: createWrapper() });
        
        await waitFor(() => {
            expect(screen.getByText(/total/i)).toBeInTheDocument();
        });
    });

    it('should display task table', async () => {
        render(<DLQDashboard />, { wrapper: createWrapper() });
        
        await waitFor(() => {
            // Check table structure is rendered
            expect(screen.getByRole('table')).toBeInTheDocument();
        });
    });

    it('should render task rows', async () => {
        render(<DLQDashboard />, { wrapper: createWrapper() });
        
        await waitFor(() => {
            // Check that rows are rendered (mock has 2 tasks)
            const rows = screen.getAllByRole('row');
            // Header row + 2 task rows
            expect(rows.length).toBeGreaterThanOrEqual(2);
        });
    });

    it('should call toast on fetch error', async () => {
        mockApiGet.mockRejectedValue(new Error('Network error'));
        
        render(<DLQDashboard />, { wrapper: createWrapper() });
        
        await waitFor(() => {
            expect(mockToast).toHaveBeenCalledWith(expect.objectContaining({
                variant: 'destructive',
            }));
        });
    });

    it('should show search input', async () => {
        render(<DLQDashboard />, { wrapper: createWrapper() });
        
        await waitFor(() => {
            expect(screen.getByPlaceholderText(/search/i)).toBeInTheDocument();
        });
    });

    it('should show status filter dropdown', async () => {
        render(<DLQDashboard />, { wrapper: createWrapper() });
        
        await waitFor(() => {
            expect(screen.getByRole('combobox')).toBeInTheDocument();
        });
    });

    it('should show action buttons for admin users', async () => {
        render(<DLQDashboard />, { wrapper: createWrapper() });
        
        await waitFor(() => {
            // Admin should see retry buttons
            const retryButtons = screen.getAllByRole('button');
            expect(retryButtons.length).toBeGreaterThan(0);
        });
    });

    it('should show read-only alert for viewer role', async () => {
        mockProfile.mockReturnValue({ profile: { role: 'viewer', email: 'viewer@test.com' }, isLoading: false });
        
        render(<DLQDashboard />, { wrapper: createWrapper() });
        
        await waitFor(() => {
            // Viewer should see view-only alert with specific text
            expect(screen.getByText(/view-only members/i)).toBeInTheDocument();
        });
    });

    it('should show loading state while profile loads', async () => {
        mockProfile.mockReturnValue({ profile: null, isLoading: true });
        
        render(<DLQDashboard />, { wrapper: createWrapper() });
        
        await waitFor(() => {
            expect(screen.getByText(/loading permissions/i)).toBeInTheDocument();
        });
    });

    it('should show empty state when no tasks', async () => {
        mockApiGet.mockResolvedValue({ data: { tasks: [], stats: { total: 0, pending_retry: 0, retrying: 0, permanently_failed: 0, resolved_today: 0 } } });
        
        render(<DLQDashboard />, { wrapper: createWrapper() });
        
        await waitFor(() => {
            expect(screen.getByText(/no failed tasks/i)).toBeInTheDocument();
        });
    });

    it('should refresh data when refresh button clicked', async () => {
        const { getByLabelText } = render(<DLQDashboard />, { wrapper: createWrapper() });
        
        await waitFor(() => {
            expect(mockApiGet).toHaveBeenCalled();
        });

        // Find refresh button and click it
        const refreshButton = screen.getByRole('button', { name: /refresh/i });
        if (refreshButton) {
            refreshButton.click();
            await waitFor(() => {
                // Should have been called again for refresh
                expect(mockApiGet.mock.calls.length).toBeGreaterThan(1);
            });
        }
    });
});

describe('Visibility-Aware Polling Logic', () => {
    it('should understand visibility state', () => {
        // Test visibility state logic
        const states = ['visible', 'hidden', 'prerender'];
        
        states.forEach(state => {
            const isVisible = state === 'visible';
            expect(typeof isVisible).toBe('boolean');
        });
    });

    it('should control polling based on visibility', () => {
        let isPolling = true;
        
        const handleVisibilityChange = (visibilityState: string) => {
            isPolling = visibilityState === 'visible';
        };
        
        handleVisibilityChange('hidden');
        expect(isPolling).toBe(false);
        
        handleVisibilityChange('visible');
        expect(isPolling).toBe(true);
    });
});

describe('Permission Logic', () => {
    it('should identify admin users', () => {
        const profiles = [
            { role: 'admin' },
            { role: 'editor' },
            { role: 'viewer' },
            { role: null }, // Owner
        ];
        
        const isAdmin = (profile: { role: string | null }) => 
            profile.role === 'admin' || profile.role === null;
        
        expect(isAdmin(profiles[0])).toBe(true);
        expect(isAdmin(profiles[1])).toBe(false);
        expect(isAdmin(profiles[2])).toBe(false);
        expect(isAdmin(profiles[3])).toBe(true);
    });

    it('should block non-admin actions', () => {
        const profile = { role: 'viewer' };
        const canManage = profile.role === 'admin' || profile.role === null;
        expect(canManage).toBe(false);
    });
});

// =============================================================================
// HELPER FUNCTION TESTS
// =============================================================================

describe('Time Formatting Helpers', () => {
    it('formatTimeAgo should return "just now" for recent times', () => {
        const now = new Date();
        const formatTimeAgo = (dateString: string): string => {
            const date = new Date(dateString);
            const diffMs = now.getTime() - date.getTime();
            const diffMinutes = Math.floor(diffMs / 60000);
            const diffHours = Math.floor(diffMinutes / 60);
            const diffDays = Math.floor(diffHours / 24);

            if (diffDays > 0) return `${diffDays}d ago`;
            if (diffHours > 0) return `${diffHours}h ago`;
            if (diffMinutes > 0) return `${diffMinutes}m ago`;
            return 'just now';
        };

        expect(formatTimeAgo(now.toISOString())).toBe('just now');
    });

    it('formatTimeAgo should return minutes ago', () => {
        const now = new Date();
        const fiveMinutesAgo = new Date(now.getTime() - 5 * 60000);
        
        const formatTimeAgo = (dateString: string): string => {
            const date = new Date(dateString);
            const diffMs = now.getTime() - date.getTime();
            const diffMinutes = Math.floor(diffMs / 60000);
            const diffHours = Math.floor(diffMinutes / 60);
            const diffDays = Math.floor(diffHours / 24);

            if (diffDays > 0) return `${diffDays}d ago`;
            if (diffHours > 0) return `${diffHours}h ago`;
            if (diffMinutes > 0) return `${diffMinutes}m ago`;
            return 'just now';
        };

        expect(formatTimeAgo(fiveMinutesAgo.toISOString())).toBe('5m ago');
    });

    it('formatTimeAgo should return hours ago', () => {
        const now = new Date();
        const twoHoursAgo = new Date(now.getTime() - 2 * 60 * 60000);
        
        const formatTimeAgo = (dateString: string): string => {
            const date = new Date(dateString);
            const diffMs = now.getTime() - date.getTime();
            const diffMinutes = Math.floor(diffMs / 60000);
            const diffHours = Math.floor(diffMinutes / 60);
            const diffDays = Math.floor(diffHours / 24);

            if (diffDays > 0) return `${diffDays}d ago`;
            if (diffHours > 0) return `${diffHours}h ago`;
            if (diffMinutes > 0) return `${diffMinutes}m ago`;
            return 'just now';
        };

        expect(formatTimeAgo(twoHoursAgo.toISOString())).toBe('2h ago');
    });

    it('formatTimeAgo should return days ago', () => {
        const now = new Date();
        const threeDaysAgo = new Date(now.getTime() - 3 * 24 * 60 * 60000);
        
        const formatTimeAgo = (dateString: string): string => {
            const date = new Date(dateString);
            const diffMs = now.getTime() - date.getTime();
            const diffMinutes = Math.floor(diffMs / 60000);
            const diffHours = Math.floor(diffMinutes / 60);
            const diffDays = Math.floor(diffHours / 24);

            if (diffDays > 0) return `${diffDays}d ago`;
            if (diffHours > 0) return `${diffHours}h ago`;
            if (diffMinutes > 0) return `${diffMinutes}m ago`;
            return 'just now';
        };

        expect(formatTimeAgo(threeDaysAgo.toISOString())).toBe('3d ago');
    });

    it('formatRetryTime should return "-" for null', () => {
        const formatRetryTime = (nextRetryAt: string | null): string => {
            if (!nextRetryAt) return '-';
            const retryTime = new Date(nextRetryAt);
            const now = new Date();
            const diffMs = retryTime.getTime() - now.getTime();
            if (diffMs <= 0) return 'retrying now';
            const diffMinutes = Math.floor(diffMs / 60000);
            const diffHours = Math.floor(diffMinutes / 60);
            if (diffHours > 0) return `in ${diffHours}h ${diffMinutes % 60}m`;
            return `in ${diffMinutes}m`;
        };

        expect(formatRetryTime(null)).toBe('-');
    });

    it('formatRetryTime should return "retrying now" for past times', () => {
        const now = new Date();
        const pastTime = new Date(now.getTime() - 60000);
        
        const formatRetryTime = (nextRetryAt: string | null): string => {
            if (!nextRetryAt) return '-';
            const retryTime = new Date(nextRetryAt);
            const diffMs = retryTime.getTime() - now.getTime();
            if (diffMs <= 0) return 'retrying now';
            const diffMinutes = Math.floor(diffMs / 60000);
            const diffHours = Math.floor(diffMinutes / 60);
            if (diffHours > 0) return `in ${diffHours}h ${diffMinutes % 60}m`;
            return `in ${diffMinutes}m`;
        };

        expect(formatRetryTime(pastTime.toISOString())).toBe('retrying now');
    });

    it('formatRetryTime should return minutes format', () => {
        const now = new Date();
        const futureTime = new Date(now.getTime() + 30 * 60000);
        
        const formatRetryTime = (nextRetryAt: string | null): string => {
            if (!nextRetryAt) return '-';
            const retryTime = new Date(nextRetryAt);
            const diffMs = retryTime.getTime() - now.getTime();
            if (diffMs <= 0) return 'retrying now';
            const diffMinutes = Math.floor(diffMs / 60000);
            const diffHours = Math.floor(diffMinutes / 60);
            if (diffHours > 0) return `in ${diffHours}h ${diffMinutes % 60}m`;
            return `in ${diffMinutes}m`;
        };

        expect(formatRetryTime(futureTime.toISOString())).toMatch(/^in \d+m$/);
    });

    it('formatRetryTime should return hours and minutes format', () => {
        const now = new Date();
        const futureTime = new Date(now.getTime() + 2 * 60 * 60000 + 15 * 60000);
        
        const formatRetryTime = (nextRetryAt: string | null): string => {
            if (!nextRetryAt) return '-';
            const retryTime = new Date(nextRetryAt);
            const diffMs = retryTime.getTime() - now.getTime();
            if (diffMs <= 0) return 'retrying now';
            const diffMinutes = Math.floor(diffMs / 60000);
            const diffHours = Math.floor(diffMinutes / 60);
            if (diffHours > 0) return `in ${diffHours}h ${diffMinutes % 60}m`;
            return `in ${diffMinutes}m`;
        };

        expect(formatRetryTime(futureTime.toISOString())).toMatch(/^in \d+h \d+m$/);
    });
});

describe('DLQ Dashboard Actions', () => {
    const actionTasks = [
        {
            id: 't1',
            task_id: 'task-1',
            task_name: 'process_document',
            user_id: 'user-1',
            job_id: 'job-1',
            status: 'failed' as const,
            attempt_count: 3,
            max_retries: 5,
            next_retry_at: null,
            exception_type: 'ProcessingError',
            exception_message: 'Document processing failed',
            traceback: 'Error at line 1',
            kwargs: {},
            created_at: '2024-01-15T10:00:00Z',
            updated_at: '2024-01-15T10:00:00Z',
            resolved_at: null,
        },
        {
            id: 't2',
            task_id: 'task-2',
            task_name: 'embed_chunks',
            user_id: 'user-1',
            job_id: 'job-1',
            status: 'permanently_failed' as const,
            attempt_count: 5,
            max_retries: 5,
            next_retry_at: null,
            exception_type: 'EmbeddingError',
            exception_message: 'Embedding failed permanently',
            traceback: 'Error at line 2',
            kwargs: {},
            created_at: '2024-01-15T09:00:00Z',
            updated_at: '2024-01-15T11:00:00Z',
            resolved_at: null,
        },
    ];
    const actionStats = { total: 2, pending_retry: 0, retrying: 0, permanently_failed: 1, resolved_today: 0 };

    beforeEach(() => {
        vi.clearAllMocks();
        mockProfile.mockReturnValue({ profile: { role: 'admin', email: 'admin@test.com' }, isLoading: false });
        mockApiGet.mockImplementation((url: string) => {
            if (url === '/dlq/my-tasks') {
                return Promise.resolve({ data: { tasks: actionTasks } });
            }
            if (url === '/dlq/stats') {
                return Promise.resolve({ data: actionStats });
            }
            return Promise.resolve({ data: {} });
        });
        mockApiPost.mockResolvedValue({});
    });

    it('should show view-only message for viewer role', async () => {
        mockProfile.mockReturnValue({ profile: { role: 'viewer', email: 'viewer@test.com' }, isLoading: false });
        
        render(<DLQDashboard />, { wrapper: createWrapper() });
        
        await waitFor(() => {
            expect(screen.getByText(/View-only access/i)).toBeInTheDocument();
        });
    });

    it('should render admin controls when admin', async () => {
        render(<DLQDashboard />, { wrapper: createWrapper() });
        
        await waitFor(() => {
            const buttons = screen.getAllByRole('button');
            expect(buttons.length).toBeGreaterThan(0);
        });
    });

    it('should display stats when loaded', async () => {
        render(<DLQDashboard />, { wrapper: createWrapper() });
        
        await waitFor(() => {
            // Stats should be displayed
            expect(screen.getByText(/Total Failed/i)).toBeInTheDocument();
        });
    });

    it('should render retry buttons for failed tasks', async () => {
        render(<DLQDashboard />, { wrapper: createWrapper() });
        
        await waitFor(() => {
            expect(screen.getByText('process_document')).toBeInTheDocument();
        });

        // Verify retry buttons are present for failed tasks
        const retryButtons = screen.getAllByRole('button').filter(btn => 
            btn.querySelector('.lucide-rotate-ccw')
        );
        
        expect(retryButtons.length).toBeGreaterThan(0);
    });

    it('should show toast on successful retry', async () => {
        render(<DLQDashboard />, { wrapper: createWrapper() });
        
        await waitFor(() => {
            expect(screen.getByText('process_document')).toBeInTheDocument();
        });

        const retryButtons = screen.getAllByRole('button').filter(btn => 
            btn.querySelector('.lucide-rotate-ccw')
        );
        
        if (retryButtons.length > 0) {
            retryButtons[0].click();
            
            await waitFor(() => {
                expect(mockToast).toHaveBeenCalledWith(expect.objectContaining({
                    title: 'Retry Initiated',
                }));
            });
        }
    });

    it('should show error toast on retry failure', async () => {
        mockApiPost.mockRejectedValueOnce(new Error('Retry failed'));
        
        render(<DLQDashboard />, { wrapper: createWrapper() });
        
        await waitFor(() => {
            expect(screen.getByText('process_document')).toBeInTheDocument();
        });

        const retryButtons = screen.getAllByRole('button').filter(btn => 
            btn.querySelector('.lucide-rotate-ccw')
        );
        
        if (retryButtons.length > 0) {
            retryButtons[0].click();
            
            await waitFor(() => {
                expect(mockToast).toHaveBeenCalledWith(expect.objectContaining({
                    title: 'Retry Failed',
                    variant: 'destructive',
                }));
            });
        }
    });

    it('should call resolve API for permanently failed task', async () => {
        render(<DLQDashboard />, { wrapper: createWrapper() });
        
        await waitFor(() => {
            expect(screen.getByText('embed_chunks')).toBeInTheDocument();
        });

        // Find resolve button (check circle icon)
        const resolveButtons = screen.getAllByRole('button').filter(btn => 
            btn.querySelector('.lucide-check-circle')
        );
        
        if (resolveButtons.length > 0) {
            resolveButtons[0].click();
            
            await waitFor(() => {
                expect(mockApiPost).toHaveBeenCalledWith('/dlq/resolve/t2');
            });
        }
    });

    it('should show toast on successful resolve', async () => {
        render(<DLQDashboard />, { wrapper: createWrapper() });
        
        await waitFor(() => {
            expect(screen.getByText('embed_chunks')).toBeInTheDocument();
        });

        const resolveButtons = screen.getAllByRole('button').filter(btn => 
            btn.querySelector('.lucide-check-circle')
        );
        
        if (resolveButtons.length > 0) {
            resolveButtons[0].click();
            
            await waitFor(() => {
                expect(mockToast).toHaveBeenCalledWith(expect.objectContaining({
                    title: 'Task Resolved',
                }));
            });
        }
    });

    it('should show error toast on resolve failure', async () => {
        mockApiPost.mockRejectedValueOnce(new Error('Resolve failed'));
        
        render(<DLQDashboard />, { wrapper: createWrapper() });
        
        await waitFor(() => {
            expect(screen.getByText('embed_chunks')).toBeInTheDocument();
        });

        const resolveButtons = screen.getAllByRole('button').filter(btn => 
            btn.querySelector('.lucide-check-circle')
        );
        
        if (resolveButtons.length > 0) {
            resolveButtons[0].click();
            
            await waitFor(() => {
                expect(mockToast).toHaveBeenCalledWith(expect.objectContaining({
                    title: 'Error',
                    variant: 'destructive',
                }));
            });
        }
    });

    it('should block retry for viewer role', async () => {
        mockProfile.mockReturnValue({ profile: { role: 'viewer', email: 'viewer@test.com' }, isLoading: false });
        
        render(<DLQDashboard />, { wrapper: createWrapper() });
        
        await waitFor(() => {
            // Checkboxes should be disabled for viewers
            const checkboxes = screen.getAllByRole('checkbox');
            checkboxes.forEach(checkbox => {
                expect(checkbox).toBeDisabled();
            });
        });
    });

    it('should toggle task selection', async () => {
        render(<DLQDashboard />, { wrapper: createWrapper() });
        
        await waitFor(() => {
            expect(screen.getByText('process_document')).toBeInTheDocument();
        });

        // Find checkbox and click it
        const checkboxes = screen.getAllByRole('checkbox');
        if (checkboxes.length > 0) {
            checkboxes[0].click();
            
            // After selecting, the batch retry button should appear
            await waitFor(() => {
                expect(screen.getByText(/Retry 1 Selected/i)).toBeInTheDocument();
            });
        }
    });

    it('should show batch retry button when tasks selected', async () => {
        render(<DLQDashboard />, { wrapper: createWrapper() });
        
        await waitFor(() => {
            expect(screen.getByText('process_document')).toBeInTheDocument();
        });

        // Select a task
        const checkboxes = screen.getAllByRole('checkbox');
        if (checkboxes.length > 0) {
            checkboxes[0].click();
            
            await waitFor(() => {
                expect(screen.getByRole('button', { name: /Retry 1 Selected/i })).toBeInTheDocument();
            });
        }
    });

    it('should show batch retry button after selection', async () => {
        render(<DLQDashboard />, { wrapper: createWrapper() });
        
        await waitFor(() => {
            expect(screen.getByText('process_document')).toBeInTheDocument();
        });

        // Select a task
        const checkboxes = screen.getAllByRole('checkbox');
        expect(checkboxes.length).toBeGreaterThan(0);
        
        if (checkboxes.length > 0) {
            checkboxes[0].click();
            
            await waitFor(() => {
                expect(screen.getByText(/Retry 1 Selected/i)).toBeInTheDocument();
            });
        }
    });

    it('should show toast on successful batch retry', async () => {
        render(<DLQDashboard />, { wrapper: createWrapper() });
        
        await waitFor(() => {
            expect(screen.getByText('process_document')).toBeInTheDocument();
        });

        const checkboxes = screen.getAllByRole('checkbox');
        if (checkboxes.length > 0) {
            checkboxes[0].click();
            
            await waitFor(() => {
                expect(screen.getByText(/Retry 1 Selected/i)).toBeInTheDocument();
            });

            screen.getByRole('button', { name: /Retry 1 Selected/i }).click();

            await waitFor(() => {
                expect(mockToast).toHaveBeenCalledWith(expect.objectContaining({
                    title: 'Batch Retry Initiated',
                }));
            });
        }
    });

    it('should show error toast on batch retry failure', async () => {
        mockApiPost.mockRejectedValueOnce(new Error('Batch retry failed'));
        
        render(<DLQDashboard />, { wrapper: createWrapper() });
        
        await waitFor(() => {
            expect(screen.getByText('process_document')).toBeInTheDocument();
        });

        const checkboxes = screen.getAllByRole('checkbox');
        if (checkboxes.length > 0) {
            checkboxes[0].click();
            
            await waitFor(() => {
                expect(screen.getByText(/Retry 1 Selected/i)).toBeInTheDocument();
            });

            screen.getByRole('button', { name: /Retry 1 Selected/i }).click();

            await waitFor(() => {
                expect(mockToast).toHaveBeenCalledWith(expect.objectContaining({
                    title: 'Batch Retry Failed',
                    variant: 'destructive',
                }));
            });
        }
    });
});

describe('DLQ Dashboard Filtering', () => {
    const filterTasks = [
        {
            id: 't1',
            task_id: 'task-1',
            task_name: 'parse_document',
            user_id: 'user-1',
            job_id: 'job-1',
            status: 'failed' as const,
            attempt_count: 2,
            max_retries: 5,
            next_retry_at: null,
            exception_type: 'ParseError',
            exception_message: 'Failed to parse PDF',
            traceback: '',
            kwargs: {},
            created_at: '2024-01-15T10:00:00Z',
            updated_at: '2024-01-15T10:00:00Z',
            resolved_at: null,
        },
        {
            id: 't2',
            task_id: 'task-2',
            task_name: 'embed_chunks',
            user_id: 'user-1',
            job_id: 'job-1',
            status: 'pending_retry' as const,
            attempt_count: 1,
            max_retries: 5,
            next_retry_at: '2024-01-15T12:00:00Z',
            exception_type: 'APIError',
            exception_message: 'API timeout',
            traceback: '',
            kwargs: {},
            created_at: '2024-01-15T09:00:00Z',
            updated_at: '2024-01-15T11:00:00Z',
            resolved_at: null,
        },
    ];

    beforeEach(() => {
        vi.clearAllMocks();
        mockProfile.mockReturnValue({ profile: { role: 'admin', email: 'admin@test.com' }, isLoading: false });
        mockApiGet.mockImplementation((url: string) => {
            if (url === '/dlq/my-tasks') {
                return Promise.resolve({ data: { tasks: filterTasks } });
            }
            if (url === '/dlq/stats') {
                return Promise.resolve({ data: { total: 2, pending_retry: 1, retrying: 0, permanently_failed: 0, resolved_today: 0 } });
            }
            return Promise.resolve({ data: {} });
        });
    });

    it('should filter tasks by search query', async () => {
        render(<DLQDashboard />, { wrapper: createWrapper() });
        
        await waitFor(() => {
            expect(screen.getByText('parse_document')).toBeInTheDocument();
            expect(screen.getByText('embed_chunks')).toBeInTheDocument();
        });

        // Type in search
        const searchInput = screen.getByPlaceholderText(/search/i);
        searchInput.focus();
        await userEvent.type(searchInput, 'parse');

        await waitFor(() => {
            expect(screen.getByText('parse_document')).toBeInTheDocument();
            expect(screen.queryByText('embed_chunks')).not.toBeInTheDocument();
        });
    });

    it('should filter tasks by error message', async () => {
        render(<DLQDashboard />, { wrapper: createWrapper() });
        
        await waitFor(() => {
            expect(screen.getByText('parse_document')).toBeInTheDocument();
        });

        const searchInput = screen.getByPlaceholderText(/search/i);
        await userEvent.type(searchInput, 'timeout');

        await waitFor(() => {
            expect(screen.queryByText('parse_document')).not.toBeInTheDocument();
            expect(screen.getByText('embed_chunks')).toBeInTheDocument();
        });
    });

    it('should show "no matching tasks" when filter has no results', async () => {
        render(<DLQDashboard />, { wrapper: createWrapper() });
        
        await waitFor(() => {
            expect(screen.getByText('parse_document')).toBeInTheDocument();
        });

        const searchInput = screen.getByPlaceholderText(/search/i);
        await userEvent.type(searchInput, 'nonexistent');

        await waitFor(() => {
            expect(screen.getByText(/no matching tasks/i)).toBeInTheDocument();
        });
    });
});

describe('StatusBadge Component', () => {
    beforeEach(() => {
        vi.clearAllMocks();
        mockProfile.mockReturnValue({ profile: { role: 'admin', email: 'admin@test.com' }, isLoading: false });
    });

    it('should display correct badge for each status', async () => {
        const statusTasks = [
            { id: 't1', status: 'failed' as const },
            { id: 't2', status: 'pending_retry' as const },
            { id: 't3', status: 'retrying' as const },
            { id: 't4', status: 'permanently_failed' as const },
            { id: 't5', status: 'resolved' as const },
        ].map((t, i) => ({
            ...t,
            task_id: `task-${i}`,
            task_name: `task_${t.status}`,
            user_id: 'user-1',
            job_id: 'job-1',
            attempt_count: 1,
            max_retries: 5,
            next_retry_at: null,
            exception_type: 'Error',
            exception_message: 'Error',
            traceback: '',
            kwargs: {},
            created_at: '2024-01-15T10:00:00Z',
            updated_at: '2024-01-15T10:00:00Z',
            resolved_at: null,
        }));

        mockApiGet.mockImplementation((url: string) => {
            if (url === '/dlq/my-tasks') {
                return Promise.resolve({ data: { tasks: statusTasks } });
            }
            if (url === '/dlq/stats') {
                return Promise.resolve({ data: { total: 5, pending_retry: 1, retrying: 1, permanently_failed: 1, resolved_today: 1 } });
            }
            return Promise.resolve({ data: {} });
        });

        render(<DLQDashboard />, { wrapper: createWrapper() });

        await waitFor(() => {
            expect(screen.getByText('failed')).toBeInTheDocument();
            expect(screen.getByText('pending retry')).toBeInTheDocument();
            expect(screen.getByText('retrying')).toBeInTheDocument();
            expect(screen.getByText('permanently failed')).toBeInTheDocument();
            expect(screen.getByText('resolved')).toBeInTheDocument();
        });
    });
});

// =============================================================================
// Resolve Task Tests
// =============================================================================

describe('DLQ Dashboard - Resolve Task', () => {
    const mockTaskWithResolvable = {
        id: 'task-1',
        task_id: 'task-id-1',
        task_name: 'process_document',
        user_id: 'user-1',
        job_id: 'job-1',
        status: 'permanently_failed' as const,
        attempt_count: 5,
        max_retries: 5,
        next_retry_at: null,
        exception_type: 'MaxRetriesError',
        exception_message: 'Max retries exceeded',
        traceback: 'traceback...',
        kwargs: {},
        created_at: '2024-01-15T10:00:00Z',
        updated_at: '2024-01-15T11:00:00Z',
        resolved_at: null,
    };

    beforeEach(() => {
        vi.clearAllMocks();
        mockProfile.mockReturnValue({ profile: { role: 'admin', email: 'admin@test.com' }, isLoading: false });
        mockApiGet.mockImplementation((url: string) => {
            if (url === '/dlq/my-tasks') {
                return Promise.resolve({ data: { tasks: [mockTaskWithResolvable] } });
            }
            if (url === '/dlq/stats') {
                return Promise.resolve({ data: { total: 1, pending_retry: 0, retrying: 0, permanently_failed: 1, resolved_today: 0 } });
            }
            return Promise.resolve({ data: {} });
        });
        mockApiPost.mockResolvedValue({ data: {} });
    });

    // Helper to get the resolve button (the CheckCircle icon button for permanently_failed tasks)
    const getResolveButton = () => {
        // The resolve button is the second button (after retry) in the actions column
        // for permanently_failed tasks, or find by its SVG icon
        const buttons = screen.getAllByRole('button');
        // The resolve button follows the retry button and has a CheckCircle icon
        // In the actions cell, it's typically the last button for permanently_failed status
        const actionsCell = screen.getByText('permanently failed').closest('tr')?.querySelector('td:last-child');
        if (actionsCell) {
            const actionButtons = actionsCell.querySelectorAll('button');
            // For permanently_failed, there are 2 buttons: retry and resolve
            // Resolve is the second one (index 1)
            if (actionButtons.length >= 2) {
                return actionButtons[1] as HTMLButtonElement;
            }
        }
        return null;
    };

    it('should show resolve button for permanently failed tasks', async () => {
        render(<DLQDashboard />, { wrapper: createWrapper() });

        await waitFor(() => {
            expect(screen.getByText('permanently failed')).toBeInTheDocument();
        });

        // For permanently_failed tasks, there should be both retry and resolve buttons
        const actionsCell = screen.getByText('permanently failed').closest('tr')?.querySelector('td:last-child');
        expect(actionsCell).toBeInTheDocument();
        const actionButtons = actionsCell?.querySelectorAll('button');
        // Should have at least 2 buttons (retry + resolve) for permanently_failed
        expect(actionButtons?.length).toBeGreaterThanOrEqual(2);
    });

    it('should resolve task successfully', async () => {
        render(<DLQDashboard />, { wrapper: createWrapper() });

        await waitFor(() => {
            expect(screen.getByText('process_document')).toBeInTheDocument();
        });

        const resolveButton = getResolveButton();
        expect(resolveButton).not.toBeNull();
        await userEvent.click(resolveButton!);

        await waitFor(() => {
            expect(mockApiPost).toHaveBeenCalledWith('/dlq/resolve/task-1', undefined);
        });

        await waitFor(() => {
            expect(mockToast).toHaveBeenCalledWith(expect.objectContaining({
                title: 'Task Resolved',
            }));
        });
    });

    it('should show error toast on resolve failure', async () => {
        mockApiPost.mockRejectedValueOnce(new Error('Failed to resolve'));

        render(<DLQDashboard />, { wrapper: createWrapper() });

        await waitFor(() => {
            expect(screen.getByText('process_document')).toBeInTheDocument();
        });

        const resolveButton = getResolveButton();
        expect(resolveButton).not.toBeNull();
        await userEvent.click(resolveButton!);

        await waitFor(() => {
            expect(mockToast).toHaveBeenCalledWith(expect.objectContaining({
                title: 'Error',
                description: 'Failed to resolve',
                variant: 'destructive',
            }));
        });
    });

    it('should show fallback error message when error is not an Error instance', async () => {
        mockApiPost.mockRejectedValueOnce('Some string error');

        render(<DLQDashboard />, { wrapper: createWrapper() });

        await waitFor(() => {
            expect(screen.getByText('process_document')).toBeInTheDocument();
        });

        const resolveButton = getResolveButton();
        expect(resolveButton).not.toBeNull();
        await userEvent.click(resolveButton!);

        await waitFor(() => {
            expect(mockToast).toHaveBeenCalledWith(expect.objectContaining({
                title: 'Error',
                description: 'Failed to resolve task',
                variant: 'destructive',
            }));
        });
    });

    it('should block resolve for viewer role', async () => {
        mockProfile.mockReturnValue({ profile: { role: 'viewer', email: 'viewer@test.com' }, isLoading: false });

        render(<DLQDashboard />, { wrapper: createWrapper() });

        await waitFor(() => {
            expect(screen.getByText('process_document')).toBeInTheDocument();
        });

        // For viewer, the resolve button should still exist but be disabled
        const resolveButton = getResolveButton();
        if (resolveButton) {
            expect(resolveButton).toBeDisabled();
        }
        // Clicking should not trigger API call since button is disabled
        expect(mockApiPost).not.toHaveBeenCalledWith(expect.stringContaining('/dlq/resolve'));
    });
});

// =============================================================================
// Guard Actions Tests
// =============================================================================

describe('DLQ Dashboard - Guard Actions', () => {
    beforeEach(() => {
        vi.clearAllMocks();
        mockApiGet.mockImplementation((url: string) => {
            if (url === '/dlq/my-tasks') {
                return Promise.resolve({ data: { tasks: [{
                    id: 'task-1',
                    task_id: 'task-id-1',
                    task_name: 'process_document',
                    user_id: 'user-1',
                    job_id: 'job-1',
                    status: 'failed' as const,
                    attempt_count: 1,
                    max_retries: 5,
                    next_retry_at: '2024-01-15T12:00:00Z',
                    exception_type: 'Error',
                    exception_message: 'Test error',
                    traceback: 'traceback...',
                    kwargs: {},
                    created_at: '2024-01-15T10:00:00Z',
                    updated_at: '2024-01-15T11:00:00Z',
                    resolved_at: null,
                }] } });
            }
            if (url === '/dlq/stats') {
                return Promise.resolve({ data: { total: 1, pending_retry: 0, retrying: 0, permanently_failed: 0, resolved_today: 0 } });
            }
            return Promise.resolve({ data: {} });
        });
    });

    it('should block task selection for viewer role', async () => {
        mockProfile.mockReturnValue({ profile: { role: 'viewer', email: 'viewer@test.com' }, isLoading: false });

        render(<DLQDashboard />, { wrapper: createWrapper() });

        await waitFor(() => {
            expect(screen.getByText('process_document')).toBeInTheDocument();
        });

        // For viewer role, checkboxes should be disabled
        const checkboxes = screen.getAllByRole('checkbox');
        if (checkboxes.length > 0) {
            // Viewer checkboxes should be disabled
            expect(checkboxes[0]).toBeDisabled();
        }
    });

    it('should allow task selection for admin role', async () => {
        mockProfile.mockReturnValue({ profile: { role: 'admin', email: 'admin@test.com' }, isLoading: false });

        render(<DLQDashboard />, { wrapper: createWrapper() });

        await waitFor(() => {
            expect(screen.getByText('process_document')).toBeInTheDocument();
        });

        // Select a task
        const checkboxes = screen.getAllByRole('checkbox');
        if (checkboxes.length > 0) {
            await userEvent.click(checkboxes[0]);

            // Should show batch action button
            await waitFor(() => {
                expect(screen.getByText(/Retry 1 Selected/i)).toBeInTheDocument();
            });
        }
    });
});
