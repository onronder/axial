"use client";

import { useState, useEffect } from "react";
import { supabase } from "@/lib/supabase";
import { User } from "@supabase/supabase-js";
import { useRouter } from "next/navigation";

export interface CustomUser {
    id: string;
    email?: string;
    name?: string;
    plan?: string;
}

export const useAuth = () => {
    const [user, setUser] = useState<CustomUser | null>(null);
    const [loading, setLoading] = useState(true);
    const router = useRouter();

    const mapUser = (sessionUser: User | undefined): CustomUser | null => {
        if (!sessionUser) return null;
        return {
            id: sessionUser.id,
            email: sessionUser.email,
            name: sessionUser.user_metadata?.full_name || sessionUser.email?.split('@')[0],
            plan: 'Free' // Default plan
        };
    };

    useEffect(() => {
        // Initial session check
        const initAuth = async () => {
            try {
                const { data: { session } } = await supabase.auth.getSession();
                setUser(mapUser(session?.user));
            } catch (error) {
                console.error("Auth init error:", error);
                setUser(null);
            } finally {
                setLoading(false);
            }
        };

        initAuth();

        // Listen for auth changes
        const { data: { subscription } } = supabase.auth.onAuthStateChange(
            async (_event, session) => {
                setUser(mapUser(session?.user));
                setLoading(false);
            }
        );

        return () => subscription.unsubscribe();
    }, []);

    const login = async (email: string, pass: string) => {
        const { error } = await supabase.auth.signInWithPassword({
            email,
            password: pass,
        });
        if (error) throw error;
        return true;
    };

    const register = async (name: string, email: string, pass: string) => {
        const { error } = await supabase.auth.signUp({
            email,
            password: pass,
            options: {
                data: { full_name: name },
            },
        });
        if (error) throw error;
        return true;
    };

    const logout = async () => {
        await supabase.auth.signOut();
        setUser(null);
        router.push("/login");
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
