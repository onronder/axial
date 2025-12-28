"use client";

import { useRouter, usePathname } from "next/navigation";
import { useAuth } from "@/hooks/useAuth";
import { useProfile } from "@/hooks/useProfile";
import { useTheme } from "@/hooks/useTheme";
import { useChatHistory } from "@/hooks/useChatHistory";
import { Settings, LogOut, User, Moon, Sun, ChevronUp, MessageSquarePlus } from "lucide-react";
import { ChatHistoryList } from "@/components/layout/ChatHistoryList";
import { NotificationCenter } from "@/components/layout/NotificationCenter";
import { UsageIndicator } from "@/components/UsageIndicator";
import { HelpTrigger } from "@/components/help/HelpTrigger";
import { HelpModal } from "@/components/help/HelpModal";
import { AxioLogo } from "@/components/branding/AxioLogo";
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

/**
 * Main sidebar component for desktop view.
 * Contains: Logo, New Chat button, Chat history, Settings link, User menu.
 */
export function DashboardSidebar() {
    const pathname = usePathname();
    const router = useRouter();
    const { user, logout } = useAuth();
    const { profile } = useProfile();
    const { theme, setTheme, resolvedTheme } = useTheme();

    const displayName = profile?.first_name && profile?.last_name
        ? `${profile.first_name} ${profile.last_name}`
        : profile?.first_name || user?.name || user?.email?.split('@')[0] || 'User';

    const handleLogout = () => {
        logout();
        router.push("/login");
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

            {/* Chat History - scrollable */}
            <div className="flex-1 overflow-y-auto overflow-x-visible px-2">
                <ChatHistoryList />
            </div>

            {/* Usage Indicator - shows file/storage usage */}
            <UsageIndicator />

            {/* Help & Support */}
            <div className="px-4 py-1">
                <HelpTrigger />
            </div>

            {/* Settings Link */}
            <div className="px-4 py-2">
                <a
                    href="/dashboard/settings"
                    className={`flex items-center gap-2 px-2 py-2 rounded-md transition-colors ${isSettingsActive ? 'bg-sidebar-accent text-sidebar-accent-foreground' : 'hover:bg-sidebar-accent/50'
                        }`}
                >
                    <Settings className="h-4 w-4" />
                    <span>Settings</span>
                </a>
            </div>

            {/* Help Modal */}
            <HelpModal />

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
