"use client";

/**
 * NotificationCenter Component
 * 
 * A polished notification center with:
 * - Bell icon with unread badge
 * - Popover with notification list
 * - Filter tabs (All / Unread)
 * - Dynamic icons and colors by type
 * - Mark as read functionality
 */

import { useState, useEffect } from "react";
import { Bell, CheckCircle2, AlertTriangle, XCircle, Info, Check, Trash2, Loader2 } from "lucide-react";
import { Button } from "@/components/ui/button";
import { Badge } from "@/components/ui/badge";
import {
    Popover,
    PopoverContent,
    PopoverTrigger,
} from "@/components/ui/popover";
import { ScrollArea } from "@/components/ui/scroll-area";
import { Tabs, TabsContent, TabsList, TabsTrigger } from "@/components/ui/tabs";
import { useNotifications, Notification } from "@/hooks/useNotifications";
import { cn } from "@/lib/utils";

// Helper to format relative time
function formatRelativeTime(dateString?: string): string {
    if (!dateString) return "";

    const date = new Date(dateString);
    const now = new Date();
    const diffMs = now.getTime() - date.getTime();
    const diffMins = Math.floor(diffMs / (1000 * 60));
    const diffHours = Math.floor(diffMs / (1000 * 60 * 60));
    const diffDays = Math.floor(diffMs / (1000 * 60 * 60 * 24));

    if (diffMins < 1) return "Just now";
    if (diffMins < 60) return `${diffMins}m ago`;
    if (diffHours < 24) return `${diffHours}h ago`;
    if (diffDays < 7) return `${diffDays}d ago`;

    return date.toLocaleDateString();
}

// Notification type config
const typeConfig: Record<string, { icon: React.ReactNode; color: string; bg: string }> = {
    success: {
        icon: <CheckCircle2 className="h-4 w-4" />,
        color: "text-green-600 dark:text-green-400",
        bg: "bg-green-50 dark:bg-green-500/10",
    },
    warning: {
        icon: <AlertTriangle className="h-4 w-4" />,
        color: "text-yellow-600 dark:text-yellow-400",
        bg: "bg-yellow-50 dark:bg-yellow-500/10",
    },
    error: {
        icon: <XCircle className="h-4 w-4" />,
        color: "text-red-600 dark:text-red-400",
        bg: "bg-red-50 dark:bg-red-500/10",
    },
    info: {
        icon: <Info className="h-4 w-4" />,
        color: "text-blue-600 dark:text-blue-400",
        bg: "bg-blue-50 dark:bg-blue-500/10",
    },
};

interface NotificationItemProps {
    notification: Notification;
    onMarkAsRead: (id: string) => void;
}

/**
 * Validates that a URL is safe for redirect (same-origin or trusted external domains).
 * Prevents open redirect vulnerabilities.
 */
function isSafeRedirectUrl(url: string): boolean {
    try {
        const parsed = new URL(url, window.location.origin);
        // Allow same-origin URLs
        if (parsed.origin === window.location.origin) {
            return true;
        }
        // Allow trusted external domains (billing/checkout)
        const trustedDomains = ['polar.sh', 'checkout.polar.sh'];
        return trustedDomains.some(domain => parsed.hostname === domain || parsed.hostname.endsWith(`.${domain}`));
    } catch {
        // Invalid URL - only allow relative paths
        return url.startsWith('/') && !url.startsWith('//');
    }
}

function NotificationItem({ notification, onMarkAsRead }: NotificationItemProps) {
    const config = typeConfig[notification.type] || typeConfig.info;
    const [isExpanded, setIsExpanded] = useState(false);

    // Get action_url from metadata
    const actionUrl = notification.metadata?.action_url as string | undefined;
    // Validate URL to prevent open redirect attacks
    const safeActionUrl = actionUrl && isSafeRedirectUrl(actionUrl) ? actionUrl : undefined;

    const handleClick = () => {
        // Mark as read when clicked
        if (!notification.is_read) {
            onMarkAsRead(notification.id);
        }

        // Navigate to action_url if present and validated
        if (safeActionUrl) {
            window.location.href = safeActionUrl;
        } else {
            setIsExpanded(!isExpanded);
        }
    };

    return (
        <div
            className={cn(
                "p-3 border-b border-border transition-colors cursor-pointer",
                "hover:bg-muted/50",
                !notification.is_read && "bg-muted/30",
                safeActionUrl && "hover:bg-primary/5"
            )}
            onClick={handleClick}
        >
            <div className="flex gap-3">
                {/* Icon */}
                <div className={cn("flex-shrink-0 p-2 rounded-full", config.bg)}>
                    <span className={config.color}>{config.icon}</span>
                </div>

                {/* Content */}
                <div className="flex-1 min-w-0">
                    <div className="flex items-start justify-between gap-2">
                        <p className={cn(
                            "text-sm font-medium truncate",
                            !notification.is_read && "font-semibold"
                        )}>
                            {notification.title}
                        </p>
                        {!notification.is_read && (
                            <Button
                                variant="ghost"
                                size="sm"
                                className="h-6 w-6 p-0 flex-shrink-0"
                                onClick={(e) => {
                                    e.stopPropagation();
                                    onMarkAsRead(notification.id);
                                }}
                            >
                                <Check className="h-3 w-3" />
                            </Button>
                        )}
                    </div>

                    {notification.message && (
                        <p className={cn(
                            "text-xs text-muted-foreground mt-0.5",
                            isExpanded ? "" : "truncate"
                        )}>
                            {notification.message}
                        </p>
                    )}

                    <p className="text-xs text-muted-foreground/70 mt-1">
                        {formatRelativeTime(notification.created_at)}
                        {safeActionUrl && (
                            <span className="ml-2 text-primary">Click to open →</span>
                        )}
                    </p>
                </div>

                {/* Unread indicator */}
                {!notification.is_read && (
                    <div className="w-2 h-2 rounded-full bg-blue-500 flex-shrink-0 mt-2" />
                )}
            </div>
        </div>
    );
}

