"use client";

/**
 * Jobs Dashboard Component
 *
 * Displays and manages ingestion jobs with real-time updates.
 *
 * Features:
 * - Real-time job status updates via Supabase Realtime
 * - Cancel in-progress jobs
 * - Retry failed jobs
 * - View per-file status for each job
 * - Filter by status
 * - Pagination
 */

import { useState } from "react";
import { parseISO, formatDistanceToNow } from "date-fns";
import {
  Briefcase,
  RefreshCw,
  XCircle,
  RotateCcw,
  ChevronDown,
  ChevronUp,
  Clock,
  CheckCircle,
  AlertCircle,
  Loader2,
  Ban,
  FileText,
  Filter,
  Upload,
  Brain,
  Database,
  HelpCircle,
} from "lucide-react";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "@/components/ui/select";
import {
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from "@/components/ui/table";
import {
  Collapsible,
  CollapsibleContent,
  CollapsibleTrigger,
} from "@/components/ui/collapsible";
import { Badge } from "@/components/ui/badge";
import { Progress } from "@/components/ui/progress";
import { Spinner } from "@/components/ui/spinner";
import { useIngestionJobs, IngestionJob, JobFile } from "@/hooks/useIngestionJobs";
import { cn } from "@/lib/utils";

/**
 * Status configuration for visual display of job/file states.
 * 
 * File statuses can include intermediate processing stages:
 * - pending: Queued for processing
 * - uploading: File is being uploaded
 * - processing: Generic processing state
 * - embedding: Generating embeddings for the content
 * - indexing: Indexing into vector store
 * - completed: Successfully processed
 * - failed: Processing failed
 * - cancelled: Cancelled by user
 */
interface StatusConfig {
  icon: React.ElementType;
  color: string;
  bgColor: string;
  label: string;
  isAnimated?: boolean; // Whether icon should animate (spin)
}

const statusConfig: Record<string, StatusConfig> = {
  // Base statuses (shared between jobs and files)
  pending: {
    icon: Clock,
    color: "text-amber-600 dark:text-amber-400",
    bgColor: "bg-amber-500/10",
    label: "Pending",
  },
  processing: {
    icon: Loader2,
    color: "text-blue-600 dark:text-blue-400",
    bgColor: "bg-blue-500/10",
    label: "Processing",
    isAnimated: true,
  },
  completed: {
    icon: CheckCircle,
    color: "text-green-600 dark:text-green-400",
    bgColor: "bg-green-500/10",
    label: "Completed",
  },
  failed: {
    icon: AlertCircle,
    color: "text-red-600 dark:text-red-400",
    bgColor: "bg-red-500/10",
    label: "Failed",
  },
  cancelled: {
    icon: Ban,
    color: "text-gray-600 dark:text-gray-400",
    bgColor: "bg-gray-500/10",
    label: "Cancelled",
  },
  // File-specific intermediate statuses
  uploading: {
    icon: Upload,
    color: "text-cyan-600 dark:text-cyan-400",
    bgColor: "bg-cyan-500/10",
    label: "Uploading",
    isAnimated: true,
  },
  embedding: {
    icon: Brain,
    color: "text-purple-600 dark:text-purple-400",
    bgColor: "bg-purple-500/10",
    label: "Embedding",
    isAnimated: true,
  },
  indexing: {
    icon: Database,
    color: "text-indigo-600 dark:text-indigo-400",
    bgColor: "bg-indigo-500/10",
    label: "Indexing",
    isAnimated: true,
  },
};

/**
 * Default configuration for unknown statuses.
 * Ensures the UI never crashes on unexpected status values from the API.
 */
const defaultStatusConfig: StatusConfig = {
  icon: HelpCircle,
  color: "text-gray-500 dark:text-gray-400",
  bgColor: "bg-gray-500/10",
  label: "Unknown",
};

/**
 * Safely retrieves status configuration with fallback for unknown statuses.
 * This prevents runtime errors when the API returns unexpected status values.
 */
function getStatusConfig(status: string): StatusConfig {
  return statusConfig[status] ?? defaultStatusConfig;
}

const providerLabels: Record<string, string> = {
  google_drive: "Google Drive",
  onedrive: "OneDrive",
  sharepoint: "SharePoint",
  dropbox: "Dropbox",
  notion: "Notion",
  github: "GitHub",
  box: "Box",
  web: "Web Crawl",
  upload: "File Upload",
  youtube: "YouTube",
  s3: "Amazon S3",
};

interface JobRowProps {
  job: IngestionJob;
  onCancel: (jobId: string) => Promise<void>;
  onRetry: (jobId: string) => Promise<void>;
  getJobFiles: (jobId: string) => Promise<JobFile[]>;
}

function JobRow({ job, onCancel, onRetry, getJobFiles }: JobRowProps) {
  const [isExpanded, setIsExpanded] = useState(false);
  const [files, setFiles] = useState<JobFile[]>([]);
  const [isLoadingFiles, setIsLoadingFiles] = useState(false);
  const [isActing, setIsActing] = useState(false);

  const config = getStatusConfig(job.status);
  const StatusIcon = config.icon;
  const isActive = job.status === "pending" || job.status === "processing";
  const isFailed = job.status === "failed";
  const progress =
    job.total_files > 0
      ? Math.round((job.processed_files / job.total_files) * 100)
      : 0;

  const handleExpand = async () => {
    if (!isExpanded && files.length === 0) {
      setIsLoadingFiles(true);
      const jobFiles = await getJobFiles(job.id);
      setFiles(jobFiles);
      setIsLoadingFiles(false);
    }
    setIsExpanded(!isExpanded);
  };

  const handleCancel = async () => {
    setIsActing(true);
    try {
      await onCancel(job.id);
    } finally {
      setIsActing(false);
    }
  };

  const handleRetry = async () => {
    setIsActing(true);
    try {
      await onRetry(job.id);
    } finally {
      setIsActing(false);
    }
  };

  return (
    <Collapsible open={isExpanded} onOpenChange={handleExpand}>
      <TableRow className="hover:bg-muted/30">
        <TableCell>
          <CollapsibleTrigger asChild>
            <Button variant="ghost" size="sm" className="p-1 h-7 w-7">
              {isExpanded ? (
                <ChevronUp className="h-4 w-4" />
              ) : (
                <ChevronDown className="h-4 w-4" />
              )}
            </Button>
          </CollapsibleTrigger>
        </TableCell>
        <TableCell>
          <div className="flex flex-col gap-1">
            <span className="font-medium">
              {providerLabels[job.provider] || job.provider}
            </span>
            <span className="text-xs text-muted-foreground font-mono">
              {job.id.slice(0, 8)}...
            </span>
          </div>
        </TableCell>
        <TableCell>
          <Badge
            variant="secondary"
            className={cn("gap-1.5", config.bgColor, config.color)}
          >
            <StatusIcon
              className={cn(
                "h-3 w-3",
                config.isAnimated && "animate-spin"
              )}
            />
            {config.label}
          </Badge>
        </TableCell>
        <TableCell>
          <div className="flex flex-col gap-1">
            <div className="flex items-center gap-2">
              <Progress value={progress} className="h-2 w-24" />
              <span className="text-xs text-muted-foreground">{progress}%</span>
            </div>
            <span className="text-xs text-muted-foreground">
              {job.processed_files} / {job.total_files} files
            </span>
          </div>
        </TableCell>
        <TableCell className="text-sm text-muted-foreground">
          {formatDistanceToNow(parseISO(job.created_at), { addSuffix: true })}
        </TableCell>
        <TableCell>
          <div className="flex items-center gap-2">
            {isActive && (
              <Button
                variant="outline"
                size="sm"
                onClick={handleCancel}
                disabled={isActing}
                className="text-destructive hover:text-destructive hover:bg-destructive/10 border-destructive/30"
              >
                {isActing ? (
                  <Spinner className="h-4 w-4 animate-spin" />
                ) : (
                  <>
                    <XCircle className="h-4 w-4 mr-1" />
                    Cancel
                  </>
                )}
              </Button>
            )}
            {isFailed && (
              <Button
                variant="outline"
                size="sm"
                onClick={handleRetry}
                disabled={isActing}
                className="text-primary hover:text-primary"
              >
                {isActing ? (
                  <Spinner className="h-4 w-4 animate-spin" />
                ) : (
                  <>
                    <RotateCcw className="h-4 w-4 mr-1" />
                    Retry
                  </>
                )}
              </Button>
            )}
          </div>
        </TableCell>
      </TableRow>

      <CollapsibleContent asChild>
        <tr>
          <td colSpan={6} className="p-0">
            <div className="bg-muted/20 border-y border-border/50 p-4">
              {isLoadingFiles ? (
                <div className="flex items-center justify-center py-4">
                  <Spinner className="h-5 w-5 animate-spin text-primary" />
                  <span className="ml-2 text-sm text-muted-foreground">
                    Loading files...
                  </span>
                </div>
              ) : files.length === 0 ? (
                <div className="flex items-center justify-center py-4 text-sm text-muted-foreground">
                  <FileText className="h-4 w-4 mr-2" />
                  No file details available
                </div>
              ) : (
                <div className="space-y-2">
                  <h4 className="text-sm font-medium mb-3">
                    Files ({files.length})
                  </h4>
                  <div className="max-h-48 overflow-y-auto space-y-1.5">
                    {files.map((file) => {
                      const fileConfig = getStatusConfig(file.status);
                      const FileStatusIcon = fileConfig.icon;
                      const isInProgress = fileConfig.isAnimated;
                      return (
                        <div
                          key={file.id}
                          className="flex items-center justify-between gap-2 text-sm py-1.5 px-2 rounded-md bg-background/50"
                        >
                          <div className="flex items-center gap-2 min-w-0 flex-1">
                            <FileStatusIcon
                              className={cn(
                                "h-4 w-4 shrink-0",
                                fileConfig.color,
                                isInProgress && "animate-spin"
                              )}
                            />
                            <span className="truncate">{file.filename}</span>
                          </div>
                          <div className="flex items-center gap-2 shrink-0">
                            {isInProgress && (
                              <Progress
                                value={file.progress}
                                className="h-1.5 w-16"
                              />
                            )}
                            <Badge
                              variant="outline"
                              className={cn("text-xs", fileConfig.color)}
                            >
                              {fileConfig.label}
                            </Badge>
                            {file.retry_count > 0 && (
                              <span className="text-xs text-muted-foreground">
                                (retry {file.retry_count}/3)
                              </span>
                            )}
                          </div>
                        </div>
                      );
                    })}
                  </div>
                  {job.error_message && (
                    <div className="mt-3 p-2 rounded-md bg-destructive/10 border border-destructive/20">
                      <p className="text-xs text-destructive">
                        <strong>Error:</strong> {job.error_message}
                      </p>
                    </div>
                  )}
                </div>
              )}
            </div>
          </td>
        </tr>
      </CollapsibleContent>
    </Collapsible>
  );
}

export function JobsDashboard() {
  const { jobs, activeJobs, isLoading, refresh, retryJob, cancelJob, getJobFiles } =
    useIngestionJobs();
  const [isRefreshing, setIsRefreshing] = useState(false);
  const [statusFilter, setStatusFilter] = useState<string>("all");

  const handleRefresh = async () => {
    setIsRefreshing(true);
    await refresh();
    setIsRefreshing(false);
  };

  // Filter jobs by status
  const filteredJobs =
    statusFilter === "all"
      ? jobs
      : jobs.filter((job) => job.status === statusFilter);

  // Calculate stats
  const stats = {
    total: jobs.length,
    active: activeJobs.length,
    completed: jobs.filter((j) => j.status === "completed").length,
    failed: jobs.filter((j) => j.status === "failed").length,
    cancelled: jobs.filter((j) => j.status === "cancelled").length,
  };

  if (isLoading) {
    return (
      <div className="flex items-center justify-center py-12">
        <div className="flex flex-col items-center gap-3">
          <Spinner className="h-8 w-8 animate-spin text-primary" />
          <p className="text-sm text-muted-foreground">Loading jobs...</p>
        </div>
      </div>
    );
  }

  return (
    <div className="space-y-6 animate-fade-in">
      {/* Header Card */}
      <Card className="overflow-hidden transition-all duration-300 hover:shadow-lg hover:shadow-primary/5">
        <CardHeader className="border-b border-border/50 bg-muted/30">
          <div className="flex items-center justify-between">
            <div className="flex items-center gap-3">
              <div className="flex h-10 w-10 items-center justify-center rounded-xl bg-gradient-to-br from-primary to-accent text-white shadow-lg shadow-primary/20">
                <Briefcase className="h-5 w-5" />
              </div>
              <div>
                <CardTitle className="text-lg">Ingestion Jobs</CardTitle>
                <CardDescription>
                  Monitor and manage your data ingestion tasks
                </CardDescription>
              </div>
            </div>
            <Button
              variant="outline"
              size="sm"
              onClick={handleRefresh}
              disabled={isRefreshing}
            >
              <RefreshCw
                className={cn("h-4 w-4 mr-2", isRefreshing && "animate-spin")}
              />
              Refresh
            </Button>
          </div>
        </CardHeader>
        <CardContent className="p-6">
          {/* Stats */}
          <div className="grid grid-cols-2 md:grid-cols-5 gap-4 mb-6">
            <div className="p-3 rounded-lg bg-muted/30 border border-border/50">
              <p className="text-2xl font-bold">{stats.total}</p>
              <p className="text-xs text-muted-foreground">Total Jobs</p>
            </div>
            <div className="p-3 rounded-lg bg-blue-500/10 border border-blue-500/20">
              <p className="text-2xl font-bold text-blue-600 dark:text-blue-400">
                {stats.active}
              </p>
              <p className="text-xs text-muted-foreground">Active</p>
            </div>
            <div className="p-3 rounded-lg bg-green-500/10 border border-green-500/20">
              <p className="text-2xl font-bold text-green-600 dark:text-green-400">
                {stats.completed}
              </p>
              <p className="text-xs text-muted-foreground">Completed</p>
            </div>
            <div className="p-3 rounded-lg bg-red-500/10 border border-red-500/20">
              <p className="text-2xl font-bold text-red-600 dark:text-red-400">
                {stats.failed}
              </p>
              <p className="text-xs text-muted-foreground">Failed</p>
            </div>
            <div className="p-3 rounded-lg bg-gray-500/10 border border-gray-500/20">
              <p className="text-2xl font-bold text-gray-600 dark:text-gray-400">
                {stats.cancelled}
              </p>
              <p className="text-xs text-muted-foreground">Cancelled</p>
            </div>
          </div>

          {/* Filter */}
          <div className="flex items-center gap-2 mb-4">
            <Filter className="h-4 w-4 text-muted-foreground" />
            <Select value={statusFilter} onValueChange={setStatusFilter}>
              <SelectTrigger className="w-[160px]">
                <SelectValue placeholder="Filter by status" />
              </SelectTrigger>
              <SelectContent>
                <SelectItem value="all">All Status</SelectItem>
                <SelectItem value="pending">Pending</SelectItem>
                <SelectItem value="processing">Processing</SelectItem>
                <SelectItem value="completed">Completed</SelectItem>
                <SelectItem value="failed">Failed</SelectItem>
                <SelectItem value="cancelled">Cancelled</SelectItem>
              </SelectContent>
            </Select>
          </div>

          {/* Jobs Table */}
          {filteredJobs.length === 0 ? (
            <div className="flex flex-col items-center justify-center py-12 text-center">
              <Briefcase className="h-12 w-12 text-muted-foreground/50 mb-4" />
              <h3 className="text-lg font-semibold">No jobs found</h3>
              <p className="text-sm text-muted-foreground max-w-md mt-1">
                {statusFilter !== "all"
                  ? "Try changing the status filter to see more jobs."
                  : "Jobs will appear here when you start ingesting data."}
              </p>
            </div>
          ) : (
            <div className="rounded-lg border">
              <Table>
                <TableHeader>
                  <TableRow className="bg-muted/30">
                    <TableHead className="w-[50px]" />
                    <TableHead className="w-[180px]">Source</TableHead>
                    <TableHead className="w-[120px]">Status</TableHead>
                    <TableHead className="w-[200px]">Progress</TableHead>
                    <TableHead className="w-[150px]">Started</TableHead>
                    <TableHead className="w-[150px]">Actions</TableHead>
                  </TableRow>
                </TableHeader>
                <TableBody>
                  {filteredJobs.map((job) => (
                    <JobRow
                      key={job.id}
                      job={job}
                      onCancel={cancelJob}
                      onRetry={retryJob}
                      getJobFiles={getJobFiles}
                    />
                  ))}
                </TableBody>
              </Table>
            </div>
          )}
        </CardContent>
      </Card>
    </div>
  );
}
