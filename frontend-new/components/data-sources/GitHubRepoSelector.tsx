
"use client";

import { useState, useEffect } from "react";
import { GitBranch, Lock, Globe, Star, GitFork, Archive, CheckCircle2, Search, Building2, User } from "lucide-react";
import {
    Dialog,
    DialogContent,
    DialogHeader,
    DialogTitle,
    DialogDescription,
    DialogFooter,
} from "@/components/ui/dialog";
import { Button } from "@/components/ui/button";
import { Checkbox } from "@/components/ui/checkbox";
import { Input } from "@/components/ui/input";
import { Badge } from "@/components/ui/badge";
import { ScrollArea } from "@/components/ui/scroll-area";
import { api } from "@/lib/api";
import { cn } from "@/lib/utils";
import { Spinner } from "@/components/ui/spinner";

// =============================================================================
// Types
// =============================================================================

export interface GitHubRepo {
    id: number;
    name: string;
    full_name: string;
    description?: string;
    private: boolean;
    fork: boolean;
    archived: boolean;
    default_branch: string;
    owner: string;
    owner_type: "User" | "Organization";
    updated_at?: string;
    language?: string;
    stargazers_count: number;
}

interface GitHubRepoSelectorProps {
    open: boolean;
    onOpenChange: (open: boolean) => void;
    onComplete: () => void;
}

// =============================================================================
// Component
// =============================================================================

