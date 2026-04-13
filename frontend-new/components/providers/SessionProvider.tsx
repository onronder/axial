"use client";

import {
    createContext,
    useCallback,
    useContext,
    useEffect,
    useMemo,
    useState,
} from "react";
import { User, Session } from "@supabase/supabase-js";
import { supabase } from "@/lib/supabase";
import { clearAuthCache } from "@/lib/api";
import { usePathname, useRouter } from "next/navigation";

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

function isAuthRoute(pathname: string | null): boolean {
    if (!pathname) {
        return false;
    }

    return (
        pathname === "/login" ||
        pathname === "/register" ||
        pathname.startsWith("/forgot-password") ||
        pathname.startsWith("/auth/")
    );
}

export function SessionProvider({ children }: { children: React.ReactNode }) {
    const [session, setSession] = useState<Session | null>(null);
    const [user, setUser] = useState<User | null>(null);
    const [loading, setLoading] = useState(true);
    const router = useRouter();
    const pathname = usePathname();

    useEffect(() => {
        let mounted = true;

        // 1. Get initial session
        const initSession = async () => {
            try {
                const {
                    data: { session },
                } = await supabase.auth.getSession();

                if (!mounted) {
                    return;
                }

                setSession(session);
                setUser(session?.user ?? null);
            } catch (error) {
                if (process.env.NODE_ENV !== 'production') {
                    console.error("Failed to get session:", error);
                }
            } finally {
                if (mounted) {
                    setLoading(false);
                }
            }
        };

        initSession();

        // 2. Listen for auth changes
        const {
            data: { subscription },
        } = supabase.auth.onAuthStateChange(async (event, session) => {
            if (!mounted) {
                return;
            }

            setSession(session);
            setUser(session?.user ?? null);
            setLoading(false);

            if (event === "SIGNED_OUT" && !isAuthRoute(pathname)) {
                router.replace("/login");
            }
        });

        return () => {
            mounted = false;
            subscription.unsubscribe();
        };
    }, [pathname, router]);

    const signOut = useCallback(async () => {
        clearAuthCache();

        const { error } = await supabase.auth.signOut();
        if (error && process.env.NODE_ENV !== "production") {
            console.error("Failed to sign out:", error.message);
        }
    }, []);

    const value = useMemo(
        () => ({
            session,
            user,
            loading,
            signOut,
        }),
        [loading, session, signOut, user]
    );

    return (
        <SessionContext.Provider value={value}>{children}</SessionContext.Provider>
    );
}
