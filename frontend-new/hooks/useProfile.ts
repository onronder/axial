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
        console.log('📋 [useProfile] Fetching profile...');
        setIsLoading(true);
        setError(null);
        try {
            const { data } = await api.get('/api/v1/settings/profile');
            console.log('📋 [useProfile] ✅ Profile fetched:', data?.first_name, data?.last_name);
            setProfile(data);
        } catch (err: any) {
            console.error('📋 [useProfile] ❌ Failed:', err.response?.status, err.message);
            setError(err.message || 'Failed to fetch profile');
        } finally {
            setIsLoading(false);
        }
    }, []);

    // Only fetch on mount - empty dependency array
    useEffect(() => {
        fetchProfile();
        // eslint-disable-next-line react-hooks/exhaustive-deps
    }, []);

    const updateProfile = async (payload: ProfileUpdatePayload): Promise<boolean> => {
        console.log('📋 [useProfile] Updating with:', payload);
        try {
            const { data } = await api.patch('/api/v1/settings/profile', payload);
            console.log('📋 [useProfile] ✅ Updated');
            setProfile(data);
            toast({
                title: 'Profile updated',
                description: 'Your profile information has been saved.',
            });
            return true;
        } catch (err: any) {
            console.error('📋 [useProfile] ❌ Update failed:', err.message);
            toast({
                title: 'Error',
                description: err.response?.data?.detail || 'Failed to update profile.',
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
