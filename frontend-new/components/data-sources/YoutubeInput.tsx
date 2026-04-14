
"use client";

import { useState, useCallback, useMemo } from "react";
import { Youtube, ArrowRight, AlertCircle, FileText } from "lucide-react";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Textarea } from "@/components/ui/textarea";
import { DataSource } from "@/lib/mockData";
import { useToast } from "@/hooks/use-toast";
import { useIngestionProgress } from "@/hooks/useIngestionProgress";
import { api, ingestYoutubeManualTranscript } from "@/lib/api";
import { cn } from "@/lib/utils";
import { 

  isValidYoutubeUrl, 
  normalizeYoutubeUrl, 
  extractYoutubeVideoId,
  YOUTUBE_ERROR_MESSAGES 
} from "@/lib/youtube-utils";
import { ROLE_TOAST_TITLES, ROLE_MESSAGES } from "@/lib/role-messages";
import { Spinner } from "@/components/ui/spinner";
import { Alert, AlertDescription, AlertTitle } from "@/components/ui/alert";

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
// Component
// =============================================================================

export function YoutubeInput({ 
  source, 
  disabled = false, 
  disabledReason 
}: YoutubeInputProps) {
  const { toast } = useToast();
  
  // Form state
  const [url, setUrl] = useState("");
  const [isLoading, setIsLoading] = useState(false);
  const [isManualLoading, setIsManualLoading] = useState(false);
  const [validationError, setValidationError] = useState<string | null>(null);
  const [showManualFallback, setShowManualFallback] = useState(false);
  const [manualTitle, setManualTitle] = useState("");
  const [manualTranscript, setManualTranscript] = useState("");

  // Use centralized ingestion progress context - GlobalProgress renders the UI
  const { registerJob } = useIngestionProgress();

  // Computed validation state
  const isValidUrl = useMemo(() => {
    if (!url.trim()) return null; // Not yet entered
    return isValidYoutubeUrl(url);
  }, [url]);

  const videoId = useMemo(() => {
    if (!url.trim() || !isValidUrl) return null;
    return extractYoutubeVideoId(url);
  }, [url, isValidUrl]);

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
        title: ROLE_TOAST_TITLES.ACTION_LOCKED,
        description: disabledReason || ROLE_MESSAGES.NEED_EDITOR_INGEST_VIDEOS,
        variant: "destructive",
      });
      return;
    }

    // Validate URL presence
    if (!url.trim()) {
      setValidationError(YOUTUBE_ERROR_MESSAGES.EMPTY_URL);
      return;
    }

    // Validate YouTube URL format
    if (!isValidYoutubeUrl(url)) {
      setValidationError(YOUTUBE_ERROR_MESSAGES.INVALID_URL_DETAILED);
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

      // Extract job ID from response and register with centralized context
      const jobId = (response as { data?: { job_id?: string; crawl_id?: string } })?.data?.job_id
        || (response as { data?: { crawl_id?: string } })?.data?.crawl_id
        || null;
      
      if (jobId) {
        // Register job with centralized context - GlobalProgress will show UI
        registerJob(jobId);
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
      if (process.env.NODE_ENV !== 'production') {
        console.error("[YoutubeInput] Ingestion failed:", apiError);
      }
      
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
  }, [url, disabled, disabledReason, registerJob, toast]);

  const handleManualIngest = useCallback(async () => {
    if (disabled) {
      toast({
        title: ROLE_TOAST_TITLES.ACTION_LOCKED,
        description: disabledReason || ROLE_MESSAGES.NEED_EDITOR_INGEST_VIDEOS,
        variant: "destructive",
      });
      return;
    }

    if (!url.trim()) {
      setValidationError(YOUTUBE_ERROR_MESSAGES.EMPTY_URL);
      return;
    }

    if (!isValidYoutubeUrl(url)) {
      setValidationError(YOUTUBE_ERROR_MESSAGES.INVALID_URL_DETAILED);
      toast({
        title: "Invalid YouTube URL",
        description: "Add a valid YouTube video URL before pasting the transcript.",
        variant: "destructive",
      });
      return;
    }

    if (!manualTranscript.trim()) {
      toast({
        title: "Transcript Required",
        description: "Paste the transcript text to continue.",
        variant: "destructive",
      });
      return;
    }

    setIsManualLoading(true);
    setValidationError(null);

    try {
      const response = await ingestYoutubeManualTranscript(
        normalizeYoutubeUrl(url),
        manualTranscript.trim(),
        manualTitle.trim() || undefined,
      );

      if (response?.job_id) {
        registerJob(response.job_id);
      }

      toast({
        title: "Manual Transcript Queued",
        description: "Processing the transcript you provided.",
        className: "bg-green-50 border-green-200 text-green-900",
      });

      setManualTitle("");
      setManualTranscript("");
      setShowManualFallback(false);
      setUrl("");
    } catch (error: unknown) {
      const apiError = error as ApiError;
      const errorMessage = apiError.response?.data?.detail
        || apiError.message
        || "Could not process the transcript. Please try again.";

      toast({
        title: "Manual Transcript Failed",
        description: errorMessage,
        variant: "destructive",
      });
    } finally {
      setIsManualLoading(false);
    }
  }, [disabled, disabledReason, manualTitle, manualTranscript, registerJob, toast, url]);

  /**
   * Handle Enter key press
   */
  const handleKeyDown = useCallback((e: React.KeyboardEvent<HTMLInputElement>) => {
    if (e.key === "Enter" && url.trim() && !isLoading && !disabled) {
      e.preventDefault();
      handleIngest();
    }
  }, [url, isLoading, disabled, handleIngest]);

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

        <Alert className="border-amber-500/30 bg-amber-500/5">
          <AlertCircle className="h-4 w-4 text-amber-500" />
          <AlertTitle className="text-sm text-foreground">Best Effort</AlertTitle>
          <AlertDescription className="text-xs text-muted-foreground">
            Automatic transcript fetch runs from our servers and can fail on caption-less, private, or blocked YouTube videos.
            If that happens, paste the transcript below or upload `.srt` / `.vtt` from Local Files.
          </AlertDescription>
        </Alert>

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
              disabled={!url.trim() || isLoading || isManualLoading || disabled || isValidUrl === false}
              variant="gradient"
              size="icon"
              aria-label="Ingest YouTube video"
            >
              {isLoading ? (
                <Spinner className="h-4 w-4 animate-spin" />
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

        <div className="space-y-3 rounded-lg border border-border/60 bg-background/40 p-3">
          <div className="flex items-center justify-between gap-3">
            <div>
              <p className="text-sm font-medium text-foreground">Manual Transcript Fallback</p>
              <p className="text-xs text-muted-foreground">
                Use this when auto-fetch fails or you already have the transcript text.
              </p>
            </div>
            <Button
              type="button"
              variant="outline"
              size="sm"
              onClick={() => setShowManualFallback((value) => !value)}
            >
              {showManualFallback ? "Hide" : "Paste Transcript"}
            </Button>
          </div>

          {showManualFallback && (
            <div className="space-y-3">
              <Input
                placeholder="Optional title override"
                value={manualTitle}
                onChange={(e) => setManualTitle(e.target.value)}
                disabled={isManualLoading || disabled}
              />
              <Textarea
                placeholder="Paste the YouTube transcript here..."
                value={manualTranscript}
                onChange={(e) => setManualTranscript(e.target.value)}
                disabled={isManualLoading || disabled}
                rows={8}
              />
              <div className="flex items-center justify-between gap-3">
                <p className="text-xs text-muted-foreground">
                  Subtitle files also work through Local Files upload.
                </p>
                <Button
                  type="button"
                  variant="outline"
                  onClick={handleManualIngest}
                  disabled={!url.trim() || !manualTranscript.trim() || isManualLoading || isLoading || disabled || isValidUrl === false}
                >
                  {isManualLoading ? (
                    <Spinner className="mr-2 h-4 w-4 animate-spin" />
                  ) : (
                    <FileText className="mr-2 h-4 w-4" />
                  )}
                  Queue Transcript
                </Button>
              </div>
            </div>
          )}
        </div>

        {/* Help text */}
        <p className="text-xs text-muted-foreground">
          Paste a YouTube video URL to transcribe and chat with the video content.
          Supports standard, short, and embed URLs. Automatic fetching is best effort.
        </p>
      </div>

      {/* Disabled reason notice */}
      {disabledReason && (
        <p className="mt-3 text-xs text-amber-500">{disabledReason}</p>
      )}

      {/* Progress UI is now rendered by GlobalProgress - single source of truth */}
    </div>
  );
}
