"use client";

import { useRouter, usePathname } from "next/navigation";
import Link from "next/link";
import { useAuth } from "@/hooks/useAuth";
import { useProfile } from "@/hooks/useProfile";
import { useUsage } from "@/hooks/useUsage";
import { useTheme } from "@/hooks/useTheme";
import { Settings, LogOut, User, Moon, Sun, ChevronUp, MessageSquarePlus } from "lucide-react";
import { ChatHistoryList } from "@/components/layout/ChatHistoryList";
import { NotificationCenter } from "@/components/layout/NotificationCenter";
import { UsageIndicator } from "@/components/UsageIndicator";
import { HelpTrigger } from "@/components/help/HelpTrigger";
import { HelpModal } from "@/components/help/HelpModal";
import { AxioLogo } from "@/components/branding/AxioLogo";
import { Button } from "@/components/ui/button";
import { DeterministicAvatar } from "@/components/ui/DeterministicAvatar"; // New import
import { Badge } from "@/components/ui/badge";
import {
    DropdownMenu,
    DropdownMenuContent,
    DropdownMenuItem,
    DropdownMenuSeparator,
    DropdownMenuTrigger,
} from "@/components/ui/dropdown-menu";

/**
 * Main sidebar component for desktop view.
 * Contains: Logo, New Chat button, Chat history, Settings link, User menu.
 */
export function DashboardSidebar() {
    const pathname = usePathname();
    const router = useRouter();
    const { user, logout } = useAuth();
    const { profile } = useProfile();
    const { plan: effectivePlan } = useUsage();
    const { setTheme, resolvedTheme } = useTheme();

    const displayName = profile?.first_name && profile?.last_name
        ? `${profile.first_name} ${profile.last_name}`
        : profile?.first_name || user?.name || user?.email?.split('@')[0] || 'User';

    const handleLogout = async () => {
        await logout();
        // Navigation is handled in useAuth.logout()
    };

    const toggleTheme = () => {
        setTheme(resolvedTheme === "dark" ? "light" : "dark");
    };

    const handleNewChat = () => {
        router.push('/dashboard/chat/new');
    };

    const isSettingsActive = pathname?.startsWith("/dashboard/settings");

    return (
        <div className="flex h-full flex-col bg-sidebar/80 backdrop-blur-xl text-sidebar-foreground border-r border-white/10 shadow-glow px-4 py-3 gap-3">
            {/* Header */}
            <div className="flex items-center justify-between gap-2">
                <div className="flex items-center gap-3">
                    <AxioLogo variant="icon" size="md" forceDark />
                    <span className="font-display text-lg font-semibold text-gradient">Axio Hub</span>
                </div>
                <NotificationCenter />
            </div>

            {/* New Chat Button */}
            <div className="pt-1">
                <Button
                    variant="gradient"
                    className="w-full justify-center gap-2 shadow-glow bg-gradient"
                    onClick={handleNewChat}
                >
                    <MessageSquarePlus className="h-4 w-4" />
                    New Chat
                </Button>
            </div>

            {/* Chat History - scrollable */}
            <div className="flex-1 overflow-y-auto overflow-x-visible pr-1">
                <ChatHistoryList />
            </div>

            {/* Usage Indicator - shows file/storage usage */}
            <UsageIndicator />

            {/* Help & Support */}
            <div className="px-1">
                <HelpTrigger />
            </div>

            {/* Settings Link */}
            <div className="px-1">
                <Link
                    href="/dashboard/settings"
                    className={`flex items-center gap-2 px-3 py-2 rounded-lg transition-all border border-transparent ${isSettingsActive
                        ? 'bg-sidebar-accent bg-white/10 text-white shadow-glow'
                        : 'hover:bg-white/5 hover:border-white/10'
                        }`}
                >
                    <Settings className="h-4 w-4" />
                    <span>Settings</span>
                </Link>
            </div>

            {/* Help Modal */}
            <HelpModal />

            {/* User Menu */}
            <div className="pt-2 border-t border-white/10">
                <DropdownMenu>
                    <DropdownMenuTrigger asChild>
                        <button className="w-full flex items-center gap-2 p-2 rounded-lg hover:bg-white/5 transition-colors group focus:outline-none focus:ring-2 focus:ring-primary/40">
                            <DeterministicAvatar name={displayName} className="h-8 w-8 text-xs" />
                            <div className="flex flex-1 flex-col items-start text-left text-sm overflow-hidden">
                                <span className="font-medium truncate w-full">{displayName}</span>

                                <Link
                                    href="/dashboard/settings/billing"
                                    className="z-10 mt-0.5" // z-10 to ensure it catches clicks above the button
                                    onClick={(e) => e.stopPropagation()} // Prevent dropdown toggle
                                >
                                    <Badge
                                        variant="secondary"
                                        className="h-4 px-1.5 text-[10px] bg-white/10 hover:bg-primary/20 hover:text-primary transition-colors cursor-pointer border border-transparent hover:border-primary/30"
                                    >
                                        {effectivePlan
                                            ? effectivePlan.charAt(0).toUpperCase() + effectivePlan.slice(1)
                                            : <span className="animate-pulse">···</span>}
                                    </Badge>
                                </Link>
                            </div>
                            <ChevronUp className="h-4 w-4 text-sidebar-muted group-hover:text-sidebar-foreground transition-colors" />
                        </button>
                    </DropdownMenuTrigger>
                    <DropdownMenuContent side="top" align="start" className="w-56 z-[100] bg-sidebar/90 backdrop-blur-xl border border-white/10">
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
