"use client";

import { ReactNode, useEffect, useState } from "react";
import { useRouter, usePathname } from "next/navigation";
import { useAuth } from "@/hooks/useAuth";
import { ChatHistoryProvider } from "@/hooks/useChatHistory";
import { IngestModalProvider } from "@/hooks/useIngestModal";
import { Loader2, Settings, LogOut, User, Moon, Sun, ChevronUp, MessageSquarePlus, Menu, X } from "lucide-react";
import { useProfile, ProfileProvider } from "@/hooks/useProfile";
import { useTheme } from "@/hooks/useTheme";
import { useChatHistory } from "@/hooks/useChatHistory";
import { ChatHistoryList } from "@/components/layout/ChatHistoryList";
import { GlobalProgress } from "@/components/layout/global-progress";
import { NotificationCenter } from "@/components/layout/NotificationCenter";
import { AxioLogo } from "@/components/branding/AxioLogo";
import { GlobalIngestModal } from "@/components/GlobalIngestModal";
import { Button } from "@/components/ui/button";
import { Avatar, AvatarFallback } from "@/components/ui/avatar";
import { Badge } from "@/components/ui/badge";
import {
    DropdownMenu,
    DropdownMenuContent,
    DropdownMenuItem,
    DropdownMenuSeparator,
    DropdownMenuTrigger,
} from "@/components/ui/dropdown-menu";

interface DashboardLayoutProps {
    children: ReactNode;
}

// Simple sidebar width constant
const SIDEBAR_WIDTH = 256; // 16rem = 256px

function SimpleSidebar() {
    const pathname = usePathname();
    const router = useRouter();
    const { user, logout } = useAuth();
    const { profile } = useProfile();
    const { theme, setTheme, resolvedTheme } = useTheme();
    const { createNewChat } = useChatHistory();

    const displayName = profile?.first_name && profile?.last_name
        ? `${profile.first_name} ${profile.last_name}`
        : profile?.first_name || user?.name || user?.email?.split('@')[0] || 'User';

    const handleLogout = () => {
        logout();
        router.push("/auth/login");
    };

    const toggleTheme = () => {
        setTheme(resolvedTheme === "dark" ? "light" : "dark");
    };

    const handleNewChat = () => {
        router.push('/dashboard/chat/new');
    };

    const isSettingsActive = pathname?.startsWith("/dashboard/settings");

    return (
        <div className="flex flex-col h-full bg-sidebar text-sidebar-foreground">
            {/* Header */}
            <div className="p-4 flex items-center justify-between">
                <div className="flex items-center gap-2">
                    <AxioLogo variant="icon" size="md" forceDark />
                    <span className="font-display text-lg font-semibold">Axio Hub</span>
                </div>
                <NotificationCenter />
            </div>

            {/* New Chat Button */}
            <div className="px-4 pb-4">
                <Button
                    variant="default"
                    className="w-full justify-start gap-2 bg-gradient-to-r from-blue-600 to-indigo-600 hover:from-blue-700 hover:to-indigo-700 text-white shadow-sm"
                    onClick={handleNewChat}
                >
                    <MessageSquarePlus className="h-4 w-4" />
                    New Chat
                </Button>
            </div>

            {/* Chat History - scrollable but allows dropdown to escape */}
            <div className="flex-1 overflow-y-auto overflow-x-visible px-2">
                <ChatHistoryList />
            </div>

            {/* Settings Link */}
            <div className="px-4 py-2 border-t border-sidebar-border/50">
                <a
                    href="/dashboard/settings"
                    className={`flex items-center gap-2 px-2 py-2 rounded-md transition-colors ${isSettingsActive ? 'bg-sidebar-accent text-sidebar-accent-foreground' : 'hover:bg-sidebar-accent/50'
                        }`}
                >
                    <Settings className="h-4 w-4" />
                    <span>Settings</span>
                </a>
            </div>

            {/* User Menu */}
            <div className="p-2 border-t border-sidebar-border/50">
                <DropdownMenu>
                    <DropdownMenuTrigger asChild>
                        <button className="w-full flex items-center gap-2 p-2 rounded-md hover:bg-sidebar-accent/50 transition-colors">
                            <Avatar className="h-6 w-6">
                                <AvatarFallback className="bg-gradient-to-br from-blue-500 to-indigo-500 text-white text-xs">
                                    {displayName?.split(" ").map((n) => n[0]).join("").toUpperCase() || "U"}
                                </AvatarFallback>
                            </Avatar>
                            <div className="flex flex-1 flex-col items-start text-left text-sm">
                                <span className="font-medium">{displayName}</span>
                                <Badge variant="secondary" className="mt-0.5 h-4 px-1 text-[10px] bg-sidebar-accent">
                                    {user?.plan}
                                </Badge>
                            </div>
                            <ChevronUp className="h-4 w-4 text-sidebar-muted" />
                        </button>
                    </DropdownMenuTrigger>
                    <DropdownMenuContent side="top" align="start" className="w-56 z-[100]">
                        <DropdownMenuItem onClick={() => router.push("/dashboard/settings/general")}>
                            <User className="mr-2 h-4 w-4" />
                            Profile
                        </DropdownMenuItem>
                        <DropdownMenuItem onClick={toggleTheme}>
                            {resolvedTheme === "dark" ? <Sun className="mr-2 h-4 w-4" /> : <Moon className="mr-2 h-4 w-4" />}
                            {resolvedTheme === "dark" ? "Light Mode" : "Dark Mode"}
                        </DropdownMenuItem>
                        <DropdownMenuSeparator />
                        <DropdownMenuItem onClick={handleLogout}>
                            <LogOut className="mr-2 h-4 w-4" />
                            Logout
                        </DropdownMenuItem>
                    </DropdownMenuContent>
                </DropdownMenu>
            </div>
        </div>
    );
}

