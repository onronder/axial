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
        console.log('📋 [useProfile] Starting profile fetch...');
        setIsLoading(true);
        setError(null);
        try {
            console.log('📋 [useProfile] Making API request to /api/v1/settings/profile');
            const { data } = await api.get('/api/v1/settings/profile');
            console.log('📋 [useProfile] ✅ Profile fetched successfully:', data);
            setProfile(data);
        } catch (err: any) {
            console.error('📋 [useProfile] ❌ Failed to fetch profile:', err);
            console.error('📋 [useProfile] Error response:', err.response?.data);
            console.error('📋 [useProfile] Error status:', err.response?.status);
            setError(err.message || 'Failed to fetch profile');
        } finally {
            setIsLoading(false);
            console.log('📋 [useProfile] Fetch complete. isLoading:', false);
        }
    }, []);

    useEffect(() => {
        console.log('📋 [useProfile] Hook mounted, triggering fetchProfile');
        fetchProfile();
    }, [fetchProfile]);

    const updateProfile = async (payload: ProfileUpdatePayload): Promise<boolean> => {
        console.log('📋 [useProfile] Starting profile update with payload:', payload);
        try {
            console.log('📋 [useProfile] Making PATCH request to /api/v1/settings/profile');
            const { data } = await api.patch('/api/v1/settings/profile', payload);
            console.log('📋 [useProfile] ✅ Profile updated successfully:', data);
            setProfile(data);
            toast({
                title: 'Profile updated',
                description: 'Your profile information has been saved.',
            });
            return true;
        } catch (err: any) {
            console.error('📋 [useProfile] ❌ Failed to update profile:', err);
            console.error('📋 [useProfile] Error response:', err.response?.data);
            console.error('📋 [useProfile] Error status:', err.response?.status);
            toast({
                title: 'Error',
                description: err.response?.data?.detail || 'Failed to update profile.',
                variant: 'destructive',
            });
            return false;
        }
    };

    // Log current state on each render (helpful for debugging)
    console.log('📋 [useProfile] Current state:', {
        hasProfile: !!profile,
        isLoading,
        hasError: !!error
    });

    return {
        profile,
        isLoading,
        error,
        updateProfile,
        refresh: fetchProfile,
    };
};
