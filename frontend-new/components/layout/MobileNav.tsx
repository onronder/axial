"use client";

import { Menu } from "lucide-react";
import { DashboardSidebar } from "./DashboardSidebar";

interface MobileNavProps {
    isOpen: boolean;
    onToggle: (open: boolean) => void;
}

/**
 * Mobile navigation component with hamburger menu and slide-out sidebar.
 */
export function MobileNav({ isOpen, onToggle }: MobileNavProps) {
    return (
        <>
            {/* Mobile header */}
            <header className="sticky top-0 z-30 flex h-14 items-center gap-4 border-b bg-background px-4 md:hidden">
                <button
                    onClick={() => onToggle(true)}
                    className="p-2 -ml-2 rounded-md hover:bg-muted"
                    aria-label="Open menu"
                >
                    <Menu className="h-5 w-5" />
                </button>
                <span className="font-semibold">Axio Hub</span>
            </header>

            {/* Mobile sidebar overlay */}
            {isOpen && (
                <div className="fixed inset-0 z-50 md:hidden">
                    {/* Backdrop */}
                    <div
                        className="absolute inset-0 bg-black/50"
                        onClick={() => onToggle(false)}
                        aria-label="Close menu"
                    />
                    {/* Sidebar */}
                    <aside className="absolute inset-y-0 left-0 w-72 border-r border-sidebar-border">
                        <DashboardSidebar />
                    </aside>
                </div>
            )}
        </>
    );
}
