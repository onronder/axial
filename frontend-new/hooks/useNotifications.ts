"use client";

/**
 * useNotifications Hook
 * 
 * Real-time notification system with:
 * - Supabase Realtime subscription for instant updates
 * - Toast notifications for new items
 * - Polling fallback (every 30 seconds)
 * - Notification grouping support
 */

import { useState, useEffect, useCallback, useRef } from "react";
import { authFetch } from "@/lib/api";
import { createClient } from "@supabase/supabase-js";
import { useToast } from "@/hooks/use-toast";

export interface Notification {
    id: string;
    title: string;
    message?: string;
    type: "info" | "success" | "warning" | "error";
    is_read: boolean;
    metadata?: Record<string, unknown>;
    action_url?: string;
    created_at?: string;
}

interface NotificationListResponse {
    notifications: Notification[];
    total: number;
    unread_count: number;
}

// Group similar notifications
export interface GroupedNotification {
    id: string;
    title: string;
    message?: string;
    type: "info" | "success" | "warning" | "error";
    count: number;
    action_url?: string;
    is_read: boolean;
    created_at?: string;
    items: Notification[];
}

const POLL_INTERVAL = 30000; // 30 seconds fallback

// Initialize Supabase client for realtime
const supabaseUrl = process.env.NEXT_PUBLIC_SUPABASE_URL || "";
const supabaseAnonKey = process.env.NEXT_PUBLIC_SUPABASE_ANON_KEY || "";

