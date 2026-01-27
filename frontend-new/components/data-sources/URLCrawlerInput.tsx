
"use client";

import { useState } from "react";
import { Globe, ArrowRight } from "lucide-react";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Slider } from "@/components/ui/slider";
import { DataSource } from "@/lib/mockData";
import { useToast } from "@/hooks/use-toast";
import { useIngestionProgress } from "@/hooks/useIngestionProgress";
import { api } from "@/lib/api";
import { ROLE_TOAST_TITLES, ROLE_MESSAGES } from "@/lib/role-messages";
import { Spinner } from "@/components/ui/spinner";

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

export function URLCrawlerInput({ source, disabled = false, disabledReason }: URLCrawlerInputProps) {
  const { toast } = useToast();
  const [url, setUrl] = useState("");
  const [depth, setDepth] = useState(1);
  const [isLoading, setIsLoading] = useState(false);

  // Use centralized ingestion progress context - GlobalProgress renders the UI
  const { registerJob } = useIngestionProgress();

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

      const jobId = (response as { data?: { job_id?: string; crawl_id?: string } })?.data?.job_id
        || (response as { data?: { crawl_id?: string } })?.data?.crawl_id
        || null;
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
      console.error("Crawl failed:", apiError);
      toast({
        title: "Crawl Failed",
        description: apiError.response?.data?.detail || "Could not crawl the URL. Please try again.",
        variant: "destructive",
      });
    } finally {
      setIsLoading(false);
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
          />
        </div>

        {/* Input & Action */}
        <div className="flex gap-2">
          <Input
            type="url"
            placeholder="https://example.com/docs"
            value={url}
            onChange={(e) => setUrl(e.target.value)}
            disabled={isLoading || disabled}
            onKeyDown={(e) => {
              if (e.key === "Enter" && url.trim()) {
                handleCrawl();
              }
            }}
          />
          <Button
            onClick={handleCrawl}
            disabled={!url.trim() || isLoading || disabled}
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