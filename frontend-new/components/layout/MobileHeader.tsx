/**
 * Mobile Header Component
 * 
 * Header bar for mobile with hamburger menu button.
 */

"use client";

import { Menu } from 'lucide-react';
import { Button } from '@/components/ui/button';
import { AxioLogo } from '@/components/branding/AxioLogo';

interface MobileHeaderProps {
    onMenuClick: () => void;
}

export function MobileHeader({ onMenuClick }: MobileHeaderProps) {
    return (
        <header className="sticky top-0 z-40 flex h-14 items-center gap-4 border-b bg-background px-4 lg:hidden">
            <Button
                variant="ghost"
                size="icon"
                onClick={onMenuClick}
                aria-label="Open menu"
                className="shrink-0"
            >
                <Menu className="h-5 w-5" />
            </Button>

            <div className="flex items-center gap-2">
                <AxioLogo variant="icon" size="sm" />
                <span className="font-display text-lg font-semibold">Axio Hub</span>
            </div>
        </header>
    );
}
