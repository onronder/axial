"use client";

import Link from "next/link";
import { usePathname } from "next/navigation";
import dynamic from "next/dynamic";
import { useMemo } from "react";
import {
    User,
    Database,
    FileText,
    Bell,
    CreditCard,
    Users,
    Settings,
    AlertTriangle,
    BarChart3,
    ScrollText,
    Briefcase,
    Shield,
    Lock,
} from "lucide-react";
import { cn } from "@/lib/utils";
import { useUsage } from "@/hooks/useUsage";
import { useProfile } from "@/hooks/useProfile";

type SettingsGroup = 'account' | 'data' | 'team' | 'admin';

interface NavItem {
    name: string;
    path: string;
    icon: React.ElementType;
    group: SettingsGroup;
    adminOnly?: boolean;
    freeAllowed?: boolean;
}

const settingsGroups: Record<SettingsGroup, { label: string; order: number }> = {
    account: { label: 'Account', order: 1 },
    data: { label: 'Data', order: 2 },
    team: { label: 'Team', order: 3 },
    admin: { label: 'Admin', order: 4 },
};

const settingsNav: NavItem[] = [
    { name: "General", path: "/dashboard/settings/general", icon: User, group: 'account', freeAllowed: true },
    { name: "Notifications", path: "/dashboard/settings/notifications", icon: Bell, group: 'account' },
    { name: "Billing", path: "/dashboard/settings/billing", icon: CreditCard, group: 'account', freeAllowed: true },
    { name: "Data Sources", path: "/dashboard/settings/data-sources", icon: Database, group: 'data' },
    { name: "Knowledge Base", path: "/dashboard/settings/knowledge-base", icon: FileText, group: 'data' },
    { name: "Jobs", path: "/dashboard/settings/jobs", icon: Briefcase, group: 'data', freeAllowed: true },
    { name: "Failed Tasks", path: "/dashboard/settings/failed-tasks", icon: AlertTriangle, group: 'data' },
    { name: "Team Members", path: "/dashboard/settings/team", icon: Users, group: 'team' },
    { name: "Analytics", path: "/dashboard/settings/analytics", icon: BarChart3, group: 'admin', adminOnly: true },
    { name: "Audit Logs", path: "/dashboard/settings/audit-logs", icon: ScrollText, group: 'admin', adminOnly: true },
    { name: "Security Log", path: "/dashboard/settings/security-log", icon: Lock, group: 'admin', adminOnly: true },
    { name: "Consent", path: "/dashboard/settings/consent", icon: Shield, group: 'admin', adminOnly: true },
];

// Skeleton for mobile header while Sheet component loads
function MobileHeaderSkeleton() {
    return (
        <div className="lg:hidden border-b border-white/10 bg-background/70 backdrop-blur-xl">
            <div className="flex items-center gap-3 p-4">
                <div className="h-10 w-10 rounded-lg bg-muted/50 animate-pulse" />
                <div className="flex h-10 w-10 items-center justify-center rounded-xl bg-gradient-to-br from-primary to-accent text-white shadow-glow">
                    <Settings className="h-5 w-5" />
                </div>
                <div>
                    <h1 className="font-display text-lg font-bold text-foreground">
                        Settings
                    </h1>
                    <p className="text-xs text-muted-foreground">
                        Manage your account
                    </p>
                </div>
            </div>
        </div>
    );
}

// Lazy load mobile Sheet navigation
const MobileSettingsSheet = dynamic(
    () => import("./_components/MobileSettingsSheet"),
    {
        ssr: false,
        loading: () => <MobileHeaderSkeleton />
    }
);

interface SidebarNavProps {
    items: NavItem[];
    pathname: string;
    onNavigate?: () => void;
}

