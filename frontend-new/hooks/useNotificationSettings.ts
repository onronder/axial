'use client';

import { useState, useEffect, useCallback } from 'react';
import { api } from '@/lib/api';
import { useToast } from '@/hooks/use-toast';

export interface NotificationSetting {
    id: string;
    setting_key: string;
    setting_label: string;
    setting_description: string | null;
    category: 'email' | 'system';
    enabled: boolean;
}

/**
 * Hook for managing user notification settings.
 * Fetches settings on mount and provides toggle functionality.
 */
export const useNotificationSettings = () => {
    const { toast } = useToast();
    const [settings, setSettings] = useState<NotificationSetting[]>([]);
    const [isLoading, setIsLoading] = useState(true);
    const [error, setError] = useState<string | null>(null);

    const fetchSettings = useCallback(async () => {
        setIsLoading(true);
        setError(null);
        try {
            const { data } = await api.get('api/v1/settings/notifications');
            setSettings(data);
        } catch (err: any) {
            console.error('Failed to fetch notification settings:', err);
            setError(err.message || 'Failed to fetch settings');
        } finally {
            setIsLoading(false);
        }
    }, []);

    useEffect(() => {
        fetchSettings();
    }, [fetchSettings]);

    const toggleSetting = async (settingKey: string): Promise<boolean> => {
        // Optimistic update
        const currentSetting = settings.find(s => s.setting_key === settingKey);
        if (!currentSetting) return false;

        const newEnabled = !currentSetting.enabled;

        // Update local state immediately
        setSettings(prev => prev.map(s =>
            s.setting_key === settingKey ? { ...s, enabled: newEnabled } : s
        ));

        try {
            const { data } = await api.patch('api/v1/settings/notifications', {
                setting_key: settingKey,
                enabled: newEnabled,
            });

            // Update with server response
            setSettings(prev => prev.map(s =>
                s.setting_key === settingKey ? data : s
            ));

            toast({
                title: 'Preference updated',
                description: 'Your notification settings have been saved.',
            });
            return true;
        } catch (err: any) {
            console.error('Failed to update notification setting:', err);

            // Revert optimistic update
            setSettings(prev => prev.map(s =>
                s.setting_key === settingKey ? { ...s, enabled: !newEnabled } : s
            ));

            toast({
                title: 'Error',
                description: 'Failed to update notification setting.',
                variant: 'destructive',
            });
            return false;
        }
    };

    // Group settings by category for easy UI rendering
    const emailSettings = settings.filter(s => s.category === 'email');
    const systemSettings = settings.filter(s => s.category === 'system');

    return {
        settings,
        emailSettings,
        systemSettings,
        isLoading,
        error,
        toggleSetting,
        refresh: fetchSettings,
    };
};