export function GitHubRepoSelector({ 
    open, 
    onOpenChange, 
    onComplete 
}: GitHubRepoSelectorProps) {
    const [repos, setRepos] = useState<GitHubRepo[]>([]);
    const [selectedRepos, setSelectedRepos] = useState<Set<string>>(new Set());
    const [loading, setLoading] = useState(true);
    const [saving, setSaving] = useState(false);
    const [error, setError] = useState<string | null>(null);
    const [searchQuery, setSearchQuery] = useState("");

    // Fetch repositories on mount
    useEffect(() => {
        if (open) {
            fetchRepos();
        }
    }, [open]);

    const fetchRepos = async () => {
        setLoading(true);
        setError(null);
        
        try {
            const response = await api.get<{ repositories: GitHubRepo[] }>("/integrations/github/repos");
            setRepos(response.data.repositories || []);
        } catch (err) {
            console.error("Failed to fetch GitHub repos:", err);
            setError("Failed to load repositories. Please try again.");
        } finally {
            setLoading(false);
        }
    };

    const handleSelectRepo = (fullName: string) => {
        setSelectedRepos(prev => {
            const next = new Set(prev);
            if (next.has(fullName)) {
                next.delete(fullName);
            } else {
                next.add(fullName);
            }
            return next;
        });
    };

    const handleSelectAll = () => {
        if (selectedRepos.size === filteredRepos.length) {
            setSelectedRepos(new Set());
        } else {
            setSelectedRepos(new Set(filteredRepos.map(r => r.full_name)));
        }
    };

    const handleSave = async () => {
        if (selectedRepos.size === 0) {
            setError("Please select at least one repository to sync.");
            return;
        }

        setSaving(true);
        setError(null);

        try {
            // Build the selection payload
            const selectedRepoData = Array.from(selectedRepos).map(fullName => {
                const repo = repos.find(r => r.full_name === fullName);
                return {
                    full_name: fullName,
                    branch: repo?.default_branch || "main",
                    enabled: true,
                };
            });

            await api.post("/integrations/github/repos/select", {
                selected_repositories: selectedRepoData,
            });

            console.log("✅ GitHub repos selected:", selectedRepoData);
            onComplete();
        } catch (err) {
            console.error("Failed to save repo selection:", err);
            setError("Failed to save selection. Please try again.");
        } finally {
            setSaving(false);
        }
    };

    // Filter repos by search query
    const filteredRepos = repos.filter(repo => {
        if (!searchQuery) return true;
        const q = searchQuery.toLowerCase();
        return (
            repo.name.toLowerCase().includes(q) ||
            repo.full_name.toLowerCase().includes(q) ||
            repo.description?.toLowerCase().includes(q) ||
            repo.language?.toLowerCase().includes(q)
        );
    });

    // Group repos by owner
    const groupedRepos = filteredRepos.reduce((acc, repo) => {
        const key = repo.owner;
        if (!acc[key]) {
            acc[key] = {
                owner: repo.owner,
                ownerType: repo.owner_type,
                repos: [],
            };
        }
        acc[key].repos.push(repo);
        return acc;
    }, {} as Record<string, { owner: string; ownerType: string; repos: GitHubRepo[] }>);

    const formatDate = (dateStr?: string) => {
        if (!dateStr) return "";
        const date = new Date(dateStr);
        return date.toLocaleDateString("en-US", { 
            month: "short", 
            day: "numeric", 
            year: "numeric" 
        });
    };

    return (
        <Dialog open={open} onOpenChange={onOpenChange}>
            <DialogContent className="max-w-2xl max-h-[85vh] flex flex-col">
                <DialogHeader>
                    <DialogTitle className="flex items-center gap-2">
                        <GitBranch className="h-5 w-5 text-primary" />
                        Select Repositories to Sync
                    </DialogTitle>
                    <DialogDescription>
                        Choose which repositories to include in your knowledge base. 
                        Only code and documentation files will be indexed.
                    </DialogDescription>
                </DialogHeader>

                {/* Search */}
                <div className="relative">
                    <Search className="absolute left-3 top-1/2 h-4 w-4 -translate-y-1/2 text-muted-foreground" />
                    <Input
                        placeholder="Search repositories..."
                        value={searchQuery}
                        onChange={(e) => setSearchQuery(e.target.value)}
                        className="pl-9"
                    />
                </div>

                {/* Content */}
                <div className="flex-1 min-h-0">
                    {loading ? (
                        <div className="flex flex-col items-center justify-center py-12">
                            <Spinner className="h-8 w-8 animate-spin text-primary" />
                            <p className="mt-2 text-sm text-muted-foreground">
                                Loading repositories...
                            </p>
                        </div>
                    ) : error && repos.length === 0 ? (
                        <div className="flex flex-col items-center justify-center py-12">
                            <p className="text-sm text-destructive">{error}</p>
                            <Button 
                                variant="outline" 
                                size="sm" 
                                className="mt-4"
                                onClick={fetchRepos}
                            >
                                Try Again
                            </Button>
                        </div>
                    ) : filteredRepos.length === 0 ? (
                        <div className="flex flex-col items-center justify-center py-12">
                            <p className="text-sm text-muted-foreground">
                                {searchQuery ? "No repositories match your search." : "No repositories found."}
                            </p>
                        </div>
                    ) : (
                        <ScrollArea className="h-[400px] pr-4">
                            {/* Select All */}
                            <div className="flex items-center justify-between py-2 border-b mb-2">
                                <div
                                    className="flex items-center gap-2 text-sm text-muted-foreground hover:text-foreground transition-colors cursor-pointer"
                                    onClick={handleSelectAll}
                                    role="button"
                                    tabIndex={0}
                                    onKeyDown={(e) => e.key === 'Enter' && handleSelectAll()}
                                >
                                    <Checkbox 
                                        checked={selectedRepos.size === filteredRepos.length && filteredRepos.length > 0}
                                        className="data-[state=checked]:bg-primary"
                                    />
                                    <span>
                                        {selectedRepos.size === filteredRepos.length && filteredRepos.length > 0
                                            ? "Deselect all"
                                            : "Select all"}
                                    </span>
                                </div>
                                <span className="text-xs text-muted-foreground">
                                    {selectedRepos.size} of {filteredRepos.length} selected
                                </span>
                            </div>

                            {/* Grouped Repos */}
                            <div className="space-y-6">
                                {Object.values(groupedRepos).map(({ owner, ownerType, repos: ownerRepos }) => (
                                    <div key={owner}>
                                        {/* Owner Header */}
                                        <div className="flex items-center gap-2 mb-2">
                                            {ownerType === "Organization" ? (
                                                <Building2 className="h-4 w-4 text-muted-foreground" />
                                            ) : (
                                                <User className="h-4 w-4 text-muted-foreground" />
                                            )}
                                            <span className="text-sm font-medium">{owner}</span>
                                            <Badge variant="secondary" className="text-xs">
                                                {ownerRepos.length}
                                            </Badge>
                                        </div>

                                        {/* Repos List */}
                                        <div className="space-y-1">
                                            {ownerRepos.map((repo) => (
                                                <RepoItem
                                                    key={repo.id}
                                                    repo={repo}
                                                    selected={selectedRepos.has(repo.full_name)}
                                                    onSelect={() => handleSelectRepo(repo.full_name)}
                                                    formatDate={formatDate}
                                                />
                                            ))}
                                        </div>
                                    </div>
                                ))}
                            </div>
                        </ScrollArea>
                    )}
                </div>

                {/* Error Display */}
                {error && repos.length > 0 && (
                    <p className="text-sm text-destructive text-center">{error}</p>
                )}

                {/* Footer */}
                <DialogFooter className="gap-2 sm:gap-2">
                    <Button
                        variant="outline"
                        onClick={() => onOpenChange(false)}
                        disabled={saving}
                    >
                        Cancel
                    </Button>
                    <Button
                        onClick={handleSave}
                        disabled={saving || selectedRepos.size === 0}
                        className="min-w-[140px]"
                    >
                        {saving ? (
                            <>
                                <Spinner className="mr-2 h-4 w-4 animate-spin" />
                                Saving...
                            </>
                        ) : (
                            <>
                                <CheckCircle2 className="mr-2 h-4 w-4" />
                                Save Selection ({selectedRepos.size})
                            </>
                        )}
                    </Button>
                </DialogFooter>
            </DialogContent>
        </Dialog>
    );
}

