"use client";

import { ReactNode, useEffect, useState } from "react";
import { useRouter } from "next/navigation";
import { useAuth } from "@/hooks/useAuth";
import { ChatHistoryProvider } from "@/hooks/useChatHistory";
import { IngestModalProvider } from "@/hooks/useIngestModal";
import { Loader2 } from "lucide-react";
import { ProfileProvider } from "@/hooks/useProfile";
import { DashboardSidebar } from "@/components/layout/DashboardSidebar";
import { MobileNav } from "@/components/layout/MobileNav";
import { GlobalProgress } from "@/components/layout/global-progress";
import { GlobalIngestModal } from "@/components/GlobalIngestModal";
import { AppErrorBoundary, SidebarErrorBoundary } from "@/components/providers/ErrorBoundary";

interface DashboardLayoutProps {
    children: ReactNode;
}

// Sidebar width constant
const SIDEBAR_WIDTH = 256; // 16rem = 256px

export default function DashboardLayout({ children }: DashboardLayoutProps) {
    const { isAuthenticated, loading } = useAuth();
    const router = useRouter();
    const [mobileMenuOpen, setMobileMenuOpen] = useState(false);

    useEffect(() => {
        if (!loading && !isAuthenticated) {
            router.push("/auth/login");
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
        <ProfileProvider>
            <ChatHistoryProvider>
                <IngestModalProvider>
                    <div className="min-h-screen bg-background">
                        {/* DESKTOP SIDEBAR - Isolated error boundary */}
                        <aside
                            className="fixed inset-y-0 left-0 z-40 hidden md:block border-r border-sidebar-border"
                            style={{ width: `${SIDEBAR_WIDTH}px` }}
                        >
                            <SidebarErrorBoundary>
                                <DashboardSidebar />
                            </SidebarErrorBoundary>
                        </aside>

                        {/* MAIN CONTENT AREA */}
                        <div className="md:ml-64 min-h-screen">
                            {/* Mobile navigation */}
                            <MobileNav
                                isOpen={mobileMenuOpen}
                                onToggle={setMobileMenuOpen}
                            />

                            {/* Page content - with error boundary */}
                            <main className="h-[calc(100vh-56px)] md:h-screen">
                                <AppErrorBoundary name="PageContent">
                                    {children}
                                </AppErrorBoundary>
                            </main>
                        </div>

                        {/* Global modals and overlays - isolated */}
                        <SidebarErrorBoundary>
                            <GlobalIngestModal />
                        </SidebarErrorBoundary>
                        <SidebarErrorBoundary>
                            <GlobalProgress />
                        </SidebarErrorBoundary>
                    </div>
                </IngestModalProvider>
            </ChatHistoryProvider>
        </ProfileProvider>
    );
}
