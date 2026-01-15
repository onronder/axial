"use client";

import { useState } from "react";
import { Loader2, Check, X, ExternalLink, Clock, RefreshCw, AlertCircle } from "lucide-react";
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
import type { MergedDataSource } from "@/types";

interface DataSourceCardProps {
  source: MergedDataSource;
  onBrowse: () => void;
  onConnect: (type: string) => void;
  onDisconnect: (type: string) => Promise<void>;
  onSync: (integrationId: string) => Promise<{ success: boolean; jobId: string }>;
  disabled?: boolean;
  /** Indicates this source encountered a quota/limit issue */
  quotaExceeded?: boolean;
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
}: DataSourceCardProps) {
  const { toast } = useToast();
  const [isLoading, setIsLoading] = useState(false);
  const [isSyncing, setIsSyncing] = useState(false);

  const handleConnect = async () => {
    if (disabled) {
      toast({
        title: "View only",
        description: "You need editor or admin access to connect sources.",
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
        title: "View only",
        description: "You need editor or admin access to manage connections.",
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
        title: "View only",
        description: "You need editor or admin access to sync data.",
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
        "group glass-card border-white/10 p-4 transition-all duration-300",
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
                : "bg-muted group-hover:bg-primary/10"
            )}
          >
            <DataSourceIcon
              sourceId={source.type}
              className="h-6 w-6"
            />
          </div>

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

        {source.isConnected && (
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
        )}
      </div>

      {/* Row 2: Title + Sync Status */}
      <div className="mb-4">
        <h3 className="font-semibold text-foreground text-base">{source.name}</h3>
        {source.isConnected ? (
          <p className="text-xs text-muted-foreground flex items-center gap-1 mt-0.5">
            <Clock className="h-3 w-3" />
            Synced: {formatLastSync(source.lastSyncAt)}
          </p>
        ) : (
          <p className="text-xs text-muted-foreground line-clamp-2 mt-0.5">
            {source.description}
          </p>
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
                    <Loader2 className="h-4 w-4 animate-spin" />
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
      ) : (
        <Button
          variant="outline"
          size="sm"
          className="w-full h-8 text-xs font-medium hover:border-primary hover:bg-primary/5 hover:text-primary"
          onClick={handleConnect}
          disabled={isLoading || disabled}
        >
          {isLoading && <Loader2 className="mr-1.5 h-3.5 w-3.5 animate-spin" />}
          Connect
        </Button>
      )}
    </div>
  );
}