// =============================================================================
// Repo Item Component
// =============================================================================

interface RepoItemProps {
    repo: GitHubRepo;
    selected: boolean;
    onSelect: () => void;
    formatDate: (date?: string) => string;
}

function RepoItem({ repo, selected, onSelect, formatDate }: RepoItemProps) {
    return (
        <div
            className={cn(
                "w-full flex items-start gap-3 p-3 rounded-lg border transition-all text-left cursor-pointer",
                selected 
                    ? "bg-primary/5 border-primary/30" 
                    : "bg-background border-border hover:border-primary/20 hover:bg-muted/30"
            )}
            onClick={onSelect}
            role="button"
            tabIndex={0}
            onKeyDown={(e) => e.key === 'Enter' && onSelect()}
        >
            <Checkbox 
                checked={selected}
                className="mt-0.5 data-[state=checked]:bg-primary pointer-events-none"
            />
            
            <div className="flex-1 min-w-0">
                <div className="flex items-center gap-2 flex-wrap">
                    <span className="font-medium truncate">{repo.name}</span>
                    
                    {/* Badges */}
                    <div className="flex items-center gap-1 flex-wrap">
                        {repo.private ? (
                            <Badge variant="secondary" className="gap-1 text-xs">
                                <Lock className="h-3 w-3" />
                                Private
                            </Badge>
                        ) : (
                            <Badge variant="outline" className="gap-1 text-xs">
                                <Globe className="h-3 w-3" />
                                Public
                            </Badge>
                        )}
                        
                        {repo.fork && (
                            <Badge variant="outline" className="gap-1 text-xs">
                                <GitFork className="h-3 w-3" />
                                Fork
                            </Badge>
                        )}
                        
                        {repo.archived && (
                            <Badge variant="destructive" className="gap-1 text-xs">
                                <Archive className="h-3 w-3" />
                                Archived
                            </Badge>
                        )}
                    </div>
                </div>

                {repo.description && (
                    <p className="mt-1 text-sm text-muted-foreground line-clamp-1">
                        {repo.description}
                    </p>
                )}

                <div className="mt-2 flex items-center gap-3 text-xs text-muted-foreground">
                    {repo.language && (
                        <span className="flex items-center gap-1">
                            <span className="h-2 w-2 rounded-full bg-primary" />
                            {repo.language}
                        </span>
                    )}
                    
                    {repo.stargazers_count > 0 && (
                        <span className="flex items-center gap-1">
                            <Star className="h-3 w-3" />
                            {repo.stargazers_count}
                        </span>
                    )}
                    
                    {repo.updated_at && (
                        <span>Updated {formatDate(repo.updated_at)}</span>
                    )}
                    
                    <span className="flex items-center gap-1">
                        <GitBranch className="h-3 w-3" />
                        {repo.default_branch}
                    </span>
                </div>
            </div>
        </div>
    );
}

export default GitHubRepoSelector;