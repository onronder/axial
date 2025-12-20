"use client";

import Link from "next/link";
import { usePathname, useRouter } from "next/navigation";
import {
  Settings,
  LogOut,
  User,
  Moon,
  Sun,
  ChevronUp,
  MessageSquarePlus,
} from "lucide-react";
import {
  Sidebar,
  SidebarContent,
  SidebarFooter,
  SidebarGroup,
  SidebarGroupContent,
  SidebarHeader,
  SidebarMenu,
  SidebarMenuButton,
  SidebarMenuItem,
} from "@/components/ui/sidebar";
import {
  DropdownMenu,
  DropdownMenuContent,
  DropdownMenuItem,
  DropdownMenuSeparator,
  DropdownMenuTrigger,
} from "@/components/ui/dropdown-menu";
import { Button } from "@/components/ui/button";
import { Avatar, AvatarFallback } from "@/components/ui/avatar";
import { Badge } from "@/components/ui/badge";
import { useAuth } from "@/hooks/useAuth";
import { useProfile } from "@/hooks/useProfile";
import { useTheme } from "@/hooks/useTheme";
import { useChatHistory } from "@/hooks/useChatHistory";
import { ChatHistoryList } from "./ChatHistoryList";
import { AxioLogo } from "@/components/branding/AxioLogo";

export function AppSidebar() {
  const pathname = usePathname();
  const router = useRouter();
  const { user, logout } = useAuth();
  const { profile } = useProfile();
  const { theme, setTheme, resolvedTheme } = useTheme();
  const { createNewChat } = useChatHistory();

  // Compute display name: prefer profile name, fallback to auth name
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
    // Just navigate to dashboard - chat will be created when user sends first message
    router.push('/dashboard');
  };

  // Check against /dashboard/settings
  const isSettingsActive = pathname?.startsWith("/dashboard/settings");

  return (
    <Sidebar className="border-r border-sidebar-border">
      <SidebarHeader className="p-4">
        <div className="flex items-center gap-2">
          <AxioLogo variant="icon" size="md" forceDark />
          <span className="font-display text-lg font-semibold text-sidebar-foreground">
            Axio Hub
          </span>
        </div>
      </SidebarHeader>

      <SidebarContent className="px-2 flex flex-col overflow-hidden">
        {/* New Chat Button */}
        <SidebarGroup>
          <SidebarGroupContent>
            <Button
              variant="default"
              className="w-full justify-start gap-2 bg-gradient-to-r from-blue-600 to-indigo-600 hover:from-blue-700 hover:to-indigo-700 text-white shadow-sm"
              onClick={handleNewChat}
            >
              <MessageSquarePlus className="h-4 w-4" />
              New Chat
            </Button>
          </SidebarGroupContent>
        </SidebarGroup>

        {/* Chat History List - takes remaining space with scroll */}
        <SidebarGroup className="flex-1 mt-4 min-h-0 overflow-hidden">
          <SidebarGroupContent className="h-full overflow-hidden">
            <ChatHistoryList />
          </SidebarGroupContent>
        </SidebarGroup>

        {/* Settings Link - always visible at bottom */}
        <SidebarGroup className="flex-shrink-0 pt-2 border-t border-sidebar-border/50 mt-2">
          <SidebarGroupContent>
            <SidebarMenu>
              <SidebarMenuItem>
                <SidebarMenuButton
                  asChild
                  isActive={isSettingsActive}
                  className="transition-colors"
                >
                  <Link href="/dashboard/settings" className="flex w-full items-center gap-2">
                    <Settings className="h-4 w-4" />
                    <span>Settings</span>
                  </Link>
                </SidebarMenuButton>
              </SidebarMenuItem>
            </SidebarMenu>
          </SidebarGroupContent>
        </SidebarGroup>
      </SidebarContent>

      <SidebarFooter className="p-2">
        <SidebarMenu>
          <SidebarMenuItem>
            <DropdownMenu>
              <DropdownMenuTrigger asChild>
                <SidebarMenuButton className="w-full">
                  <Avatar className="h-6 w-6">
                    <AvatarFallback className="bg-gradient-to-br from-blue-500 to-indigo-500 text-white text-xs">
                      {displayName
                        ?.split(" ")
                        .map((n) => n[0])
                        .join("")
                        .toUpperCase() || "U"}
                    </AvatarFallback>
                  </Avatar>
                  <div className="flex flex-1 flex-col items-start text-left text-sm">
                    <span className="font-medium text-sidebar-foreground">
                      {displayName}
                    </span>
                    <Badge
                      variant="secondary"
                      className="mt-0.5 h-4 px-1 text-[10px] bg-sidebar-accent text-sidebar-foreground"
                    >
                      {user?.plan}
                    </Badge>
                  </div>
                  <ChevronUp className="h-4 w-4 text-sidebar-muted" />
                </SidebarMenuButton>
              </DropdownMenuTrigger>
              <DropdownMenuContent
                side="top"
                align="start"
                className="w-[--radix-dropdown-menu-trigger-width] z-[100]"
              >
                <DropdownMenuItem onClick={() => router.push("/dashboard/settings/general")}>
                  <User className="mr-2 h-4 w-4" />
                  Profile
                </DropdownMenuItem>
                <DropdownMenuItem onClick={toggleTheme}>
                  {resolvedTheme === "dark" ? (
                    <Sun className="mr-2 h-4 w-4" />
                  ) : (
                    <Moon className="mr-2 h-4 w-4" />
                  )}
                  {resolvedTheme === "dark" ? "Light Mode" : "Dark Mode"}
                </DropdownMenuItem>
                <DropdownMenuSeparator />
                <DropdownMenuItem onClick={handleLogout}>
                  <LogOut className="mr-2 h-4 w-4" />
                  Logout
                </DropdownMenuItem>
              </DropdownMenuContent>
            </DropdownMenu>
          </SidebarMenuItem>
        </SidebarMenu>
      </SidebarFooter>
    </Sidebar>
  );
}