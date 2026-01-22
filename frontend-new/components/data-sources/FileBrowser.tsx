"use client";

import { useState, useEffect, useCallback } from "react";
import {
  ArrowLeft,
  Folder,
  FileText,
  ChevronRight,
  Loader2,
  Check,
  Search,
  CheckCircle2,
} from "lucide-react";
import { Button } from "@/components/ui/button";
import { Checkbox } from "@/components/ui/checkbox";
import { Input } from "@/components/ui/input";
import {
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from "@/components/ui/table";
import { Badge } from "@/components/ui/badge";
import { useDataSources } from "@/hooks/useDataSources";
import { useToast } from "@/hooks/use-toast";
import { DataSourceIcon } from "./DataSourceIcon";
import { DataSource } from "@/lib/mockData";
import { ROLE_TOAST_TITLES, ROLE_MESSAGES } from "@/lib/role-messages";

export interface FileItem {
  id: string;
  name: string;
  type: "file" | "folder";
  size?: number | string; // Adjust to match mockData return
  mimeType?: string;
}

interface FileBrowserProps {
  source: DataSource;
  onBack: () => void;
  isViewer?: boolean;
}

interface BreadcrumbItem {
  id: string;
  name: string;
}

const MIME_TYPE_LABELS: Record<string, string> = {
  "application/pdf": "PDF",
  "text/plain": "Text",
  "text/csv": "CSV",
  "application/zip": "ZIP",
  "application/x-7z-compressed": "7Z",
  "application/x-rar-compressed": "RAR",
  "application/vnd.ms-excel": "Excel",
  "application/vnd.ms-excel.sheet.macroenabled.12": "Excel",
  "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet": "Excel",
  "application/vnd.openxmlformats-officedocument.spreadsheetml.template": "Excel",
  "application/msword": "Word",
  "application/vnd.openxmlformats-officedocument.wordprocessingml.document": "Word",
  "application/vnd.openxmlformats-officedocument.wordprocessingml.template": "Word",
  "application/vnd.ms-powerpoint": "PowerPoint",
  "application/vnd.openxmlformats-officedocument.presentationml.presentation": "PowerPoint",
  "application/vnd.openxmlformats-officedocument.presentationml.slideshow": "PowerPoint",
  "application/vnd.openxmlformats-officedocument.presentationml.template": "PowerPoint",
};

const getFileTypeLabel = (file: FileItem): string => {
  if (file.type === "folder") return "Folder";
  const mimeType = (file.mimeType || "").toLowerCase();
  if (mimeType) {
    const directMatch = MIME_TYPE_LABELS[mimeType];
    if (directMatch) return directMatch;
    if (mimeType.includes("spreadsheetml") || mimeType.includes("ms-excel") || mimeType.includes("excel")) {
      return "Excel";
    }
    if (mimeType.includes("wordprocessingml") || mimeType.includes("msword") || mimeType.includes("word")) {
      return "Word";
    }
    if (mimeType.includes("presentationml") || mimeType.includes("powerpoint")) {
      return "PowerPoint";
    }
    if (mimeType.startsWith("image/")) {
      return mimeType.split("/")[1]?.toUpperCase() || "Image";
    }
    if (mimeType.startsWith("text/")) {
      return mimeType.split("/")[1]?.toUpperCase() || "Text";
    }
    if (mimeType.startsWith("audio/")) {
      return "Audio";
    }
    if (mimeType.startsWith("video/")) {
      return "Video";
    }
  }

  const extension = file.name.split(".").pop();
  if (extension && extension !== file.name) {
    return extension.toUpperCase();
  }

  return mimeType ? mimeType.split("/")[1]?.toUpperCase() || "File" : "File";
};

export function FileBrowser({ source, onBack, isViewer = false }: FileBrowserProps) {
  const { getFiles, ingestFiles, getIngestedFileIds } = useDataSources();
  const { toast } = useToast();
  // Use 'any' temporarily if FileItem isn't strictly defined in the mock hook result or define strict LocalFileItem
  const [files, setFiles] = useState<FileItem[]>([]);
  const [loading, setLoading] = useState(true);
  const [selectedIds, setSelectedIds] = useState<Set<string>>(new Set());
  const [ingesting, setIngesting] = useState(false);
  const [searchQuery, setSearchQuery] = useState("");
  const [breadcrumbs, setBreadcrumbs] = useState<BreadcrumbItem[]>([
    { id: "root", name: "Home" },
  ]);
  // Track which files have already been ingested (shown with "Added" badge)
  const [ingestedIds, setIngestedIds] = useState<Set<string>>(new Set());

  const currentFolderId = breadcrumbs[breadcrumbs.length - 1].id;

  const filteredFiles = files.filter((f: FileItem) =>
    f.name.toLowerCase().includes(searchQuery.toLowerCase())
  );

  // Fetch list of already-ingested file IDs on mount
  useEffect(() => {
    const fetchIngestedIds = async () => {
      try {
        const ids = await getIngestedFileIds(source.type);
        setIngestedIds(ids);
      } catch {
        // Non-critical - just don't show badges
        console.warn('Failed to fetch ingested file IDs');
      }
    };
    fetchIngestedIds();
  }, [source.type, getIngestedFileIds]);

  const loadFiles = useCallback(async () => {
    setLoading(true);
    try {
      const data = await getFiles(source.id, currentFolderId);
      setFiles(data);
    } catch {
      toast({
        title: "Failed to load files",
        description: "Please try again.",
        variant: "destructive",
      });
    } finally {
      setLoading(false);
    }
  }, [getFiles, source.id, currentFolderId, toast]);

  useEffect(() => {
    loadFiles();
  }, [loadFiles]);

  // Helper to check if a file is already ingested
  const isFileIngested = useCallback((fileId: string): boolean => {
    return ingestedIds.has(fileId);
  }, [ingestedIds]);

  const handleFolderClick = (folder: FileItem) => {
    setBreadcrumbs((prev) => [...prev, { id: folder.id, name: folder.name }]);
    setSelectedIds(new Set());
  };

  const handleBreadcrumbClick = (index: number) => {
    setBreadcrumbs((prev) => prev.slice(0, index + 1));
    setSelectedIds(new Set());
  };

  const toggleSelection = (id: string) => {
    if (isViewer) return;
    setSelectedIds((prev) => {
      const next = new Set(prev);
      if (next.has(id)) {
        next.delete(id);
      } else {
        next.add(id);
      }
      return next;
    });
  };

  const toggleAll = () => {
    if (isViewer) return;
    // Select all items (both files and folders)
    const allIds = files.map((f) => f.id);
    if (allIds.every((id) => selectedIds.has(id))) {
      setSelectedIds(new Set());
    } else {
      setSelectedIds(new Set(allIds));
    }
  };

  const handleIngest = async () => {
    if (isViewer) {
      toast({
        title: ROLE_TOAST_TITLES.VIEW_ONLY,
        description: ROLE_MESSAGES.NEED_EDITOR_INGEST,
        variant: "destructive",
      });
      return;
    }

    setIngesting(true);
    const ingestedFileIds = Array.from(selectedIds);
    try {
      await ingestFiles(source.id, ingestedFileIds);
      toast({
        title: "Files queued for ingestion",
        description: `${selectedIds.size} file(s) are being added to your knowledge base.`,
      });
      // Optimistically update ingested IDs to show "Added" badge immediately
      setIngestedIds(prev => {
        const updated = new Set(prev);
        ingestedFileIds.forEach(id => updated.add(id));
        return updated;
      });
      setSelectedIds(new Set());
    } catch (err: unknown) {
      const message = err instanceof Error ? err.message : "Please try again.";
      toast({
        title: "Ingestion failed",
        description: message,
        variant: "destructive",
      });
    } finally {
      setIngesting(false);
    }
  };

  const formatSize = (bytes?: number | string) => {
    if (!bytes) return "-";
    if (typeof bytes === 'string') return bytes;
    if (bytes < 1024) return `${bytes} B`;
    if (bytes < 1024 * 1024) return `${(bytes / 1024).toFixed(1)} KB`;
    return `${(bytes / (1024 * 1024)).toFixed(1)} MB`;
  };

  const itemCount = files.length;
  const allItemsSelected = itemCount > 0 && files.every((f) => selectedIds.has(f.id));

  return (
    <div className="space-y-4">
      {/* Header */}
      <div className="flex items-center justify-between gap-4">
        <div className="flex items-center gap-3">
          <Button variant="ghost" size="icon" onClick={onBack}>
            <ArrowLeft className="h-5 w-5" />
          </Button>
          <DataSourceIcon sourceId={source.id} className="h-10 w-10" />
          <div>
            <h2 className="font-display text-xl font-semibold text-foreground">
              {source.name}
            </h2>
          </div>
        </div>

        {/* Search */}
        <div className="relative w-64">
          <Search className="absolute left-2 top-2.5 h-4 w-4 text-muted-foreground" />
          <Input
            placeholder="Search files..."
            value={searchQuery}
            onChange={(e) => setSearchQuery(e.target.value)}
            className="pl-8"
          />
        </div>
      </div>

      {/* Breadcrumbs */}
      <div className="flex items-center gap-1 text-sm">
        {breadcrumbs.map((crumb, index) => (
          <div key={crumb.id} className="flex items-center gap-1">
            {index > 0 && <ChevronRight className="h-4 w-4 text-muted-foreground" />}
            <button
              onClick={() => handleBreadcrumbClick(index)}
              className={`px-2 py-1 rounded hover:bg-muted transition-colors ${index === breadcrumbs.length - 1
                ? "font-medium text-foreground"
                : "text-muted-foreground"
                }`}
            >
              {crumb.name}
            </button>
          </div>
        ))}
      </div>

      {/* File Table */}
      <div className="rounded-lg border border-border">
        <Table>
          <TableHeader>
            <TableRow>
              <TableHead className="w-12">
              <Checkbox
                  checked={allItemsSelected}
                  onCheckedChange={toggleAll}
                  disabled={itemCount === 0 || isViewer}
                />
              </TableHead>
              <TableHead>Name</TableHead>
              <TableHead className="w-24">Type</TableHead>
              <TableHead className="w-24 text-right">Size</TableHead>
            </TableRow>
          </TableHeader>
          <TableBody>
            {loading ? (
              <TableRow>
                <TableCell colSpan={4} className="h-32 text-center">
                  <Loader2 className="mx-auto h-6 w-6 animate-spin text-muted-foreground" />
                </TableCell>
              </TableRow>
            ) : filteredFiles.length === 0 ? (
              <TableRow>
                <TableCell colSpan={4} className="h-32 text-center text-muted-foreground">
                  {searchQuery ? "No matching files found" : "This folder is empty"}
                </TableCell>
              </TableRow>
            ) : (
              filteredFiles.map((file) => {
                const alreadyIngested = file.type !== "folder" && isFileIngested(file.id);
                return (
                  <TableRow
                    key={file.id}
                    className={`cursor-pointer transition-colors ${
                      selectedIds.has(file.id) 
                        ? "bg-muted/50" 
                        : alreadyIngested 
                          ? "bg-green-500/5" 
                          : ""
                    }`}
                    onClick={() => {
                      if (file.type === "folder") {
                        handleFolderClick(file);
                      } else if (!isViewer) {
                        toggleSelection(file.id);
                      }
                    }}
                  >
                    <TableCell onClick={(e) => e.stopPropagation()}>
                      <Checkbox
                        checked={selectedIds.has(file.id)}
                        onCheckedChange={() => toggleSelection(file.id)}
                        disabled={isViewer}
                      />
                    </TableCell>
                    <TableCell>
                      <div className="flex items-center gap-2">
                        {file.type === "folder" ? (
                          <Folder className="h-4 w-4 text-primary" />
                        ) : alreadyIngested ? (
                          <CheckCircle2 className="h-4 w-4 text-green-500" />
                        ) : (
                          <FileText className="h-4 w-4 text-muted-foreground" />
                        )}
                        <span className="font-medium">{file.name}</span>
                        {alreadyIngested && (
                          <Badge 
                            variant="outline" 
                            className="ml-2 text-xs bg-green-500/10 text-green-600 border-green-500/30"
                          >
                            Added
                          </Badge>
                        )}
                      </div>
                    </TableCell>
                    <TableCell className="text-muted-foreground">
                      {getFileTypeLabel(file)}
                    </TableCell>
                    <TableCell className="text-right text-muted-foreground">
                      {formatSize(file.size)}
                    </TableCell>
                  </TableRow>
                );
              })
            )}
          </TableBody>
        </Table>
      </div>

      {/* Floating Action Bar */}
      {selectedIds.size > 0 && (
        <div className="fixed bottom-6 left-1/2 -translate-x-1/2 z-50 animate-slide-up">
          <div className="flex items-center gap-4 rounded-full border border-border bg-card px-6 py-3 shadow-lg">
            <span className="text-sm font-medium">
              {selectedIds.size} item{selectedIds.size > 1 ? "s" : ""} selected
            </span>
            <Button onClick={handleIngest} disabled={ingesting || isViewer} className="gap-2">
              {ingesting ? (
                <Loader2 className="h-4 w-4 animate-spin" />
              ) : (
                <Check className="h-4 w-4" />
              )}
              Ingest Selected
            </Button>
          </div>
        </div>
      )}
    </div>
  );
}
