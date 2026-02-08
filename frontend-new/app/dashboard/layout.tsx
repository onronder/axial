
"use client";

import { ReactNode, Suspense, useEffect, useState } from "react";
import { useRouter } from "next/navigation";
import { useAuth } from "@/hooks/useAuth";
import { ChatHistoryProvider } from "@/hooks/useChatHistory";
import { IngestModalProvider } from "@/hooks/useIngestModal";
import { IngestionProgressProvider } from "@/hooks/useIngestionProgress";

import { ProfileProvider } from "@/hooks/useProfile";
import { UsageProvider } from "@/hooks/useUsage";
import { QuotaStatusProvider } from "@/hooks/useQuotaStatus";
import { DataInvalidationProvider } from "@/components/providers/DataInvalidationProvider";
import { DashboardSidebar } from "@/components/layout/DashboardSidebar";
import { MobileNav } from "@/components/layout/MobileNav";
import { LazyGlobalIngestModal, LazyGlobalProgress } from "@/components/lazy";
import { ModalLoadingFallback } from "@/components/lazy/ModalLoadingFallback";
import { UsageWarningBanner } from "@/components/UsageWarningBanner";
import { PaywallGuard } from "@/components/PaywallGuard";
import { AppErrorBoundary, SidebarErrorBoundary } from "@/components/providers/ErrorBoundary";
import { ConnectionStatusIndicator } from "@/components/layout/ConnectionStatusIndicator";
import { OfflineBanner } from "@/components/layout/OfflineBanner";
import { useQueryClient } from "@tanstack/react-query";
import { prefetchDashboardData } from "@/lib/prefetch";
import { Spinner } from "@/components/ui/spinner";

interface DashboardLayoutProps {
    children: ReactNode;
}

// Sidebar width constant
const SIDEBAR_WIDTH = 256; // 16rem = 256px

export default function DashboardLayout({ children }: DashboardLayoutProps) {
    const { isAuthenticated, loading, user } = useAuth();
    const router = useRouter();
    const [mobileMenuOpen, setMobileMenuOpen] = useState(false);
    const queryClient = useQueryClient();

    useEffect(() => {
        if (!loading && !isAuthenticated) {
            // Middleware should have already redirected, but this is a fallback
            // Preserve current path for post-login redirect
            const currentPath = window.location.pathname + window.location.search;
            router.push(`/login?redirectTo=${encodeURIComponent(currentPath)}`);
        }
    }, [isAuthenticated, loading, router]);

    useEffect(() => {
        if (user?.id) {
            void prefetchDashboardData(queryClient);
        }
    }, [user?.id, queryClient]);

    if (loading) {
        return (
            <div className="flex h-screen items-center justify-center bg-background">
                <Spinner className="animate-spin h-8 w-8 text-primary" />
            </div>
        );
    }

    if (!isAuthenticated) {
        return null;
    }

    return (
        <ProfileProvider>
            <UsageProvider>
                <QuotaStatusProvider>
                    <DataInvalidationProvider>
                    <ChatHistoryProvider>
                        <IngestModalProvider>
                            <IngestionProgressProvider>
                            <PaywallGuard>
                            <div className="min-h-screen bg-background">
                                <OfflineBanner />
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

                                    <ConnectionStatusIndicator />

                                    {/* Usage Warning Banner */}
                                    <UsageWarningBanner />

                                    {/* Page content - with error boundary */}
                                    <main className="h-[calc(100vh-56px)] md:h-screen">
                                        <AppErrorBoundary name="PageContent">
                                            {children}
                                        </AppErrorBoundary>
                                    </main>
                                </div>

                                {/* Global modals and overlays - isolated */}
                                <SidebarErrorBoundary>
                                    <Suspense fallback={<ModalLoadingFallback />}>
                                        <LazyGlobalIngestModal />
                                    </Suspense>
                                </SidebarErrorBoundary>
                                <SidebarErrorBoundary>
                                    <Suspense fallback={<ModalLoadingFallback />}>
                                        <LazyGlobalProgress />
                                    </Suspense>
                                </SidebarErrorBoundary>
                            </div>
                        </PaywallGuard>
                            </IngestionProgressProvider>
                        </IngestModalProvider>
                    </ChatHistoryProvider>
                    </DataInvalidationProvider>
                </QuotaStatusProvider>
            </UsageProvider>
        </ProfileProvider>
    );
}
