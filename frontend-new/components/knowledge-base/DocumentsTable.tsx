"use client";

import { useState, useMemo } from "react";
import {
  Search,
  RefreshCw,
  Trash2,
  FileText,
  Globe,
  Upload,
  Database,
  MessageSquare,
  ChevronUp,
  ChevronDown,
  ChevronLeft,
  ChevronRight,
  PlayCircle,
  MoreVertical,
  Download,
  ExternalLink,
  Filter
} from "lucide-react";
import { Input } from "@/components/ui/input";
import { Button } from "@/components/ui/button";
import { Badge } from "@/components/ui/badge";
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
  DropdownMenu,
  DropdownMenuContent,
  DropdownMenuItem,
  DropdownMenuLabel,
  DropdownMenuSeparator,
  DropdownMenuTrigger,
} from "@/components/ui/dropdown-menu";
import {
  AlertDialog,
  AlertDialogAction,
  AlertDialogCancel,
  AlertDialogContent,
  AlertDialogDescription,
  AlertDialogFooter,
  AlertDialogHeader,
  AlertDialogTitle,
} from "@/components/ui/alert-dialog";
import { Document } from "@/types";
import { useDocuments } from "@/hooks/useDocuments";
import { StorageMeter } from "@/components/documents/StorageMeter";
import { cn } from "@/lib/utils";

const sourceIcons: Record<string, typeof FileText> = {
  drive: FileText,
  web: Globe,
  upload: Upload,
  notion: Database,
  slack: MessageSquare,
  youtube: PlayCircle,
  file: FileText,
};

const statusStyles: Record<string, { label: string; className: string; dotClass: string }> = {
  indexed: {
    label: "Indexed",
    className: "bg-emerald-50 text-emerald-700 border-emerald-200",
    dotClass: "bg-emerald-500"
  },
  processing: {
    label: "Processing",
    className: "bg-blue-50 text-blue-700 border-blue-200",
    dotClass: "bg-blue-500 animate-pulse"
  },
  error: {
    label: "Error",
    className: "bg-red-50 text-red-700 border-red-200",
    dotClass: "bg-red-500"
  },
};

type SortField = "name" | "source" | "status" | "addedAt" | "size";
type SortDirection = "asc" | "desc";

const PAGE_SIZE_OPTIONS = [5, 10, 25, 50];