function SidebarNav({ items, pathname, onNavigate }: SidebarNavProps) {
    // Group items by category
    const groupedItems = useMemo(() => {
        const groups: Record<SettingsGroup, NavItem[]> = {
            account: [],
            data: [],
            team: [],
            admin: [],
        };

        items.forEach((item) => {
            groups[item.group].push(item);
        });

        return Object.entries(groups)
            .filter(([, groupItems]) => groupItems.length > 0)
            .sort(([a], [b]) => settingsGroups[a as SettingsGroup].order - settingsGroups[b as SettingsGroup].order)
            .map(([group, groupItems]) => ({
                group: group as SettingsGroup,
                label: settingsGroups[group as SettingsGroup].label,
                items: groupItems,
            }));
    }, [items]);

    return (
        <nav className="flex flex-col gap-6 py-4">
            {groupedItems.map(({ group, label, items: groupItems }) => (
                <div key={group} className="flex flex-col gap-1">
                    <h3 className="px-4 text-xs font-semibold uppercase tracking-wider text-muted-foreground mb-2">
                        {label}
                    </h3>
                    {groupItems.map((item) => {
                        const Icon = item.icon;
                        const isActive = pathname === item.path ||
                            (pathname === "/dashboard/settings" && item.path === "/dashboard/settings/general");

                        return (
                            <Link
                                key={item.path}
                                href={item.path}
                                onClick={onNavigate}
                                className={cn(
                                    "flex items-center gap-3 px-4 py-2.5 text-sm font-medium transition-all duration-200 rounded-lg mx-2",
                                    isActive
                                        ? "bg-primary/10 text-primary border-l-2 border-primary -ml-0.5 pl-[14px]"
                                        : "text-muted-foreground hover:bg-muted/80 hover:text-foreground focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring focus-visible:ring-offset-1"
                                )}
                            >
                                <Icon className={cn(
                                    "h-4 w-4 shrink-0",
                                    isActive ? "text-primary" : ""
                                )} />
                                <span>{item.name}</span>
                            </Link>
                        );
                    })}
                </div>
            ))}
        </nav>
    );
}

export default function SettingsLayout({
    children,
}: {
    children: React.ReactNode;
}) {
    const pathname = usePathname();
    const { plan } = useUsage();
    const { profile } = useProfile();

    const isFreePlan = plan === "free" || plan === "none";
    const isAdmin = profile?.role === "admin";

    // Filter navigation based on plan and admin role
    const visibleNav = useMemo(() => {
        return settingsNav.filter((item) => {
            // Admin-only items: only show to admins
            if (item.adminOnly && !isAdmin) {
                return false;
            }
            // Free plan: only show freeAllowed items
            if (isFreePlan && !item.freeAllowed) {
                return false;
            }
            return true;
        });
    }, [isFreePlan, isAdmin]);

    return (
        <div className="relative min-h-full w-full overflow-hidden bg-background">
            {/* Background decorations */}
            <div className="pointer-events-none absolute inset-0">
                <div className="absolute -left-24 top-10 h-72 w-72 rounded-full bg-primary/15 blur-3xl" />
                <div className="absolute right-0 top-0 h-80 w-80 rounded-full bg-accent/10 blur-3xl" />
                <div className="absolute inset-x-0 bottom-[-10%] h-64 bg-[radial-gradient(circle_at_50%_0%,rgba(255,255,255,0.08),transparent_45%)]" />
            </div>

            <div className="relative flex min-h-full w-full">
                {/* Desktop Sidebar */}
                <aside className="hidden lg:flex w-60 shrink-0 flex-col border-r border-white/10 bg-card/30 backdrop-blur-xl">
                    {/* Sidebar Header */}
                    <div className="flex items-center gap-3 p-6 border-b border-white/10">
                        <div className="flex h-10 w-10 items-center justify-center rounded-xl bg-gradient-to-br from-primary to-accent text-white shadow-glow">
                            <Settings className="h-5 w-5" />
                        </div>
                        <div>
                            <h1 className="font-display text-lg font-bold text-foreground">
                                Settings
                            </h1>
                            <p className="text-xs text-muted-foreground">
                                Manage your account
                            </p>
                        </div>
                    </div>

                    {/* Sidebar Navigation */}
                    <div className="flex-1 overflow-y-auto">
                        <SidebarNav items={visibleNav} pathname={pathname} />
                    </div>
                </aside>

                {/* Mobile Header + Sheet */}
                <div className="flex flex-1 flex-col min-h-full">
                    {/* Mobile Header - Lazy loaded */}
                    <MobileSettingsSheet items={visibleNav} pathname={pathname} />

                    {/* Main Content */}
                    <main className="flex-1 overflow-y-auto p-4 lg:p-8">
                        <div className="mx-auto max-w-5xl space-y-6">
                            {children}
                        </div>
                    </main>
                </div>
            </div>
        </div>
    );
}
