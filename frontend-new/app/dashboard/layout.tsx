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

    // The AppSidebar uses fixed positioning internally.
    // We simply need to add left padding to the main content area.
    return (
        <ChatHistoryProvider>
            <SidebarProvider defaultOpen={true}>
                {/* Fixed sidebar - renders its own fixed positioning */}
                <AppSidebar />

                {/* Main content - needs left padding to not be under the fixed sidebar */}
                <div className="min-h-screen w-full pl-0 md:pl-64">
                    {/* Mobile header */}
                    <header className="sticky top-0 z-10 flex h-14 items-center gap-4 border-b bg-background px-4 md:hidden">
                        <SidebarTrigger />
                        <span className="font-semibold">Axio Hub</span>
                    </header>

                    {/* Page content */}
                    <main className="min-h-[calc(100vh-56px)] md:min-h-screen">
                        {children}
                    </main>
                </div>
            </SidebarProvider>
        </ChatHistoryProvider>
    );
}
