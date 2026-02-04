"use client";

import { useState } from "react";
import Link from "next/link";
import { useMemo } from "react";
import { Menu, Settings } from "lucide-react";
import { cn } from "@/lib/utils";
import { Button } from "@/components/ui/button";
import {
    Sheet,
    SheetContent,
    SheetHeader,
    SheetTitle,
    SheetTrigger,
} from "@/components/ui/sheet";

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

interface SidebarNavProps {
    items: NavItem[];
    pathname: string;
    onNavigate?: () => void;
}

function SidebarNav({ items, pathname, onNavigate }: SidebarNavProps) {
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
                                        : "text-muted-foreground hover:bg-accent/50 hover:text-foreground"
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

export interface MobileSettingsSheetProps {
    items: NavItem[];
    pathname: string;
}

export default function MobileSettingsSheet({ items, pathname }: MobileSettingsSheetProps) {
    const [sheetOpen, setSheetOpen] = useState(false);

    return (
        <div className="lg:hidden border-b border-white/10 bg-background/70 backdrop-blur-xl">
            <div className="flex items-center gap-3 p-4">
                <Sheet open={sheetOpen} onOpenChange={setSheetOpen}>
                    <SheetTrigger asChild>
                        <Button variant="ghost" size="icon" className="shrink-0">
                            <Menu className="h-5 w-5" />
                            <span className="sr-only">Toggle settings menu</span>
                        </Button>
                    </SheetTrigger>
                    <SheetContent side="left" className="w-72 p-0 bg-card/95 backdrop-blur-xl">
                        <SheetHeader className="p-6 border-b border-white/10">
                            <div className="flex items-center gap-3">
                                <div className="flex h-10 w-10 items-center justify-center rounded-xl bg-gradient-to-br from-primary to-accent text-white shadow-glow">
                                    <Settings className="h-5 w-5" />
                                </div>
                                <SheetTitle className="font-display text-lg font-bold">
                                    Settings
                                </SheetTitle>
                            </div>
                        </SheetHeader>
                        <div className="overflow-y-auto max-h-[calc(100vh-120px)]">
                            <SidebarNav
                                items={items}
                                pathname={pathname}
                                onNavigate={() => setSheetOpen(false)}
                            />
                        </div>
                    </SheetContent>
                </Sheet>

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