export function useNotifications() {
    const { toast } = useToast();
    const [notifications, setNotifications] = useState<Notification[]>([]);
    const [unreadCount, setUnreadCount] = useState(0);
    const [total, setTotal] = useState(0);
    const [isLoading, setIsLoading] = useState(false);
    const [error, setError] = useState<string | null>(null);
    const [isRealtimeConnected, setIsRealtimeConnected] = useState(false);

    const subscriptionRef = useRef<any>(null);
    const userIdRef = useRef<string | null>(null);

    // Parse metadata and extract action_url
    const parseNotification = (n: any): Notification => {
        let metadata = n.metadata;
        let action_url = n.action_url;

        // Parse extra_data if present
        if (n.extra_data) {
            try {
                const parsed = typeof n.extra_data === 'string'
                    ? JSON.parse(n.extra_data)
                    : n.extra_data;
                metadata = parsed;
                action_url = parsed?.action_url || action_url;
            } catch {
                // Ignore parse errors
            }
        }

        return {
            id: n.id,
            title: n.title,
            message: n.message,
            type: n.type,
            is_read: n.is_read,
            metadata,
            action_url,
            created_at: n.created_at,
        };
    };

    // Show toast for new notification
    const showNotificationToast = useCallback((notification: Notification) => {
        const variant = notification.type === "error" ? "destructive" : "default";

        toast({
            title: notification.title,
            description: notification.message,
            variant,
            // Include action_url in the toast if needed
        });
    }, [toast]);

    // Add new notification from realtime
    const handleRealtimeInsert = useCallback((payload: any) => {
        const newNotification = parseNotification(payload.new);

        console.log("🔔 [Realtime] New notification:", newNotification.title);

        // Add to list (prepend)
        setNotifications(prev => [newNotification, ...prev]);
        setUnreadCount(prev => prev + 1);
        setTotal(prev => prev + 1);

        // Show toast immediately
        showNotificationToast(newNotification);
    }, [showNotificationToast]);

    // Setup Supabase Realtime subscription
    const setupRealtimeSubscription = useCallback(async () => {
        if (!supabaseUrl || !supabaseAnonKey) {
            console.warn("⚠️ Supabase credentials not configured for realtime");
            return;
        }

        try {
            const supabase = createClient(supabaseUrl, supabaseAnonKey);

            // Get current user ID from profile API
            const response = await authFetch.get("/settings/profile");
            const userId = response.data?.user_id;

            if (!userId) {
                console.warn("⚠️ Could not get user ID for realtime subscription");
                return;
            }

            userIdRef.current = userId;

            // Subscribe to notifications table changes for this user
            const channel = supabase
                .channel('notifications-realtime')
                .on(
                    'postgres_changes',
                    {
                        event: 'INSERT',
                        schema: 'public',
                        table: 'notifications',
                        filter: `user_id=eq.${userId}`,
                    },
                    handleRealtimeInsert
                )
                .subscribe((status) => {
                    console.log("🔔 [Realtime] Subscription status:", status);
                    setIsRealtimeConnected(status === 'SUBSCRIBED');
                });

            subscriptionRef.current = channel;
            console.log("🔔 [Realtime] Subscribed to notifications for user:", userId);

        } catch (err) {
            console.error("❌ [Realtime] Failed to setup subscription:", err);
        }
    }, [handleRealtimeInsert]);

    // Cleanup subscription
    const cleanupSubscription = useCallback(() => {
        if (subscriptionRef.current) {
            subscriptionRef.current.unsubscribe();
            subscriptionRef.current = null;
            setIsRealtimeConnected(false);
            console.log("🔔 [Realtime] Unsubscribed");
        }
    }, []);

    // Fetch unread count (lightweight, for polling fallback)
    const fetchUnreadCount = useCallback(async () => {
        try {
            const response = await authFetch.get("/notifications/unread-count");
            if (response.data) {
                setUnreadCount(response.data.count);
            }
        } catch (err) {
            console.debug("Failed to fetch unread count:", err);
        }
    }, []);

    // Fetch full notification list
    const fetchNotifications = useCallback(async (unreadOnly = false) => {
        setIsLoading(true);
        setError(null);

        try {
            const url = unreadOnly
                ? "/notifications?unread_only=true"
                : "/notifications";
            const response = await authFetch.get(url);

            if (response.data) {
                const data = response.data as NotificationListResponse;
                const parsed = data.notifications.map(parseNotification);
                setNotifications(parsed);
                setTotal(data.total);
                setUnreadCount(data.unread_count);
            }
        } catch (err) {
            setError("Failed to fetch notifications");
            console.error("Failed to fetch notifications:", err);
        } finally {
            setIsLoading(false);
        }
    }, []);

    // Mark single notification as read (optimistic update)
    const markAsRead = useCallback(async (notificationId: string) => {
        setNotifications(prev =>
            prev.map(n => n.id === notificationId ? { ...n, is_read: true } : n)
        );
        setUnreadCount(prev => Math.max(0, prev - 1));

        try {
            await authFetch.patch(`/notifications/${notificationId}/read`);
        } catch (err) {
            setNotifications(prev =>
                prev.map(n => n.id === notificationId ? { ...n, is_read: false } : n)
            );
            setUnreadCount(prev => prev + 1);
            console.error("Failed to mark as read:", err);
        }
    }, []);

    // Mark all notifications as read
    const markAllAsRead = useCallback(async () => {
        const prevNotifications = notifications;
        const prevUnreadCount = unreadCount;

        setNotifications(prev => prev.map(n => ({ ...n, is_read: true })));
        setUnreadCount(0);

        try {
            await authFetch.patch("/notifications/read-all");
        } catch (err) {
            setNotifications(prevNotifications);
            setUnreadCount(prevUnreadCount);
            console.error("Failed to mark all as read:", err);
        }
    }, [notifications, unreadCount]);

    // Clear all notifications
    const clearAll = useCallback(async () => {
        const prevNotifications = notifications;

        setNotifications([]);
        setTotal(0);
        setUnreadCount(0);

        try {
            await authFetch.delete("/notifications/all");
        } catch (err) {
            setNotifications(prevNotifications);
            console.error("Failed to clear notifications:", err);
        }
    }, [notifications]);

    // Group notifications by type+title pattern (e.g., "5 files processed")
    const groupNotifications = useCallback((items: Notification[]): GroupedNotification[] => {
        const groups: Map<string, Notification[]> = new Map();

        items.forEach(item => {
            // Group by type + normalized title pattern
            const key = `${item.type}:${item.title.replace(/\d+/g, 'N')}`;
            const existing = groups.get(key) || [];
            existing.push(item);
            groups.set(key, existing);
        });

        return Array.from(groups.values()).map(group => {
            const first = group[0];
            const totalCount = group.length;

            // Create grouped display
            let title = first.title;
            if (totalCount > 1) {
                // Extract common pattern and show count
                if (first.title.includes("file") || first.title.includes("document")) {
                    title = `${totalCount} files processed`;
                } else if (first.title.includes("page")) {
                    title = `${totalCount} pages crawled`;
                }
            }

            return {
                id: first.id,
                title,
                message: totalCount > 1 ? `${totalCount} similar notifications` : first.message,
                type: first.type,
                count: totalCount,
                action_url: first.action_url,
                is_read: group.every(n => n.is_read),
                created_at: first.created_at,
                items: group,
            };
        });
    }, []);

    // Setup realtime on mount
    useEffect(() => {
        setupRealtimeSubscription();

        return () => {
            cleanupSubscription();
        };
    }, [setupRealtimeSubscription, cleanupSubscription]);

    // Fallback polling (when realtime is disconnected)
    useEffect(() => {
        fetchUnreadCount(); // Initial fetch

        const interval = setInterval(() => {
            // Only poll when tab is visible AND realtime is not connected
            if (!document.hidden && !isRealtimeConnected) {
                fetchUnreadCount();
            }
        }, POLL_INTERVAL);

        const handleVisibilityChange = () => {
            if (!document.hidden) {
                fetchUnreadCount();
            }
        };
        document.addEventListener("visibilitychange", handleVisibilityChange);

        return () => {
            clearInterval(interval);
            document.removeEventListener("visibilitychange", handleVisibilityChange);
        };
    }, [fetchUnreadCount, isRealtimeConnected]);

    return {
        notifications,
        unreadCount,
        total,
        isLoading,
        error,
        isRealtimeConnected,
        fetchNotifications,
        markAsRead,
        markAllAsRead,
        clearAll,
        groupNotifications,
        refresh: fetchUnreadCount,
    };
}