export default function DashboardLayout({ children }: DashboardLayoutProps) {
    const { isAuthenticated, loading } = useAuth();
    const router = useRouter();
    const [mobileMenuOpen, setMobileMenuOpen] = useState(false);

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

    // SIMPLE BULLETPROOF LAYOUT:
    // - Fixed sidebar on left (256px wide, hidden on mobile)
    // - Main content fills remaining space with left margin on desktop
    // - Mobile: full width with hamburger menu
    return (
        <ProfileProvider>
            <ChatHistoryProvider>
                <IngestModalProvider>
                    <div className="min-h-screen bg-background">
                        {/* DESKTOP SIDEBAR - Fixed position, always visible on md+ */}
                        <aside
                            className="fixed inset-y-0 left-0 z-40 hidden md:block border-r border-sidebar-border"
                            style={{ width: `${SIDEBAR_WIDTH}px` }}
                        >
                            <SimpleSidebar />
                        </aside>

                        {/* MOBILE SIDEBAR - Overlay when open */}
                        {mobileMenuOpen && (
                            <div className="fixed inset-0 z-50 md:hidden">
                                {/* Backdrop */}
                                <div
                                    className="absolute inset-0 bg-black/50"
                                    onClick={() => setMobileMenuOpen(false)}
                                />
                                {/* Sidebar */}
                                <aside className="absolute inset-y-0 left-0 w-72 border-r border-sidebar-border">
                                    <SimpleSidebar />
                                </aside>
                            </div>
                        )}

                        {/* MAIN CONTENT AREA */}
                        <div
                            className="min-h-screen"
                            style={{
                                // On desktop (md+), add left margin equal to sidebar width
                                // Using CSS media query via style prop
                                marginLeft: 0
                            }}
                        >
                            {/* We need CSS for responsive margin, so use a wrapper with classes */}
                            <div className="md:ml-64 min-h-screen">
                                {/* Mobile header */}
                                <header className="sticky top-0 z-30 flex h-14 items-center gap-4 border-b bg-background px-4 md:hidden">
                                    <button
                                        onClick={() => setMobileMenuOpen(true)}
                                        className="p-2 -ml-2 rounded-md hover:bg-muted"
                                    >
                                        <Menu className="h-5 w-5" />
                                    </button>
                                    <span className="font-semibold">Axio Hub</span>
                                </header>

                                {/* Page content - full height minus mobile header */}
                                <main className="h-[calc(100vh-56px)] md:h-screen">
                                    {children}
                                </main>
                            </div>
                        </div>

                        {/* Global IngestModal - controlled via context */}
                        <GlobalIngestModal />

                        {/* Global Progress Bar - for ingestion tracking */}
                        <GlobalProgress />
                    </div>
                </IngestModalProvider>
            </ChatHistoryProvider>
        </ProfileProvider>
    );
}
