"use client";

import { useState, useCallback, type KeyboardEvent } from "react";
import {
  UploadCloud,
  Globe,
  FileText,
  ArrowRight,
  AlertTriangle,
  GitCompare,
  BarChart3,
  Loader2,
} from "lucide-react";
import { useDropzone, type FileRejection } from "react-dropzone";
import { useRouter } from "next/navigation";
import { useIngestModal } from "@/hooks/useIngestModal";
import { useDocumentCount } from "@/hooks/useDocumentCount";
import { starterQueries } from "@/lib/mockData";
import { cn } from "@/lib/utils";
import { AxioLogo } from "@/components/branding/AxioLogo";
import { useToast } from "@/hooks/use-toast";
import {
  SIMPLE_ACCEPTED_FILE_TYPES,
  MAX_FILE_SIZE,
  MAX_FILE_SIZE_LABEL,
  MIN_FILE_SIZE,
  getDropRejectionMessage,
} from "@/lib/file-validation";

// =============================================================================
// TYPES
// =============================================================================

interface EmptyStateProps {
  /** Callback when user selects a starter query */
  onQuerySelect: (query: string) => void;
}

interface ActionCardProps {
  icon: React.ReactNode;
  title: string;
  description: string;
  onClick: () => void;
  ariaLabel: string;
}

interface QueryCardProps {
  icon: React.ReactNode;
  title: string;
  description: string;
  onClick: () => void;
}

// =============================================================================
// CONSTANTS
// =============================================================================

/** Map of query icon names to Lucide components */
const ICON_MAP: Record<string, React.ComponentType<{ className?: string }>> = {
  "file-text": FileText,
  "alert-triangle": AlertTriangle,
  "git-compare": GitCompare,
  "file-bar-chart": BarChart3,
};

/** 
 * Accepted file types use the simplified set from file-validation.ts
 * (PDF, DOCX, TXT, MD for quick chat uploads)
 */

// =============================================================================
// SUB-COMPONENTS
// =============================================================================

/** Primary action card (Upload Files / Add Website) */
function ActionCard({ icon, title, description, onClick, ariaLabel }: ActionCardProps) {
  const handleKeyDown = (e: KeyboardEvent<HTMLButtonElement>) => {
    if (e.key === "Enter" || e.key === " ") {
      e.preventDefault();
      onClick();
    }
  };

  return (
    <button
      type="button"
      onClick={onClick}
      onKeyDown={handleKeyDown}
      aria-label={ariaLabel}
      className={cn(
        "group flex flex-col items-center gap-4 p-6 rounded-xl",
        "border border-border bg-card text-center",
        "transition-all duration-200 ease-out",
        "hover:border-foreground/20 hover:bg-accent/50",
        "hover:scale-[1.02] active:scale-[0.98]",
        "focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring focus-visible:ring-offset-2",
        "cursor-pointer"
      )}
    >
      <div
        className={cn(
          "flex h-12 w-12 items-center justify-center rounded-xl",
          "bg-muted text-muted-foreground",
          "transition-colors duration-200",
          "group-hover:bg-primary/10 group-hover:text-primary"
        )}
      >
        {icon}
      </div>
      <div className="space-y-1">
        <h3 className="font-medium text-foreground">{title}</h3>
        <p className="text-sm text-muted-foreground">{description}</p>
      </div>
    </button>
  );
}

/** Starter query suggestion card */
function QueryCard({ icon, title, description, onClick }: QueryCardProps) {
  const handleKeyDown = (e: KeyboardEvent<HTMLButtonElement>) => {
    if (e.key === "Enter" || e.key === " ") {
      e.preventDefault();
      onClick();
    }
  };

  return (
    <button
      type="button"
      onClick={onClick}
      onKeyDown={handleKeyDown}
      aria-label={`Ask: ${title}`}
      className={cn(
        "group flex w-full items-center gap-3 p-4 rounded-xl",
        "border border-border bg-card text-left",
        "transition-all duration-200 ease-out",
        "hover:border-foreground/20 hover:bg-accent/50",
        "hover:scale-[1.01] active:scale-[0.98]",
        "focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring focus-visible:ring-offset-2",
        "cursor-pointer"
      )}
    >
      <div
        className={cn(
          "flex h-10 w-10 shrink-0 items-center justify-center rounded-lg",
          "bg-muted text-muted-foreground",
          "transition-colors duration-200",
          "group-hover:bg-primary/10 group-hover:text-primary"
        )}
      >
        {icon}
      </div>
      <div className="flex-1 min-w-0">
        <p className="font-medium text-foreground truncate">{title}</p>
        <p className="text-sm text-muted-foreground truncate">{description}</p>
      </div>
      <ArrowRight
        className="h-4 w-4 text-muted-foreground opacity-40 group-hover:opacity-100 transition-opacity"
        aria-hidden="true"
      />
    </button>
  );
}

