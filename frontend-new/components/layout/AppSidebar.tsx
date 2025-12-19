"use client";

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
import { useTheme } from "@/hooks/useTheme";
import { useChatHistory } from "@/hooks/useChatHistory";
import { ChatHistoryList } from "./ChatHistoryList";
import { AxioLogo } from "@/components/branding/AxioLogo";

export function AppSidebar() {
  const pathname = usePathname();
  const router = useRouter();
  const { user, logout } = useAuth();
  const { theme, setTheme, resolvedTheme } = useTheme();
  const { createNewChat } = useChatHistory();

  const handleLogout = () => {
    logout();
    router.push("/auth/login");
  };

  const toggleTheme = () => {
    setTheme(resolvedTheme === "dark" ? "light" : "dark");
  };

  const handleNewChat = () => {
    const chatId = createNewChat();
    router.push(`/dashboard/chat/${chatId}`);
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

      <SidebarContent className="px-2 flex flex-col">
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

        {/* Chat History List */}
        <SidebarGroup className="flex-1 mt-4 min-h-0">
          <SidebarGroupContent className="h-full">
            <ChatHistoryList />
          </SidebarGroupContent>
        </SidebarGroup>

        {/* Settings Link */}
        <SidebarGroup className="mt-auto">
          <SidebarGroupContent>
            <SidebarMenu>
              <SidebarMenuItem>
                <SidebarMenuButton
                  asChild
                  isActive={isSettingsActive}
                  className="transition-colors"
                >
                  <button
                    onClick={() => router.push("/dashboard/settings")}
                    className="flex w-full items-center gap-2"
                  >
                    <Settings className="h-4 w-4" />
                    <span>Settings</span>
                  </button>
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
                      {user?.name
                        ?.split(" ")
                        .map((n) => n[0])
                        .join("")
                        .toUpperCase() || "U"}
                    </AvatarFallback>
                  </Avatar>
                  <div className="flex flex-1 flex-col items-start text-left text-sm">
                    <span className="font-medium text-sidebar-foreground">
                      {user?.name}
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
                className="w-[--radix-dropdown-menu-trigger-width]"
              >
                <DropdownMenuItem onClick={() => router.push("/dashboard/settings/profile")}>
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