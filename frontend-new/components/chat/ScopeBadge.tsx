"use client";

/**
 * ScopeBadge Component
 * 
 * Displays scope context information when a response is from a specific scope.
 * Shows the scope name and optionally the classification (dominant/contested).
 */

import { 
    FolderOpen, 
    Github, 
    Cloud, 
    Globe, 
    FileText, 
    BookOpen,
    Check,
    AlertCircle,
} from "lucide-react";
import { cn } from "@/lib/utils";
import { getScopeTypeName, extractScopeName } from "@/lib/chat-utils";
import type { ScopeContext } from "@/types";

interface ScopeBadgeProps {
    scopeContext: ScopeContext;
    variant?: "inline" | "footer";
    className?: string;
}

/**
 * Get the appropriate icon for a scope type (smaller version)
 */
function ScopeIcon({ scopeType, className }: { scopeType?: string; className?: string }) {
    const iconProps = { className: cn("h-3.5 w-3.5", className) };
    
    if (!scopeType) return null;
    
    switch (scopeType) {
        case 'github_repo':
            return <Github {...iconProps} />;
        case 's3_bucket':
            return <Cloud {...iconProps} />;
        case 'box_folder':
        case 'dropbox_folder':
        case 'gdrive_folder':
            return <FolderOpen {...iconProps} />;
        case 'notion_workspace':
            return <BookOpen {...iconProps} />;
        case 'web_domain':
            return <Globe {...iconProps} />;
        case 'file_upload':
            return <FileText {...iconProps} />;
        default:
            return <FolderOpen {...iconProps} />;
    }
}

/**
 * Inline badge - shown next to message or in response header
 */
function InlineBadge({ scopeContext, className }: { scopeContext: ScopeContext; className?: string }) {
    const scopeName = scopeContext.scope_name || extractScopeName(scopeContext.scope_id);
    const isDominant = scopeContext.classification === 'dominant' || scopeContext.classification === 'explicit';
    
    return (
        <span 
            className={cn(
                "inline-flex items-center gap-1.5 px-2 py-0.5 rounded-full text-xs font-medium",
                isDominant 
                    ? "bg-primary/10 text-primary border border-primary/20"
                    : "bg-amber-500/10 text-amber-600 dark:text-amber-400 border border-amber-500/20",
                className
            )}
            title={`Source: ${scopeContext.scope_id}`}
        >
            <ScopeIcon scopeType={scopeContext.scope_type} />
            <span className="truncate max-w-[150px]">{scopeName}</span>
            {isDominant ? (
                <Check className="h-3 w-3" />
            ) : (
                <AlertCircle className="h-3 w-3" />
            )}
        </span>
    );
}

/**
 * Footer badge - shown at the bottom of a message
 */
function FooterBadge({ scopeContext, className }: { scopeContext: ScopeContext; className?: string }) {
    const scopeName = scopeContext.scope_name || extractScopeName(scopeContext.scope_id);
    const typeName = scopeContext.scope_type ? getScopeTypeName(scopeContext.scope_type) : null;
    const isDominant = scopeContext.classification === 'dominant' || scopeContext.classification === 'explicit';
    const confidencePercent = Math.round(scopeContext.dominance_ratio * 100);
    
    return (
        <div 
            className={cn(
                "flex items-center gap-2 mt-3 pt-3 border-t border-border/50 text-xs text-muted-foreground",
                className
            )}
        >
            <div className={cn(
                "flex items-center gap-1.5 px-2 py-1 rounded-md",
                isDominant 
                    ? "bg-primary/5 text-primary/80"
                    : "bg-amber-500/5 text-amber-600/80 dark:text-amber-400/80"
            )}>
                <ScopeIcon scopeType={scopeContext.scope_type} />
                <span>Answered from</span>
                <span className="font-medium text-foreground">{scopeName}</span>
            </div>
            
            {typeName && (
                <span className="text-muted-foreground">
                    ({typeName})
                </span>
            )}
            
            {confidencePercent > 0 && (
                <span className="text-muted-foreground">
                    • {confidencePercent}% match
                </span>
            )}
        </div>
    );
}

export function ScopeBadge({
    scopeContext,
    variant = "inline",
    className,
}: ScopeBadgeProps) {
    if (variant === "footer") {
        return <FooterBadge scopeContext={scopeContext} className={className} />;
    }
    
    return <InlineBadge scopeContext={scopeContext} className={className} />;
}

/**
 * Scope context footnote - renders the markdown footnote style text
 * Used when the backend adds a footnote to the response
 */
export function ScopeFootnote({ 
    scopeName,
    className,
}: { 
    scopeName: string;
    className?: string;
}) {
    return (
        <div className={cn(
            "mt-4 pt-3 border-t border-border/30 text-xs text-muted-foreground italic",
            className
        )}>
            Answered based on context from <strong className="font-medium text-foreground not-italic">{scopeName}</strong>.
        </div>
    );
}