/** Secondary link button */
function SecondaryAction({ onClick, children }: { onClick: () => void; children: React.ReactNode }) {
  const handleKeyDown = (e: KeyboardEvent<HTMLButtonElement>) => {
    if (e.key === "Enter" || e.key === " ") {
      e.preventDefault();
      onClick();
    }
  };

  return (
    <button
      type="button"
      onClick={onClick}
      onKeyDown={handleKeyDown}
      className={cn(
        "inline-flex items-center gap-1.5 text-sm",
        "text-muted-foreground hover:text-foreground",
        "transition-colors duration-200",
        "focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring focus-visible:ring-offset-2 rounded",
        "min-h-[44px] py-2 px-1 cursor-pointer"
      )}
    >
      <span>{children}</span>
      <ArrowRight className="h-3.5 w-3.5" aria-hidden="true" />
    </button>
  );
}

// =============================================================================
// MAIN COMPONENT
// =============================================================================

/**
 * Empty state component for the chat interface.
 * 
 * Shows different content based on whether the user has documents:
 * - No documents: Prompts to add data sources with upload/website cards
 * - Has documents: Shows starter query suggestions
 * 
 * Features:
 * - Drag & drop file upload zone
 * - Keyboard accessible
 * - Loading state handling
 */
export function EmptyState({ onQuerySelect }: EmptyStateProps) {
  const { openModal } = useIngestModal();
  const { isEmpty, isLoading } = useDocumentCount();
  const router = useRouter();
  const { toast } = useToast();
  const [isDragActive, setIsDragActive] = useState(false);

  // File drop handler - opens the upload modal
  const onDrop = useCallback(() => {
    openModal("file");
    setIsDragActive(false);
  }, [openModal]);

  // Handle rejected files (size/type validation failed)
  const onDropRejected = useCallback(
    (rejections: FileRejection[]) => {
      setIsDragActive(false);
      const message = getDropRejectionMessage(rejections);
      toast({
        title: "Files Rejected",
        description: message,
        variant: "destructive",
      });
    },
    [toast]
  );

  // Dropzone configuration with file size validation
  const { getRootProps, getInputProps, isDragActive: dropzoneActive } = useDropzone({
    onDrop,
    onDropRejected,
    onDragEnter: () => setIsDragActive(true),
    onDragLeave: () => setIsDragActive(false),
    noClick: true,
    accept: SIMPLE_ACCEPTED_FILE_TYPES,
    maxSize: MAX_FILE_SIZE,
    minSize: MIN_FILE_SIZE,
  });

  // Navigation handlers
  const handleOpenFileModal = useCallback(() => openModal("file"), [openModal]);
  const handleOpenUrlModal = useCallback(() => openModal("url"), [openModal]);
  const handleNavigateToDataSources = useCallback(
    () => router.push("/dashboard/settings/data-sources"),
    [router]
  );

  // Computed state
  const showDataSourcePrompt = isEmpty && !isLoading;
  const showDropOverlay = isDragActive || dropzoneActive;

  // Loading state
  if (isLoading) {
  return (
      <div
        className="flex min-h-full flex-col items-center justify-center px-4 py-16 md:py-24"
        role="status"
        aria-live="polite"
        aria-busy="true"
      >
        <div className="flex flex-col items-center gap-4">
          <Loader2
            className="h-8 w-8 text-muted-foreground animate-spin motion-reduce:animate-none"
            aria-hidden="true"
          />
          <p className="text-sm text-muted-foreground">Loading...</p>
          <span className="sr-only">Loading data sources, please wait</span>
        </div>
      </div>
    );
  }

  return (
    <div
      {...getRootProps()}
      className="relative flex min-h-full flex-col items-center justify-center px-4 py-16 md:py-24"
      role="region"
      aria-label={showDataSourcePrompt ? "Add your first data source" : "Start a conversation"}
    >
      {/* Hidden file input for dropzone */}
      <input {...getInputProps()} aria-hidden="true" />

      {/* Drop Overlay */}
      {showDropOverlay && (
        <div
          className="absolute inset-0 z-50 flex items-center justify-center bg-background/95 backdrop-blur-sm animate-in fade-in duration-200"
          role="status"
          aria-label="Drop files to upload"
        >
          <div className="flex flex-col items-center gap-4 p-8 rounded-2xl border-2 border-dashed border-primary bg-primary/5">
            <UploadCloud className="h-12 w-12 text-primary" aria-hidden="true" />
            <p className="text-lg font-medium text-foreground">Drop to analyze</p>
            <p className="text-sm text-muted-foreground">
              PDF, DOCX, TXT, MD (max {MAX_FILE_SIZE_LABEL})
            </p>
          </div>
        </div>
      )}

      <div className="max-w-xl w-full space-y-10 text-center">
        {/* Empty State - No documents */}
        {showDataSourcePrompt && (
          <div className="space-y-10 animate-in fade-in slide-in-from-bottom-4 duration-500">
            {/* Hero Section */}
            <header className="space-y-4">
              <div
                className="mx-auto flex h-16 w-16 items-center justify-center rounded-2xl bg-muted"
                aria-hidden="true"
              >
                <AxioLogo variant="icon" size="lg" />
            </div>
              <h1 className="text-2xl font-semibold text-foreground tracking-tight">
                I&apos;m ready to learn.
              </h1>
              <p className="text-muted-foreground">
                Connect a data source to start chatting with your knowledge base.
              </p>
            </header>

            {/* Primary Action Cards */}
            <div className="grid gap-4 sm:grid-cols-2" role="group" aria-label="Quick actions">
              <ActionCard
                icon={<UploadCloud className="h-6 w-6" />}
                title="Upload Files"
                description="Drag & drop PDF, DOCX, TXT"
                onClick={handleOpenFileModal}
                ariaLabel="Upload files - supports PDF, DOCX, and TXT"
              />
              <ActionCard
                icon={<Globe className="h-6 w-6" />}
                title="Add Website"
                description="Crawl a URL or YouTube video"
                onClick={handleOpenUrlModal}
                ariaLabel="Add website - crawl a URL or YouTube video"
              />
            </div>

            {/* Secondary Action */}
            <SecondaryAction onClick={handleNavigateToDataSources}>
              or connect apps like Google Drive, Notion & GitHub
            </SecondaryAction>
          </div>
        )}

        {/* Has Documents - Show starter queries */}
        {!showDataSourcePrompt && !isLoading && (
          <div className="space-y-10 animate-in fade-in slide-in-from-bottom-4 duration-500">
            {/* Hero Section */}
            <header className="space-y-4">
              <div
                className="mx-auto flex h-16 w-16 items-center justify-center rounded-2xl bg-muted"
                aria-hidden="true"
              >
                <AxioLogo variant="icon" size="lg" />
              </div>
              <h1 className="text-2xl font-semibold text-foreground tracking-tight">
                What can I help you with?
              </h1>
              <p className="text-muted-foreground">
                Ask questions about your knowledge base or try a suggestion below.
              </p>
            </header>

            {/* Starter Queries */}
            <nav className="space-y-3" aria-label="Suggested questions">
              {starterQueries.slice(0, 4).map((query) => {
                const Icon = ICON_MAP[query.icon] || FileText;
              return (
                  <QueryCard
                  key={query.title}
                    icon={<Icon className="h-5 w-5" />}
                    title={query.title}
                    description={query.description}
                  onClick={() => onQuerySelect(query.title)}
                  />
              );
            })}
            </nav>

            {/* Secondary Action */}
            <SecondaryAction onClick={handleNavigateToDataSources}>
              Add more data sources
            </SecondaryAction>
          </div>
        )}

        {/* Subtle hint */}
        <p className="text-xs text-muted-foreground/50" aria-live="polite">
          {showDataSourcePrompt
            ? "Drag files anywhere to upload"
            : "Type a message below to start"}
        </p>
      </div>
    </div>
  );
}
