'use client';

import { useState, useEffect, useCallback } from 'react';
import { api } from '@/lib/api';
import { useToast } from '@/hooks/use-toast';

export interface UserProfile {
    id: string;
    user_id: string;
    first_name: string | null;
    last_name: string | null;
    plan: 'free' | 'pro' | 'enterprise';
    theme: 'light' | 'dark' | 'system';
    created_at: string;
    updated_at: string;
}

export interface ProfileUpdatePayload {
    first_name?: string;
    last_name?: string;
    theme?: 'light' | 'dark' | 'system';
}

/**
 * Hook for managing user profile data.
 * Fetches profile on mount and provides update functionality.
 */
export const useProfile = () => {
    const { toast } = useToast();
    const [profile, setProfile] = useState<UserProfile | null>(null);
    const [isLoading, setIsLoading] = useState(true);
    const [error, setError] = useState<string | null>(null);

    const fetchProfile = useCallback(async () => {
        setIsLoading(true);
        setError(null);
        try {
            const { data } = await api.get('/api/v1/settings/profile');
            setProfile(data);
        } catch (err: any) {
            console.error('Failed to fetch profile:', err);
            setError(err.message || 'Failed to fetch profile');
        } finally {
            setIsLoading(false);
        }
    }, []);

    useEffect(() => {
        fetchProfile();
    }, [fetchProfile]);

    const updateProfile = async (payload: ProfileUpdatePayload): Promise<boolean> => {
        try {
            const { data } = await api.patch('/api/v1/settings/profile', payload);
            setProfile(data);
            toast({
                title: 'Profile updated',
                description: 'Your profile information has been saved.',
            });
            return true;
        } catch (err: any) {
            console.error('Failed to update profile:', err);
            toast({
                title: 'Error',
                description: 'Failed to update profile.',
                variant: 'destructive',
            });
            return false;
        }
    };

    return {
        profile,
        isLoading,
        error,
        updateProfile,
        refresh: fetchProfile,
    };
};
