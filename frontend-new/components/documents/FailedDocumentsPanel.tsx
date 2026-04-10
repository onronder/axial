"use client";

import { AlertTriangle, FileWarning } from "lucide-react";

import type { Document } from "@/types";
import { cn } from "@/lib/utils";

interface FailedDocumentsPanelProps {
  failedFiles: Document[];
  failedCount: number;
  title?: string;
  description?: string;
  className?: string;
}

export function FailedDocumentsPanel({
  failedFiles,
  failedCount,
  title = "Failed ingestions",
  description = "These files failed during ingestion and are listed separately from indexed documents.",
  className,
}: FailedDocumentsPanelProps) {
  if (failedCount <= 0) {
    return null;
  }

  const previewCount = failedFiles.length;

  return (
    <div className={cn("rounded-xl border border-red-500/20 bg-red-500/5 p-4", className)}>
      <div className="flex flex-col gap-3 sm:flex-row sm:items-start sm:justify-between">
        <div className="space-y-1">
          <div className="flex items-center gap-2 text-red-200">
            <AlertTriangle className="h-4 w-4" />
            <h3 className="text-sm font-semibold">{title}</h3>
          </div>
          <p className="text-sm text-muted-foreground">{description}</p>
        </div>
        <div className="rounded-full border border-red-500/20 bg-red-500/10 px-3 py-1 text-xs font-medium text-red-100">
          {failedCount} failed
        </div>
      </div>

      {previewCount > 0 && (
        <div className="mt-4 space-y-2">
          {failedFiles.map((file) => (
            <div
              key={file.id}
              className="flex flex-col gap-1 rounded-lg border border-white/10 bg-black/10 px-3 py-2 sm:flex-row sm:items-start sm:justify-between"
            >
              <div className="min-w-0 space-y-1">
                <div className="flex items-center gap-2 text-sm font-medium text-foreground">
                  <FileWarning className="h-4 w-4 text-red-300" />
                  <span className="truncate">{file.name}</span>
                </div>
                <p className="truncate text-xs text-muted-foreground">
                  {file.source}
                  {file.path ? ` • ${file.path}` : ""}
                </p>
              </div>
              <p
                className="max-w-xl text-xs text-red-100/90 sm:text-right"
                title={file.errorMessage}
              >
                {file.errorMessage || "Unknown ingestion failure"}
              </p>
            </div>
          ))}

          {failedCount > previewCount && (
            <p className="text-xs text-muted-foreground">
              Showing {previewCount} of {failedCount} failed files.
            </p>
          )}
        </div>
      )}
    </div>
  );
}