function EmptyState({ message }: { message: string }) {
    return (
        <div className="flex flex-col items-center justify-center py-12 text-center">
            <Bell className="h-10 w-10 text-muted-foreground/50 mb-3" />
            <p className="text-sm text-muted-foreground">{message}</p>
        </div>
    );
}

export function NotificationCenter() {
    const {
        notifications,
        unreadCount,
        isLoading,
        fetchNotifications,
        markAsRead,
        markAllAsRead,
        clearAll,
    } = useNotifications();

    const [isOpen, setIsOpen] = useState(false);
    const [activeTab, setActiveTab] = useState<"all" | "unread">("all");

    // Fetch notifications when popover opens
    useEffect(() => {
        if (isOpen) {
            fetchNotifications(activeTab === "unread");
        }
    }, [isOpen, activeTab, fetchNotifications]);

    const displayedNotifications = activeTab === "unread"
        ? notifications.filter(n => !n.is_read)
        : notifications;

    return (
        <Popover open={isOpen} onOpenChange={setIsOpen}>
            <PopoverTrigger asChild>
                <Button
                    variant="ghost"
                    size="sm"
                    className="relative h-9 w-9 p-0"
                >
                    <Bell className="h-5 w-5" />
                    {unreadCount > 0 && (
                        <Badge
                            variant="destructive"
                            className="absolute -top-1 -right-1 h-5 min-w-5 flex items-center justify-center p-0 text-xs"
                        >
                            {unreadCount > 99 ? "99+" : unreadCount}
                        </Badge>
                    )}
                </Button>
            </PopoverTrigger>

            <PopoverContent
                className="w-96 p-0"
                align="end"
                sideOffset={8}
            >
                {/* Header */}
                <div className="flex items-center justify-between px-4 py-3 border-b border-border">
                    <h3 className="font-semibold">Notifications</h3>
                    <div className="flex items-center gap-1">
                        {unreadCount > 0 && (
                            <Button
                                variant="ghost"
                                size="sm"
                                className="h-8 text-xs"
                                onClick={markAllAsRead}
                            >
                                <Check className="h-3 w-3 mr-1" />
                                Mark all read
                            </Button>
                        )}
                        <Button
                            variant="ghost"
                            size="sm"
                            className="h-8 w-8 p-0"
                            onClick={clearAll}
                        >
                            <Trash2 className="h-4 w-4" />
                        </Button>
                    </div>
                </div>

                {/* Tabs */}
                <Tabs value={activeTab} onValueChange={(v) => setActiveTab(v as "all" | "unread")}>
                    <TabsList className="w-full rounded-none border-b border-border">
                        <TabsTrigger value="all" className="flex-1">
                            All
                        </TabsTrigger>
                        <TabsTrigger value="unread" className="flex-1">
                            Unread {unreadCount > 0 && `(${unreadCount})`}
                        </TabsTrigger>
                    </TabsList>

                    <TabsContent value={activeTab} className="m-0">
                        <ScrollArea className="h-[400px]">
                            {isLoading ? (
                                <div className="flex items-center justify-center py-12">
                                    <Loader2 className="h-6 w-6 animate-spin text-primary" />
                                </div>
                            ) : displayedNotifications.length === 0 ? (
                                <EmptyState
                                    message={activeTab === "unread"
                                        ? "All caught up! No unread notifications."
                                        : "No notifications yet."
                                    }
                                />
                            ) : (
                                displayedNotifications.map((notification) => (
                                    <NotificationItem
                                        key={notification.id}
                                        notification={notification}
                                        onMarkAsRead={markAsRead}
                                    />
                                ))
                            )}
                        </ScrollArea>
                    </TabsContent>
                </Tabs>
            </PopoverContent>
        </Popover>
    );
}
