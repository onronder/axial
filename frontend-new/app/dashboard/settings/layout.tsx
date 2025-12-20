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
        <div className="flex min-h-full">
            {/* Settings Sidebar Navigation */}
            <aside className="w-56 shrink-0 border-r border-border bg-card">
                <div className="sticky top-0 p-6">
                    <h2 className="font-display text-lg font-semibold text-foreground">Settings</h2>
                </div>
                <nav className="px-3 pb-6 space-y-1">
                    {settingsNav.map((item) => {
                        const Icon = item.icon;
                        const isActive = pathname === item.path;
                        return (
                            <Link
                                key={item.path}
                                href={item.path}
                                className={cn(
                                    "flex items-center gap-3 rounded-lg px-3 py-2 text-sm font-medium transition-all",
                                    isActive
                                        ? "bg-primary text-primary-foreground shadow-sm"
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

            {/* Main Content */}
            <main className="flex-1 overflow-auto p-6 lg:p-10">
                <div className="mx-auto max-w-4xl">
                    {children}
                </div>
            </main>
        </div>
    );
}
