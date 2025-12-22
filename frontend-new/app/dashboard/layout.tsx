"use client";

import { ReactNode, useEffect } from "react";
import { useRouter } from "next/navigation";
import { useAuth } from "@/hooks/useAuth";
import { AppSidebar } from "@/components/layout/AppSidebar";
import { SidebarProvider, SidebarInset, SidebarTrigger, useSidebar } from "@/components/ui/sidebar";
import { Loader2 } from "lucide-react";

interface DashboardLayoutProps {
    children: ReactNode;
}

// Inner component that has access to sidebar context
function DashboardContent({ children }: { children: ReactNode }) {
    const { state } = useSidebar();

    // Calculate left margin based on sidebar state
    // Sidebar width is 16rem (256px) when open, 3rem (48px) when collapsed to icon
    const marginLeft = state === "expanded" ? "md:ml-64" : "md:ml-12";

    return (
        <div className={`flex flex-1 flex-col min-w-0 overflow-x-hidden transition-[margin-left] duration-200 ease-linear ${marginLeft}`}>
            {/* Mobile header with sidebar trigger */}
            <header className="sticky top-0 z-10 flex h-14 shrink-0 items-center gap-4 border-b border-border bg-background/95 backdrop-blur supports-[backdrop-filter]:bg-background/60 px-4 md:hidden">
                <SidebarTrigger className="-ml-1" />
            </header>
            {/* Main content area */}
            <div className="flex flex-1 flex-col min-w-0 overflow-x-hidden">
                {children}
            </div>
        </div>
    );
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
        <SidebarProvider defaultOpen={true}>
            <AppSidebar />
            <DashboardContent>{children}</DashboardContent>
        </SidebarProvider>
    );
}