export function DocumentsTable() {
  const { documents, isLoading: isRefreshing, refresh: handleRefresh, deleteDocument } = useDocuments();
  const [searchQuery, setSearchQuery] = useState("");
  const [sortField, setSortField] = useState<SortField>("addedAt");
  const [sortDirection, setSortDirection] = useState<SortDirection>("desc");
  const [currentPage, setCurrentPage] = useState(1);
  const [pageSize, setPageSize] = useState(10);
  const [deleteId, setDeleteId] = useState<string | null>(null);

  const filteredAndSortedDocuments = useMemo(() => {
    const result = documents.filter((doc) =>
      doc.name.toLowerCase().includes(searchQuery.toLowerCase())
    );

    result.sort((a, b) => {
      let comparison = 0;
      switch (sortField) {
        case "name":
          comparison = a.name.localeCompare(b.name);
          break;
        case "source":
          comparison = a.source.localeCompare(b.source);
          break;
        case "status":
          comparison = a.status.localeCompare(b.status);
          break;
        case "addedAt":
          comparison = new Date(a.addedAt).getTime() - new Date(b.addedAt).getTime();
          break;
        case "size":
          comparison = (a.size || 0) - (b.size || 0);
          break;
      }
      return sortDirection === "asc" ? comparison : -comparison;
    });

    return result;
  }, [documents, searchQuery, sortField, sortDirection]);

  const totalPages = Math.ceil(filteredAndSortedDocuments.length / pageSize);
  const paginatedDocuments = filteredAndSortedDocuments.slice(
    (currentPage - 1) * pageSize,
    currentPage * pageSize
  );

  const handleSort = (field: SortField) => {
    if (sortField === field) {
      setSortDirection(sortDirection === "asc" ? "desc" : "asc");
    } else {
      setSortField(field);
      setSortDirection("asc");
    }
    setCurrentPage(1);
  };

  const handleDelete = async () => {
    if (deleteId) {
      await deleteDocument(deleteId);
      setDeleteId(null);
    }
  };

  const formatDate = (dateString: string) => {
    return new Date(dateString).toLocaleDateString("en-US", {
      month: "short",
      day: "numeric",
      year: "numeric",
    });
  };

  const formatSize = (bytes?: number) => {
    if (bytes === undefined || bytes === null || bytes === 0) return "-";
    if (bytes < 1024) return `${bytes} B`;
    if (bytes < 1024 * 1024) return `${(bytes / 1024).toFixed(1)} KB`;
    return `${(bytes / (1024 * 1024)).toFixed(1)} MB`;
  };

  const SortIcon = ({ field }: { field: SortField }) => {
    if (sortField !== field) return null;
    return sortDirection === "asc" ? (
      <ChevronUp className="h-3 w-3 ml-1" />
    ) : (
      <ChevronDown className="h-3 w-3 ml-1" />
    );
  };

  const SortableHeader = ({
    field,
    children,
    className,
  }: {
    field: SortField;
    children: React.ReactNode;
    className?: string;
  }) => (
    <TableHead className={className}>
      <button
        onClick={() => handleSort(field)}
        className="flex items-center hover:text-foreground transition-colors font-medium text-xs uppercase tracking-wider"
      >
        {children}
        <SortIcon field={field} />
      </button>
    </TableHead>
  );

  return (
    <div className="space-y-8">
      {/* Header Area */}
      <div className="space-y-6">
        <div className="space-y-1">
          <h1 className="text-3xl font-bold tracking-tight text-foreground">Knowledge Base</h1>
          <p className="text-muted-foreground text-lg">
            Manage your ingested documents and connected data sources.
          </p>
        </div>

        {/* Storage Meter Banner */}
        <div className="w-full">
          <StorageMeter variant="horizontal" className="w-full" />
        </div>
      </div>

      <div className="bg-card rounded-xl border shadow-sm overflow-hidden">
        {/* Toolbar */}
        <div className="p-4 border-b flex flex-col sm:flex-row gap-4 justify-between items-center bg-muted/30">
          <div className="relative w-full sm:w-72">
            <Search className="absolute left-3 top-1/2 h-4 w-4 -translate-y-1/2 text-muted-foreground" />
            <Input
              placeholder="Search documents..."
              value={searchQuery}
              onChange={(e) => {
                setSearchQuery(e.target.value);
                setCurrentPage(1);
              }}
              className="pl-9 bg-background focus-visible:ring-offset-0"
            />
          </div>
          <div className="flex items-center gap-2 w-full sm:w-auto">
            <Button
              variant="outline"
              size="sm"
              onClick={() => handleRefresh()}
              disabled={isRefreshing}
              className="ml-auto sm:ml-0 gap-2 h-9"
            >
              <RefreshCw className={cn("h-3.5 w-3.5", isRefreshing && "animate-spin")} />
              Refresh
            </Button>
            <Button variant="outline" size="sm" className="h-9 gap-2">
              <Filter className="h-3.5 w-3.5" />
              Filter
            </Button>
          </div>
        </div>

        {/* Table Content */}
        <div className="relative">
          <Table>
            <TableHeader className="bg-muted/50">
              <TableRow className="hover:bg-transparent border-b border-border/60">
                <SortableHeader field="name" className="pl-6 w-[40%]">Name</SortableHeader>
                <SortableHeader field="source" className="w-[15%]">Source</SortableHeader>
                <SortableHeader field="status" className="w-[15%]">Status</SortableHeader>
                <SortableHeader field="size" className="w-[10%] text-right">Size</SortableHeader>
                <SortableHeader field="addedAt" className="w-[15%] text-right pr-6">Added</SortableHeader>
                <TableHead className="w-[5%]"></TableHead>
              </TableRow>
            </TableHeader>
            <TableBody>
              {paginatedDocuments.length === 0 ? (
                <TableRow>
                  <TableCell colSpan={6} className="h-64 text-center">
                    <div className="flex flex-col items-center justify-center space-y-3">
                      <div className="h-12 w-12 rounded-full bg-muted flex items-center justify-center">
                        <FileText className="h-6 w-6 text-muted-foreground" />
                      </div>
                      <div className="space-y-1">
                        <h3 className="font-medium text-foreground">No documents found</h3>
                        <p className="text-sm text-muted-foreground max-w-xs mx-auto">
                          {searchQuery
                            ? "Try adjusting your search query."
                            : "Upload files or connect a data source to get started."}
                        </p>
                      </div>
                    </div>
                  </TableCell>
                </TableRow>
              ) : (
                paginatedDocuments.map((doc) => {
                  const SourceIcon = sourceIcons[doc.sourceType] || FileText;
                  const status = statusStyles[doc.status] || statusStyles.indexed;

                  return (
                    <TableRow key={doc.id} className="group hover:bg-muted/30 transition-colors">
                      <TableCell className="pl-6 py-4">
                        <div className="flex items-center gap-3">
                          <div className="h-9 w-9 rounded-lg bg-primary/10 flex items-center justify-center shrink-0">
                            <FileText className="h-4 w-4 text-primary" />
                          </div>
                          <div className="flex flex-col min-w-0">
                            <span className="font-medium text-sm truncate max-w-[240px] lg:max-w-[400px] text-foreground">
                              {doc.name}
                            </span>
                            <span className="text-xs text-muted-foreground truncate">
                              ID: {doc.id.slice(0, 8)}
                            </span>
                          </div>
                        </div>
                      </TableCell>
                      <TableCell>
                        <div className="flex items-center gap-2">
                          <SourceIcon className="h-4 w-4 text-muted-foreground" />
                          <span className="text-sm text-muted-foreground capitalize font-medium">{doc.source}</span>
                        </div>
                      </TableCell>
                      <TableCell>
                        <div className={cn("inline-flex items-center gap-1.5 px-2.5 py-0.5 rounded-full text-xs font-medium border", status.className)}>
                          <span className={cn("w-1.5 h-1.5 rounded-full", status.dotClass)} />
                          {status.label}
                        </div>
                      </TableCell>
                      <TableCell className="text-right font-mono text-sm text-muted-foreground">
                        {formatSize(doc.size)}
                      </TableCell>
                      <TableCell className="text-right pr-6 text-sm text-muted-foreground">
                        {formatDate(doc.addedAt)}
                      </TableCell>
                      <TableCell>
                        <DropdownMenu>
                          <DropdownMenuTrigger asChild>
                            <Button variant="ghost" size="icon" className="h-8 w-8 opacity-0 group-hover:opacity-100 transition-opacity">
                              <MoreVertical className="h-4 w-4 text-muted-foreground" />
                            </Button>
                          </DropdownMenuTrigger>
                          <DropdownMenuContent align="end">
                            <DropdownMenuLabel>Actions</DropdownMenuLabel>
                            {doc.sourceType === 'upload' && (
                              <DropdownMenuItem>
                                <Download className="mr-2 h-4 w-4" /> Download
                              </DropdownMenuItem>
                            )}
                            <DropdownMenuItem>
                              <ExternalLink className="mr-2 h-4 w-4" /> View Source
                            </DropdownMenuItem>
                            <DropdownMenuSeparator />
                            <DropdownMenuItem
                              className="text-destructive focus:text-destructive"
                              onClick={() => setDeleteId(doc.id)}
                            >
                              <Trash2 className="mr-2 h-4 w-4" /> Delete
                            </DropdownMenuItem>
                          </DropdownMenuContent>
                        </DropdownMenu>
                      </TableCell>
                    </TableRow>
                  );
                })
              )}
            </TableBody>
          </Table>
        </div>

        {/* Footer / Pagination */}
        <div className="p-4 border-t bg-muted/30 flex items-center justify-between">
          <div className="flex items-center gap-2 text-sm text-muted-foreground">
            <span>Rows per page</span>
            <Select
              value={pageSize.toString()}
              onValueChange={(value) => {
                setPageSize(Number(value));
                setCurrentPage(1);
              }}
            >
              <SelectTrigger className="w-[70px] h-8 bg-background">
                <SelectValue />
              </SelectTrigger>
              <SelectContent>
                {PAGE_SIZE_OPTIONS.map((size) => (
                  <SelectItem key={size} value={size.toString()}>
                    {size}
                  </SelectItem>
                ))}
              </SelectContent>
            </Select>
          </div>

          <div className="flex items-center gap-4 text-sm text-muted-foreground">
            <span>
              {filteredAndSortedDocuments.length > 0
                ? `${(currentPage - 1) * pageSize + 1}-${Math.min(currentPage * pageSize, filteredAndSortedDocuments.length)} of ${filteredAndSortedDocuments.length}`
                : "0 documents"
              }
            </span>
            <div className="flex items-center gap-1">
              <Button
                variant="outline"
                size="icon"
                className="h-8 w-8 bg-background"
                onClick={() => setCurrentPage((p) => Math.max(1, p - 1))}
                disabled={currentPage === 1}
              >
                <ChevronLeft className="h-4 w-4" />
              </Button>
              <Button
                variant="outline"
                size="icon"
                className="h-8 w-8 bg-background"
                onClick={() => setCurrentPage((p) => Math.min(totalPages, p + 1))}
                disabled={currentPage === totalPages}
              >
                <ChevronRight className="h-4 w-4" />
              </Button>
            </div>
          </div>
        </div>
      </div>

      <AlertDialog open={!!deleteId} onOpenChange={(open) => !open && setDeleteId(null)}>
        <AlertDialogContent>
          <AlertDialogHeader>
            <AlertDialogTitle>Are you absolutely sure?</AlertDialogTitle>
            <AlertDialogDescription>
              This action cannot be undone. This will permanently delete the document
              and remove all associated data from the knowledge base.
            </AlertDialogDescription>
          </AlertDialogHeader>
          <AlertDialogFooter>
            <AlertDialogCancel>Cancel</AlertDialogCancel>
            <AlertDialogAction
              onClick={handleDelete}
              className="bg-destructive text-destructive-foreground hover:bg-destructive/90"
            >
              Delete
            </AlertDialogAction>
          </AlertDialogFooter>
        </AlertDialogContent>
      </AlertDialog>
    </div>
  );
}
