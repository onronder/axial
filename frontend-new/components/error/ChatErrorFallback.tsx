/**
 * Chat Error Fallback
 * 
 * Specialized error fallback for chat interface.
 */

import { AlertCircle, RefreshCw } from 'lucide-react';
import { Button } from '@/components/ui/button';
import { Card } from '@/components/ui/card';

interface ChatErrorFallbackProps {
    error?: Error;
    onReset?: () => void;
}

export function ChatErrorFallback({ error, onReset }: ChatErrorFallbackProps) {
    return (
        <div className="flex items-center justify-center h-full p-8">
            <Card className="max-w-md p-8 text-center space-y-6">
                <div className="flex justify-center">
                    <div className="rounded-full bg-destructive/10 p-4">
                        <AlertCircle className="h-12 w-12 text-destructive" />
                    </div>
                </div>

                <div className="space-y-2">
                    <h3 className="text-xl font-semibold">Chat Error</h3>
                    <p className="text-sm text-muted-foreground">
                        {error?.message || "We couldn't load your chat. This might be a temporary issue."}
                    </p>
                </div>

                <div className="flex flex-col gap-2">
                    <Button onClick={onReset} className="w-full gap-2">
                        <RefreshCw className="h-4 w-4" />
                        Retry
                    </Button>
                    <Button
                        variant="outline"
                        onClick={() => window.location.href = '/dashboard'}
                        className="w-full"
                    >
                        Go to Dashboard
                    </Button>
                </div>

                <p className="text-xs text-muted-foreground">
                    If this problem persists, please contact support.
                </p>
            </Card>
        </div>
    );
}
