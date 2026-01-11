/**
 * Mobile Sidebar Component
 * 
 * Slide-in sidebar for mobile devices with overlay backdrop.
 */

"use client";

import { useEffect } from 'react';
import { X } from 'lucide-react';
import { DashboardSidebar } from './DashboardSidebar';
import { cn } from '@/lib/utils';

interface MobileSidebarProps {
    isOpen: boolean;
    onClose: () => void;
}

export function MobileSidebar({ isOpen, onClose }: MobileSidebarProps) {
    // Close on escape key
    useEffect(() => {
        const handleEscape = (e: KeyboardEvent) => {
            if (e.key === 'Escape' && isOpen) {
                onClose();
            }
        };

        document.addEventListener('keydown', handleEscape);
        return () => document.removeEventListener('keydown', handleEscape);
    }, [isOpen, onClose]);

    // Prevent body scroll when open
    useEffect(() => {
        if (isOpen) {
            document.body.style.overflow = 'hidden';
        } else {
            document.body.style.overflow = '';
        }

        return () => {
            document.body.style.overflow = '';
        };
    }, [isOpen]);

    if (!isOpen) return null;

    return (
        <>
            {/* Backdrop */}
            <div
                className="fixed inset-0 z-50 bg-black/60 backdrop-blur-sm animate-fade-in lg:hidden"
                onClick={onClose}
                aria-hidden="true"
            />

            {/* Sidebar */}
            <aside
                className={cn(
                    "fixed inset-y-0 left-0 z-50 w-64 bg-sidebar/90 backdrop-blur-xl border-r border-white/10 shadow-2xl lg:hidden",
                    "transform transition-transform duration-300 ease-in-out",
                    isOpen ? "translate-x-0" : "-translate-x-full"
                )}
                aria-label="Mobile navigation"
            >
                {/* Close button */}
                <button
                    onClick={onClose}
                    className="absolute top-4 right-4 p-2 rounded-md hover:bg-white/5 transition-colors focus:outline-none focus:ring-2 focus:ring-primary/40"
                    aria-label="Close menu"
                >
                    <X className="h-5 w-5" />
                </button>

                <DashboardSidebar />
            </aside>
        </>
    );
}
