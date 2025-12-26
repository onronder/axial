"use client";

import { useState } from "react";
import {
    FileText,
    Globe,
    PlayCircle,
    ExternalLink,
    Database,
} from "lucide-react";
import { cn } from "@/lib/utils";

/**
 * Source metadata for RAG citations
 * 
 * The backend returns structured sources with:
 * - index: Citation number [1], [2], [3]
 * - type: "File" | "Web" | "Drive" | "Notion"
 * - label: Human-readable source name
 * - url: Link to source (optional)
 * - page: Page number for PDFs
 * - section: Header path for markdown (e.g., "Setup > Installation")
 */
export interface SourceMetadata {
    // New RAG fields from backend
    index?: number;         // Citation index [1], [2], [3]
    type?: string;          // "File" | "Web" | "Drive" | "Notion"
    label?: string;         // Human-readable name
    url?: string;           // Link to source
    page?: number;          // Page number for PDFs
    section?: string;       // Header path for markdown

    // Legacy fields (for backwards compatibility)
    source?: string;        // 'web' | 'youtube' | 'drive' | 'notion' | 'file'
    source_type?: string;   // Alternative field name
    title?: string;
    source_url?: string;
    video_id?: string;
    page_id?: string;
    file_id?: string;
}

interface SourceCardProps {
    source: SourceMetadata;
    className?: string;
}

/**
 * Extracts YouTube video ID from various URL formats
 */
function extractYouTubeVideoId(url: string): string | null {
    const patterns = [
        /(?:youtube\.com\/watch\?v=)([a-zA-Z0-9_-]{11})/,
        /(?:youtu\.be\/)([a-zA-Z0-9_-]{11})/,
        /(?:youtube\.com\/embed\/)([a-zA-Z0-9_-]{11})/,
    ];

    for (const pattern of patterns) {
        const match = url.match(pattern);
        if (match) return match[1];
    }
    return null;
}

/**
 * Gets favicon URL for a domain
 */
function getFaviconUrl(url: string): string {
    try {
        const domain = new URL(url).hostname;
        return `https://www.google.com/s2/favicons?domain=${domain}&sz=32`;
    } catch {
        return "";
    }
}

/**
 * SourceCard - Displays a citation source with rich previews
 * 
 * - YouTube: Shows thumbnail with play overlay
 * - Web: Shows favicon and domain
 * - Other: Shows icon based on source type
 * - NEW: Shows citation index badge [1], [2]
 */
