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

    return (
        <ChatHistoryProvider>
            <SidebarProvider defaultOpen={true}>
                {/* Fixed sidebar */}
                <AppSidebar />

                {/* Main content area - simple div with left margin */}
                <div className="flex-1 flex flex-col min-h-screen md:pl-64">
                    {/* Mobile header */}
                    <header className="sticky top-0 z-10 flex h-14 shrink-0 items-center gap-4 border-b border-border bg-background/95 backdrop-blur px-4 md:hidden">
                        <SidebarTrigger className="-ml-1" />
                    </header>
                    {/* Page content */}
                    <main className="flex-1 overflow-auto">
                        {children}
                    </main>
                </div>
            </SidebarProvider>
        </ChatHistoryProvider>
    );
}
