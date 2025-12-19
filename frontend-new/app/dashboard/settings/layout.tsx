"use client";

import Link from "next/link";
import { usePathname } from "next/navigation";
import { User, Database, FileText, Bell, CreditCard, Users } from "lucide-react";
import { cn } from "@/lib/utils";

const settingsNav = [
    { name: "General", path: "/dashboard/settings/general", icon: User },
    { name: "Data Sources", path: "/dashboard/settings/data-sources", icon: Database },
    { name: "Knowledge Base", path: "/dashboard/settings/knowledge-base", icon: FileText },
    { name: "Team Members", path: "/dashboard/settings/team", icon: Users },
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
        <div className="flex h-full flex-col lg:flex-row">
            <aside className="w-full lg:w-64 shrink-0 lg:border-r border-border bg-card/50 lg:bg-card">
                <div className="p-6 pb-2 lg:pb-6">
                    <h2 className="font-display text-lg font-semibold text-foreground">Settings</h2>
                    <p className="text-sm text-muted-foreground">Manage your workspace preferences</p>
                </div>
                <nav className="px-3 pb-6 flex overflow-x-auto lg:flex-col lg:overflow-x-visible gap-1 lg:space-y-1">
                    {settingsNav.map((item) => {
                        const Icon = item.icon;
                        const isActive = pathname === item.path;
                        return (
                            <Link
                                key={item.path}
                                href={item.path}
                                className={cn(
                                    "flex min-w-max items-center gap-3 rounded-lg px-3 py-2 text-sm font-medium transition-all",
                                    isActive
                                        ? "bg-axio-gradient text-white shadow-brand"
                                        : "text-muted-foreground hover:bg-muted hover:text-foreground"
                                )}
                            >
                                <Icon className="h-4 w-4" />
                                {item.name}
                            </Link>
                        );
                    })}
                </nav>
            </aside>

            <main className="flex-1 overflow-auto bg-background/50 p-6 lg:p-10">
                <div className="mx-auto max-w-4xl animate-fade-in">
                    {children}
                </div>
            </main>
        </div>
    );
}
