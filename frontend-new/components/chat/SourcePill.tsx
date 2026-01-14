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
    /** Optional badge showing citation count */
    citationCount?: number;
}

export const SourcePill = forwardRef<HTMLAnchorElement, SourcePillProps>(
    ({ source, isHighlighted = false, showExternalIcon = false, citationCount, className, ...props }, ref) => {
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
                    {/* Citation count badge */}
                    {citationCount && citationCount > 1 && (
                        <span 
                            className="ml-1 flex h-4 min-w-4 items-center justify-center rounded-full bg-secondary px-1 text-[10px] font-bold text-background"
                            title={`Cited ${citationCount} times`}
                        >
                            {citationCount}
                        </span>
                    )}
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
                {/* Citation count badge */}
                {citationCount && citationCount > 1 && (
                    <span 
                        className="ml-1 flex h-4 min-w-4 items-center justify-center rounded-full bg-secondary px-1 text-[10px] font-bold text-background"
                        title={`Cited ${citationCount} times`}
                    >
                        {citationCount}
                    </span>
                )}
            </span>
        );
    }
);

SourcePill.displayName = "SourcePill";

/**
 * SourcePillList - Horizontal list of source citation pills
 * 
 * Features:
 * - Deduplication by source name (no duplicate pills)
 * - Max 5 visible sources with "+X more" overflow
 * - Citation count badge for repeated sources
 * - Hover coordination with inline citations
 * - Accessible keyboard navigation
 */

const MAX_VISIBLE_SOURCES = 5;

interface DeduplicatedSource {
    source: SourceMetadata;
    count: number;
    indices: number[];
}

/**
 * Deduplicates sources by their label/title to avoid showing
 * the same document multiple times as separate pills.
 */
function deduplicateSources(sources: SourceMetadata[]): DeduplicatedSource[] {
    const sourceMap = new Map<string, DeduplicatedSource>();
    
    sources.forEach((source, idx) => {
        // Create a unique key based on source identity
        const key = (source.label || source.title || source.source || source.url || `source-${idx}`).toLowerCase().trim();
        
        if (sourceMap.has(key)) {
            const existing = sourceMap.get(key)!;
            existing.count++;
            existing.indices.push(source.index || idx + 1);
        } else {
            sourceMap.set(key, {
                source,
                count: 1,
                indices: [source.index || idx + 1],
            });
        }
    });
    
    return Array.from(sourceMap.values());
}

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

    // Deduplicate sources to avoid showing 10 identical pills
    const deduplicated = deduplicateSources(sources);
    const visibleSources = deduplicated.slice(0, MAX_VISIBLE_SOURCES);
    const overflowCount = deduplicated.length - MAX_VISIBLE_SOURCES;

    return (
        <nav
            aria-label="Source citations"
            className={cn("flex flex-wrap items-center gap-2", className)}
        >
            {visibleSources.map((item, idx) => {
                // Check if any of this source's indices are highlighted
                const isHighlighted = item.indices.some(i => i === highlightedIndex);

                return (
                    <SourcePill
                        key={`source-pill-${idx}`}
                        source={item.source}
                        isHighlighted={isHighlighted}
                        citationCount={item.count}
                        onMouseEnter={() => onSourceHover?.(item.indices[0])}
                        onMouseLeave={() => onSourceHover?.(null)}
                        onFocus={() => onSourceHover?.(item.indices[0])}
                        onBlur={() => onSourceHover?.(null)}
                    />
                );
            })}
            
            {/* Overflow indicator */}
            {overflowCount > 0 && (
                <span 
                    className="px-3 py-1.5 text-sm text-muted-foreground border border-dashed border-muted-foreground/30 rounded-full"
                    title={`${overflowCount} more sources not shown`}
                >
                    +{overflowCount} more
                </span>
            )}
        </nav>
    );
}
