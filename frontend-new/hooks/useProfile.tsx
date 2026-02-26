'use client';

import { createContext, useContext, useMemo, useCallback, ReactNode } from 'react';
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import { api } from '@/lib/api';
import { useToast } from '@/hooks/use-toast';

export interface UserProfile {
    id: string;
    user_id: string;
    first_name: string | null;
    last_name: string | null;
    plan: 'free' | 'starter' | 'pro' | 'enterprise';
    theme: 'light' | 'dark' | 'system';
    has_team?: boolean;
    role?: 'admin' | 'editor' | 'viewer';
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

const PROFILE_QUERY_KEY = ['profile'] as const;

type ApiError = {
    response?: {
        status?: number;
        data?: {
            detail?: string;
        };
    };
    message?: string;
};

const getErrorMessage = (error: unknown, fallback: string): string => {
    const apiError = error as ApiError;
    if (apiError.response?.data?.detail) {
        return apiError.response.data.detail;
    }
    if (error instanceof Error && error.message) {
        return error.message;
    }
    return fallback;
};

/**
 * Provider component that wraps the app and provides profile state.
 * Uses React Query for caching, retry, dedup, and cross-tab sync.
 */
export function ProfileProvider({ children }: { children: ReactNode }) {
    const { toast } = useToast();
    const queryClient = useQueryClient();

    const {
        data: profile = null,
        isLoading,
        error: queryError,
    } = useQuery<UserProfile | null>({
        queryKey: PROFILE_QUERY_KEY,
        queryFn: async ({ signal }) => {
            const { data } = await api.get('/settings/profile', { signal });
            return data;
        },
    });

    const error = queryError ? getErrorMessage(queryError, 'Failed to fetch profile') : null;

    const { mutateAsync } = useMutation({
        mutationFn: async (payload: ProfileUpdatePayload) => {
            const { data } = await api.patch('/settings/profile', payload);
            return data as UserProfile;
        },
        onSuccess: (data) => {
            queryClient.setQueryData(PROFILE_QUERY_KEY, data);
            toast({
                title: 'Profile updated',
                description: 'Your profile information has been saved.',
            });
        },
        onError: (err: unknown) => {
            toast({
                title: 'Error',
                description: getErrorMessage(err, 'Failed to update profile.'),
                variant: 'destructive',
            });
        },
    });

    const updateProfile = useCallback(async (payload: ProfileUpdatePayload): Promise<boolean> => {
        try {
            await mutateAsync(payload);
            return true;
        } catch {
            return false;
        }
    }, [mutateAsync]);

    const refresh = useCallback(async () => {
        await queryClient.invalidateQueries({ queryKey: PROFILE_QUERY_KEY });
    }, [queryClient]);

    const value = useMemo<ProfileContextType>(() => ({
        profile,
        isLoading,
        error,
        updateProfile,
        refresh,
    }), [profile, isLoading, error, updateProfile, refresh]);

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
        if (process.env.NODE_ENV !== 'production') {
            console.warn('[useProfile] Used outside ProfileProvider - returning default state');
        }
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
