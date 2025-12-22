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

    // Exact shadcn pattern from docs:
    // SidebarProvider (flex container) > AppSidebar (with internal spacer) > main (flex: 1)
    // The Sidebar component includes a spacer div that pushes main content
    return (
        <ChatHistoryProvider>
            <SidebarProvider defaultOpen={true}>
                <AppSidebar />
                <main className="flex-1 overflow-hidden">
                    {/* Mobile header with menu toggle */}
                    <header className="sticky top-0 z-10 flex h-14 items-center gap-4 border-b bg-background px-4 md:hidden">
                        <SidebarTrigger />
                        <span className="font-semibold">Axio Hub</span>
                    </header>
                    {/* Page content */}
                    {children}
                </main>
            </SidebarProvider>
        </ChatHistoryProvider>
    );
}
