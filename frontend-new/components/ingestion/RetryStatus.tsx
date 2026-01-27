
/**
 * Retry Status Component
 * 
 * Displays retry information for failed ingestion jobs.
 * Shows countdown, attempt count, and status updates in realtime.
 */

import React from 'react';
import { Alert, AlertDescription, AlertTitle } from '@/components/ui/alert';
import { Button } from '@/components/ui/button';
import { Clock, XCircle, CheckCircle2 } from "lucide-react";
import { Spinner } from "@/components/ui/spinner";

import { useFailedTaskStatus, getTimeUntilRetry, formatRetryTime } from '@/hooks/useFailedTaskStatus';
import {
    Collapsible,
    CollapsibleContent,
    CollapsibleTrigger,
} from '@/components/ui/collapsible';

interface RetryStatusProps {
    jobId: string;
    className?: string;
}

export function RetryStatus({ jobId, className }: RetryStatusProps) {
    const { failedTask, loading } = useFailedTaskStatus(jobId);
    const [showDetails, setShowDetails] = React.useState(false);

    if (loading || !failedTask) {
        return null;
    }

    // Pending retry - show countdown
    if (failedTask.status === 'pending_retry') {
        return (
            <Alert className={className} variant="default">
                <Clock className="h-4 w-4" />
                <AlertTitle>Automatic Retry Scheduled</AlertTitle>
                <AlertDescription>
                    <div className="space-y-2">
                        <p>
                            This job will be automatically retried in{' '}
                            <strong>{getTimeUntilRetry(failedTask.next_retry_at)}</strong>
                            {' '}({formatRetryTime(failedTask.next_retry_at)})
                        </p>
                        <div className="flex items-center gap-2 text-sm text-muted-foreground">
                            <span>Attempt {failedTask.attempt_count}/{failedTask.max_retries}</span>
                            <span>•</span>
                            <span>{failedTask.exception_type}</span>
                        </div>

                        <Collapsible open={showDetails} onOpenChange={setShowDetails}>
                            <CollapsibleTrigger asChild>
                                <Button variant="ghost" size="sm" className="mt-2">
                                    {showDetails ? 'Hide' : 'Show'} Error Details
                                </Button>
                            </CollapsibleTrigger>
                            <CollapsibleContent className="mt-2">
                                <div className="rounded-md bg-muted p-3">
                                    <p className="text-xs font-mono text-muted-foreground break-all">
                                        {failedTask.exception_message}
                                    </p>
                                </div>
                            </CollapsibleContent>
                        </Collapsible>
                    </div>
                </AlertDescription>
            </Alert>
        );
    }

    // Currently retrying
    if (failedTask.status === 'retrying') {
        return (
            <Alert className={className} variant="default">
                <Spinner className="h-4 w-4 animate-spin" />
                <AlertTitle>Retrying Now...</AlertTitle>
                <AlertDescription>
                    <p>
                        Retry attempt {failedTask.attempt_count}/{failedTask.max_retries} in progress.
                        This may take a few minutes.
                    </p>
                </AlertDescription>
            </Alert>
        );
    }

    // Permanently failed
    if (failedTask.status === 'permanently_failed') {
        return (
            <Alert className={className} variant="destructive">
                <XCircle className="h-4 w-4" />
                <AlertTitle>Failed After {failedTask.attempt_count} Attempts</AlertTitle>
                <AlertDescription>
                    <div className="space-y-3">
                        <p>
                            This job failed after {failedTask.attempt_count} automatic retry attempts.
                            Please contact support for assistance.
                        </p>

                        <div className="rounded-md bg-destructive/10 p-3">
                            <p className="text-sm font-semibold mb-1">Error:</p>
                            <p className="text-xs font-mono break-all">
                                {failedTask.exception_message}
                            </p>
                        </div>

                        <div className="flex gap-2">
                            <Button
                                variant="outline"
                                size="sm"
                                onClick={() => {
                                    const supportUrl = `/support?task_id=${failedTask.task_id}&job_id=${failedTask.job_id}`;
                                    window.location.href = supportUrl;
                                }}
                            >
                                Contact Support
                            </Button>

                            <Collapsible open={showDetails} onOpenChange={setShowDetails}>
                                <CollapsibleTrigger asChild>
                                    <Button variant="ghost" size="sm">
                                        {showDetails ? 'Hide' : 'Show'} Full Traceback
                                    </Button>
                                </CollapsibleTrigger>
                                <CollapsibleContent className="mt-2">
                                    <div className="rounded-md bg-muted p-3 max-h-64 overflow-auto">
                                        <pre className="text-xs font-mono whitespace-pre-wrap">
                                            {failedTask.traceback}
                                        </pre>
                                    </div>
                                </CollapsibleContent>
                            </Collapsible>
                        </div>
                    </div>
                </AlertDescription>
            </Alert>
        );
    }

    // Resolved (retry succeeded)
    if (failedTask.status === 'resolved') {
        return (
            <Alert className={className} variant="default">
                <CheckCircle2 className="h-4 w-4 text-green-600" />
                <AlertTitle className="text-green-900">Retry Succeeded!</AlertTitle>
                <AlertDescription className="text-green-800">
                    <p>
                        This job succeeded after {failedTask.attempt_count} attempt{failedTask.attempt_count > 1 ? 's' : ''}.
                        Your documents are now ready.
                    </p>
                </AlertDescription>
            </Alert>
        );
    }

    return null;
}
