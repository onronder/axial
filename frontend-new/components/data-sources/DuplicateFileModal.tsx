"use client";

import { FileWarning, RefreshCw, XCircle, Calendar, HardDrive } from "lucide-react";
import {
  AlertDialog,
  AlertDialogContent,
  AlertDialogHeader,
  AlertDialogFooter,
  AlertDialogTitle,
  AlertDialogDescription,
  AlertDialogAction,
  AlertDialogCancel,
} from "@/components/ui/alert-dialog";
import { formatFileSize, formatDate } from "@/lib/hash";
import type { ExistingDocument } from "@/lib/api";

export type DuplicateAction = "overwrite" | "cancel";

interface DuplicateFileModalProps {
  /**
   * Whether the modal is open
   */
  open: boolean;
  
  /**
   * The name of the file being uploaded
   */
  filename: string;
  
  /**
   * Information about the existing duplicate document
   */
  existingDocument?: ExistingDocument;
  
  /**
   * Callback when user makes a choice
   */
  onAction: (action: DuplicateAction) => void;
}

/**
 * Modal shown when a duplicate file is detected during upload.
 * Allows user to choose between overwriting the existing file or canceling.
 * 
 * Design: Production-grade with clear visual hierarchy and destructive action warning.
 */
export function DuplicateFileModal({
  open,
  filename,
  existingDocument,
  onAction,
}: DuplicateFileModalProps) {
  return (
    <AlertDialog open={open}>
      <AlertDialogContent className="max-w-md">
        <AlertDialogHeader>
          {/* Warning Icon */}
          <div className="mx-auto mb-4 flex h-14 w-14 items-center justify-center rounded-full bg-amber-500/10 ring-1 ring-amber-500/20">
            <FileWarning className="h-7 w-7 text-amber-500" />
          </div>
          
          <AlertDialogTitle className="text-center text-xl">
            File Already Exists
          </AlertDialogTitle>
          
          <AlertDialogDescription className="text-center">
            A file with identical content already exists in your knowledge base.
          </AlertDialogDescription>
        </AlertDialogHeader>

        {/* File Comparison Card */}
        <div className="mt-2 rounded-lg border border-border bg-muted/30 p-4">
          <div className="space-y-3">
            {/* New File */}
            <div className="flex items-start gap-3">
              <div className="flex h-8 w-8 shrink-0 items-center justify-center rounded-md bg-primary/10">
                <RefreshCw className="h-4 w-4 text-primary" />
              </div>
              <div className="min-w-0 flex-1">
                <p className="text-xs font-medium uppercase tracking-wide text-muted-foreground">
                  Uploading
                </p>
                <p className="truncate font-medium text-foreground" title={filename}>
                  {filename}
                </p>
              </div>
            </div>

            {/* Divider with "same as" text */}
            <div className="flex items-center gap-2 py-1">
              <div className="h-px flex-1 bg-border" />
              <span className="text-xs text-muted-foreground">same content as</span>
              <div className="h-px flex-1 bg-border" />
            </div>

            {/* Existing File */}
            <div className="flex items-start gap-3">
              <div className="flex h-8 w-8 shrink-0 items-center justify-center rounded-md bg-amber-500/10">
                <FileWarning className="h-4 w-4 text-amber-500" />
              </div>
              <div className="min-w-0 flex-1">
                <p className="text-xs font-medium uppercase tracking-wide text-muted-foreground">
                  Existing
                </p>
                <p className="truncate font-medium text-foreground" title={existingDocument?.title}>
                  {existingDocument?.title || filename}
                </p>
                
                {/* Metadata */}
                <div className="mt-1.5 flex flex-wrap items-center gap-x-3 gap-y-1 text-xs text-muted-foreground">
                  {existingDocument?.created_at && (
                    <span className="flex items-center gap-1">
                      <Calendar className="h-3 w-3" />
                      {formatDate(existingDocument.created_at)}
                    </span>
                  )}
                  {existingDocument?.file_size_bytes && (
                    <span className="flex items-center gap-1">
                      <HardDrive className="h-3 w-3" />
                      {formatFileSize(existingDocument.file_size_bytes)}
                    </span>
                  )}
                </div>
              </div>
            </div>
          </div>
        </div>

        {/* Info text */}
        <p className="mt-3 text-center text-xs text-muted-foreground">
          Overwriting will replace the existing file and its indexed content.
        </p>

        <AlertDialogFooter className="mt-4 gap-2 sm:gap-2">
          <AlertDialogCancel 
            onClick={() => onAction("cancel")}
            className="flex-1 gap-2"
          >
            <XCircle className="h-4 w-4" />
            Cancel
          </AlertDialogCancel>
          <AlertDialogAction
            onClick={() => onAction("overwrite")}
            className="flex-1 gap-2 bg-amber-600 text-white hover:bg-amber-700 focus:ring-amber-500"
          >
            <RefreshCw className="h-4 w-4" />
            Overwrite
          </AlertDialogAction>
        </AlertDialogFooter>
      </AlertDialogContent>
    </AlertDialog>
  );
}

export default DuplicateFileModal;

