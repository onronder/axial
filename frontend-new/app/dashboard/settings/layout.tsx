"use client";

import Link from "next/link";
import { usePathname } from "next/navigation";
import { User, Database, FileText, Bell, CreditCard, Users } from "lucide-react";
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
            {/* Settings Header with Tab Navigation */}
            <div className="sticky top-0 z-10 bg-background border-b border-border">
                <div className="px-4 lg:px-8 pt-6 pb-0">
                    <h1 className="font-display text-2xl font-bold text-foreground mb-1">
                        Settings
                    </h1>
                    <p className="text-sm text-muted-foreground mb-4">
                        Manage your account and preferences
                    </p>
                </div>

                {/* Horizontal Tab Navigation */}
                <ScrollArea className="w-full">
                    <nav className="flex px-4 lg:px-8 gap-1">
                        {settingsNav.map((item) => {
                            const Icon = item.icon;
                            const isActive = pathname === item.path ||
                                (pathname === "/dashboard/settings" && item.path === "/dashboard/settings/general");

                            return (
                                <Link
                                    key={item.path}
                                    href={item.path}
                                    className={cn(
                                        "flex items-center gap-2 px-4 py-2.5 text-sm font-medium whitespace-nowrap transition-all border-b-2 -mb-px",
                                        isActive
                                            ? "border-primary text-primary"
                                            : "border-transparent text-muted-foreground hover:text-foreground hover:border-muted-foreground/30"
                                    )}
                                >
                                    <Icon className="h-4 w-4" />
                                    <span className="hidden sm:inline">{item.name}</span>
                                </Link>
                            );
                        })}
                    </nav>
                    <ScrollBar orientation="horizontal" />
                </ScrollArea>
            </div>

            {/* Main Content */}
            <main className="flex-1 overflow-auto p-4 lg:p-8">
                <div className="mx-auto max-w-4xl">
                    {children}
                </div>
            </main>
        </div>
    );
}
