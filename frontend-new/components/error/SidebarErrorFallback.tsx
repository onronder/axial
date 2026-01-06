/**
 * Sidebar Error Fallback
 * 
 * Minimal error fallback for sidebar to maintain navigation.
 */

import { AlertTriangle } from 'lucide-react';

export function SidebarErrorFallback() {
    return (
        <div className="flex flex-col h-full bg-sidebar text-sidebar-foreground p-4">
            <div className="flex-1 flex items-center justify-center">
                <div className="text-center space-y-3 max-w-xs">
                    <AlertTriangle className="h-8 w-8 text-yellow-500 mx-auto" />
                    <p className="text-sm text-muted-foreground">
                        Sidebar temporarily unavailable
                    </p>
                    <button
                        onClick={() => window.location.reload()}
                        className="text-xs text-primary hover:underline"
                    >
                        Reload page
                    </button>
                </div>
            </div>
        </div>
    );
}
