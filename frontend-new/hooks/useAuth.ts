"use client";

import { useState, useEffect, useCallback } from "react";
import { supabase } from "@/lib/supabase";
import { User, AuthError } from "@supabase/supabase-js";
import { useRouter } from "next/navigation";

export interface CustomUser {
    id: string;
    email?: string;
    name?: string;
    plan?: string;
}

/**
 * Production-grade authentication hook using Supabase SSR client.
 * 
 * This hook:
 * - Uses the SSR-compatible browser client that manages cookies
 * - Properly handles loading states to prevent flash of unauthenticated content
 * - Listens to auth state changes for real-time session updates
 * - Provides typed error handling for auth operations
 */
export const useAuth = () => {
    const [user, setUser] = useState<CustomUser | null>(null);
    const [loading, setLoading] = useState(true);
    const router = useRouter();

    /**
     * Maps Supabase User to CustomUser with app-specific fields
     */
    const mapUser = useCallback((supabaseUser: User | null | undefined): CustomUser | null => {
        if (!supabaseUser) return null;
        return {
            id: supabaseUser.id,
            email: supabaseUser.email,
            name: supabaseUser.user_metadata?.full_name || supabaseUser.email?.split('@')[0],
            plan: 'Free' // Default plan - can be fetched from profiles table later
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

                    // Optional: Handle specific auth events
                    if (event === 'SIGNED_OUT') {
                        router.push('/login');
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
     * Register a new user
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
     * Sign out the current user
     */
    const logout = async (): Promise<void> => {
        const { error } = await supabase.auth.signOut();

        if (error) {
            console.error("Logout error:", error.message);
        }

        setUser(null);
        router.push("/auth/login");
    };

    return {
        user,
        loading,
        isAuthenticated: !!user,
        login,
        register,
        logout
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
    };

    return errorMap[error.message] || error.message;
}
