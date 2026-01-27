
'use client';

import { useState, useEffect, useCallback } from 'react';
import { AlertTriangle, RefreshCw, Clock, CheckCircle, XCircle, Filter, RotateCcw, Search } from "lucide-react";
import { Spinner } from "@/components/ui/spinner";

import { Button } from '@/components/ui/button';
import { Input } from '@/components/ui/input';
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card';
import { Badge } from '@/components/ui/badge';
import {
    Table,
    TableBody,
    TableCell,
    TableHead,
    TableHeader,
    TableRow,
} from '@/components/ui/table';
import {
    Select,
    SelectContent,
    SelectItem,
    SelectTrigger,
    SelectValue,
} from '@/components/ui/select';
import { useToast } from '@/hooks/use-toast';
import { api } from '@/lib/api';
import { cn } from '@/lib/utils';
import { useProfile } from '@/hooks/useProfile';
import { Alert, AlertDescription, AlertTitle } from '@/components/ui/alert';
import { ROLE_TOAST_TITLES } from '@/lib/role-messages';

// ============================================================
// Types
// ============================================================

export type FailedTaskStatus =
    | 'failed'
    | 'pending_retry'
    | 'retrying'
    | 'permanently_failed'
    | 'resolved';

export interface FailedTask {
    id: string;
    task_id: string;
    task_name: string;
    user_id: string;
    job_id: string;
    status: FailedTaskStatus;
    attempt_count: number;
    max_retries: number;
    next_retry_at: string | null;
    exception_type: string;
    exception_message: string;
    traceback: string;
    kwargs: Record<string, unknown>;
    created_at: string;
    updated_at: string;
    resolved_at: string | null;
}

interface DLQStats {
    total: number;
    pending_retry: number;
    retrying: number;
    permanently_failed: number;
    resolved_today: number;
}

// ============================================================
// Status Badge Component
// ============================================================

function StatusBadge({ status }: { status: FailedTaskStatus }) {
    const variants: Record<FailedTaskStatus, { variant: 'default' | 'secondary' | 'destructive' | 'outline'; icon: React.ReactNode }> = {
        failed: { variant: 'destructive', icon: <XCircle className="h-3 w-3" /> },
        pending_retry: { variant: 'secondary', icon: <Clock className="h-3 w-3" /> },
        retrying: { variant: 'default', icon: <RefreshCw className="h-3 w-3 animate-spin" /> },
        permanently_failed: { variant: 'destructive', icon: <AlertTriangle className="h-3 w-3" /> },
        resolved: { variant: 'outline', icon: <CheckCircle className="h-3 w-3" /> },
    };

    const { variant, icon } = variants[status];

    return (
        <Badge variant={variant} className="gap-1">
            {icon}
            {status.replace('_', ' ')}
        </Badge>
    );
}

// ============================================================
// Time helpers
// ============================================================

function formatTimeAgo(dateString: string): string {
    const date = new Date(dateString);
    const now = new Date();
    const diffMs = now.getTime() - date.getTime();
    const diffMinutes = Math.floor(diffMs / 60000);
    const diffHours = Math.floor(diffMinutes / 60);
    const diffDays = Math.floor(diffHours / 24);

    if (diffDays > 0) return `${diffDays}d ago`;
    if (diffHours > 0) return `${diffHours}h ago`;
    if (diffMinutes > 0) return `${diffMinutes}m ago`;
    return 'just now';
}

function formatRetryTime(nextRetryAt: string | null): string {
    if (!nextRetryAt) return '-';

    const retryTime = new Date(nextRetryAt);
    const now = new Date();
    const diffMs = retryTime.getTime() - now.getTime();

    if (diffMs <= 0) return 'retrying now';

    const diffMinutes = Math.floor(diffMs / 60000);
    const diffHours = Math.floor(diffMinutes / 60);

    if (diffHours > 0) return `in ${diffHours}h ${diffMinutes % 60}m`;
    return `in ${diffMinutes}m`;
}

// ============================================================
// DLQ Dashboard Component
// ============================================================

