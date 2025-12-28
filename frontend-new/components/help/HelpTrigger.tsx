"use client";

/**
 * Help Trigger Component
 * 
 * Button to open the Help Center modal.
 */

import { HelpCircle } from 'lucide-react';
import { useHelpStore } from '@/store/useHelpStore';
import { Button } from '@/components/ui/button';
import {
    Tooltip,
    TooltipContent,
    TooltipTrigger,
} from '@/components/ui/tooltip';

interface HelpTriggerProps {
    variant?: 'sidebar' | 'fab' | 'icon';
    className?: string;
}

export function HelpTrigger({ variant = 'sidebar', className }: HelpTriggerProps) {
    const openHelp = useHelpStore((state) => state.openHelp);

    if (variant === 'fab') {
        return (
            <Tooltip>
                <TooltipTrigger asChild>
                    <Button
                        onClick={openHelp}
                        size="icon"
                        className="fixed bottom-6 right-6 h-14 w-14 rounded-full shadow-lg bg-primary hover:bg-primary/90 z-50"
                    >
                        <HelpCircle className="h-6 w-6" />
                    </Button>
                </TooltipTrigger>
                <TooltipContent side="left">
                    <p>Help & Support</p>
                </TooltipContent>
            </Tooltip>
        );
    }

    if (variant === 'icon') {
        return (
            <Tooltip>
                <TooltipTrigger asChild>
                    <Button
                        onClick={openHelp}
                        variant="ghost"
                        size="icon"
                        className={className}
                    >
                        <HelpCircle className="h-5 w-5" />
                    </Button>
                </TooltipTrigger>
                <TooltipContent>
                    <p>Help Center</p>
                </TooltipContent>
            </Tooltip>
        );
    }

    // Default: sidebar variant
    return (
        <Button
            onClick={openHelp}
            variant="ghost"
            className="w-full justify-start gap-3 text-muted-foreground hover:text-foreground"
        >
            <HelpCircle className="h-5 w-5" />
            Help & Support
        </Button>
    );
}
