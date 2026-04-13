"use client";

import { useCallback, useMemo } from "react";
import { AuthError, Provider, User } from "@supabase/supabase-js";
import { supabase } from "@/lib/supabase";
import { useSession } from "@/components/providers/SessionProvider";

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

function mapUser(supabaseUser: User | null | undefined): CustomUser | null {
    if (!supabaseUser) {
        return null;
    }

    const metadata = supabaseUser.user_metadata || {};
    const appMetadata = supabaseUser.app_metadata || {};

    const firstName = metadata.first_name || metadata.given_name || "";
    const lastName = metadata.last_name || metadata.family_name || "";
    const fullName =
        metadata.full_name ||
        metadata.name ||
        (firstName && lastName ? `${firstName} ${lastName}`.trim() : "") ||
        supabaseUser.email?.split("@")[0] ||
        "";

    return {
        id: supabaseUser.id,
        email: supabaseUser.email,
        name: fullName,
        firstName,
        lastName,
        avatarUrl: metadata.avatar_url || metadata.picture,
        provider: appMetadata.provider || "email",
        plan: "Free",
    };
}

/**
 * Production-grade authentication hook backed by the root SessionProvider.
 *
 * All session state flows from a single Supabase subscription owned by SessionProvider.
 * This hook only adds typed action methods and app-specific user mapping.
 */
export const useAuth = () => {
    const { session, user: rawUser, loading, signOut } = useSession();
    const user = useMemo(() => mapUser(rawUser), [rawUser]);

    const login = useCallback(async (email: string, password: string): Promise<void> => {
        const { error } = await supabase.auth.signInWithPassword({
            email,
            password,
        });

        if (error) {
            throw new Error(getAuthErrorMessage(error));
        }
    }, []);

    const register = useCallback(
        async (
            firstName: string,
            lastName: string,
            email: string,
            password: string
        ): Promise<void> => {
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
        },
        []
    );

    const signInWithOAuth = useCallback(
        async (provider: Provider, options?: OAuthOptions): Promise<void> => {
            const redirectTo =
                options?.redirectTo || `${window.location.origin}/auth/callback`;

            const providerConfig: Record<
                string,
                { queryParams?: Record<string, string>; scopes?: string }
            > = {
                google: {
                    queryParams: {
                        access_type: "offline",
                        prompt: "consent",
                    },
                    scopes: options?.scopes || "openid email profile",
                },
                github: {
                    scopes: options?.scopes || "read:user user:email",
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
        },
        []
    );

    const resetPassword = useCallback(async (email: string): Promise<void> => {
        const redirectTo =
            typeof window !== "undefined"
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
    }, []);

    const updatePassword = useCallback(async (newPassword: string): Promise<void> => {
        const { error } = await supabase.auth.updateUser({
            password: newPassword,
        });

        if (error) {
            throw new Error(getAuthErrorMessage(error));
        }
    }, []);

    const logout = useCallback(async (): Promise<void> => {
        await signOut();
    }, [signOut]);

    const getSession = useCallback(async () => session, [session]);

    return useMemo(
        () => ({
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
        }),
        [
            getSession,
            loading,
            login,
            logout,
            register,
            resetPassword,
            signInWithOAuth,
            updatePassword,
            user,
        ]
    );
};

/**
 * Convert Supabase AuthError to user-friendly message
 */
function getAuthErrorMessage(error: AuthError): string {
    const errorMap: Record<string, string> = {
        "Invalid login credentials":
            "Invalid email or password. Please try again.",
        "Email not confirmed":
            "Please verify your email before logging in.",
        "User already registered":
            "An account with this email already exists.",
        "Password should be at least 6 characters":
            "Password must be at least 6 characters long.",
        "Signup requires a valid password":
            "Please provide a valid password.",
        "Email rate limit exceeded":
            "Too many attempts. Please try again later.",
        "For security purposes, you can only request this once every 60 seconds":
            "Please wait 60 seconds before requesting another email.",
        "New password should be different from the old password":
            "Please choose a different password than your current one.",
        "Auth session missing!":
            "Your session has expired. Please log in again.",
        "Token has expired or is invalid":
            "Your session has expired. Please log in again.",
    };

    return errorMap[error.message] || error.message;
}

/**
 * Export the auth error message helper for use in other components
 */
export { getAuthErrorMessage, mapUser };