export function SourceCard({ source, className }: SourceCardProps) {
    const [imageError, setImageError] = useState(false);

    // Use new RAG fields with fallbacks to legacy fields
    const sourceType = source.type?.toLowerCase() || source.source_type || source.source || "file";
    const title = source.label || source.title || "Untitled Source";
    const url = source.url || source.source_url;
    const citationIndex = source.index;
    const pageInfo = source.page ? `Page ${source.page}` : source.section || null;

    // YouTube source
    if (sourceType === "youtube" || (url && url.includes("youtube"))) {
        const videoId = source.video_id || (url ? extractYouTubeVideoId(url) : null);
        const thumbnailUrl = videoId
            ? `https://img.youtube.com/vi/${videoId}/mqdefault.jpg`
            : null;

        return (
            <a
                href={url || "#"}
                target="_blank"
                rel="noopener noreferrer"
                className={cn(
                    "group relative flex flex-col overflow-hidden rounded-lg border border-border bg-card transition-all hover:border-primary/50 hover:shadow-md",
                    className
                )}
            >
                {/* Thumbnail */}
                {thumbnailUrl && !imageError ? (
                    <div className="relative aspect-video w-full bg-muted">
                        <img
                            src={thumbnailUrl}
                            alt={title}
                            className="h-full w-full object-cover"
                            onError={() => setImageError(true)}
                        />
                        {/* Play overlay */}
                        <div className="absolute inset-0 flex items-center justify-center bg-black/30 opacity-0 transition-opacity group-hover:opacity-100">
                            <PlayCircle className="h-12 w-12 text-white drop-shadow-lg" />
                        </div>
                        {/* YouTube badge */}
                        <div className="absolute bottom-2 left-2 flex items-center gap-1 rounded bg-red-600 px-1.5 py-0.5 text-[10px] font-medium text-white">
                            <PlayCircle className="h-3 w-3" />
                            YouTube
                        </div>
                    </div>
                ) : (
                    <div className="flex aspect-video w-full items-center justify-center bg-muted">
                        <PlayCircle className="h-8 w-8 text-muted-foreground" />
                    </div>
                )}

                {/* Title */}
                <div className="p-2">
                    <p className="line-clamp-2 text-xs font-medium text-foreground">{title}</p>
                </div>
            </a>
        );
    }

    // Web source
    if (sourceType === "web" && url) {
        const faviconUrl = getFaviconUrl(url);
        let domain = "";
        try {
            domain = new URL(url).hostname.replace("www.", "");
        } catch { }

        return (
            <a
                href={url}
                target="_blank"
                rel="noopener noreferrer"
                className={cn(
                    "flex items-center gap-3 rounded-lg border border-border bg-card p-3 transition-all hover:border-primary/50 hover:shadow-md",
                    className
                )}
            >
                {/* Favicon */}
                <div className="flex h-10 w-10 shrink-0 items-center justify-center rounded-lg bg-muted">
                    {faviconUrl ? (
                        <img
                            src={faviconUrl}
                            alt=""
                            className="h-5 w-5"
                            onError={(e) => {
                                e.currentTarget.style.display = "none";
                            }}
                        />
                    ) : (
                        <Globe className="h-5 w-5 text-muted-foreground" />
                    )}
                </div>

                {/* Content */}
                <div className="min-w-0 flex-1">
                    <p className="truncate text-sm font-medium text-foreground">{title}</p>
                    <p className="truncate text-xs text-muted-foreground">{domain}</p>
                </div>

                <ExternalLink className="h-4 w-4 shrink-0 text-muted-foreground" />
            </a>
        );
    }

    // Notion source
    if (sourceType === "notion") {
        return (
            <div className={cn(
                "flex items-center gap-3 rounded-lg border border-border bg-card p-3",
                className
            )}>
                <div className="flex h-10 w-10 shrink-0 items-center justify-center rounded-lg bg-muted">
                    <Database className="h-5 w-5 text-muted-foreground" />
                </div>
                <div className="min-w-0 flex-1">
                    <p className="truncate text-sm font-medium text-foreground">{title}</p>
                    <p className="text-xs text-muted-foreground">Notion</p>
                </div>
            </div>
        );
    }

    // Default (file, drive, etc.)
    return (
        <div className={cn(
            "flex items-center gap-3 rounded-lg border border-border bg-card p-3 relative",
            className
        )}>
            {/* Citation Index Badge */}
            {citationIndex && (
                <div className="absolute -top-2 -left-2 flex h-5 w-5 items-center justify-center rounded-full bg-primary text-[10px] font-bold text-primary-foreground shadow-sm">
                    {citationIndex}
                </div>
            )}

            <div className="flex h-10 w-10 shrink-0 items-center justify-center rounded-lg bg-muted">
                <FileText className="h-5 w-5 text-muted-foreground" />
            </div>
            <div className="min-w-0 flex-1">
                <p className="truncate text-sm font-medium text-foreground">{title}</p>
                <p className="truncate text-xs text-muted-foreground">
                    <span className="capitalize">{sourceType}</span>
                    {pageInfo && <span className="ml-1">• {pageInfo}</span>}
                </p>
            </div>
        </div>
    );
}

/**
 * SourceCardGrid - Displays multiple sources in a responsive grid
 */
interface SourceCardGridProps {
    sources: SourceMetadata[];
    className?: string;
}

export function SourceCardGrid({ sources, className }: SourceCardGridProps) {
    if (!sources || sources.length === 0) return null;

    return (
        <div className={cn(
            "mt-3 grid gap-2",
            sources.length === 1
                ? "grid-cols-1"
                : "grid-cols-2 lg:grid-cols-3",
            className
        )}>
            {sources.map((source, index) => (
                <SourceCard key={index} source={source} />
            ))}
        </div>
    );
}
