"use client";

import { useCallback } from "react";
import { useDropzone } from "react-dropzone";
import { Upload, FileText } from "lucide-react";
import { DataSource } from "@/lib/mockData";
import { useToast } from "@/hooks/use-toast";
import { cn } from "@/lib/utils";

interface FileUploadZoneProps {
  source: DataSource;
}

export function FileUploadZone({ source }: FileUploadZoneProps) {
  const { toast } = useToast();

  const onDrop = useCallback(
    (acceptedFiles: File[]) => {
      if (acceptedFiles.length > 0) {
        toast({
          title: "Files uploaded",
          description: `${acceptedFiles.length} file(s) added to your knowledge base.`,
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
  });

  return (
    <div
      {...getRootProps()}
      className={cn(
        "rounded-xl border-2 border-dashed bg-card p-5 transition-all cursor-pointer",
        isDragActive
          ? "border-primary bg-primary/5 shadow-brand"
          : "border-border hover:border-primary/50"
      )}
    >
      <input {...getInputProps()} />
      <div className="space-y-3 text-center">
        <div className={cn(
          "mx-auto flex h-10 w-10 items-center justify-center rounded-lg transition-all",
          isDragActive ? "bg-axio-gradient shadow-brand" : "bg-muted"
        )}>
          <Upload className={cn("h-5 w-5", isDragActive ? "text-white" : "text-primary")} />
        </div>
        <div>
          <h3 className="font-medium text-foreground">{source.name}</h3>
          <p className="mt-1 text-sm text-muted-foreground">
            {isDragActive ? "Drop files here..." : source.description}
          </p>
        </div>
        <div className="flex items-center justify-center gap-2 text-xs text-muted-foreground">
          <FileText className="h-3 w-3" />
          PDF, TXT, DOCX
        </div>
      </div>
    </div>
  );
}