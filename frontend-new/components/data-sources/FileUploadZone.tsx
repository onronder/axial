
"use client";

import { useCallback, useState, useRef } from "react";
import { useDropzone, type FileRejection } from "react-dropzone";
import { Upload, FileText, AlertCircle } from "lucide-react";
import { DataSource } from "@/lib/mockData";
import { useToast } from "@/hooks/use-toast";
import { cn } from "@/lib/utils";
import { useUsage } from "@/hooks/useUsage";
import { useIngestionProgress } from "@/hooks/useIngestionProgress";
import { useQuotaStatus } from "@/hooks/useQuotaStatus";
import { Alert, AlertDescription, AlertTitle } from "@/components/ui/alert";
import { getUploadUrl, uploadToStorage, ingestFileReference, checkDuplicates } from "@/lib/api";
import type { ExistingDocument } from "@/lib/api";
import { DuplicateFileModal, type DuplicateAction } from "./DuplicateFileModal";
import { calculateSHA256 } from "@/lib/hash";
import {
  ACCEPTED_FILE_TYPES,
  MAX_FILE_SIZE,
  MAX_FILE_SIZE_LABEL,
  MIN_FILE_SIZE,
  getDropRejectionMessage,
} from "@/lib/file-validation";
import { ROLE_TOAST_TITLES, ROLE_MESSAGES } from "@/lib/role-messages";
import { Spinner } from "@/components/ui/spinner";

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
  const { filesUsed, filesLimit, refresh } = useUsage();
  const { hasQuotaIssue, quotaExceededProviders } = useQuotaStatus();
  const [isUploading, setIsUploading] = useState(false);
  const [uploadedCount, setUploadedCount] = useState(0);
  const [uploadStage, setUploadStage] = useState<string>("");

  // Use centralized ingestion progress context - GlobalProgress renders the UI
  const { registerJob } = useIngestionProgress();

  // Duplicate detection state
  const [pendingDuplicate, setPendingDuplicate] = useState<PendingDuplicate | null>(null);
  const [hashProgress, setHashProgress] = useState<number>(0);
  const pendingFilesRef = useRef<File[]>([]);
  const uploadResultsRef = useRef<{ success: number; fail: number }>({ success: 0, fail: 0 });

  const isOverLimit = filesUsed >= filesLimit;

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
        title: ROLE_TOAST_TITLES.VIEW_ONLY,
        description: ROLE_MESSAGES.NEED_EDITOR_UPLOAD,
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

      // Register job with centralized context - GlobalProgress will show UI
      if (ingestionResponse?.job_id) {
        registerJob(ingestionResponse.job_id);
      }

      return true;
    } catch (error: unknown) {
      const message = error instanceof Error ? error.message : "Upload failed";
      console.error(`Failed to upload ${file.name}:`, message);
      return false;
    }
  }, [disabled, registerJob, toast]);

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
  }, [pendingDuplicate, processNextFile, toast, uploadFile]);

  const onDrop = useCallback(
    async (acceptedFiles: File[]) => {
      if (disabled) {
        toast({
          title: ROLE_TOAST_TITLES.VIEW_ONLY,
          description: ROLE_MESSAGES.NEED_EDITOR_UPLOAD,
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

  /**
   * Handle rejected files (size/type validation failed)
   */
  const onDropRejected = useCallback(
    (rejections: FileRejection[]) => {
      const message = getDropRejectionMessage(rejections);
      toast({
        title: "Files Rejected",
        description: message,
        variant: "destructive",
      });
    },
    [toast]
  );

  const { getRootProps, getInputProps, isDragActive } = useDropzone({
    onDrop,
    onDropRejected,
    accept: ACCEPTED_FILE_TYPES,
    maxSize: MAX_FILE_SIZE,
    minSize: MIN_FILE_SIZE,
    disabled: isUploading || isOverLimit || disabled,
  });

  return (
    <div className="space-y-4">
      {disabled && (
        <Alert variant="destructive">
          <AlertCircle className="h-4 w-4" />
          <AlertTitle>{ROLE_TOAST_TITLES.VIEW_ONLY}</AlertTitle>
          <AlertDescription>
            {ROLE_MESSAGES.NEED_EDITOR_UPLOAD}
          </AlertDescription>
        </Alert>
      )}

      {/* Only show limit warning here if no external source exceeded quota 
          (external sources show warning on their own cards) */}
      {isOverLimit && !hasQuotaIssue && (
        <Alert variant="destructive">
          <AlertCircle className="h-4 w-4" />
          <AlertTitle>File Limit Reached</AlertTitle>
          <AlertDescription>
            You have reached your limit of {filesLimit} files. Please upgrade your plan to upload more.
          </AlertDescription>
        </Alert>
      )}
      
      {/* Show a softer warning if limit reached but caused by external source */}
      {isOverLimit && hasQuotaIssue && (
        <Alert variant="default" className="border-amber-500/50 bg-amber-500/10">
          <AlertCircle className="h-4 w-4 text-amber-500" />
          <AlertTitle className="text-amber-600 dark:text-amber-400">File Limit Reached</AlertTitle>
          <AlertDescription className="text-amber-600/80 dark:text-amber-400/80">
            Your file limit was reached during sync from {Array.from(quotaExceededProviders).join(", ")}. 
            Upgrade your plan to continue uploading.
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
              <Spinner className="h-5 w-5 animate-spin text-primary" />
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
            PDF, Office, CSV, Code, Images & more (max {MAX_FILE_SIZE_LABEL})
          </div>
        </div>
      </div>

      {/* Progress UI is now rendered by GlobalProgress - single source of truth */}

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
