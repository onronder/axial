"use client";

/**
 * useNotifications Hook
 * 
 * Manages user notifications with:
 * - Polling for unread count (every 30 seconds)
 * - Fetching full notification list on demand
 * - Optimistic updates for mark as read
 */

import { useState, useEffect, useCallback } from "react";
import { authFetch } from "@/lib/api";

export interface Notification {
    id: string;
    title: string;
    message?: string;
    type: "info" | "success" | "warning" | "error";
    is_read: boolean;
    metadata?: Record<string, unknown>;
    created_at?: string;
}

interface NotificationListResponse {
    notifications: Notification[];
    total: number;
    unread_count: number;
}

const POLL_INTERVAL = 30000; // 30 seconds

export function useNotifications() {
    const [notifications, setNotifications] = useState<Notification[]>([]);
    const [unreadCount, setUnreadCount] = useState(0);
    const [total, setTotal] = useState(0);
    const [isLoading, setIsLoading] = useState(false);
    const [error, setError] = useState<string | null>(null);

    // Fetch unread count (lightweight, for polling)
    const fetchUnreadCount = useCallback(async () => {
        try {
            const response = await authFetch.get("/notifications/unread-count");
            if (response.data) {
                setUnreadCount(response.data.count);
            }
        } catch (err) {
            // Silently fail for polling - don't disrupt UX
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
                setNotifications(data.notifications);
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
        // Optimistic update
        setNotifications(prev =>
            prev.map(n => n.id === notificationId ? { ...n, is_read: true } : n)
        );
        setUnreadCount(prev => Math.max(0, prev - 1));

        try {
            await authFetch.patch(`/notifications/${notificationId}/read`);
        } catch (err) {
            // Revert on error
            setNotifications(prev =>
                prev.map(n => n.id === notificationId ? { ...n, is_read: false } : n)
            );
            setUnreadCount(prev => prev + 1);
            console.error("Failed to mark as read:", err);
        }
    }, []);

    // Mark all notifications as read
    const markAllAsRead = useCallback(async () => {
        // Optimistic update
        const prevNotifications = notifications;
        const prevUnreadCount = unreadCount;

        setNotifications(prev => prev.map(n => ({ ...n, is_read: true })));
        setUnreadCount(0);

        try {
            await authFetch.patch("/notifications/read-all");
        } catch (err) {
            // Revert on error
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
            // Revert on error
            setNotifications(prevNotifications);
            console.error("Failed to clear notifications:", err);
        }
    }, [notifications]);

    // Poll for unread count (pause when tab is hidden for performance)
    useEffect(() => {
        fetchUnreadCount(); // Initial fetch

        const interval = setInterval(() => {
            // Only poll when tab is visible
            if (!document.hidden) {
                fetchUnreadCount();
            }
        }, POLL_INTERVAL);

        // Also refresh when tab becomes visible again
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
    }, [fetchUnreadCount]);

    return {
        notifications,
        unreadCount,
        total,
        isLoading,
        error,
        fetchNotifications,
        markAsRead,
        markAllAsRead,
        clearAll,
        refresh: fetchUnreadCount,
    };
}
