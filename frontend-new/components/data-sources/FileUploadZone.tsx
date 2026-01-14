"use client";

import { useCallback, useState, useRef } from "react";
import { useDropzone } from "react-dropzone";
import { useQueryClient } from "@tanstack/react-query";
import { Upload, FileText, Loader2, AlertCircle } from "lucide-react";
import { DataSource } from "@/lib/mockData";
import { useToast } from "@/hooks/use-toast";
import { cn } from "@/lib/utils";
import { useUsage } from "@/hooks/useUsage";
import { useFileStatus } from "@/hooks/useFileStatus";
import { Alert, AlertDescription, AlertTitle } from "@/components/ui/alert";
import { getUploadUrl, uploadToStorage, ingestFileReference, checkDuplicates } from "@/lib/api";
import type { ExistingDocument } from "@/lib/api";
import { IngestionProgressModal } from "@/components/ingestion/IngestionProgressModal";
import { DuplicateFileModal, type DuplicateAction } from "./DuplicateFileModal";
import { calculateSHA256 } from "@/lib/hash";

interface FileUploadZoneProps {
  source: DataSource;
  disabled?: boolean;
}

// Type for pending duplicate resolution
interface PendingDuplicate {
  file: File;
  contentHash: string;
  existingDocument?: ExistingDocument;
}

