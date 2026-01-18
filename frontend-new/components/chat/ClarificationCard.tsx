"use client";

/**
 * ClarificationCard Component
 * 
 * Displays when the backend returns HTTP 300 (Multiple Choices).
 * Shows a list of scope candidates for the user to select from.
 */

import { useState } from "react";
import { 
    FolderOpen, 
    Github, 
    Cloud, 
    Globe, 
    FileText, 
    BookOpen,
    HelpCircle,
    ChevronRight,
    Loader2,
} from "lucide-react";
import { cn } from "@/lib/utils";
import { getScopeTypeName, extractScopeName } from "@/lib/chat-utils";
import type { ScopeCandidate } from "@/types";

interface ClarificationCardProps {
    message: string;
    candidates: ScopeCandidate[];
    onSelectScope: (scopeId: string) => void;
    isLoading?: boolean;
    className?: string;
}

/**
 * Get the appropriate icon for a scope type
 */
function ScopeIcon({ type, className }: { type: string; className?: string }) {
    const iconProps = { className: cn("h-5 w-5", className) };
    
    switch (type) {
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
            return <HelpCircle {...iconProps} />;
    }
}

/**
 * Individual scope candidate item
 */
function ScopeCandidateItem({ 
    candidate, 
    onSelect,
    isSelected,
    disabled,
}: { 
    candidate: ScopeCandidate; 
    onSelect: () => void;
    isSelected: boolean;
    disabled: boolean;
}) {
    const scopeName = extractScopeName(candidate.id);
    const typeName = getScopeTypeName(candidate.type);
    
    return (
        <button
            onClick={onSelect}
            disabled={disabled}
            className={cn(
                "w-full flex items-start gap-3 p-3 rounded-lg border transition-all text-left",
                "hover:border-primary/50 hover:bg-primary/5",
                "focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring focus-visible:ring-offset-2",
                "disabled:opacity-50 disabled:cursor-not-allowed",
                isSelected 
                    ? "border-primary bg-primary/10" 
                    : "border-border bg-card/50"
            )}
        >
            <div className={cn(
                "flex h-10 w-10 shrink-0 items-center justify-center rounded-lg",
                isSelected ? "bg-primary text-primary-foreground" : "bg-muted"
            )}>
                <ScopeIcon type={candidate.type} />
            </div>
            
            <div className="flex-1 min-w-0">
                <div className="flex items-center gap-2">
                    <span className="font-medium text-foreground truncate">
                        {scopeName}
                    </span>
                    {isSelected && (
                        <Loader2 className="h-4 w-4 animate-spin text-primary" />
                    )}
                </div>
                <span className="text-xs text-muted-foreground">
                    {typeName}
                </span>
                {candidate.summary && (
                    <p className="mt-1 text-sm text-muted-foreground line-clamp-2">
                        {candidate.summary}
                    </p>
                )}
            </div>
            
            <ChevronRight className={cn(
                "h-5 w-5 shrink-0 transition-transform",
                isSelected ? "text-primary" : "text-muted-foreground",
                "group-hover:translate-x-0.5"
            )} />
        </button>
    );
}

export function ClarificationCard({
    message,
    candidates,
    onSelectScope,
    isLoading = false,
    className,
}: ClarificationCardProps) {
    const [selectedScopeId, setSelectedScopeId] = useState<string | null>(null);
    
    const handleSelect = (scopeId: string) => {
        setSelectedScopeId(scopeId);
        onSelectScope(scopeId);
    };
    
    return (
        <div className={cn(
            "flex items-start gap-3 animate-fade-in",
            className
        )}>
            {/* Avatar */}
            <div className="flex h-8 w-8 shrink-0 items-center justify-center rounded-lg bg-amber-500/10 border border-amber-500/20">
                <HelpCircle className="h-4 w-4 text-amber-500" />
            </div>
            
            {/* Content */}
            <div className="max-w-[85%]">
                <div className="rounded-xl bg-amber-50/50 dark:bg-amber-500/10 border border-amber-200 dark:border-amber-500/20 px-4 py-3 shadow-sm">
                    {/* Header */}
                    <div className="mb-3">
                        <h3 className="font-medium text-foreground flex items-center gap-2">
                            <span className="text-amber-600 dark:text-amber-400">Multiple contexts found</span>
                        </h3>
                        <p className="text-sm text-muted-foreground mt-1">
                            {message}
                        </p>
                    </div>
                    
                    {/* Candidates list */}
                    <div className="space-y-2">
                        {candidates.map((candidate) => (
                            <ScopeCandidateItem
                                key={candidate.id}
                                candidate={candidate}
                                onSelect={() => handleSelect(candidate.id)}
                                isSelected={selectedScopeId === candidate.id && isLoading}
                                disabled={isLoading}
                            />
                        ))}
                    </div>
                    
                    {/* Helper text */}
                    <p className="mt-3 text-xs text-muted-foreground">
                        Select a source to search, or{" "}
                        <button 
                            className="text-primary hover:underline disabled:opacity-50"
                            onClick={() => handleSelect("__all__")}
                            disabled={isLoading}
                        >
                            search all sources
                        </button>
                    </p>
                </div>
            </div>
        </div>
    );
}
