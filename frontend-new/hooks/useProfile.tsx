'use client';

import { createContext, useContext, useState, useEffect, useCallback, useRef, ReactNode } from 'react';
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

interface ProfileContextType {
    profile: UserProfile | null;
    isLoading: boolean;
    error: string | null;
    updateProfile: (payload: ProfileUpdatePayload) => Promise<boolean>;
    refresh: () => Promise<void>;
}

const ProfileContext = createContext<ProfileContextType | null>(null);

/**
 * Provider component that wraps the app and provides profile state.
 * This ensures only ONE fetch happens regardless of how many components use the hook.
 */
export function ProfileProvider({ children }: { children: ReactNode }) {
    const { toast } = useToast();
    const [profile, setProfile] = useState<UserProfile | null>(null);
    const [isLoading, setIsLoading] = useState(true);
    const [error, setError] = useState<string | null>(null);
    const hasFetched = useRef(false);

    const fetchProfile = useCallback(async () => {
        console.log('📋 [useProfile] Fetching profile...');
        setIsLoading(true);
        setError(null);
        try {
            const { data } = await api.get('/settings/profile');
            console.log('📋 [useProfile] ✅ Profile fetched:', data?.first_name, data?.last_name);
            setProfile(data);
        } catch (err: any) {
            console.error('📋 [useProfile] ❌ Failed:', err.response?.status, err.message);
            setError(err.message || 'Failed to fetch profile');
        } finally {
            setIsLoading(false);
        }
    }, []);

    // Fetch once on mount - prevents duplicate fetches
    useEffect(() => {
        if (!hasFetched.current) {
            hasFetched.current = true;
            fetchProfile();
        }
    }, [fetchProfile]);

    const updateProfile = useCallback(async (payload: ProfileUpdatePayload): Promise<boolean> => {
        console.log('📋 [useProfile] Updating with:', payload);
        try {
            const { data } = await api.patch('/settings/profile', payload);
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
    }, [toast]);

    const value: ProfileContextType = {
        profile,
        isLoading,
        error,
        updateProfile,
        refresh: fetchProfile,
    };

    return (
        <ProfileContext.Provider value={value} >
            {children}
        </ProfileContext.Provider>
    );
}

/**
 * Hook for accessing profile from anywhere in the app.
 * All consumers share the same state - no duplicate API calls.
 */
export const useProfile = (): ProfileContextType => {
    const context = useContext(ProfileContext);
    if (!context) {
        // Fallback for when used outside provider (e.g., in settings pages)
        // Return a minimal non-error state to prevent crashes
        console.warn('[useProfile] Used outside ProfileProvider - returning default state');
        return {
            profile: null,
            isLoading: false,
            error: null,
            updateProfile: async () => false,
            refresh: async () => { },
        };
    }
    return context;
};