export function FileUploadZone({ source, disabled = false }: FileUploadZoneProps) {
  const { toast } = useToast();
  const queryClient = useQueryClient();
  const { filesUsed, filesLimit, refresh } = useUsage();
  const [isUploading, setIsUploading] = useState(false);
  const [uploadedCount, setUploadedCount] = useState(0);
  const [uploadStage, setUploadStage] = useState<string>("");
  const [currentJobId, setCurrentJobId] = useState<string | null>(null);

  // Track file-level progress
  const { files: fileStatuses } = useFileStatus(currentJobId);

  // Duplicate detection state
  const [pendingDuplicate, setPendingDuplicate] = useState<PendingDuplicate | null>(null);
  const [hashProgress, setHashProgress] = useState<number>(0);
  const pendingFilesRef = useRef<File[]>([]);
  const uploadResultsRef = useRef<{ success: number; fail: number }>({ success: 0, fail: 0 });

  /**
   * Called when all files in the ingestion job have finished processing.
   * Refreshes usage stats and invalidates document cache to update UI.
   */
  const handleIngestionComplete = useCallback(() => {
    console.log("📊 [FileUpload] Ingestion complete - refreshing data...");
    
    // Refresh usage stats (file count, storage) in sidebar
    refresh(true);
    
    // Invalidate documents cache so Knowledge Base table updates
    queryClient.invalidateQueries({ queryKey: ["documents"] });
    
    // Also invalidate document count for any dependent components
    queryClient.invalidateQueries({ queryKey: ["documentCount"] });
  }, [refresh, queryClient]);

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
   * Direct-to-Storage Upload Flow with Duplicate Detection:
   * 1. Calculate SHA-256 hash of file (shows progress for large files)
   * 2. Check for duplicate via API
   * 3. If duplicate, pause and ask user (modal)
   * 4. Get presigned URL from our backend
   * 5. Upload file directly to Supabase Storage
   * 6. Trigger ingestion via our backend
   */
  const uploadFile = useCallback(async (
    file: File,
    contentHash?: string,
    forceOverwrite: boolean = false
  ): Promise<boolean> => {
    if (disabled) {
      toast({
        title: "View only",
        description: "You need editor or admin access to upload files.",
        variant: "destructive",
      });
      return false;
    }

    try {
      // Step 1: Calculate content hash if not provided (for duplicate detection)
      let hash = contentHash;
      if (!hash) {
        setUploadStage("Calculating checksum...");
        hash = await calculateSHA256(file, (progress) => {
          setHashProgress(progress);
        });
        console.log(`📊 [Upload] Hash for ${file.name}: ${hash.slice(0, 12)}...`);
      }

      // Step 2: Check for duplicates (skip if forceOverwrite)
      if (!forceOverwrite) {
        setUploadStage("Checking for duplicates...");
        const dupCheck = await checkDuplicates(hash, file.name, file.size);
        
        if (dupCheck.is_duplicate && dupCheck.action_required === "confirm_overwrite") {
          console.log(`⚠️ [Upload] Duplicate detected for ${file.name}`);
          // Pause and show modal - user will decide
          setPendingDuplicate({
            file,
            contentHash: hash,
            existingDocument: dupCheck.existing_document,
          });
          return false; // Return false to indicate upload didn't complete yet
        }
      }

      // Step 3: Get presigned upload URL (with content hash for stable path)
      setUploadStage("Getting upload URL...");
      const urlResponse = await getUploadUrl(
        file.name,
        file.type || "application/octet-stream",
        file.size,
        hash,
        forceOverwrite
      );

      // Step 4: Upload directly to storage (bypasses our API server)
      setUploadStage("Uploading to storage...");
      const uploadSuccess = await uploadToStorage(urlResponse.upload_url, file);

      if (!uploadSuccess) {
        throw new Error("Failed to upload file to storage");
      }

      // Step 5: Trigger ingestion and capture job ID
      setUploadStage("Processing file...");
      const ingestionResponse = await ingestFileReference(
        urlResponse.storage_path,
        file.name,
        file.size,
        {
          filename: file.name,
          size: file.size,
          type: file.type,
          content_hash: hash,
          force_overwrite: forceOverwrite,
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

  /**
   * Handle user's decision on duplicate file modal
   */
  const handleDuplicateAction = useCallback(async (action: DuplicateAction) => {
    if (!pendingDuplicate) return;

    const { file, contentHash } = pendingDuplicate;
    setPendingDuplicate(null);

    if (action === "overwrite") {
      // User chose to overwrite - proceed with upload
      console.log(`✅ [Upload] User confirmed overwrite for ${file.name}`);
      const success = await uploadFile(file, contentHash, true);
      
      if (success) {
        uploadResultsRef.current.success++;
        setUploadedCount((c) => c + 1);
      } else {
        uploadResultsRef.current.fail++;
      }
    } else {
      // User cancelled - skip this file
      console.log(`❌ [Upload] User cancelled upload for ${file.name}`);
      toast({
        title: "Upload Cancelled",
        description: `Skipped ${file.name} (duplicate).`,
      });
    }

    // Continue with remaining files
    processNextFile();
  }, [pendingDuplicate, uploadFile, toast]);

  /**
   * Process the next file in the queue
   */
  const processNextFile = useCallback(async () => {
    const pendingFiles = pendingFilesRef.current;
    
    if (pendingFiles.length === 0) {
      // All files processed - show final toast
      setIsUploading(false);
      const { success, fail } = uploadResultsRef.current;
      
      if (success > 0 && fail === 0) {
        refresh();
        toast({
          title: "Files Uploaded",
          description: `${success} file(s) added to your knowledge base.`,
        });
      } else if (success > 0 && fail > 0) {
        toast({
          title: "Partial Upload",
          description: `${success} succeeded, ${fail} failed.`,
          variant: "destructive",
        });
      } else if (fail > 0) {
        toast({
          title: "Upload Failed",
          description: "Could not upload files. Please try again.",
          variant: "destructive",
        });
      }
      return;
    }

    const file = pendingFiles.shift()!;
    const success = await uploadFile(file);
    
    // If duplicate was detected, uploadFile returns false and shows modal
    // We'll continue after user responds to modal
    if (success) {
      uploadResultsRef.current.success++;
      setUploadedCount((c) => c + 1);
      // Continue with next file immediately
      processNextFile();
    } else if (!pendingDuplicate) {
      // Upload failed (not a duplicate pause)
      uploadResultsRef.current.fail++;
      processNextFile();
    }
    // If pendingDuplicate is set, wait for user action via handleDuplicateAction
  }, [uploadFile, refresh, toast, pendingDuplicate]);

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

      // Initialize upload state
      setIsUploading(true);
      setUploadedCount(0);
      setHashProgress(0);
      uploadResultsRef.current = { success: 0, fail: 0 };
      
      // Queue files for sequential processing (allows pausing for duplicate modal)
      pendingFilesRef.current = [...acceptedFiles];
      
      // Start processing the queue
      processNextFile();
    },
    [toast, disabled, processNextFile]
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
                ? uploadStage === "Calculating checksum..." 
                  ? `Calculating checksum... ${hashProgress}%`
                  : uploadStage || `Uploading... (${uploadedCount} uploaded)`
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
          onComplete={handleIngestionComplete}
        />
      )}

      {/* Duplicate File Confirmation Modal */}
      <DuplicateFileModal
        open={pendingDuplicate !== null}
        filename={pendingDuplicate?.file.name || ""}
        existingDocument={pendingDuplicate?.existingDocument}
        onAction={handleDuplicateAction}
      />
    </div>
  );
}
