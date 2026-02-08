
"use client";

import { useState } from "react";
import { Check, X, ExternalLink, Clock, RefreshCw, AlertCircle, Lock, Sparkles } from "lucide-react";
import { Button } from "@/components/ui/button";
import { Badge } from "@/components/ui/badge";
import {
  Tooltip,
  TooltipContent,
  TooltipProvider,
  TooltipTrigger,
} from "@/components/ui/tooltip";
import { useToast } from "@/hooks/use-toast";
import { DataSourceIcon } from "./DataSourceIcon";
import { cn } from "@/lib/utils";
import type { MergedDataSource, PlanType } from "@/types";
import { ROLE_TOAST_TITLES, ROLE_MESSAGES } from "@/lib/role-messages";
import { Spinner } from "@/components/ui/spinner";

interface DataSourceCardProps {
  source: MergedDataSource;
  onBrowse: () => void;
  onConnect: (type: string) => void;
  onDisconnect: (type: string) => Promise<void>;
  onSync: (integrationId: string) => Promise<{ success: boolean; jobId: string }>;
  disabled?: boolean;
  /** Indicates this source encountered a quota/limit issue */
  quotaExceeded?: boolean;
  /** Indicates this connector requires Enterprise plan */
  enterpriseOnly?: boolean;
  /** Current user's plan for enterprise gating */
  userPlan?: PlanType | null;
}

function formatLastSync(lastSyncAt: string | null): string {
  if (!lastSyncAt) return "Never";

  const syncDate = new Date(lastSyncAt);
  const now = new Date();
  const diffMs = now.getTime() - syncDate.getTime();
  const diffMins = Math.floor(diffMs / 60000);
  const diffHours = Math.floor(diffMs / 3600000);
  const diffDays = Math.floor(diffMs / 86400000);

  if (diffMins < 1) return "Just now";
  if (diffMins < 60) return `${diffMins}m ago`;
  if (diffHours < 24) return `${diffHours}h ago`;
  if (diffDays < 7) return `${diffDays}d ago`;
  return syncDate.toLocaleDateString();
}

