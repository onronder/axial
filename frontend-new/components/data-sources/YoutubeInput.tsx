"use client";

import { useState, useCallback, useMemo } from "react";
import { useQueryClient } from "@tanstack/react-query";
import { Youtube, Loader2, ArrowRight, AlertCircle } from "lucide-react";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { DataSource } from "@/lib/mockData";
import { useToast } from "@/hooks/use-toast";
import { useUsage } from "@/hooks/useUsage";
import { api } from "@/lib/api";
import { useFileStatus } from "@/hooks/useFileStatus";
import { IngestionProgressModal } from "@/components/ingestion/IngestionProgressModal";
import { cn } from "@/lib/utils";

// =============================================================================
// Types
// =============================================================================

interface YoutubeInputProps {
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
  message?: string;
};

// =============================================================================
// YouTube URL Validation
// =============================================================================

/**
 * Comprehensive YouTube URL validation regex.
 * Supports:
 * - Standard watch URLs: youtube.com/watch?v=VIDEO_ID
 * - Short URLs: youtu.be/VIDEO_ID
 * - Embed URLs: youtube.com/embed/VIDEO_ID
 * - v/ URLs: youtube.com/v/VIDEO_ID
 * - Shorts: youtube.com/shorts/VIDEO_ID
 * - With or without www prefix
 * - With or without https:// prefix
 * - With additional query parameters (e.g., &t=120 for timestamp)
 */
const YOUTUBE_URL_PATTERNS = [
  // Standard watch URL
  /^(https?:\/\/)?(www\.)?youtube\.com\/watch\?v=[\w-]{11}/i,
  // Short URL
  /^(https?:\/\/)?(www\.)?youtu\.be\/[\w-]{11}/i,
  // Embed URL
  /^(https?:\/\/)?(www\.)?youtube\.com\/embed\/[\w-]{11}/i,
  // v/ URL (legacy)
  /^(https?:\/\/)?(www\.)?youtube\.com\/v\/[\w-]{11}/i,
  // Shorts URL
  /^(https?:\/\/)?(www\.)?youtube\.com\/shorts\/[\w-]{11}/i,
];

/**
 * Validates if a given URL is a valid YouTube video URL.
 * @param url - The URL to validate
 * @returns true if the URL is a valid YouTube video URL
 */
function isValidYoutubeUrl(url: string): boolean {
  const trimmedUrl = url.trim();
  if (!trimmedUrl) return false;
  
  return YOUTUBE_URL_PATTERNS.some((pattern) => pattern.test(trimmedUrl));
}

/**
 * Extracts the video ID from a YouTube URL.
 * @param url - The YouTube URL
 * @returns The video ID or null if not found
 */
function extractVideoId(url: string): string | null {
  const trimmedUrl = url.trim();
  
  // Try to extract from watch URL
  const watchMatch = trimmedUrl.match(/[?&]v=([\w-]{11})/);
  if (watchMatch) return watchMatch[1];
  
  // Try to extract from short URL, embed, v/, or shorts
  const pathMatch = trimmedUrl.match(/(?:youtu\.be\/|embed\/|v\/|shorts\/)([\w-]{11})/);
  if (pathMatch) return pathMatch[1];
  
  return null;
}

/**
 * Normalizes a YouTube URL to ensure it has proper protocol.
 * @param url - The YouTube URL to normalize
 * @returns Normalized URL with https:// prefix
 */
function normalizeYoutubeUrl(url: string): string {
  const trimmedUrl = url.trim();
  
  // Add https:// if missing
  if (!trimmedUrl.startsWith('http://') && !trimmedUrl.startsWith('https://')) {
    return `https://${trimmedUrl}`;
  }
  
  // Convert http to https
  if (trimmedUrl.startsWith('http://')) {
    return trimmedUrl.replace('http://', 'https://');
  }
  
  return trimmedUrl;
}

// =============================================================================
// Component
// =============================================================================

