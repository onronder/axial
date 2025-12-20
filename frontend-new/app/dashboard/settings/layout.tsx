"use client";

import Link from "next/link";
import { usePathname } from "next/navigation";
import { User, Database, FileText, Bell, CreditCard, Users, Settings } from "lucide-react";
import { cn } from "@/lib/utils";
import { ScrollArea, ScrollBar } from "@/components/ui/scroll-area";

const settingsNav = [
    { name: "General", path: "/dashboard/settings/general", icon: User },
    { name: "Data Sources", path: "/dashboard/settings/data-sources", icon: Database },
    { name: "Knowledge Base", path: "/dashboard/settings/knowledge-base", icon: FileText },
    { name: "Team", path: "/dashboard/settings/team", icon: Users },
    { name: "Notifications", path: "/dashboard/settings/notifications", icon: Bell },
    { name: "Billing", path: "/dashboard/settings/billing", icon: CreditCard },
];

export default function SettingsLayout({
    children,
}: {
    children: React.ReactNode;
}) {
    const pathname = usePathname();

    return (
        <div className="flex flex-col h-full">
            {/* Settings Header with Premium Styling */}
            <div className="sticky top-0 z-10 bg-background/95 backdrop-blur-xl border-b border-border">
                <div className="px-4 lg:px-8 pt-6 pb-0">
                    <div className="flex items-center gap-3 mb-1">
                        <div className="flex h-10 w-10 items-center justify-center rounded-xl bg-gradient-to-br from-primary to-accent text-white shadow-lg shadow-primary/20">
                            <Settings className="h-5 w-5" />
                        </div>
                        <div>
                            <h1 className="font-display text-2xl font-bold text-foreground">
                                Settings
                            </h1>
                            <p className="text-sm text-muted-foreground">
                                Manage your account and preferences
                            </p>
                        </div>
                    </div>
                </div>

                {/* Premium Tab Navigation */}
                <ScrollArea className="w-full">
                    <nav className="flex px-4 lg:px-8 gap-1 mt-4">
                        {settingsNav.map((item) => {
                            const Icon = item.icon;
                            const isActive = pathname === item.path ||
                                (pathname === "/dashboard/settings" && item.path === "/dashboard/settings/general");

                            return (
                                <Link
                                    key={item.path}
                                    href={item.path}
                                    className={cn(
                                        "relative flex items-center gap-2 px-4 py-3 text-sm font-medium whitespace-nowrap transition-all duration-300 rounded-t-lg -mb-px",
                                        isActive
                                            ? "text-primary bg-primary/5"
                                            : "text-muted-foreground hover:text-foreground hover:bg-muted/50"
                                    )}
                                >
                                    <Icon className={cn(
                                        "h-4 w-4 transition-colors",
                                        isActive ? "text-primary" : ""
                                    )} />
                                    <span className="hidden sm:inline">{item.name}</span>

                                    {/* Active indicator bar */}
                                    {isActive && (
                                        <span className="absolute bottom-0 left-2 right-2 h-0.5 bg-gradient-to-r from-primary to-accent rounded-full" />
                                    )}
                                </Link>
                            );
                        })}
                    </nav>
                    <ScrollBar orientation="horizontal" />
                </ScrollArea>
            </div>

            {/* Main Content with subtle animation */}
            <main className="flex-1 overflow-auto p-4 lg:p-8">
                <div className="mx-auto max-w-4xl animate-fade-in">
                    {children}
                </div>
            </main>
        </div>
    );
}