export function DataSourceCard({
  source,
  onBrowse,
  onConnect,
  onDisconnect,
  onSync,
  disabled = false,
  quotaExceeded = false,
  enterpriseOnly = false,
  userPlan = null,
}: DataSourceCardProps) {
  const { toast } = useToast();
  const [isLoading, setIsLoading] = useState(false);
  const [isSyncing, setIsSyncing] = useState(false);

  // Enterprise gate: Check if user can access this connector
  const isEnterpriseUser = userPlan === 'enterprise' || 
    (userPlan?.startsWith('enterprise_') ?? false);
  const showEnterpriseLock = enterpriseOnly && !isEnterpriseUser && !source.isConnected;

  const handleConnect = async () => {
    if (disabled) {
      toast({
        title: ROLE_TOAST_TITLES.VIEW_ONLY,
        description: ROLE_MESSAGES.NEED_EDITOR_CONNECT,
        variant: "destructive",
      });
      return;
    }
    setIsLoading(true);
    try {
      onConnect(source.type);
    } catch {
      toast({
        title: "Connection failed",
        description: "Please try again.",
        variant: "destructive",
      });
      setIsLoading(false);
    }
  };

  const handleDisconnect = async () => {
    if (disabled) {
      toast({
        title: ROLE_TOAST_TITLES.VIEW_ONLY,
        description: ROLE_MESSAGES.NEED_EDITOR_DISCONNECT,
        variant: "destructive",
      });
      return;
    }
    setIsLoading(true);
    try {
      await onDisconnect(source.type);
      toast({
        title: `${source.name} disconnected`,
        description: "Your connection has been removed.",
      });
    } catch {
      toast({
        title: "Disconnection failed",
        description: "Please try again.",
        variant: "destructive",
      });
    } finally {
      setIsLoading(false);
    }
  };

  const handleSync = async () => {
    if (disabled) {
      toast({
        title: ROLE_TOAST_TITLES.VIEW_ONLY,
        description: ROLE_MESSAGES.NEED_EDITOR_SYNC,
        variant: "destructive",
      });
      return;
    }
    if (!source.integrationId) return;
    setIsSyncing(true);
    try {
      await onSync(source.integrationId);
      toast({
        title: "Sync Started",
        description: `Started syncing ${source.name}. You'll be notified when complete.`,
      });
    } catch (err: unknown) {
      const message = err instanceof Error ? err.message : "Could not start sync.";
      toast({
        title: "Sync Failed",
        description: message,
        variant: "destructive",
      });
    } finally {
      setIsSyncing(false);
    }
  };

  return (
    <div
      className={cn(
        "group glass-card border-white/10 p-6 transition-all duration-300 flex flex-col",
        source.isConnected
          ? "border-primary/30 bg-gradient-to-br from-primary/10 via-transparent to-transparent shadow-glow"
          : "hover:border-primary/30 hover:shadow-md hover:-translate-y-0.5"
      )}
    >
      {/* Row 1: Icon + Badge */}
      <div className="flex items-start justify-between mb-3">
        <div className="relative">
          <div
            className={cn(
              "flex h-12 w-12 items-center justify-center rounded-xl",
              source.isConnected
                ? quotaExceeded
                  ? "bg-card border-2 border-destructive/50 shadow-md"
                  : "bg-card border-2 border-emerald-500/40 shadow-md"
                : showEnterpriseLock
                  ? "bg-muted/50 opacity-75"
                  : "bg-muted group-hover:bg-primary/10"
            )}
          >
            <DataSourceIcon
              sourceId={source.type}
              className={cn("h-6 w-6", showEnterpriseLock && "opacity-60")}
            />
          </div>

          {/* Enterprise-only badge */}
          {enterpriseOnly && !source.isConnected && (
            <TooltipProvider delayDuration={0}>
              <Tooltip>
                <TooltipTrigger asChild>
                  <div className="absolute -top-1.5 -right-1.5 h-5 w-5 rounded-full bg-gradient-to-r from-violet-500 to-purple-500 flex items-center justify-center shadow-lg cursor-help ring-2 ring-background">
                    <Lock className="h-2.5 w-2.5 text-white" />
                  </div>
                </TooltipTrigger>
                <TooltipContent side="top" className="max-w-[220px] text-center">
                  <p className="text-xs font-medium">Enterprise Only</p>
                  <p className="text-xs text-muted-foreground mt-0.5">
                    This connector requires an Enterprise plan.
                  </p>
                </TooltipContent>
              </Tooltip>
            </TooltipProvider>
          )}

          {/* Quota exceeded warning indicator */}
          {quotaExceeded && source.isConnected && (
            <TooltipProvider delayDuration={0}>
              <Tooltip>
                <TooltipTrigger asChild>
                  <div className="absolute -top-1.5 -right-1.5 h-5 w-5 rounded-full bg-destructive flex items-center justify-center shadow-lg cursor-help ring-2 ring-background">
                    <AlertCircle className="h-3 w-3 text-white" />
                  </div>
                </TooltipTrigger>
                <TooltipContent side="top" className="max-w-[220px] text-center">
                  <p className="text-xs font-medium">File limit exceeded</p>
                  <p className="text-xs text-muted-foreground mt-0.5">
                    Upgrade your plan to ingest more files from this source.
                  </p>
                </TooltipContent>
              </Tooltip>
            </TooltipProvider>
          )}
        </div>

        {source.isConnected ? (
          <Badge 
            className={cn(
              "gap-1 text-white text-xs border-0 px-2 py-0.5",
              quotaExceeded 
                ? "bg-amber-500/90" 
                : "bg-emerald-500/90"
            )}
          >
            <Check className="h-3 w-3" />
            Connected
          </Badge>
        ) : enterpriseOnly && (
          <Badge 
            className="gap-1 text-white text-xs border-0 px-2 py-0.5 bg-gradient-to-r from-violet-500 to-purple-500"
          >
            <Sparkles className="h-3 w-3" />
            Enterprise
          </Badge>
        )}
      </div>

      {/* Row 2: Title + Description/Sync Status */}
      <div className="mb-4 min-h-[52px]">
        <h3 className="font-semibold text-foreground text-base">{source.name}</h3>
        {source.isConnected ? (
          <div className="space-y-1">
            <p className="text-xs text-muted-foreground flex items-center gap-1 mt-0.5">
              <Clock className="h-3 w-3" />
              Synced: {formatLastSync(source.lastSyncAt)}
              {source.lastSyncStatus === 'failed' && (
                <Badge variant="outline" className="ml-1 text-[10px] px-1.5 py-0 border-destructive/30 text-destructive">
                  Failed
                </Badge>
              )}
              {source.lastSyncStatus === 'running' && (
                <Badge variant="outline" className="ml-1 text-[10px] px-1.5 py-0 border-blue-500/30 text-blue-500">
                  Running
                </Badge>
              )}
            </p>
            {/* Sync Error Display */}
            {source.lastSyncError && (
              <TooltipProvider delayDuration={0}>
                <Tooltip>
                  <TooltipTrigger asChild>
                    <p className="text-xs text-destructive flex items-center gap-1 cursor-help">
                      <AlertCircle className="h-3 w-3 flex-shrink-0" />
                      <span className="truncate">{source.lastSyncError.slice(0, 40)}...</span>
                    </p>
                  </TooltipTrigger>
                  <TooltipContent 
                    side="bottom" 
                    className="max-w-[320px] text-left z-50"
                    sideOffset={5}
                  >
                    <p className="text-xs font-medium text-destructive mb-1">Sync Error</p>
                    <p className="text-xs text-muted-foreground">{source.lastSyncError}</p>
                  </TooltipContent>
                </Tooltip>
              </TooltipProvider>
            )}
          </div>
        ) : (
          <TooltipProvider delayDuration={300}>
            <Tooltip>
              <TooltipTrigger asChild>
                <p className="text-xs text-muted-foreground line-clamp-2 mt-0.5 cursor-help">
                  {source.description}
                </p>
              </TooltipTrigger>
              {source.description && source.description.length > 60 && (
                <TooltipContent 
                  side="bottom" 
                  className="max-w-[280px] text-left z-50"
                  sideOffset={5}
                >
                  <p className="text-xs">{source.description}</p>
                </TooltipContent>
              )}
            </Tooltip>
          </TooltipProvider>
        )}
      </div>

      {/* Row 3: Actions */}
      {source.isConnected ? (
        <div className="flex items-center gap-2">
          <Button
            variant="gradient"
            size="sm"
            className="gap-1.5 px-3 h-8 text-xs font-medium shadow-sm"
            onClick={onBrowse}
            disabled={isLoading || isSyncing || disabled}
          >
            <ExternalLink className="h-3.5 w-3.5" />
            Browse
          </Button>

          <TooltipProvider delayDuration={300}>
            <Tooltip>
              <TooltipTrigger asChild>
                <Button
                  variant="ghost"
                  size="icon"
                  className="h-8 w-8 text-muted-foreground hover:text-primary hover:bg-primary/10"
                  onClick={handleSync}
                  disabled={isLoading || isSyncing || disabled}
                >
                  <RefreshCw
                    className={cn("h-4 w-4", isSyncing && "animate-spin")}
                  />
                </Button>
              </TooltipTrigger>
              <TooltipContent side="bottom">
                <p className="text-xs">Sync Now</p>
              </TooltipContent>
            </Tooltip>

            <Tooltip>
              <TooltipTrigger asChild>
                <Button
                  variant="ghost"
                  size="icon"
                  className="h-8 w-8 text-muted-foreground hover:text-destructive hover:bg-destructive/10"
                  onClick={handleDisconnect}
                  disabled={isLoading || isSyncing || disabled}
                >
                  {isLoading ? (
                    <Spinner className="h-4 w-4 animate-spin" />
                  ) : (
                    <X className="h-4 w-4" />
                  )}
                </Button>
              </TooltipTrigger>
              <TooltipContent side="bottom">
                <p className="text-xs">Disconnect</p>
              </TooltipContent>
            </Tooltip>
          </TooltipProvider>
        </div>
      ) : showEnterpriseLock ? (
        /* Enterprise Upgrade CTA for non-enterprise users */
        <TooltipProvider delayDuration={400}>
          <Tooltip>
            <TooltipTrigger asChild>
              <Button
                variant="outline"
                size="sm"
                className="w-full h-8 text-xs font-medium border-violet-500/50 bg-gradient-to-r from-violet-500/10 to-purple-500/10 hover:from-violet-500/20 hover:to-purple-500/20 text-violet-400 hover:text-violet-300"
                onClick={() => window.location.href = '/dashboard/settings/billing'}
              >
                <Sparkles className="mr-1.5 h-3.5 w-3.5" />
                Upgrade to Enterprise
              </Button>
            </TooltipTrigger>
            <TooltipContent 
              side="top" 
              className="max-w-[240px] text-center z-50"
              sideOffset={8}
            >
              <p className="text-xs">
                {source.name} connector is available on Enterprise plans. 
                Upgrade to connect cloud storage with advanced security.
              </p>
            </TooltipContent>
          </Tooltip>
        </TooltipProvider>
      ) : (
        <Button
          variant="outline"
          size="sm"
          className="w-full h-8 text-xs font-medium hover:border-primary hover:bg-primary/5 hover:text-primary"
          onClick={handleConnect}
          disabled={isLoading || disabled}
        >
          {isLoading && <Spinner className="mr-2 h-4 w-4 animate-spin" />}
          Connect
        </Button>
      )}
    </div>
  );
}