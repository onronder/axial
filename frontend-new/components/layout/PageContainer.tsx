"use client";

import { cn } from "@/lib/utils";
import { ReactNode } from "react";

interface PageContainerProps {
    children: ReactNode;
    className?: string;
    maxWidth?: "sm" | "md" | "lg" | "xl" | "2xl" | "4xl" | "7xl" | "full";
}

const maxWidthClasses = {
    sm: "max-w-sm",
    md: "max-w-md",
    lg: "max-w-lg",
    xl: "max-w-xl",
    "2xl": "max-w-2xl",
    "4xl": "max-w-4xl",
    "7xl": "max-w-7xl",
    full: "max-w-full",
};

/**
 * Safe page container that prevents layout shift and overflow issues.
 * Use this to wrap page content to ensure it never overlaps with the sidebar.
 */
export function PageContainer({
    children,
    className,
    maxWidth = "7xl",
}: PageContainerProps) {
    return (
        <div
            className={cn(
                "w-full max-w-full overflow-x-hidden",
                "px-4 py-6 lg:px-8",
                "mx-auto",
                maxWidthClasses[maxWidth],
                className
            )}
        >
            {children}
        </div>
    );
}