export function YoutubeInput({ 
  source, 
  disabled = false, 
  disabledReason 
}: YoutubeInputProps) {
  const { toast } = useToast();
  const queryClient = useQueryClient();
  const { refresh } = useUsage();
  
  // Form state
  const [url, setUrl] = useState("");
  const [isLoading, setIsLoading] = useState(false);
  const [currentJobId, setCurrentJobId] = useState<string | null>(null);
  const [validationError, setValidationError] = useState<string | null>(null);

  // File status tracking for progress modal
  const { files: fileStatuses } = useFileStatus(currentJobId);

  // Computed validation state
  const isValidUrl = useMemo(() => {
    if (!url.trim()) return null; // Not yet entered
    return isValidYoutubeUrl(url);
  }, [url]);

  const videoId = useMemo(() => {
    if (!url.trim() || !isValidUrl) return null;
    return extractVideoId(url);
  }, [url, isValidUrl]);

  /**
   * Called when the YouTube video has finished processing.
   * Refreshes usage stats and invalidates document cache to update UI.
   */
  const handleIngestionComplete = useCallback(() => {
    console.log("📺 [YoutubeInput] Ingestion complete - refreshing data...");
    
    // Refresh usage stats (file count, storage) in sidebar
    refresh(true);
    
    // Invalidate documents cache so Knowledge Base table updates
    queryClient.invalidateQueries({ queryKey: ["documents"] });
    queryClient.invalidateQueries({ queryKey: ["documentCount"] });
  }, [refresh, queryClient]);

  /**
   * Handle URL input change with validation
   */
  const handleUrlChange = useCallback((e: React.ChangeEvent<HTMLInputElement>) => {
    const newUrl = e.target.value;
    setUrl(newUrl);
    
    // Clear validation error when user is typing
    if (validationError) {
      setValidationError(null);
    }
  }, [validationError]);

  /**
   * Handle form submission
   */
  const handleIngest = useCallback(async () => {
    // Check if action is disabled
    if (disabled) {
      toast({
        title: "Action locked",
        description: disabledReason || "You need editor or admin access to ingest videos.",
        variant: "destructive",
      });
      return;
    }

    // Validate URL presence
    if (!url.trim()) {
      setValidationError("Please enter a YouTube video URL");
      return;
    }

    // Validate YouTube URL format
    if (!isValidYoutubeUrl(url)) {
      setValidationError("Please enter a valid YouTube video URL (e.g., youtube.com/watch?v=... or youtu.be/...)");
      toast({
        title: "Invalid YouTube URL",
        description: "The URL you entered is not a valid YouTube video link.",
        variant: "destructive",
      });
      return;
    }

    // Normalize the URL
    const normalizedUrl = normalizeYoutubeUrl(url);

    setIsLoading(true);
    setValidationError(null);

    try {
      // Send to Web backend endpoint
      // The backend's web connector detects YouTube URLs and handles transcript fetching
      // We send source_type as "web" (implicit via the endpoint)
      const response = await api.post("/integrations/web/crawl", {
        url: normalizedUrl,
        crawl_type: "single",  // Single page for individual videos
        max_depth: 1,
        respect_robots: true,
        allow_subdomains: false,
      });

      // Extract job ID from response
      const jobId = (response as { data?: { job_id?: string; crawl_id?: string } })?.data?.job_id
        || (response as { data?: { crawl_id?: string } })?.data?.crawl_id
        || null;
      
      if (jobId) {
        setCurrentJobId(jobId);
      }

      toast({
        title: "Video Queued",
        description: "Fetching transcript and processing video content...",
        className: "bg-green-50 border-green-200 text-green-900",
      });
      
      // Reset form
      setUrl("");
    } catch (error: unknown) {
      const apiError = error as ApiError;
      console.error("[YoutubeInput] Ingestion failed:", apiError);
      
      // Extract error message
      const errorMessage = apiError.response?.data?.detail 
        || apiError.message 
        || "Could not process the YouTube video. Please try again.";
      
      toast({
        title: "Ingestion Failed",
        description: errorMessage,
        variant: "destructive",
      });
    } finally {
      setIsLoading(false);
    }
  }, [url, disabled, disabledReason, toast]);

  /**
   * Handle Enter key press
   */
  const handleKeyDown = useCallback((e: React.KeyboardEvent<HTMLInputElement>) => {
    if (e.key === "Enter" && url.trim() && !isLoading && !disabled) {
      e.preventDefault();
      handleIngest();
    }
  }, [url, isLoading, disabled, handleIngest]);

  // Calculate overall progress for the progress modal
  const overallProgress = useMemo(() => {
    if (fileStatuses.length === 0) return 0;
    const completedCount = fileStatuses.filter(
      (f) => f.status === "completed" || f.status === "indexed"
    ).length;
    return (completedCount / fileStatuses.length) * 100;
  }, [fileStatuses]);

  return (
    <div className="rounded-xl border border-border bg-card p-5">
      <div className="space-y-4">
        {/* Header Section */}
        <div className="flex items-start gap-4">
          <div className="flex h-10 w-10 shrink-0 items-center justify-center rounded-lg bg-red-500/10">
            <Youtube className="h-5 w-5 text-red-500" />
          </div>
          <div className="flex-1">
            <h3 className="font-medium text-foreground">{source.name}</h3>
            <p className="mt-1 text-sm text-muted-foreground">{source.description}</p>
          </div>
        </div>

        {/* Input & Action */}
        <div className="space-y-2">
          <div className="flex gap-2">
            <div className="relative flex-1">
              <Input
                type="url"
                placeholder="https://youtube.com/watch?v=..."
                value={url}
                onChange={handleUrlChange}
                onKeyDown={handleKeyDown}
                disabled={isLoading || disabled}
                className={cn(
                  validationError && "border-destructive focus-visible:ring-destructive",
                  isValidUrl === true && url.trim() && "border-green-500 focus-visible:ring-green-500"
                )}
                aria-invalid={!!validationError}
                aria-describedby={validationError ? "youtube-error" : undefined}
              />
              {/* Validation indicator */}
              {url.trim() && isValidUrl === false && (
                <div className="absolute right-3 top-1/2 -translate-y-1/2">
                  <AlertCircle className="h-4 w-4 text-destructive" />
                </div>
              )}
            </div>
            <Button
              onClick={handleIngest}
              disabled={!url.trim() || isLoading || disabled || isValidUrl === false}
              variant="gradient"
              size="icon"
              aria-label="Ingest YouTube video"
            >
              {isLoading ? (
                <Loader2 className="h-4 w-4 animate-spin" />
              ) : (
                <ArrowRight className="h-4 w-4" />
              )}
            </Button>
          </div>

          {/* Validation Error */}
          {validationError && (
            <p id="youtube-error" className="text-xs text-destructive flex items-center gap-1">
              <AlertCircle className="h-3 w-3" />
              {validationError}
            </p>
          )}

          {/* Video ID Preview (when valid) */}
          {videoId && (
            <p className="text-xs text-muted-foreground">
              Video ID: <code className="bg-muted px-1 py-0.5 rounded text-foreground">{videoId}</code>
            </p>
          )}
        </div>

        {/* Help text */}
        <p className="text-xs text-muted-foreground">
          Paste a YouTube video URL to transcribe and chat with the video content.
          Supports standard, short, and embed URLs.
        </p>
      </div>

      {/* Disabled reason notice */}
      {disabledReason && (
        <p className="mt-3 text-xs text-amber-500">{disabledReason}</p>
      )}

      {/* Ingestion Progress Modal */}
      {currentJobId && (
        <IngestionProgressModal
          jobId={currentJobId}
          files={fileStatuses}
          totalFiles={fileStatuses.length}
          overallProgress={overallProgress}
          onClose={() => setCurrentJobId(null)}
          onComplete={handleIngestionComplete}
        />
      )}
    </div>
  );
}
