"use client";

import { useState } from "react";
import { Globe, Loader2, ArrowRight } from "lucide-react";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Slider } from "@/components/ui/slider";
import { DataSource } from "@/lib/mockData";
import { useToast } from "@/hooks/use-toast";
import { api } from "@/lib/api";

interface URLCrawlerInputProps {
  source: DataSource;
}

export function URLCrawlerInput({ source }: URLCrawlerInputProps) {
  const { toast } = useToast();
  const [url, setUrl] = useState("");
  const [depth, setDepth] = useState(1);
  const [isLoading, setIsLoading] = useState(false);

  const handleCrawl = async () => {
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
      // Call the advanced crawler endpoint
      // Must use FormData because the endpoint expects 'Form' fields
      const formData = new FormData();
      formData.append("url", url);

      // Metadata payload for advanced options
      const metadata = {
        depth: depth,
        crawl_type: depth > 1 ? "recursive" : "single",
        respect_robots: true // Default to true
      };
      formData.append("metadata", JSON.stringify(metadata));

      await api.post("/ingest", formData, {
        headers: {
          "Content-Type": "multipart/form-data",
        },
      });

      toast({
        title: "Crawl Started",
        description: depth > 1
          ? `Recursively crawling ${url} (Depth: ${depth})`
          : `Ingesting ${url}`,
      });
      setUrl("");
      setDepth(1); // Reset depth
    } catch (error: any) {
      console.error("Crawl failed:", error);
      toast({
        title: "Crawl Failed",
        description: error.response?.data?.detail || "Could not crawl the URL. Please try again.",
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
            disabled={isLoading}
            onKeyDown={(e) => {
              if (e.key === "Enter" && url.trim()) {
                handleCrawl();
              }
            }}
          />
          <Button
            onClick={handleCrawl}
            disabled={!url.trim() || isLoading}
            variant="gradient"
            size="icon"
          >
            {isLoading ? (
              <Loader2 className="h-4 w-4 animate-spin" />
            ) : (
              <ArrowRight className="h-4 w-4" />
            )}
          </Button>
        </div>
      </div>
    </div>
  );
}