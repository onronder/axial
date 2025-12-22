"use client";

import { useState } from "react";
import { Loader2, Check, X, Lock, Bell, ExternalLink, Clock } from "lucide-react";
import { Button } from "@/components/ui/button";
import { Badge } from "@/components/ui/badge";
import { useDataSources } from "@/hooks/useDataSources";
import { useToast } from "@/hooks/use-toast";
import { DataSourceIcon } from "./DataSourceIcon";
import { cn } from "@/lib/utils";
import type { MergedDataSource } from "@/types";

interface DataSourceCardProps {
  source: MergedDataSource;
  onBrowse: () => void;
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

export function DataSourceCard({ source, onBrowse }: DataSourceCardProps) {
  const { connect, disconnect } = useDataSources();
  const { toast } = useToast();
  const [isLoading, setIsLoading] = useState(false);

  const handleConnect = async () => {
    setIsLoading(true);
    try {
      connect(source.type);
      // Note: OAuth redirect happens, so we don't need to show toast here
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
    setIsLoading(true);
    try {
      await disconnect(source.type);
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

  return (
    <div
      className={cn(
        "group relative rounded-xl border bg-card p-5 transition-all duration-300",
        source.isConnected
          ? "border-primary/50 bg-gradient-to-br from-primary/5 to-transparent shadow-lg shadow-primary/10"
          : "border-border hover:border-primary/30 hover:shadow-lg hover:shadow-primary/5 hover:-translate-y-0.5"
      )}
    >
      {/* Connection Status Badge */}
      {source.isConnected && (
        <div className="absolute right-3 top-3">
          <Badge className="gap-1.5 bg-gradient-to-r from-emerald-500 to-green-500 text-white border-0 shadow-lg shadow-emerald-500/20">
            <Check className="h-3 w-3" />
            Connected
          </Badge>
        </div>
      )}

      <div className="space-y-4">
        {/* Icon with gradient on connected state */}
        <div className={cn(
          "flex h-12 w-12 items-center justify-center rounded-xl transition-all duration-300",
          source.isConnected
            ? "bg-gradient-to-br from-primary to-accent shadow-lg shadow-primary/30"
            : "bg-muted group-hover:bg-primary/10"
        )}>
          <DataSourceIcon
            sourceId={source.type}
            className={cn(
              "h-6 w-6 transition-colors",
              source.isConnected ? "text-white" : "text-muted-foreground group-hover:text-primary"
            )}
          />
        </div>

        {/* Info */}
        <div>
          <h3 className="font-semibold text-foreground">{source.name}</h3>
          {source.isConnected ? (
            <p className="mt-1 text-sm text-muted-foreground flex items-center gap-1">
              <Clock className="h-3 w-3" />
              Synced: {formatLastSync(source.lastSyncAt)}
            </p>
          ) : (
            <p className="mt-1 text-sm text-muted-foreground line-clamp-2">{source.description}</p>
          )}
        </div>

        {/* Actions */}
        {source.isConnected ? (
          <div className="flex gap-2">
            <Button
              variant="gradient"
              size="sm"
              className="flex-1 gap-2"
              onClick={onBrowse}
              disabled={isLoading}
            >
              <ExternalLink className="h-4 w-4" />
              Browse
            </Button>
            <Button
              variant="outline"
              size="icon"
              className="h-9 w-9 shrink-0 text-muted-foreground hover:text-destructive hover:border-destructive/50 hover:bg-destructive/10"
              onClick={handleDisconnect}
              disabled={isLoading}
            >
              {isLoading ? <Loader2 className="h-4 w-4 animate-spin" /> : <X className="h-4 w-4" />}
            </Button>
          </div>
        ) : (
          <Button
            variant="outline"
            size="sm"
            className="w-full transition-all hover:border-primary hover:bg-primary/5 hover:text-primary"
            onClick={handleConnect}
            disabled={isLoading}
          >
            {isLoading && <Loader2 className="mr-2 h-4 w-4 animate-spin" />}
            Connect
          </Button>
        )}
      </div>
    </div>
  );
}