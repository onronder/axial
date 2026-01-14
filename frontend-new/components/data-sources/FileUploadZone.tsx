"use client";

import { useCallback, useState } from "react";
import { useDropzone } from "react-dropzone";
import { Upload, FileText, Loader2 } from "lucide-react";
import { DataSource } from "@/lib/mockData";
import { useToast } from "@/hooks/use-toast";
import { cn } from "@/lib/utils";
import { useUsage } from "@/hooks/useUsage";
import { useFileStatus } from "@/hooks/useFileStatus";
import { Alert, AlertDescription, AlertTitle } from "@/components/ui/alert";
import { AlertCircle } from "lucide-react";
import { getUploadUrl, uploadToStorage, ingestFileReference } from "@/lib/api";
import { IngestionProgressModal } from "@/components/ingestion/IngestionProgressModal";

interface FileUploadZoneProps {
  source: DataSource;
  disabled?: boolean;
}

export function FileUploadZone({ source, disabled = false }: FileUploadZoneProps) {
  const { toast } = useToast();
  const { filesUsed, filesLimit, refresh } = useUsage();
  const [isUploading, setIsUploading] = useState(false);
  const [uploadedCount, setUploadedCount] = useState(0);
  const [uploadStage, setUploadStage] = useState<string>("");
  const [currentJobId, setCurrentJobId] = useState<string | null>(null);

  // Track file-level progress
  const { files: fileStatuses } = useFileStatus(currentJobId);

  const isOverLimit = filesUsed >= filesLimit;
  const totalStatusCount = fileStatuses.length;
  const completedStatusCount = fileStatuses.filter((file) => {
    if (
      file.status === "completed" ||
      file.status === "indexed" ||
      file.status === "failed" ||
      file.status === "cancelled"
    ) {
      return true;
    }
    return file.status.startsWith("skipped");
  }).length;
  const overallProgress = totalStatusCount > 0 ? (completedStatusCount / totalStatusCount) * 100 : 0;

  /**
   * Direct-to-Storage Upload Flow:
   * 1. Get presigned URL from our backend
   * 2. Upload file directly to Supabase Storage
   * 3. Trigger ingestion via our backend
   */
  const uploadFile = useCallback(async (file: File): Promise<boolean> => {
    if (disabled) {
      toast({
        title: "View only",
        description: "You need editor or admin access to upload files.",
        variant: "destructive",
      });
      return false;
    }

    try {
      // Step 1: Get presigned upload URL
      setUploadStage("Getting upload URL...");
      const urlResponse = await getUploadUrl(
        file.name,
        file.type || "application/octet-stream",
        file.size
      );

      // Step 2: Upload directly to storage (bypasses our API server)
      setUploadStage("Uploading to storage...");
      const uploadSuccess = await uploadToStorage(urlResponse.upload_url, file);

      if (!uploadSuccess) {
        throw new Error("Failed to upload file to storage");
      }

      // Step 3: Trigger ingestion and capture job ID
      setUploadStage("Processing file...");
      const ingestionResponse = await ingestFileReference(
        urlResponse.storage_path,
        file.name,
        file.size,
        {
          filename: file.name,
          size: file.size,
          type: file.type,
        }
      );

      // Capture job ID for progress tracking
      if (ingestionResponse?.job_id) {
        setCurrentJobId(ingestionResponse.job_id ?? null);
      }

      return true;
    } catch (error: unknown) {
      const message = error instanceof Error ? error.message : "Upload failed";
      console.error(`Failed to upload ${file.name}:`, message);
      return false;
    }
  }, [disabled, toast]);

  const onDrop = useCallback(
    async (acceptedFiles: File[]) => {
      if (disabled) {
        toast({
          title: "View only",
          description: "You need editor or admin access to upload files.",
          variant: "destructive",
        });
        return;
      }

      if (acceptedFiles.length === 0) return;

      setIsUploading(true);
      setUploadedCount(0);

      let successCount = 0;
      let failCount = 0;

      // Upload files sequentially to avoid overwhelming the server
      for (const file of acceptedFiles) {
        const success = await uploadFile(file);
        if (success) {
          successCount++;
          setUploadedCount(successCount);
        } else {
          failCount++;
        }
      }

      setIsUploading(false);

      if (successCount > 0 && failCount === 0) {
        refresh(); // Update usage stats
        toast({
          title: "Files Uploaded",
          description: `${successCount} file(s) added to your knowledge base.`,
        });
      } else if (successCount > 0 && failCount > 0) {
        toast({
          title: "Partial Upload",
          description: `${successCount} succeeded, ${failCount} failed.`,
          variant: "destructive",
        });
      } else {
        toast({
          title: "Upload Failed",
          description: "Could not upload files. Please try again.",
          variant: "destructive",
        });
      }
    },
    [toast, refresh, uploadFile, disabled]
  );

  const { getRootProps, getInputProps, isDragActive } = useDropzone({
    onDrop,
    accept: {
      // Documents
      "application/pdf": [".pdf"],
      "application/vnd.openxmlformats-officedocument.wordprocessingml.document": [".docx"],
      "application/msword": [".doc"],
      "application/rtf": [".rtf"],

      // Spreadsheets
      "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet": [".xlsx"],
      "application/vnd.ms-excel": [".xls"],
      "text/csv": [".csv"],
      "text/tab-separated-values": [".tsv"],

      // Presentations
      "application/vnd.openxmlformats-officedocument.presentationml.presentation": [".pptx"],
      "application/vnd.ms-powerpoint": [".ppt"],

      // Email
      "message/rfc822": [".eml"],
      "application/vnd.ms-outlook": [".msg"],

      // Text & Code
      "text/plain": [
        ".txt",
        ".py",
        ".js",
        ".jsx",
        ".ts",
        ".tsx",
        ".java",
        ".go",
        ".cpp",
        ".c",
        ".cs",
        ".rb",
        ".php",
        ".rs",
        ".scala",
        ".swift",
        ".kt",
        ".json",
        ".yaml",
        ".yml",
        ".toml",
        ".ini",
        ".conf",
        ".config",
        ".xml",
        ".css",
        ".sql",
        ".env",
        ".sh",
        ".dockerfile",
        ".log",
      ],
      "text/markdown": [".md", ".markdown"],
      "text/html": [".html", ".htm"],
      "application/json": [".json"],
      "application/xml": [".xml"],
      "text/xml": [".xml"],

      // Images (OCR via LlamaParse)
      "image/jpeg": [".jpg", ".jpeg"],
      "image/png": [".png"],
      "image/tiff": [".tiff", ".tif"],
      "image/bmp": [".bmp"],
    },
    disabled: isUploading || isOverLimit || disabled,
  });

  return (
    <div className="space-y-4">
      {disabled && (
        <Alert variant="destructive">
          <AlertCircle className="h-4 w-4" />
          <AlertTitle>View only</AlertTitle>
          <AlertDescription>
            You need editor or admin access to upload files.
          </AlertDescription>
        </Alert>
      )}

      {isOverLimit && (
        <Alert variant="destructive">
          <AlertCircle className="h-4 w-4" />
          <AlertTitle>File Limit Reached</AlertTitle>
          <AlertDescription>
            You have reached your limit of {filesLimit} files. Please upgrade your plan to upload more.
          </AlertDescription>
        </Alert>
      )}

      <div
        {...getRootProps()}
        className={cn(
          "rounded-xl border-2 border-dashed bg-card p-5 transition-all",
          isUploading
            ? "cursor-wait opacity-75"
            : disabled || isOverLimit
              ? "cursor-not-allowed opacity-60 bg-muted/50"
              : "cursor-pointer",
          isDragActive && !isOverLimit
            ? "border-primary bg-primary/5 shadow-brand"
            : "border-border hover:border-primary/50"
        )}
      >
        <input {...getInputProps()} />
        <div className="space-y-3 text-center">
          <div className={cn(
            "mx-auto flex h-10 w-10 items-center justify-center rounded-lg transition-all",
            isUploading ? "bg-primary/10" : isDragActive ? "bg-axio-gradient shadow-brand" : "bg-muted"
          )}>
            {isUploading ? (
              <Loader2 className="h-5 w-5 animate-spin text-primary" />
            ) : (
              <Upload className={cn("h-5 w-5", isDragActive ? "text-white" : "text-primary")} />
            )}
          </div>
          <div>
            <h3 className="font-medium text-foreground">{source.name}</h3>
            <p className="mt-1 text-sm text-muted-foreground">
              {isUploading
                ? uploadStage || `Uploading... (${uploadedCount} uploaded)`
                : isDragActive
                  ? "Drop files here..."
                  : source.description}
            </p>
          </div>
          <div className="flex items-center justify-center gap-2 text-xs text-muted-foreground">
            <FileText className="h-3 w-3" />
            PDF, Office, CSV, Code, Images & more
          </div>
        </div>
      </div>

      {/* Progress Modal */}
      {currentJobId && (
        <IngestionProgressModal
          jobId={currentJobId}
          files={fileStatuses}
          totalFiles={totalStatusCount}
          overallProgress={overallProgress}
          onClose={() => setCurrentJobId(null)}
        />
      )}
    </div>
  );
}
