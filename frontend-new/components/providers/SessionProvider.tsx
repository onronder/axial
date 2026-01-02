"use client";

import { createContext, useContext, useEffect, useState } from "react";
import { User, Session } from "@supabase/supabase-js";
import { supabase } from "@/lib/supabase";
import { useRouter } from "next/navigation";

interface SessionContextType {
    session: Session | null;
    user: User | null;
    loading: boolean;
    signOut: () => Promise<void>;
}

const SessionContext = createContext<SessionContextType>({
    session: null,
    user: null,
    loading: true,
    signOut: async () => { },
});

export const useSession = () => useContext(SessionContext);

export function SessionProvider({ children }: { children: React.ReactNode }) {
    const [session, setSession] = useState<Session | null>(null);
    const [user, setUser] = useState<User | null>(null);
    const [loading, setLoading] = useState(true);
    const router = useRouter();

    useEffect(() => {
        // 1. Get initial session
        const initSession = async () => {
            try {
                const {
                    data: { session },
                } = await supabase.auth.getSession();
                setSession(session);
                setUser(session?.user ?? null);
            } catch (error) {
                console.error("Failed to get session:", error);
            } finally {
                setLoading(false);
            }
        };

        initSession();

        // 2. Listen for auth changes
        const {
            data: { subscription },
        } = supabase.auth.onAuthStateChange(async (event, session) => {
            setSession(session);
            setUser(session?.user ?? null);
            setLoading(false);

            if (event === "SIGNED_OUT") {
                router.push("/login");
            }
        });

        return () => {
            subscription.unsubscribe();
        };
    }, [router]);

    const signOut = async () => {
        await supabase.auth.signOut();
        router.push("/login");
    };

    const value = {
        session,
        user,
        loading,
        signOut,
    };

    return (
        <SessionContext.Provider value={value}>{children}</SessionContext.Provider>
    );
}
