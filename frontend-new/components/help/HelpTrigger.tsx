"use client";

/**
 * Help Trigger Component - Production Grade
 *
 * Button variants to open the Help Center modal.
 *
 * Variants:
 * - sidebar: Default button for sidebar integration
 * - fab: Floating action button (bottom-right)
 * - icon: Icon-only button with tooltip
 * - compact: Compact button for headers
 */

import { HelpCircle, BookOpen } from 'lucide-react';
import { useHelpStore } from '@/store/useHelpStore';
import { Button } from '@/components/ui/button';
import {
    Tooltip,
    TooltipContent,
    TooltipProvider,
    TooltipTrigger,
} from '@/components/ui/tooltip';
import { cn } from '@/lib/utils';

interface HelpTriggerProps {
    variant?: 'sidebar' | 'fab' | 'icon' | 'compact';
    className?: string;
}

export function HelpTrigger({ variant = 'sidebar', className }: HelpTriggerProps) {
    const openHelp = useHelpStore((state) => state.openHelp);

    // Floating Action Button variant
    if (variant === 'fab') {
        return (
            <TooltipProvider delayDuration={300}>
                <Tooltip>
                    <TooltipTrigger asChild>
                        <Button
                            onClick={openHelp}
                            size="icon"
                            className={cn(
                                "fixed bottom-6 right-6 h-14 w-14 rounded-full shadow-lg",
                                "bg-primary hover:bg-primary/90 text-primary-foreground",
                                "z-50 transition-all hover:scale-105 active:scale-95",
                                "cursor-pointer",
                                className
                            )}
                            aria-label="Open Help Center"
                        >
                            <HelpCircle className="h-6 w-6" />
                        </Button>
                    </TooltipTrigger>
                    <TooltipContent side="left" className="font-medium">
                        <p>Help & Support</p>
                    </TooltipContent>
                </Tooltip>
            </TooltipProvider>
        );
    }

    // Icon-only variant with tooltip
    if (variant === 'icon') {
        return (
            <TooltipProvider delayDuration={300}>
                <Tooltip>
                    <TooltipTrigger asChild>
                        <Button
                            onClick={openHelp}
                            variant="ghost"
                            size="icon"
                            className={cn(
                                "h-9 w-9 text-muted-foreground hover:text-foreground cursor-pointer",
                                className
                            )}
                            aria-label="Open Help Center"
                        >
                            <HelpCircle className="h-5 w-5" />
                        </Button>
                    </TooltipTrigger>
                    <TooltipContent>
                        <p>Help Center</p>
                    </TooltipContent>
                </Tooltip>
            </TooltipProvider>
        );
    }

    // Compact variant for headers
    if (variant === 'compact') {
        return (
            <TooltipProvider delayDuration={300}>
                <Tooltip>
                    <TooltipTrigger asChild>
                        <Button
                            onClick={openHelp}
                            variant="outline"
                            size="sm"
                            className={cn(
                                "gap-2 text-muted-foreground hover:text-foreground cursor-pointer",
                                className
                            )}
                            aria-label="Open Help Center"
                        >
                            <BookOpen className="h-4 w-4" />
                            <span className="hidden sm:inline">Help</span>
                        </Button>
                    </TooltipTrigger>
                    <TooltipContent>
                        <p>Open Help Center</p>
                    </TooltipContent>
                </Tooltip>
            </TooltipProvider>
        );
    }

    // Default: sidebar variant
    return (
        <Button
            onClick={openHelp}
            variant="ghost"
            className={cn(
                "w-full justify-start gap-3",
                "text-muted-foreground hover:text-foreground hover:bg-accent",
                "transition-colors cursor-pointer",
                className
            )}
            aria-label="Open Help Center"
        >
            <HelpCircle className="h-5 w-5" />
            Help & Support
        </Button>
    );
}
