"use client";

import { useState, useEffect } from "react";
import {
  ArrowLeft,
  Folder,
  FileText,
  ChevronRight,
  Loader2,
  Check,
  Search,
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
import { useDataSources } from "@/hooks/useDataSources";
import { useToast } from "@/hooks/use-toast";
import { DataSourceIcon } from "./DataSourceIcon";
import { DataSource } from "@/lib/mockData";

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
}

interface BreadcrumbItem {
  id: string;
  name: string;
}

export function FileBrowser({ source, onBack }: FileBrowserProps) {
  const { getFiles, ingestFiles } = useDataSources();
  const { toast } = useToast();
  // Use 'any' temporarily if FileItem isn't strictly defined in the mock hook result or define strict LocalFileItem
  const [files, setFiles] = useState<any[]>([]);
  const [loading, setLoading] = useState(true);
  const [selectedIds, setSelectedIds] = useState<Set<string>>(new Set());
  const [ingesting, setIngesting] = useState(false);
  const [searchQuery, setSearchQuery] = useState("");
  const [breadcrumbs, setBreadcrumbs] = useState<BreadcrumbItem[]>([
    { id: "root", name: "Home" },
  ]);

  const currentFolderId = breadcrumbs[breadcrumbs.length - 1].id;

  const filteredFiles = files.filter((f: any) =>
    f.name.toLowerCase().includes(searchQuery.toLowerCase())
  );

  useEffect(() => {
    loadFiles();
  }, [currentFolderId]);

  const loadFiles = async () => {
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
  };

  const handleFolderClick = (folder: FileItem) => {
    setBreadcrumbs((prev) => [...prev, { id: folder.id, name: folder.name }]);
    setSelectedIds(new Set());
  };

  const handleBreadcrumbClick = (index: number) => {
    setBreadcrumbs((prev) => prev.slice(0, index + 1));
    setSelectedIds(new Set());
  };

  const toggleSelection = (id: string) => {
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
    // Select all items (both files and folders)
    const allIds = files.map((f) => f.id);
    if (allIds.every((id) => selectedIds.has(id))) {
      setSelectedIds(new Set());
    } else {
      setSelectedIds(new Set(allIds));
    }
  };

  const handleIngest = async () => {
    setIngesting(true);
    try {
      await ingestFiles(source.id, Array.from(selectedIds));
      toast({
        title: "Files ingested successfully",
        description: `${selectedIds.size} file(s) added to your knowledge base.`,
      });
      setSelectedIds(new Set());
    } catch {
      toast({
        title: "Ingestion failed",
        description: "Please try again.",
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
                  disabled={itemCount === 0}
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
              filteredFiles.map((file) => (
                <TableRow
                  key={file.id}
                  className={`cursor-pointer transition-colors ${selectedIds.has(file.id) ? "bg-muted/50" : ""
                    }`}
                  onClick={() => {
                    if (file.type === "folder") {
                      handleFolderClick(file);
                    } else {
                      toggleSelection(file.id);
                    }
                  }}
                >
                  <TableCell onClick={(e) => e.stopPropagation()}>
                    <Checkbox
                      checked={selectedIds.has(file.id)}
                      onCheckedChange={() => toggleSelection(file.id)}
                    />
                  </TableCell>
                  <TableCell>
                    <div className="flex items-center gap-2">
                      {file.type === "folder" ? (
                        <Folder className="h-4 w-4 text-primary" />
                      ) : (
                        <FileText className="h-4 w-4 text-muted-foreground" />
                      )}
                      <span className="font-medium">{file.name}</span>
                    </div>
                  </TableCell>
                  <TableCell className="text-muted-foreground">
                    {file.type === "folder" ? "Folder" : file.mimeType?.split("/")[1]?.toUpperCase() || "File"}
                  </TableCell>
                  <TableCell className="text-right text-muted-foreground">
                    {formatSize(file.size)}
                  </TableCell>
                </TableRow>
              ))
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
            <Button onClick={handleIngest} disabled={ingesting} className="gap-2">
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
