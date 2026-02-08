
"use client";

import { useState, useEffect, useCallback, useRef } from "react";
import { Globe, ArrowRight, X } from "lucide-react";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Slider } from "@/components/ui/slider";
import { DataSource } from "@/lib/mockData";
import { useToast } from "@/hooks/use-toast";
import { useIngestionProgress } from "@/hooks/useIngestionProgress";
import { api } from "@/lib/api";
import { ROLE_TOAST_TITLES, ROLE_MESSAGES } from "@/lib/role-messages";
import { Spinner } from "@/components/ui/spinner";
import { cn } from "@/lib/utils";

interface URLCrawlerInputProps {
  source: DataSource;
  disabled?: boolean;
  disabledReason?: string;
}

type ApiError = {
  response?: {
    data?: {
      detail?: string;
    };
  };
};

interface ActiveCrawl {
  crawlId: string;
  jobId: string | null;
  url: string;
  status: string;
}

interface WebCrawlConfig {
  id: string;
  root_url: string;
  crawl_type: string;
  status: string;
  max_depth: number;
  max_pages: number;
  total_pages_found: number;
  pages_ingested: number;
  pages_failed: number;
}

export function URLCrawlerInput({ source, disabled = false, disabledReason }: URLCrawlerInputProps) {
  const { toast } = useToast();
  const [url, setUrl] = useState("");
  const [depth, setDepth] = useState(1);
  const [isLoading, setIsLoading] = useState(false);
  const [isCancelling, setIsCancelling] = useState(false);
  const [activeCrawl, setActiveCrawl] = useState<ActiveCrawl | null>(null);
  const [isInitializing, setIsInitializing] = useState(true);
  const hasFetched = useRef(false);

  // Use centralized ingestion progress context - GlobalProgress renders the UI
  const { registerJob, unregisterJob } = useIngestionProgress();

  // Fetch active crawl on mount to restore state after navigation
  const fetchActiveCrawl = useCallback(async () => {
    try {
      const response = await api.get<WebCrawlConfig | null>("/integrations/web/crawl/active");
      const data = response.data;
      
      if (data && data.id) {
        setActiveCrawl({
          crawlId: data.id,
          jobId: data.id, // crawl_id is also the job_id for web crawls
          url: data.root_url,
          status: data.status,
        });
        
        // Register with progress context if not already tracked
        registerJob(data.id);
        
        if (process.env.NODE_ENV === 'development') {
          console.log('🔄 [URLCrawler] Restored active crawl:', data.root_url);
        }
      }
    } catch (error) {
      // Silently fail - user may not have any active crawls
      if (process.env.NODE_ENV === 'development') {
        console.log('🔄 [URLCrawler] No active crawl found');
      }
    } finally {
      setIsInitializing(false);
    }
  }, [registerJob]);

  // Fetch active crawl on mount (only once)
  useEffect(() => {
    if (!hasFetched.current) {
      hasFetched.current = true;
      fetchActiveCrawl();
    }
  }, [fetchActiveCrawl]);

  // Clear active crawl when status becomes terminal
  useEffect(() => {
    if (activeCrawl && ['completed', 'failed', 'cancelled'].includes(activeCrawl.status)) {
      setActiveCrawl(null);
    }
  }, [activeCrawl]);

  const handleCrawl = async () => {
    if (disabled) {
      toast({
        title: ROLE_TOAST_TITLES.ACTION_LOCKED,
        description: disabledReason || ROLE_MESSAGES.NEED_EDITOR_CRAWL,
        variant: "destructive",
      });
      return;
    }

    if (!url.trim()) return;

    // Validate URL
    try {
      new URL(url);
    } catch {
      toast({
        title: "Invalid URL",
        description: "Please enter a valid URL including https://",
        variant: "destructive",
      });
      return;
    }

    setIsLoading(true);
    try {
      const response = await api.post("/integrations/web/crawl", {
        url,
        crawl_type: depth > 1 ? "recursive" : "single",
        max_depth: depth,
        respect_robots: true,
        allow_subdomains: false,
      });

      const responseData = response.data as { crawl_id?: string; job_id?: string };
      const crawlId = responseData?.crawl_id || null;
      const jobId = responseData?.job_id || null;
      
      if (crawlId) {
        // Track active crawl for cancellation
        setActiveCrawl({
          crawlId,
          jobId,
          url: url.trim(),
          status: 'pending',
        });
      }
      
      if (jobId) {
        // Register job with centralized context - GlobalProgress will show UI
        registerJob(jobId);
      }

      toast({
        title: "Crawl Started",
        description: depth > 1
          ? `Recursively crawling ${url} (Depth: ${depth})`
          : `Ingesting ${url}`,
      });
      setUrl("");
      setDepth(1); // Reset depth
    } catch (error: unknown) {
      const apiError = error as ApiError;
      if (process.env.NODE_ENV !== 'production') {
        console.error("Crawl failed:", apiError);
      }
      toast({
        title: "Crawl Failed",
        description: apiError.response?.data?.detail || "Could not crawl the URL. Please try again.",
        variant: "destructive",
      });
    } finally {
      setIsLoading(false);
    }
  };

  const handleCancelCrawl = async () => {
    if (!activeCrawl) return;

    setIsCancelling(true);
    try {
      await api.delete(`/integrations/web/crawl/${activeCrawl.crawlId}`);
      
      // Unregister job from progress tracking
      if (activeCrawl.jobId) {
        unregisterJob(activeCrawl.jobId);
      }
      
      toast({
        title: "Crawl Cancelled",
        description: `Stopped crawling ${activeCrawl.url}`,
      });
      
      setActiveCrawl(null);
    } catch (error: unknown) {
      const apiError = error as ApiError;
      if (process.env.NODE_ENV !== 'production') {
        console.error("Cancel crawl failed:", apiError);
      }
      toast({
        title: "Cancel Failed",
        description: apiError.response?.data?.detail || "Could not cancel the crawl. Please try again.",
        variant: "destructive",
      });
    } finally {
      setIsCancelling(false);
    }
  };

  return (
    <div className="rounded-xl border border-border bg-card p-5">
      <div className="space-y-4">
        {/* Header Section */}
        <div className="flex items-start gap-4">
          <div className="flex h-10 w-10 shrink-0 items-center justify-center rounded-lg bg-success/10">
            <Globe className="h-5 w-5 text-success" />
          </div>
          <div className="flex-1">
            <h3 className="font-medium text-foreground">{source.name}</h3>
            <p className="mt-1 text-sm text-muted-foreground">{source.description}</p>
          </div>
        </div>

        {/* Active Crawl Indicator with Cancel */}
        {activeCrawl && (
          <div className={cn(
            "flex items-center justify-between gap-3 rounded-lg border p-3",
            "bg-primary/5 border-primary/20"
          )}>
            <div className="flex items-center gap-2 min-w-0 flex-1">
              <Spinner className="h-4 w-4 animate-spin text-primary shrink-0" />
              <div className="min-w-0">
                <p className="text-sm font-medium text-foreground truncate">
                  Crawling in progress
                </p>
                <p className="text-xs text-muted-foreground truncate">
                  {activeCrawl.url}
                </p>
              </div>
            </div>
            <Button
              variant="outline"
              size="sm"
              onClick={handleCancelCrawl}
              disabled={isCancelling}
              className="shrink-0 text-destructive hover:text-destructive hover:bg-destructive/10 border-destructive/30"
            >
              {isCancelling ? (
                <Spinner className="h-4 w-4 animate-spin" />
              ) : (
                <>
                  <X className="h-4 w-4 mr-1" />
                  Cancel
                </>
              )}
            </Button>
          </div>
        )}

        {/* Depth Slider */}
        <div className="space-y-3 pt-2">
          <div className="flex items-center justify-between">
            <label className="text-xs font-medium text-muted-foreground">
              Crawl Depth
            </label>
            <span className="text-xs font-mono text-foreground bg-muted px-2 py-0.5 rounded">
              {depth} level{depth > 1 ? 's' : ''}
            </span>
          </div>
          <Slider
            defaultValue={[1]}
            value={[depth]}
            onValueChange={(vals) => setDepth(vals[0])}
            max={5}
            min={1}
            step={1}
            className="py-1"
            disabled={!!activeCrawl}
          />
        </div>

        {/* Input & Action */}
        <div className="flex gap-2">
          <Input
            type="url"
            placeholder="https://example.com/docs"
            value={url}
            onChange={(e) => setUrl(e.target.value)}
            disabled={isLoading || disabled || !!activeCrawl}
            onKeyDown={(e) => {
              if (e.key === "Enter" && url.trim() && !activeCrawl) {
                handleCrawl();
              }
            }}
          />
          <Button
            onClick={handleCrawl}
            disabled={!url.trim() || isLoading || disabled || !!activeCrawl}
            variant="gradient"
            size="icon"
          >
            {isLoading ? (
              <Spinner className="h-4 w-4 animate-spin" />
            ) : (
              <ArrowRight className="h-4 w-4" />
            )}
          </Button>
        </div>
      </div>

      {disabledReason && (
        <p className="mt-3 text-xs text-muted-foreground">{disabledReason}</p>
      )}

      {/* Progress UI is now rendered by GlobalProgress - single source of truth */}
    </div>
  );
}