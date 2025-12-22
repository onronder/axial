"use client";

import { ReactNode, useEffect } from "react";
import { useRouter } from "next/navigation";
import { useAuth } from "@/hooks/useAuth";
import { AppSidebar } from "@/components/layout/AppSidebar";
import { SidebarProvider, SidebarInset, SidebarTrigger } from "@/components/ui/sidebar";
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

    // Use the standard shadcn sidebar pattern:
    // SidebarProvider wraps everything
    // AppSidebar is the fixed sidebar
    // SidebarInset is the main content area with proper margin
    return (
        <ChatHistoryProvider>
            <SidebarProvider defaultOpen={true}>
                <AppSidebar />
                <SidebarInset>
                    {/* Mobile header with menu toggle */}
                    <header className="sticky top-0 z-10 flex h-14 items-center gap-4 border-b bg-background px-4 md:hidden">
                        <SidebarTrigger />
                        <span className="font-semibold">Axio Hub</span>
                    </header>
                    {/* Page content */}
                    {children}
                </SidebarInset>
            </SidebarProvider>
        </ChatHistoryProvider>
    );
}
