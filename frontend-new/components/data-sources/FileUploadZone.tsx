"use client";

import { useCallback, useState } from "react";
import { useDropzone } from "react-dropzone";
import { Upload, FileText, Loader2, CheckCircle } from "lucide-react";
import { DataSource } from "@/lib/mockData";
import { useToast } from "@/hooks/use-toast";
import { cn } from "@/lib/utils";
import { supabase } from "@/lib/supabase";
import { useUsage } from "@/hooks/useUsage";
import { Alert, AlertDescription, AlertTitle } from "@/components/ui/alert";
import { AlertCircle } from "lucide-react";

interface FileUploadZoneProps {
  source: DataSource;
}

export function FileUploadZone({ source }: FileUploadZoneProps) {
  const { toast } = useToast();
  const { filesUsed, filesLimit, refresh } = useUsage();
  const [isUploading, setIsUploading] = useState(false);
  const [uploadedCount, setUploadedCount] = useState(0);

  const isOverLimit = filesUsed >= filesLimit;

  const uploadFile = async (file: File): Promise<boolean> => {
    try {
      // Get auth token
      const { data: { session } } = await supabase.auth.getSession();
      if (!session?.access_token) {
        throw new Error("Not authenticated");
      }

      // Create FormData
      const formData = new FormData();
      formData.append("file", file);
      formData.append("metadata", JSON.stringify({
        filename: file.name,
        size: file.size,
        type: file.type,
      }));

      // Upload to backend via Next.js proxy
      const response = await fetch("/api/py/api/v1/ingest", {
        method: "POST",
        headers: {
          "Authorization": `Bearer ${session.access_token}`,
        },
        body: formData,
      });

      if (!response.ok) {
        const error = await response.json();
        throw new Error(error.detail || "Upload failed");
      }

      return true;
    } catch (error) {
      console.error(`Failed to upload ${file.name}:`, error);
      return false;
    }
  };

  const onDrop = useCallback(
    async (acceptedFiles: File[]) => {
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
    [toast]
  );

  const { getRootProps, getInputProps, isDragActive } = useDropzone({
    onDrop,
    accept: {
      "application/pdf": [".pdf"],
      "text/plain": [".txt"],
      "application/vnd.openxmlformats-officedocument.wordprocessingml.document": [".docx"],
    },
    disabled: isUploading || isOverLimit,
  });

  return (
    <div className="space-y-4">
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
          isUploading ? "cursor-wait opacity-75" : isOverLimit ? "cursor-not-allowed opacity-60 bg-muted/50" : "cursor-pointer",
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
                ? `Uploading... (${uploadedCount} uploaded)`
                : isDragActive
                  ? "Drop files here..."
                  : source.description}
            </p>
          </div>
          <div className="flex items-center justify-center gap-2 text-xs text-muted-foreground">
            <FileText className="h-3 w-3" />
            PDF, TXT, DOCX
          </div>
        </div>
      </div>
    </div>
  );
}