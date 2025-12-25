"use client";

import { useState } from "react";
import { Globe, Loader2, ArrowRight } from "lucide-react";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { DataSource } from "@/lib/mockData";
import { useToast } from "@/hooks/use-toast";
import { api } from "@/lib/api";

interface URLCrawlerInputProps {
  source: DataSource;
}

export function URLCrawlerInput({ source }: URLCrawlerInputProps) {
  const { toast } = useToast();
  const [url, setUrl] = useState("");
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
      // Call the backend web connector ingest endpoint
      // For web connector, item_ids are URLs
      await api.post("/integrations/web/ingest", {
        item_ids: [url]
      });

      toast({
        title: "Website Ingested",
        description: "Content has been added to your knowledge base.",
      });
      setUrl("");
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
      <div className="space-y-3">
        <div className="flex h-10 w-10 items-center justify-center rounded-lg bg-success/10">
          <Globe className="h-5 w-5 text-success" />
        </div>
        <div>
          <h3 className="font-medium text-foreground">{source.name}</h3>
          <p className="mt-1 text-sm text-muted-foreground">{source.description}</p>
        </div>
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