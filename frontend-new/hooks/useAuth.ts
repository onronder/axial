"use client";

import { useState, useEffect } from "react";
import { supabase } from "@/lib/supabase";
import { useToast } from "@/hooks/use-toast";
import { useRouter } from "next/navigation";

export const useAuth = () => {
    const [user, setUser] = useState<{ id: string; email?: string; name?: string; plan?: string } | null>(null);
    const [loading, setLoading] = useState(true);
    const { toast } = useToast();
    const router = useRouter();

    useEffect(() => {
        // Check active session
        const getSession = async () => {
            const { data: { session } } = await supabase.auth.getSession();
            if (session?.user) {
                setUser({
                    id: session.user.id,
                    email: session.user.email,
                    name: session.user.user_metadata?.full_name || session.user.email?.split('@')[0],
                    plan: 'Free' // Default plan for now, can be fetched from DB profile later
                });
            } else {
                setUser(null);
            }
            setLoading(false);
        };

        getSession();

        // Listen for changes
        const { data: { subscription } } = supabase.auth.onAuthStateChange((_event, session) => {
            if (session?.user) {
                setUser({
                    id: session.user.id,
                    email: session.user.email,
                    name: session.user.user_metadata?.full_name || session.user.email?.split('@')[0],
                    plan: 'Free'
                });
            } else {
                setUser(null);
            }
            setLoading(false);
        });

        return () => subscription.unsubscribe();
    }, []);

    const login = async (email: string, pass: string) => {
        const { error } = await supabase.auth.signInWithPassword({
            email,
            password: pass,
        });

        if (error) {
            console.error("Login error:", error.message);
            throw error;
        }

        return true;
    };

    const register = async (name: string, email: string, pass: string) => {
        const { error } = await supabase.auth.signUp({
            email,
            password: pass,
            options: {
                data: {
                    full_name: name,
                },
            },
        });

        if (error) {
            console.error("Register error:", error.message);
            throw error;
        }

        return true;
    };

    const logout = async () => {
        const { error } = await supabase.auth.signOut();
        if (error) {
            console.error("Logout error:", error.message);
            toast({
                title: "Error signing out",
                description: error.message,
                variant: "destructive"
            });
        }
        setUser(null);
        router.push("/login"); // Redirect to login after logout
    }

    return {
        user,
        loading,
        isAuthenticated: !!user,
        login,
        register,
        logout
    };
};
