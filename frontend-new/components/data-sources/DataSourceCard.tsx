import {
  Tooltip,
  TooltipContent,
  TooltipProvider,
  TooltipTrigger,
} from "@/components/ui/tooltip";

// ... existing imports

export function DataSourceCard({
  source,
  onBrowse,
  onConnect,
  onDisconnect,
  onSync
}: DataSourceCardProps) {
  // ... existing hooks

  return (
    <div
      className={cn(
        "group relative flex flex-col justify-between rounded-xl border bg-card p-5 transition-all duration-300",
        source.isConnected
          ? "border-primary/50 bg-gradient-to-br from-primary/5 to-transparent shadow-lg shadow-primary/10"
          : "border-border hover:border-primary/30 hover:shadow-lg hover:shadow-primary/5 hover:-translate-y-0.5"
      )}
    >
      {/* ... existing badge code ... */}
      {source.isConnected && (
        <div className="absolute right-3 top-3">
          <Badge className="gap-1.5 bg-gradient-to-r from-emerald-500 to-green-500 text-white border-0 shadow-lg shadow-emerald-500/20">
            <Check className="h-3 w-3" />
            Connected
          </Badge>
        </div>
      )}

      <div className="space-y-4">
        {/* ... existing icon code ... */}
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
      </div>

      <div className="mt-6 pt-4 border-t border-border/50">
        {source.isConnected ? (
          <div className="flex items-center gap-2">
            <Button
              variant="gradient"
              size="sm"
              className="flex-1 shadow-md hover:shadow-lg transition-all"
              onClick={onBrowse}
              disabled={isLoading || isSyncing}
            >
              <ExternalLink className="mr-2 h-4 w-4" />
              Browse
            </Button>

            <TooltipProvider>
              <div className="flex items-center gap-1 border-l border-border/50 pl-2 ml-1">
                <Tooltip>
                  <TooltipTrigger asChild>
                    <Button
                      variant="ghost"
                      size="icon"
                      className="h-9 w-9 text-muted-foreground hover:text-primary hover:bg-primary/10"
                      onClick={handleSync}
                      disabled={isLoading || isSyncing}
                    >
                      <RefreshCw className={cn("h-4 w-4", isSyncing && "animate-spin")} />
                      <span className="sr-only">Sync Now</span>
                    </Button>
                  </TooltipTrigger>
                  <TooltipContent>
                    <p>Sync Now</p>
                  </TooltipContent>
                </Tooltip>

                <Tooltip>
                  <TooltipTrigger asChild>
                    <Button
                      variant="ghost"
                      size="icon"
                      className="h-9 w-9 text-muted-foreground hover:text-destructive hover:bg-destructive/10"
                      onClick={handleDisconnect}
                      disabled={isLoading || isSyncing}
                    >
                      {isLoading ? (
                        <Loader2 className="h-4 w-4 animate-spin" />
                      ) : (
                        <X className="h-4 w-4" />
                      )}
                      <span className="sr-only">Disconnect</span>
                    </Button>
                  </TooltipTrigger>
                  <TooltipContent>
                    <p>Disconnect</p>
                  </TooltipContent>
                </Tooltip>
              </div>
            </TooltipProvider>
          </div>
        ) : (
          <Button
            variant="outline"
            size="sm"
            className="w-full transition-all hover:border-primary hover:bg-primary/5 hover:text-primary group-hover:border-primary/50"
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