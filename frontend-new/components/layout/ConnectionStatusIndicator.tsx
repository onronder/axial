"use client";

import { AlertTriangle, WifiOff } from "lucide-react";
import { Button } from "@/components/ui/button";
import { Tooltip, TooltipContent, TooltipTrigger } from "@/components/ui/tooltip";

import { useRealtimeStatus } from "@/hooks/useRealtimeStatus";
import { Spinner } from "@/components/ui/spinner";

export function ConnectionStatusIndicator() {
  const { status, lastConnected, reconnect } = useRealtimeStatus();

  if (status === "connected") {
    return null;
  }

  const label =
    status === "connecting"
      ? "Reconnecting to realtime"
      : status === "error"
        ? "Realtime connection error"
        : "Realtime disconnected";

  return (
    <div className="fixed right-3 top-3 z-50">
      <Tooltip>
        <TooltipTrigger asChild>
          <Button
            type="button"
            variant="ghost"
            size="icon"
            onClick={reconnect}
            aria-label={label}
            className="text-amber-600 hover:text-amber-700"
          >
            {status === "connecting" && <Spinner size="sm" label="Reconnecting" />}
            {status === "disconnected" && <WifiOff className="h-4 w-4" />}
            {status === "error" && <AlertTriangle className="h-4 w-4" />}
          </Button>
        </TooltipTrigger>
        <TooltipContent>
          <div className="space-y-1">
            <p className="text-sm">
            {status === "connecting" && "Reconnecting..."}
              {status === "disconnected" && "Disconnected from realtime."}
              {status === "error" && "Realtime connection error."}
            </p>
            {lastConnected && (
              <p className="text-xs text-muted-foreground">
                Last connected: {lastConnected.toLocaleTimeString()}
              </p>
            )}
            <p className="text-xs text-muted-foreground">Click to retry.</p>
          </div>
        </TooltipContent>
      </Tooltip>
    </div>
  );
}
