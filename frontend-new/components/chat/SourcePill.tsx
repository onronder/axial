"use client";

import { forwardRef, HTMLAttributes } from "react";
import { ExternalLink } from "lucide-react";
import { cn } from "@/lib/utils";
import { SourceMetadata } from "./SourceCard";
import { formatSourceTypeLabel, normalizeSourceType } from "@/lib/sourceType";

/**
 * SourcePill - Compact inline citation badge
 * 
 * Matches the marketing design with:
 * - Cyan/teal border and accent color
 * - Bullet point prefix
 * - Horizontal inline layout
 * - Hover highlighting for citation coordination
 */

interface SourcePillProps extends HTMLAttributes<HTMLAnchorElement> {
    source: SourceMetadata;
    isHighlighted?: boolean;
    showExternalIcon?: boolean;
}

export const SourcePill = forwardRef<HTMLAnchorElement, SourcePillProps>(
    ({ source, isHighlighted = false, showExternalIcon = false, className, ...props }, ref) => {
        // Extract display information
        const rawType = source.type || source.source_type || source.source || "";
        const normalizedType = normalizeSourceType(rawType);
        const typeLabel = formatSourceTypeLabel(normalizedType || rawType);
        
        const label = source.label || source.title || source.source || "Source";
        const url = source.url || source.source_url;
        const hasUrl = Boolean(url);
        
        // Format display: "filename (Type)" or just "filename"
        const displayLabel = typeLabel && typeLabel !== label
            ? `${label} (${typeLabel})`
            : label;

        const pillContent = (
            <>
                <span className="text-secondary" aria-hidden="true">•</span>
                <span className="truncate max-w-[200px]">{displayLabel}</span>
                {showExternalIcon && hasUrl && (
                    <ExternalLink className="h-3 w-3 opacity-60 shrink-0" />
                )}
            </>
        );

        const pillClasses = cn(
            // Base styles
            "inline-flex items-center gap-1.5 px-3 py-1.5",
            "text-sm font-medium rounded-full",
            "transition-all duration-150",
            // Default state - cyan/teal theme
            "border border-secondary/40 bg-secondary/10 text-secondary",
            // Hover state
            hasUrl && "hover:bg-secondary/20 hover:border-secondary/60 cursor-pointer",
            // Highlighted state (when hovering inline citation)
            isHighlighted && [
                "ring-2 ring-secondary ring-offset-1 ring-offset-background",
                "bg-secondary/20 border-secondary/60 scale-[1.02]"
            ],
            // Focus state for accessibility
            "focus:outline-none focus-visible:ring-2 focus-visible:ring-secondary focus-visible:ring-offset-2",
            className
        );

        // Render as link if URL exists, otherwise as span
        if (hasUrl) {
            return (
                <a
                    ref={ref}
                    href={url}
                    target="_blank"
                    rel="noopener noreferrer"
                    className={pillClasses}
                    title={`View: ${label}`}
                    {...props}
                >
                    {pillContent}
                </a>
            );
        }

        return (
            <span
                className={pillClasses}
                title={label}
                {...(props as HTMLAttributes<HTMLSpanElement>)}
            >
                {pillContent}
            </span>
        );
    }
);

SourcePill.displayName = "SourcePill";

/**
 * SourcePillList - Horizontal list of source citation pills
 * 
 * Features:
 * - Responsive horizontal layout with wrapping
 * - Hover coordination with inline citations
 * - Accessible keyboard navigation
 */
interface SourcePillListProps {
    sources: SourceMetadata[];
    className?: string;
    highlightedIndex?: number | null;
    onSourceHover?: (index: number | null) => void;
}

export function SourcePillList({
    sources,
    className,
    highlightedIndex = null,
    onSourceHover,
}: SourcePillListProps) {
    if (!sources || sources.length === 0) return null;

    return (
        <nav
            aria-label="Source citations"
            className={cn("flex flex-wrap items-center gap-2", className)}
        >
            {sources.map((source, idx) => {
                const sourceIndex = source.index || idx + 1;
                const isHighlighted = highlightedIndex === sourceIndex;

                return (
                    <SourcePill
                        key={`source-pill-${idx}`}
                        source={source}
                        isHighlighted={isHighlighted}
                        onMouseEnter={() => onSourceHover?.(sourceIndex)}
                        onMouseLeave={() => onSourceHover?.(null)}
                        onFocus={() => onSourceHover?.(sourceIndex)}
                        onBlur={() => onSourceHover?.(null)}
                    />
                );
            })}
        </nav>
    );
}

