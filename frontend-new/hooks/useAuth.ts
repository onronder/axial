"use client";

import { useState, useEffect, useCallback } from "react";
import { supabase } from "@/lib/supabase";
import { User, AuthError, Provider } from "@supabase/supabase-js";
import { useRouter } from "next/navigation";

/**
 * Extended user interface supporting both email signup and OAuth providers.
 * OAuth providers like Google use given_name/family_name instead of first_name/last_name.
 */
export interface CustomUser {
    id: string;
    email?: string;
    name?: string;
    firstName?: string;
    lastName?: string;
    avatarUrl?: string;
    provider?: string;
    plan?: string;
}

/**
 * OAuth provider options for sign-in.
 */
export interface OAuthOptions {
    scopes?: string;
    redirectTo?: string;
}

/**
 * Production-grade authentication hook using Supabase SSR client.
 * 
 * This hook:
 * - Uses the SSR-compatible browser client that manages cookies
 * - Properly handles loading states to prevent flash of unauthenticated content
 * - Listens to auth state changes for real-time session updates
 * - Provides typed error handling for auth operations
 * - Supports both email/password and OAuth authentication
 * - Maps user metadata from various providers (email, Google, etc.)
 */
export const useAuth = () => {
    const [user, setUser] = useState<CustomUser | null>(null);
    const [loading, setLoading] = useState(true);
    const router = useRouter();

    /**
     * Maps Supabase User to CustomUser with app-specific fields.
     * Handles both email signup (first_name/last_name) and OAuth (given_name/family_name).
     */
    const mapUser = useCallback((supabaseUser: User | null | undefined): CustomUser | null => {
        if (!supabaseUser) return null;

        const metadata = supabaseUser.user_metadata || {};
        const appMetadata = supabaseUser.app_metadata || {};

        // Support both email signup (first_name/last_name) and OAuth (given_name/family_name)
        const firstName = metadata.first_name || metadata.given_name || '';
        const lastName = metadata.last_name || metadata.family_name || '';
        
        // Full name: prefer explicit full_name, then combined first+last, then provider name
        const fullName = metadata.full_name 
            || metadata.name 
            || (firstName && lastName ? `${firstName} ${lastName}`.trim() : '')
            || supabaseUser.email?.split('@')[0] 
            || '';

        return {
            id: supabaseUser.id,
            email: supabaseUser.email,
            name: fullName,
            firstName,
            lastName,
            avatarUrl: metadata.avatar_url || metadata.picture,
            provider: appMetadata.provider || 'email',
            plan: 'Free', // Default plan - actual plan fetched from profiles table
        };
    }, []);

    useEffect(() => {
        let mounted = true;

        /**
         * Initialize auth state from existing session
         */
        const initAuth = async () => {
            try {
                const { data: { session }, error } = await supabase.auth.getSession();

                if (error) {
                    console.error("Session fetch error:", error.message);
                }

                if (mounted) {
                    setUser(mapUser(session?.user));
                    setLoading(false);
                }
            } catch (error) {
                console.error("Auth init error:", error);
                if (mounted) {
                    setUser(null);
                    setLoading(false);
                }
            }
        };

        initAuth();

        /**
         * Subscribe to auth state changes (login, logout, token refresh)
         */
        const { data: { subscription } } = supabase.auth.onAuthStateChange(
            async (event, session) => {
                if (mounted) {
                    setUser(mapUser(session?.user));
                    setLoading(false);

                    // Handle specific auth events
                    if (event === 'SIGNED_OUT') {
                        router.push('/login');
                    }
                    
                    // Log OAuth signin for debugging (development only)
                    if (process.env.NODE_ENV === 'development' && event === 'SIGNED_IN' && session?.user?.app_metadata?.provider) {
                        console.log(`🔐 [Auth] Signed in via ${session.user.app_metadata.provider}`);
                    }
                }
            }
        );

        return () => {
            mounted = false;
            subscription.unsubscribe();
        };
    }, [mapUser, router]);

    /**
     * Sign in with email and password
     */
    const login = async (email: string, password: string): Promise<void> => {
        const { error } = await supabase.auth.signInWithPassword({
            email,
            password,
        });

        if (error) {
            throw new Error(getAuthErrorMessage(error));
        }
    };

    /**
     * Register a new user with email and password
     */
    const register = async (firstName: string, lastName: string, email: string, password: string): Promise<void> => {
        const { error } = await supabase.auth.signUp({
            email,
            password,
            options: {
                data: {
                    full_name: `${firstName} ${lastName}`,
                    first_name: firstName,
                    last_name: lastName,
                },
            },
        });

        if (error) {
            throw new Error(getAuthErrorMessage(error));
        }
    };

    /**
     * Sign in with OAuth provider (Google, GitHub, etc.)
     * 
     * @param provider - OAuth provider name
     * @param options - Optional configuration for scopes and redirect
     * 
     * For Google OAuth:
     * - Requests offline access for refresh tokens
     * - Prompts for consent to ensure refresh token is provided
     * - Requests profile scopes for name and avatar
     */
    const signInWithOAuth = async (
        provider: Provider,
        options?: OAuthOptions
    ): Promise<void> => {
        const redirectTo = options?.redirectTo || `${window.location.origin}/auth/callback`;
        
        // Provider-specific configurations
        const providerConfig: Record<string, { queryParams?: Record<string, string>; scopes?: string }> = {
            google: {
                queryParams: {
                    access_type: 'offline',  // Request refresh token
                    prompt: 'consent',       // Force consent screen for refresh token
                },
                scopes: options?.scopes || 'openid email profile',
            },
            github: {
                scopes: options?.scopes || 'read:user user:email',
            },
        };

        const config = providerConfig[provider] || {};

        const { error } = await supabase.auth.signInWithOAuth({
            provider,
            options: {
                redirectTo,
                queryParams: config.queryParams,
                scopes: config.scopes,
            },
        });

        if (error) {
            throw new Error(getAuthErrorMessage(error));
        }
    };

    /**
     * Request password reset email
     * 
     * @param email - User's email address
     */
    const resetPassword = async (email: string): Promise<void> => {
        const redirectTo = typeof window !== 'undefined'
            ? `${window.location.origin}/auth/reset-password`
            : process.env.NEXT_PUBLIC_SITE_URL
                ? `${process.env.NEXT_PUBLIC_SITE_URL}/auth/reset-password`
                : undefined;

        const { error } = await supabase.auth.resetPasswordForEmail(email, {
            redirectTo,
        });

        if (error) {
            throw new Error(getAuthErrorMessage(error));
        }
    };

    /**
     * Update password for currently logged-in user
     * 
     * @param newPassword - New password to set
     */
    const updatePassword = async (newPassword: string): Promise<void> => {
        const { error } = await supabase.auth.updateUser({
            password: newPassword,
        });

        if (error) {
            throw new Error(getAuthErrorMessage(error));
        }
    };

    /**
     * Sign out the current user
     * 
     * IMPORTANT: Must navigate BEFORE clearing user state to avoid
     * PaywallGuard showing pricing page during the transition.
     */
    const logout = async (): Promise<void> => {
        // 1. Navigate to login FIRST (prevents flash of pricing page)
        router.push("/login");

        // 2. Sign out from Supabase (clears session/cookies)
        try {
            const { error } = await supabase.auth.signOut();
            if (error) {
                console.error("Logout error:", error.message);
            }
        } catch (error) {
            console.error("Logout exception:", error);
        }

        // 3. Clear local user state last
        setUser(null);
    };

    /**
     * Get the current session (useful for checking auth state)
     */
    const getSession = async () => {
        const { data: { session }, error } = await supabase.auth.getSession();
        if (error) {
            console.error("Get session error:", error.message);
            return null;
        }
        return session;
    };

    return {
        user,
        loading,
        isAuthenticated: !!user,
        login,
        register,
        logout,
        signInWithOAuth,
        resetPassword,
        updatePassword,
        getSession,
    };
};

/**
 * Convert Supabase AuthError to user-friendly message
 */
function getAuthErrorMessage(error: AuthError): string {
    const errorMap: Record<string, string> = {
        'Invalid login credentials': 'Invalid email or password. Please try again.',
        'Email not confirmed': 'Please verify your email before logging in.',
        'User already registered': 'An account with this email already exists.',
        'Password should be at least 6 characters': 'Password must be at least 6 characters long.',
        'Signup requires a valid password': 'Please provide a valid password.',
        'Email rate limit exceeded': 'Too many attempts. Please try again later.',
        'For security purposes, you can only request this once every 60 seconds': 'Please wait 60 seconds before requesting another email.',
        'New password should be different from the old password': 'Please choose a different password than your current one.',
        'Auth session missing!': 'Your session has expired. Please log in again.',
        'Token has expired or is invalid': 'Your session has expired. Please log in again.',
    };

    return errorMap[error.message] || error.message;
}

/**
 * Export the auth error message helper for use in other components
 */
export { getAuthErrorMessage };