export function DLQDashboard() {
    const { toast } = useToast();
    const { profile, isLoading: profileLoading } = useProfile();
    const [tasks, setTasks] = useState<FailedTask[]>([]);
    const [stats, setStats] = useState<DLQStats | null>(null);
    const [isLoading, setIsLoading] = useState(true);
    const [isRetrying, setIsRetrying] = useState<string | null>(null);
    const [searchQuery, setSearchQuery] = useState('');
    const [statusFilter, setStatusFilter] = useState<FailedTaskStatus | 'all'>('all');
    const [selectedTasks, setSelectedTasks] = useState<Set<string>>(new Set());
    const isViewer = profile?.role === 'viewer';
    const isReadOnly = profileLoading || isViewer;
    const actionLockedReason = isReadOnly
        ? profileLoading
            ? "Loading permissions..."
            : "View-only members cannot retry or resolve tasks."
        : null;

    const guardActions = (action: string) => {
        if (isReadOnly) {
            toast({
                title: ROLE_TOAST_TITLES.VIEW_ONLY,
                description: actionLockedReason || `You don't have permission to ${action}.`,
                variant: "destructive",
            });
            return false;
        }
        return true;
    };

    useEffect(() => {
        if (isReadOnly && selectedTasks.size > 0) {
            setSelectedTasks(new Set());
        }
    }, [isReadOnly, selectedTasks]);

    // Fetch DLQ data
    const fetchData = useCallback(async () => {
        setIsLoading(true);
        try {
            const [tasksRes, statsRes] = await Promise.all([
                api.get('/dlq/my-tasks'),
                api.get('/dlq/stats'),
            ]);
            setTasks(tasksRes.data?.tasks || []);
            setStats(statsRes.data || null);
        } catch (err) {
            const message = err instanceof Error ? err.message : 'Failed to fetch DLQ data';
            toast({
                title: 'Error',
                description: message,
                variant: 'destructive',
            });
        } finally {
            setIsLoading(false);
        }
    }, [toast]);

    useEffect(() => {
        fetchData();
        // Poll every 30 seconds
        const interval = setInterval(fetchData, 30000);
        return () => clearInterval(interval);
    }, [fetchData]);

    // Retry single task
    const retryTask = async (taskId: string) => {
        if (!guardActions("retry tasks")) return;
        setIsRetrying(taskId);
        try {
            await api.post(`/dlq/retry/${taskId}`);
            toast({
                title: 'Retry Initiated',
                description: 'Task has been queued for retry.',
            });
            await fetchData();
        } catch (err) {
            const message = err instanceof Error ? err.message : 'Failed to retry task';
            toast({
                title: 'Retry Failed',
                description: message,
                variant: 'destructive',
            });
        } finally {
            setIsRetrying(null);
        }
    };

    // Retry selected tasks
    const retrySelected = async () => {
        if (selectedTasks.size === 0) return;
        if (!guardActions("retry tasks")) return;

        try {
            // Sequential retry for selected tasks (no batch endpoint yet)
            for (const taskId of selectedTasks) {
                await api.post(`/dlq/retry/${taskId}`);
            }
            toast({
                title: 'Batch Retry Initiated',
                description: `${selectedTasks.size} tasks queued for retry.`,
            });
            setSelectedTasks(new Set());
            await fetchData();
        } catch (err) {
            const message = err instanceof Error ? err.message : 'Failed to retry tasks';
            toast({
                title: 'Batch Retry Failed',
                description: message,
                variant: 'destructive',
            });
        }
    };

    // Mark as resolved
    const resolveTask = async (taskId: string) => {
        if (!guardActions("resolve tasks")) return;
        try {
            await api.post(`/dlq/resolve/${taskId}`);
            toast({
                title: 'Task Resolved',
                description: 'Task has been marked as resolved.',
            });
            await fetchData();
        } catch (err) {
            const message = err instanceof Error ? err.message : 'Failed to resolve task';
            toast({
                title: 'Error',
                description: message,
                variant: 'destructive',
            });
        }
    };

    // Filter tasks
    const filteredTasks = tasks.filter(task => {
        const matchesSearch =
            task.task_name.toLowerCase().includes(searchQuery.toLowerCase()) ||
            task.exception_message.toLowerCase().includes(searchQuery.toLowerCase());
        const matchesStatus = statusFilter === 'all' || task.status === statusFilter;
        return matchesSearch && matchesStatus;
    });

    // Toggle task selection
    const toggleSelection = (taskId: string) => {
        if (!guardActions("select tasks")) return;
        setSelectedTasks(prev => {
            const next = new Set(prev);
            if (next.has(taskId)) {
                next.delete(taskId);
            } else {
                next.add(taskId);
            }
            return next;
        });
    };

    return (
        <div className="space-y-6">
            {/* Header */}
            <div className="flex items-center justify-between">
                <div>
                    <h1 className="text-2xl font-bold">Dead Letter Queue</h1>
                    <p className="text-muted-foreground">
                        Monitor and manage failed background tasks
                    </p>
                </div>
                <Button onClick={fetchData} variant="outline" className="gap-2">
                    <RefreshCw className={cn("h-4 w-4", isLoading && "animate-spin")} />
                    Refresh
                </Button>
            </div>

            {actionLockedReason && (
                <Alert className="border-amber-400/40 bg-amber-500/5">
                    <AlertTitle className="flex items-center gap-2">
                        <AlertTriangle className="h-4 w-4 text-amber-400" />
                        View-only access
                    </AlertTitle>
                    <AlertDescription className="text-sm text-amber-100">
                        {actionLockedReason}
                    </AlertDescription>
                </Alert>
            )}

            {/* Stats Cards */}
            <div className="grid gap-4 md:grid-cols-4">
                <Card>
                    <CardHeader className="pb-2">
                        <CardDescription>Total Failed</CardDescription>
                        <CardTitle className="text-2xl">{stats?.total ?? 0}</CardTitle>
                    </CardHeader>
                </Card>
                <Card>
                    <CardHeader className="pb-2">
                        <CardDescription>Pending Retry</CardDescription>
                        <CardTitle className="text-2xl text-yellow-500">{stats?.pending_retry ?? 0}</CardTitle>
                    </CardHeader>
                </Card>
                <Card>
                    <CardHeader className="pb-2">
                        <CardDescription>Permanently Failed</CardDescription>
                        <CardTitle className="text-2xl text-destructive">{stats?.permanently_failed ?? 0}</CardTitle>
                    </CardHeader>
                </Card>
                <Card>
                    <CardHeader className="pb-2">
                        <CardDescription>Resolved Today</CardDescription>
                        <CardTitle className="text-2xl text-green-500">{stats?.resolved_today ?? 0}</CardTitle>
                    </CardHeader>
                </Card>
            </div>

            {/* Filters */}
            <div className="flex items-center gap-4">
                <div className="relative flex-1 max-w-sm">
                    <Search className="absolute left-2 top-2.5 h-4 w-4 text-muted-foreground" />
                    <Input
                        placeholder="Search tasks..."
                        value={searchQuery}
                        onChange={(e) => setSearchQuery(e.target.value)}
                        className="pl-8"
                    />
                </div>
                <Select value={statusFilter} onValueChange={(v) => setStatusFilter(v as FailedTaskStatus | 'all')}>
                    <SelectTrigger className="w-[180px]">
                        <Filter className="h-4 w-4 mr-2" />
                        <SelectValue placeholder="Filter status" />
                    </SelectTrigger>
                    <SelectContent>
                        <SelectItem value="all">All Statuses</SelectItem>
                        <SelectItem value="failed">Failed</SelectItem>
                        <SelectItem value="pending_retry">Pending Retry</SelectItem>
                        <SelectItem value="retrying">Retrying</SelectItem>
                        <SelectItem value="permanently_failed">Permanently Failed</SelectItem>
                        <SelectItem value="resolved">Resolved</SelectItem>
                    </SelectContent>
                </Select>
                {selectedTasks.size > 0 && !isReadOnly && (
                    <Button onClick={retrySelected} className="gap-2">
                        <RotateCcw className="h-4 w-4" />
                        Retry {selectedTasks.size} Selected
                    </Button>
                )}
            </div>

            {/* Tasks Table */}
            <Card>
                <CardContent className="p-0">
                    <Table>
                        <TableHeader>
                            <TableRow>
                                <TableHead className="w-12"></TableHead>
                                <TableHead>Task</TableHead>
                                <TableHead>Status</TableHead>
                                <TableHead>Attempts</TableHead>
                                <TableHead>Error</TableHead>
                                <TableHead>Next Retry</TableHead>
                                <TableHead>Created</TableHead>
                                <TableHead className="w-24">Actions</TableHead>
                            </TableRow>
                        </TableHeader>
                        <TableBody>
                            {isLoading ? (
                                <TableRow>
                                    <TableCell colSpan={8} className="h-32 text-center">
                                        <Spinner className="mx-auto h-6 w-6 animate-spin text-muted-foreground" />
                                    </TableCell>
                                </TableRow>
                            ) : filteredTasks.length === 0 ? (
                                <TableRow>
                                    <TableCell colSpan={8} className="h-32 text-center text-muted-foreground">
                                        {searchQuery || statusFilter !== 'all'
                                            ? 'No matching tasks found'
                                            : 'No failed tasks - everything is healthy! 🎉'}
                                    </TableCell>
                                </TableRow>
                            ) : (
                                filteredTasks.map((task) => (
                                    <TableRow key={task.id}>
                                        <TableCell>
                                            <input
                                                type="checkbox"
                                                checked={selectedTasks.has(task.id)}
                                                onChange={() => toggleSelection(task.id)}
                                                className="h-4 w-4"
                                                disabled={isReadOnly}
                                            />
                                        </TableCell>
                                        <TableCell>
                                            <div>
                                                <p className="font-medium text-sm">{task.task_name}</p>
                                                <p className="text-xs text-muted-foreground truncate max-w-[200px]">
                                                    {task.job_id}
                                                </p>
                                            </div>
                                        </TableCell>
                                        <TableCell>
                                            <StatusBadge status={task.status} />
                                        </TableCell>
                                        <TableCell>
                                            <span className={cn(
                                                "font-medium",
                                                task.attempt_count >= task.max_retries && "text-destructive"
                                            )}>
                                                {task.attempt_count} / {task.max_retries}
                                            </span>
                                        </TableCell>
                                        <TableCell>
                                            <p className="text-sm truncate max-w-[200px]" title={task.exception_message}>
                                                {task.exception_type}: {task.exception_message}
                                            </p>
                                        </TableCell>
                                        <TableCell>
                                            <span className="text-sm text-muted-foreground">
                                                {formatRetryTime(task.next_retry_at)}
                                            </span>
                                        </TableCell>
                                        <TableCell>
                                            <span className="text-sm text-muted-foreground">
                                                {formatTimeAgo(task.created_at)}
                                            </span>
                                        </TableCell>
                                        <TableCell>
                                            <div className="flex items-center gap-1">
                                                {task.status !== 'resolved' && task.status !== 'retrying' && (
                                                    <Button
                                                        size="sm"
                                                        variant="ghost"
                                                        onClick={() => retryTask(task.id)}
                                                        disabled={isRetrying === task.id || isReadOnly}
                                                    >
                                                        {isRetrying === task.id ? (
                                                            <Spinner className="h-4 w-4 animate-spin" />
                                                        ) : (
                                                            <RotateCcw className="h-4 w-4" />
                                                        )}
                                                    </Button>
                                                )}
                                                {task.status === 'permanently_failed' && (
                                                    <Button
                                                        size="sm"
                                                        variant="ghost"
                                                        onClick={() => resolveTask(task.id)}
                                                        disabled={isReadOnly}
                                                    >
                                                        <CheckCircle className="h-4 w-4" />
                                                    </Button>
                                                )}
                                            </div>
                                        </TableCell>
                                    </TableRow>
                                ))
                            )}
                        </TableBody>
                    </Table>
                </CardContent>
            </Card>
        </div>
    );
}