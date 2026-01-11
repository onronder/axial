"use client";

import Link from "next/link";
import { usePathname } from "next/navigation";
import { User, Database, FileText, Bell, CreditCard, Users, Settings, AlertTriangle } from "lucide-react";
import { cn } from "@/lib/utils";
import { ScrollArea, ScrollBar } from "@/components/ui/scroll-area";

const settingsNav = [
    { name: "General", path: "/dashboard/settings/general", icon: User },
    { name: "Data Sources", path: "/dashboard/settings/data-sources", icon: Database },
    { name: "Knowledge Base", path: "/dashboard/settings/knowledge-base", icon: FileText },
    { name: "Team", path: "/dashboard/settings/team", icon: Users },
    { name: "Notifications", path: "/dashboard/settings/notifications", icon: Bell },
    { name: "Billing", path: "/dashboard/settings/billing", icon: CreditCard },
    { name: "Failed Tasks", path: "/dashboard/settings/failed-tasks", icon: AlertTriangle },
];

export default function SettingsLayout({
    children,
}: {
    children: React.ReactNode;
}) {
    const pathname = usePathname();

    return (
        <div className="relative min-h-full w-full overflow-hidden bg-background">
            <div className="pointer-events-none absolute inset-0">
                <div className="absolute -left-24 top-10 h-72 w-72 rounded-full bg-primary/15 blur-3xl" />
                <div className="absolute right-0 top-0 h-80 w-80 rounded-full bg-accent/10 blur-3xl" />
                <div className="absolute inset-x-0 bottom-[-10%] h-64 bg-[radial-gradient(circle_at_50%_0%,rgba(255,255,255,0.08),transparent_45%)]" />
            </div>

            <div className="relative flex flex-col min-h-full w-full">
                {/* Settings Header - proper z-index below sidebar */}
                <div className="border-b border-white/10 bg-background/70 backdrop-blur-xl shadow-[0_10px_50px_rgba(0,0,0,0.35)]">
                    <div className="px-4 lg:px-8 pt-6 pb-0">
                        <div className="flex items-center gap-3 mb-1">
                            <div className="flex h-10 w-10 items-center justify-center rounded-xl bg-gradient-to-br from-primary to-accent text-white shadow-glow">
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

                    {/* Tab Navigation */}
                    <ScrollArea className="w-full">
                        <nav className="flex px-4 lg:px-8 gap-2 mt-4 pb-2">
                            <div className="flex w-full items-center gap-1 rounded-2xl border border-white/10 bg-white/5 p-1 backdrop-blur-xl shadow-inner shadow-black/40">
                                {settingsNav.map((item) => {
                                    const Icon = item.icon;
                                    const isActive = pathname === item.path ||
                                        (pathname === "/dashboard/settings" && item.path === "/dashboard/settings/general");

                                    return (
                                        <Link
                                            key={item.path}
                                            href={item.path}
                                            className={cn(
                                                "relative flex items-center gap-2 px-4 py-3 text-sm font-medium whitespace-nowrap transition-all duration-300 rounded-xl",
                                                isActive
                                                    ? "text-primary bg-white/10 shadow-glow"
                                                    : "text-muted-foreground hover:text-foreground hover:bg-white/5"
                                            )}
                                        >
                                            <Icon className={cn(
                                                "h-4 w-4 transition-colors",
                                                isActive ? "text-primary" : ""
                                            )} />
                                            <span className="hidden sm:inline">{item.name}</span>

                                            {/* Active indicator bar */}
                                            {isActive && (
                                                <span className="absolute -bottom-1 left-3 right-3 h-0.5 bg-gradient-to-r from-primary to-accent rounded-full" />
                                            )}
                                        </Link>
                                    );
                                })}
                            </div>
                        </nav>
                        <ScrollBar orientation="horizontal" />
                    </ScrollArea>
                </div>

                {/* Main Content - scrollable */}
                <div className="flex-1 overflow-y-auto p-4 lg:p-8">
                    <div className="mx-auto max-w-6xl space-y-6">
                        {children}
                    </div>
                </div>
            </div>
        </div>
    );
}
