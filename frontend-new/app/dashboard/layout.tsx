"use client";

import { ReactNode, useEffect } from "react";
import { useRouter } from "next/navigation";
import { useAuth } from "@/hooks/useAuth";
import { AppSidebar } from "@/components/layout/AppSidebar";
import { SidebarProvider, SidebarTrigger } from "@/components/ui/sidebar";
import { ChatHistoryProvider } from "@/hooks/useChatHistory";
import { Loader2 } from "lucide-react";

interface DashboardLayoutProps {
    children: ReactNode;
}

export default function DashboardLayout({ children }: DashboardLayoutProps) {
    const { isAuthenticated, loading } = useAuth();
    const router = useRouter();

    useEffect(() => {
        if (!loading && !isAuthenticated) {
            router.push("/login");
        }
    }, [isAuthenticated, loading, router]);

    if (loading) {
        return (
            <div className="flex h-screen items-center justify-center bg-background">
                <Loader2 className="animate-spin h-8 w-8 text-primary" />
            </div>
        );
    }

    if (!isAuthenticated) {
        return null;
    }

    // Simple CSS Grid layout:
    // - Mobile: single column, sidebar hidden
    // - Desktop: 256px sidebar + flexible main area
    return (
        <ChatHistoryProvider>
            <SidebarProvider defaultOpen={true}>
                <div className="grid min-h-screen w-full md:grid-cols-[256px_1fr]">
                    {/* Sidebar - fixed 256px width on desktop */}
                    <aside className="hidden md:block">
                        <AppSidebar />
                    </aside>

                    {/* Main content area */}
                    <div className="flex flex-col">
                        {/* Mobile header with menu */}
                        <header className="sticky top-0 z-10 flex h-14 items-center gap-4 border-b bg-background px-4 md:hidden">
                            <SidebarTrigger />
                            <span className="font-semibold">Axio Hub</span>
                        </header>

                        {/* Page content */}
                        <main className="flex-1 overflow-auto">
                            {children}
                        </main>
                    </div>
                </div>
            </SidebarProvider>
        </ChatHistoryProvider>
    );
}
