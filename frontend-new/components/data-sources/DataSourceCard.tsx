"use client";

import { useState } from "react";
import { Loader2, Check, X, Lock, Bell, ExternalLink } from "lucide-react";
import { Button } from "@/components/ui/button";
import { Badge } from "@/components/ui/badge";
import { DataSource } from "@/lib/mockData";
import { useDataSources } from "@/hooks/useDataSources";
import { useToast } from "@/hooks/use-toast";
import { DataSourceIcon } from "./DataSourceIcon";
import { cn } from "@/lib/utils";

interface DataSourceCardProps {
  source: DataSource;
  onBrowse: () => void;
}

export function DataSourceCard({ source, onBrowse }: DataSourceCardProps) {
  const { connectedSources, connect, disconnect } = useDataSources();
  const { toast } = useToast();
  const [isLoading, setIsLoading] = useState(false);

  const connected = connectedSources.includes(source.id);
  const connectionInfo = connected ? { email: "john@company.com" } : null;

  const handleConnect = async () => {
    setIsLoading(true);
    try {
      await connect(source.id);
      toast({
        title: `${source.name} connected`,
        description: "You can now browse and ingest files.",
      });
    } catch {
      toast({
        title: "Connection failed",
        description: "Please try again.",
        variant: "destructive",
      });
    } finally {
      setIsLoading(false);
    }
  };

  const handleDisconnect = async () => {
    setIsLoading(true);
    try {
      await disconnect(source.id);
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

  const comingSoon = source.comingSoon ?? false;

  // Coming Soon Card
  if (comingSoon) {
    return (
      <div className="relative rounded-xl border border-border bg-card/50 p-5 opacity-70 backdrop-blur-sm">
        <div className="absolute right-3 top-3">
          <Badge variant="secondary" className="gap-1 bg-muted/80">
            <Lock className="h-3 w-3" />
            Soon
          </Badge>
        </div>
        <div className="space-y-4">
          <div className="flex h-12 w-12 items-center justify-center rounded-xl bg-muted/50">
            <DataSourceIcon sourceId={source.id} className="h-6 w-6 opacity-50" />
          </div>
          <div>
            <h3 className="font-semibold text-foreground/70">{source.name}</h3>
            <p className="mt-1 text-sm text-muted-foreground">{source.description}</p>
          </div>
          <Button variant="outline" size="sm" className="w-full gap-2 opacity-70" disabled>
            <Bell className="h-4 w-4" />
            Notify Me
          </Button>
        </div>
      </div>
    );
  }

  return (
    <div
      className={cn(
        "group relative rounded-xl border bg-card p-5 transition-all duration-300",
        connected
          ? "border-primary/50 bg-gradient-to-br from-primary/5 to-transparent shadow-lg shadow-primary/10"
          : "border-border hover:border-primary/30 hover:shadow-lg hover:shadow-primary/5 hover:-translate-y-0.5"
      )}
    >
      {/* Connection Status Badge */}
      {connected && (
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
          connected
            ? "bg-gradient-to-br from-primary to-accent shadow-lg shadow-primary/30"
            : "bg-muted group-hover:bg-primary/10"
        )}>
          <DataSourceIcon
            sourceId={source.id}
            className={cn(
              "h-6 w-6 transition-colors",
              connected ? "text-white" : "text-muted-foreground group-hover:text-primary"
            )}
          />
        </div>

        {/* Info */}
        <div>
          <h3 className="font-semibold text-foreground">{source.name}</h3>
          {connected && connectionInfo?.email ? (
            <p className="mt-1 text-sm text-primary">{connectionInfo.email}</p>
          ) : (
            <p className="mt-1 text-sm text-muted-foreground line-clamp-2">{source.description}</p>
          )}
        </div>

        {/* Actions */}
        {connected ? (
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