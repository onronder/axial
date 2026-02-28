"use client";

import { forwardRef, HTMLAttributes, useState } from "react";
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
    /** All citation indices that reference this source (e.g., [6, 10] for citations [6] and [10]) */
    citationIndices?: number[];
}

export const SourcePill = forwardRef<HTMLAnchorElement, SourcePillProps>(
    ({ source, isHighlighted = false, showExternalIcon = false, citationIndices, className, ...props }, ref) => {
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
                <span className="truncate max-w-[200px]" title={displayLabel}>{displayLabel}</span>
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

        // Citation badges component - shows all citation numbers (e.g., [6] [10])
        const citationBadges = citationIndices && citationIndices.length > 0 && (
            <span 
                className="ml-1.5 inline-flex items-center gap-0.5"
                aria-label={`Citations: ${citationIndices.join(', ')}`}
            >
                {citationIndices.map((idx) => (
                    <span 
                        key={`citation-badge-${idx}`}
                        className="flex h-4 min-w-4 items-center justify-center rounded-full bg-secondary px-1 text-[10px] font-bold text-background"
                        title={`Citation [${idx}]`}
                    >
                        {idx}
                    </span>
                ))}
            </span>
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
                    {citationBadges}
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
                {citationBadges}
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
 * - Citation index badges showing ALL citation numbers (e.g., [6] [10]) for each source
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
    const [isExpanded, setIsExpanded] = useState(false);

    if (!sources || sources.length === 0) return null;

    const deduplicated = deduplicateSources(sources);
    const visibleSources = isExpanded ? deduplicated : deduplicated.slice(0, MAX_VISIBLE_SOURCES);
    const overflowCount = deduplicated.length - MAX_VISIBLE_SOURCES;

    return (
        <nav
            aria-label="Source citations"
            className={cn("flex flex-wrap items-center gap-2", className)}
        >
            {visibleSources.map((item, idx) => {
                const isHighlighted = item.indices.some(i => i === highlightedIndex);
                return (
                    <SourcePill
                        key={`source-pill-${idx}`}
                        source={item.source}
                        isHighlighted={isHighlighted}
                        citationIndices={item.indices}
                        onMouseEnter={() => onSourceHover?.(item.indices[0])}
                        onMouseLeave={() => onSourceHover?.(null)}
                        onFocus={() => onSourceHover?.(item.indices[0])}
                        onBlur={() => onSourceHover?.(null)}
                    />
                );
            })}

            {overflowCount > 0 && !isExpanded && (
                <button
                    type="button"
                    className="px-3 py-1.5 text-sm text-muted-foreground border border-dashed border-muted-foreground/30 rounded-full hover:bg-muted/50 hover:border-muted-foreground/50 transition-colors cursor-pointer"
                    title={`Show ${overflowCount} more sources`}
                    onClick={() => setIsExpanded(true)}
                >
                    +{overflowCount} more
                </button>
            )}

            {isExpanded && overflowCount > 0 && (
                <button
                    type="button"
                    className="px-3 py-1.5 text-sm text-muted-foreground border border-dashed border-muted-foreground/30 rounded-full hover:bg-muted/50 hover:border-muted-foreground/50 transition-colors cursor-pointer"
                    title="Show fewer sources"
                    onClick={() => setIsExpanded(false)}
                >
                    Show less
                </button>
            )}
        </nav>
    );
}
