"use client";

import { useState } from "react";
import { Loader2, Check, X, Lock, Bell } from "lucide-react";
import { Button } from "@/components/ui/button";
import { Badge } from "@/components/ui/badge";
import { DataSource } from "@/lib/mockData";
import { useDataSources } from "@/hooks/useDataSources";
import { useToast } from "@/hooks/use-toast";
import { DataSourceIcon } from "./DataSourceIcon";
import { SFTPConnectionModal } from "./SFTPConnectionModal";

interface DataSourceCardProps {
  source: DataSource;
  onBrowse: () => void;
}

export function DataSourceCard({ source, onBrowse }: DataSourceCardProps) {
  const { connectedSources, connect, disconnect } = useDataSources();
  const { toast } = useToast();
  const [isLoading, setIsLoading] = useState(false);
  const [sftpModalOpen, setSftpModalOpen] = useState(false);

  // Check if connected based on ID presence in the connectedSources array
  const connected = connectedSources.includes(source.id);

  // Connection info logic would likely come from the hook if we had detailed status
  // For now we'll just show name/description
  const connectionInfo = connected ? { email: "john@company.com" } : null;

  const handleConnect = async () => {
    // Special handling for SFTP
    // if (source.id === "sftp") {
    //   setSftpModalOpen(true);
    //   return;
    // }

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

  // Use comingSoon from source data
  const comingSoon = source.comingSoon ?? false;

  if (comingSoon) {
    return (
      <div className="relative rounded-xl border border-border bg-card p-5 opacity-60">
        <div className="absolute right-3 top-3">
          <Badge variant="secondary" className="gap-1">
            <Lock className="h-3 w-3" />
            Soon
          </Badge>
        </div>
        <div className="space-y-3">
          <DataSourceIcon sourceId={source.id} className="h-10 w-10" />
          <div>
            <h3 className="font-medium text-foreground">{source.name}</h3>
            <p className="mt-1 text-sm text-muted-foreground">{source.description}</p>
          </div>
          <Button variant="outline" size="sm" className="w-full gap-2" disabled>
            <Bell className="h-4 w-4" />
            Notify Me
          </Button>
        </div>
      </div>
    );
  }

  return (
    <>
      <div
        className={`relative rounded-xl border bg-card p-5 transition-all ${connected
          ? "border-primary shadow-brand"
          : "border-border hover:border-primary/30 hover:shadow-sm"
          }`}
      >
        {connected && (
          <div className="absolute right-3 top-3">
            <Badge variant="success" className="gap-1">
              <Check className="h-3 w-3" />
              Connected
            </Badge>
          </div>
        )}

        <div className="space-y-3">
          <DataSourceIcon sourceId={source.id} className="h-10 w-10" />
          <div>
            <h3 className="font-medium text-foreground">{source.name}</h3>
            {connected && connectionInfo?.email ? (
              <p className="mt-1 text-sm text-muted-foreground">{connectionInfo.email}</p>
            ) : (
              <p className="mt-1 text-sm text-muted-foreground">{source.description}</p>
            )}
          </div>

          {connected ? (
            <div className="flex gap-2">
              <Button
                variant="gradient"
                size="sm"
                className="flex-1"
                onClick={onBrowse}
                disabled={isLoading}
              >
                Browse
              </Button>
              <Button
                variant="outline"
                size="sm"
                className="text-destructive hover:bg-destructive hover:text-destructive-foreground"
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
              className="w-full"
              onClick={handleConnect}
              disabled={isLoading}
            >
              {isLoading && <Loader2 className="mr-2 h-4 w-4 animate-spin" />}
              Connect
            </Button>
          )}
        </div>
      </div>

      {/* {source.id === "sftp" && (
        <SFTPConnectionModal
          open={sftpModalOpen}
          onOpenChange={setSftpModalOpen}
        />
      )} */}
    </>
  );
}