"use client";

import { useState, useEffect, useMemo, useCallback, useRef, Fragment } from "react";
import {
  Search,
  RefreshCw,
  Trash2,
  FileText,
  Folder,
  FolderOpen,
  ChevronRight,
  ChevronLeft,
  MoreVertical,
  Download,
  ExternalLink,
  Filter,
  Home,
  ArrowLeft,
} from "lucide-react";
import { Input } from "@/components/ui/input";
import { Button } from "@/components/ui/button";
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
import { useDocuments } from "@/hooks/useDocuments";
import { useProfile } from "@/hooks/useProfile";
import { useUsage } from "@/hooks/useUsage";
import { StorageMeter } from "@/components/documents/StorageMeter";
import { cn } from "@/lib/utils";
import { Checkbox } from "@/components/ui/checkbox";
import {
  buildFolderTree,
  findFolderByPath,
  getBreadcrumbs,
  searchTree,
  getDocumentIdsInFolder,
  isFolderNode,
  isDocumentNode,
  type FolderNode,
  type TreeNode,
  type BreadcrumbItem,
} from "@/lib/folderTree";

// =============================================================================
// CONSTANTS
// =============================================================================

const statusStyles: Record<string, { label: string; className: string; dotClass: string }> = {
  completed: {
    label: "Indexed",
    className: "bg-emerald-500/10 text-emerald-200 border-emerald-500/20",
    dotClass: "bg-emerald-400"
  },
  indexed: {
    label: "Indexed",
    className: "bg-emerald-500/10 text-emerald-200 border-emerald-500/20",
    dotClass: "bg-emerald-400"
  },
  processing: {
    label: "Processing",
    className: "bg-blue-500/10 text-blue-200 border-blue-500/30",
    dotClass: "bg-blue-400 animate-pulse"
  },
  pending: {
    label: "Pending",
    className: "bg-yellow-500/10 text-yellow-200 border-yellow-500/30",
    dotClass: "bg-yellow-400"
  },
  failed: {
    label: "Failed",
    className: "bg-red-500/10 text-red-200 border-red-500/30",
    dotClass: "bg-red-400"
  },
  error: {
    label: "Error",
    className: "bg-red-500/10 text-red-200 border-red-500/30",
    dotClass: "bg-red-400"
  },
};

const PAGE_SIZE_OPTIONS = [10, 25, 50, 100];

// =============================================================================
// HELPER COMPONENTS
// =============================================================================

interface StatusBadgeProps {
  status: string | undefined;
  errorMessage?: string;
}

function StatusBadge({ status, errorMessage }: StatusBadgeProps) {
  const displayStatus = status || "completed";
  const styles = statusStyles[displayStatus] || statusStyles.completed;

  return (
    <div className="flex flex-col">
      <div className={cn("inline-flex items-center gap-1.5 px-2.5 py-0.5 rounded-full text-xs font-medium border", styles.className)}>
        <span className={cn("w-1.5 h-1.5 rounded-full", styles.dotClass)} />
        {styles.label}
      </div>
      {displayStatus === 'failed' && errorMessage && (
        <p className="text-xs text-destructive mt-1 truncate max-w-[120px]" title={errorMessage}>
          {errorMessage}
        </p>
      )}
    </div>
  );
}

// =============================================================================
// MAIN COMPONENT
// =============================================================================

export function KnowledgeBaseBrowser() {
  // State
  const [currentPath, setCurrentPath] = useState<string>("/");
  const [searchQuery, setSearchQuery] = useState("");
  const [debouncedSearch, setDebouncedSearch] = useState("");
  const [currentPage, setCurrentPage] = useState(1);
  const [pageSize, setPageSize] = useState(25);
  const [deleteId, setDeleteId] = useState<string | null>(null);
  const [deleteFolderId, setDeleteFolderId] = useState<string | null>(null);
  const [selectedIds, setSelectedIds] = useState<Set<string>>(new Set());
  const [focusedIndex, setFocusedIndex] = useState<number>(-1);
  
  // Refs for keyboard navigation
  const tableRef = useRef<HTMLDivElement>(null);

  // Debounce search query
  useEffect(() => {
    const timer = setTimeout(() => {
      setDebouncedSearch(searchQuery);
      setCurrentPage(1);
    }, 300);
    return () => clearTimeout(timer);
  }, [searchQuery]);

  // Hooks
  const {
    documents,
    totalCount,
    isLoading: isRefreshing,
    refresh: handleRefresh,
    deleteDocument,
    bulkDeleteDocuments,
    isBulkDeleting
  } = useDocuments(1, 10000, debouncedSearch); // Fetch all for tree building

  const { profile } = useProfile();
  const isViewer = profile?.role === 'viewer';
  const { refresh: refreshUsage } = useUsage();

  // Build folder tree from documents
  const folderTree = useMemo(() => buildFolderTree(documents), [documents]);

  // Get current folder and breadcrumbs
  const currentFolder = useMemo(
    () => findFolderByPath(folderTree, currentPath),
    [folderTree, currentPath]
  );

  const breadcrumbs = useMemo(
    () => getBreadcrumbs(folderTree, currentPath),
    [folderTree, currentPath]
  );

  // Get items to display (search or current folder contents)
  // Note: currentFolder is always valid since we start at root ("/") and
  // only navigate to valid folders via navigateToFolder. The non-null
  // assertion is safe because buildFolderTree always creates a root node.
  const displayItems = useMemo(() => {
    const folder = currentFolder!;
    if (debouncedSearch) {
      // Search within current folder's subtree
      return searchTree(folder, debouncedSearch);
    }
    return folder.children;
  }, [currentFolder, debouncedSearch]);

  // Pagination
  const totalItems = displayItems.length;
  const totalPages = useMemo(
    () => Math.max(1, Math.ceil(totalItems / pageSize)),
    [totalItems, pageSize]
  );

  // Clamp page when items change
  useEffect(() => {
    if (currentPage > totalPages) {
      setCurrentPage(totalPages);
    }
  }, [currentPage, totalPages]);

  // Paginated items
  const paginatedItems = useMemo(() => {
    const start = (currentPage - 1) * pageSize;
    return displayItems.slice(start, start + pageSize);
  }, [displayItems, currentPage, pageSize]);

  // Selection helpers
  const allVisibleSelected = paginatedItems.length > 0 && 
    paginatedItems.filter(isDocumentNode).every(item => selectedIds.has(item.id));

  const selectedDocumentCount = Array.from(selectedIds).filter(id => 
    paginatedItems.some(item => isDocumentNode(item) && item.id === id)
  ).length;

  // Reset selection when navigating
  useEffect(() => {
    setSelectedIds(new Set());
    setFocusedIndex(-1);
  }, [currentPath]);

  // =============================================================================
  // NAVIGATION HANDLERS
  // =============================================================================

  const navigateToFolder = useCallback((folder: FolderNode) => {
    setCurrentPath(folder.path);
    setSearchQuery("");
    setCurrentPage(1);
    setFocusedIndex(-1);
  }, []);

  const navigateUp = useCallback(() => {
    if (breadcrumbs.length > 1) {
      const parentCrumb = breadcrumbs[breadcrumbs.length - 2];
      setCurrentPath(parentCrumb.path);
      setSearchQuery("");
      setCurrentPage(1);
    }
  }, [breadcrumbs]);

  const navigateToRoot = useCallback(() => {
    setCurrentPath("/");
    setSearchQuery("");
    setCurrentPage(1);
  }, []);

  const navigateToBreadcrumb = useCallback((crumb: BreadcrumbItem) => {
    setCurrentPath(crumb.path);
    setSearchQuery("");
    setCurrentPage(1);
  }, []);

  // =============================================================================
  // ACTION HANDLERS
  // =============================================================================

  const handleDelete = async () => {
    if (deleteId) {
      await deleteDocument(deleteId);
      setDeleteId(null);
      setSelectedIds(prev => {
        const next = new Set(prev);
        next.delete(deleteId);
        return next;
      });
      refreshUsage(true);
    }
  };

  const handleDeleteFolder = async () => {
    if (deleteFolderId && currentFolder) {
      const folder = currentFolder.children.find(
        c => isFolderNode(c) && c.id === deleteFolderId
      ) as FolderNode | undefined;
      
      if (folder) {
        const docIds = getDocumentIdsInFolder(folder);
        if (docIds.length > 0) {
          await bulkDeleteDocuments({ documentIds: docIds });
          refreshUsage(true);
        }
      }
      setDeleteFolderId(null);
    }
  };

  const toggleSelectAll = (checked: boolean) => {
    if (checked) {
      const documentIds = paginatedItems
        .filter(isDocumentNode)
        .map(item => item.id);
      setSelectedIds(new Set(documentIds));
    } else {
      setSelectedIds(new Set());
    }
  };

  const toggleSelectOne = (id: string, checked: boolean) => {
    setSelectedIds(prev => {
      const next = new Set(prev);
      if (checked) {
        next.add(id);
      } else {
        next.delete(id);
      }
      return next;
    });
  };

  const handleBulkDeleteSelected = async () => {
    // Note: Button is already disabled when no selections, so selectedIds.size > 0 here
    const confirmed = confirm(`Delete ${selectedIds.size} selected item(s)? This cannot be undone.`);
    if (!confirmed) return;
    
    try {
      await bulkDeleteDocuments({ documentIds: Array.from(selectedIds) });
      setSelectedIds(new Set());
      refreshUsage(true);
    } catch {
      // Error handled by hook
    }
  };

  // =============================================================================
  // KEYBOARD NAVIGATION
  // =============================================================================

  const handleKeyDown = useCallback((e: React.KeyboardEvent) => {
    if (paginatedItems.length === 0) return;

    switch (e.key) {
      case "ArrowDown":
        e.preventDefault();
        setFocusedIndex(prev => Math.min(prev + 1, paginatedItems.length - 1));
        break;
      case "ArrowUp":
        e.preventDefault();
        setFocusedIndex(prev => Math.max(prev - 1, 0));
        break;
      case "Enter":
        e.preventDefault();
        if (focusedIndex >= 0 && focusedIndex < paginatedItems.length) {
          const item = paginatedItems[focusedIndex];
          if (isFolderNode(item)) {
            navigateToFolder(item);
          }
        }
        break;
      case "Backspace":
        if (!searchQuery && breadcrumbs.length > 1) {
          e.preventDefault();
          navigateUp();
        }
        break;
      case " ":
        e.preventDefault();
        if (focusedIndex >= 0 && focusedIndex < paginatedItems.length) {
          const item = paginatedItems[focusedIndex];
          if (isDocumentNode(item)) {
            toggleSelectOne(item.id, !selectedIds.has(item.id));
          }
        }
        break;
      case "Escape":
        setSelectedIds(new Set());
        setFocusedIndex(-1);
        break;
    }
  }, [paginatedItems, focusedIndex, searchQuery, breadcrumbs, selectedIds, navigateToFolder, navigateUp]);

  // =============================================================================
  // FORMATTERS
  // =============================================================================

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

  // =============================================================================
  // RENDER
  // =============================================================================

  return (
    <div className="space-y-8">
      {/* Header Area */}
      <div className="space-y-6">
        <div className="space-y-1">
          <h1 className="text-3xl font-bold tracking-tight text-gradient">Knowledge Base</h1>
          <p className="text-muted-foreground text-lg">
            Browse and manage your ingested documents by folder.
          </p>
        </div>

        {/* Storage Meter Banner */}
        <div className="w-full">
          <StorageMeter variant="horizontal" className="w-full" />
        </div>
      </div>

      <div className="glass-card rounded-xl border border-white/10 shadow-glow overflow-hidden">
        {/* Breadcrumb Navigation */}
        <div className="px-4 py-3 border-b border-white/10 bg-white/5 backdrop-blur-sm">
          <div className="flex items-center gap-2">
            {/* Back Button */}
            {breadcrumbs.length > 1 && (
              <Button
                variant="ghost"
                size="sm"
                onClick={navigateUp}
                className="h-8 px-2 gap-1 text-muted-foreground hover:text-foreground"
              >
                <ArrowLeft className="h-4 w-4" />
                Back
              </Button>
            )}

            {/* Home Button */}
            <Button
              variant="ghost"
              size="icon"
              onClick={navigateToRoot}
              className="h-8 w-8 text-muted-foreground hover:text-foreground"
              title="Go to root"
            >
              <Home className="h-4 w-4" />
            </Button>

            {/* Breadcrumb Trail */}
            <div className="flex items-center gap-1 overflow-x-auto">
              {breadcrumbs.map((crumb, index) => (
                <Fragment key={crumb.id}>
                  {index > 0 && (
                    <ChevronRight className="h-4 w-4 text-muted-foreground shrink-0" />
                  )}
                  <Button
                    variant="ghost"
                    size="sm"
                    onClick={() => navigateToBreadcrumb(crumb)}
                    className={cn(
                      "h-8 px-2 shrink-0",
                      index === breadcrumbs.length - 1
                        ? "font-medium text-foreground"
                        : "text-muted-foreground hover:text-foreground"
                    )}
                  >
                    {index === 0 ? (
                      <span className="flex items-center gap-1">
                        <Folder className="h-3.5 w-3.5" />
                        {crumb.name}
                      </span>
                    ) : (
                      crumb.name
                    )}
                  </Button>
                </Fragment>
              ))}
            </div>

            {/* Item Count */}
            <div className="ml-auto text-sm text-muted-foreground">
              {totalItems} {totalItems === 1 ? "item" : "items"}
            </div>
          </div>
        </div>

        {/* Toolbar */}
        <div className="p-4 border-b border-white/10 space-y-3 bg-white/5 backdrop-blur-sm">
          <div className="flex flex-col sm:flex-row gap-4 justify-between items-center">
            <div className="relative w-full sm:w-72">
              <Search className="absolute left-3 top-1/2 h-4 w-4 -translate-y-1/2 text-muted-foreground" />
              <Input
                placeholder="Search in current folder..."
                value={searchQuery}
                onChange={(e) => {
                  setSearchQuery(e.target.value);
                  setCurrentPage(1);
                }}
                className="pl-9 bg-background focus-visible:ring-offset-0"
                onKeyDown={handleKeyDown}
              />
            </div>
            <div className="flex items-center gap-2 w-full sm:w-auto">
              <Button
                variant="outline"
                size="sm"
                onClick={() => handleRefresh()}
                disabled={isRefreshing}
                className="ml-auto sm:ml-0 gap-2 h-9 border-white/20 bg-white/5 hover:bg-white/10"
              >
                <RefreshCw className={cn("h-3.5 w-3.5", isRefreshing && "animate-spin")} />
                Refresh
              </Button>
            </div>
          </div>

          {/* Bulk Actions */}
          <div className="flex flex-col sm:flex-row gap-3 items-start sm:items-center justify-between">
            <div className="text-sm text-muted-foreground">
              {selectedIds.size > 0 ? `${selectedIds.size} selected` : "Select items for bulk actions"}
            </div>
            <div className="flex flex-wrap gap-2 w-full sm:w-auto justify-end">
              <Button
                variant="destructive"
                size="sm"
                className="h-9"
                onClick={handleBulkDeleteSelected}
                disabled={selectedIds.size === 0 || isViewer || isRefreshing || isBulkDeleting}
              >
                <Trash2 className="h-3.5 w-3.5 mr-1" />
                Delete selected
              </Button>
            </div>
          </div>
        </div>

        {/* Table Content */}
        <div 
          ref={tableRef}
          className="relative focus:outline-none"
          tabIndex={0}
          onKeyDown={handleKeyDown}
          role="grid"
          aria-label="Knowledge base file browser"
          aria-describedby="kb-navigation-hint"
        >
          <span id="kb-navigation-hint" className="sr-only">
            Use arrow keys to navigate, Enter to open folders, Space to select files, Backspace to go back
          </span>
          <Table>
            <TableHeader className="bg-transparent">
              <TableRow className="hover:bg-transparent border-b border-white/10 uppercase tracking-[0.08em] text-xs text-muted-foreground">
                <TableHead className="w-[40px] pl-4">
                  <Checkbox
                    aria-label="Select all"
                    checked={allVisibleSelected}
                    onCheckedChange={(checked) => toggleSelectAll(!!checked)}
                    disabled={isViewer}
                  />
                </TableHead>
                <TableHead className="pl-2 w-[40%] font-medium text-xs">Name</TableHead>
                <TableHead className="w-[15%] font-medium text-xs">Type</TableHead>
                <TableHead className="w-[15%] font-medium text-xs">Size / Items</TableHead>
                <TableHead className="w-[12%] font-medium text-xs">Status</TableHead>
                <TableHead className="w-[12%] text-right pr-6 font-medium text-xs">Modified</TableHead>
                <TableHead className="w-[5%]"></TableHead>
              </TableRow>
            </TableHeader>
            <TableBody>
              {paginatedItems.length === 0 ? (
                <TableRow>
                  <TableCell colSpan={7} className="h-64 text-center">
                    <div className="flex flex-col items-center justify-center space-y-3">
                      <div className="h-12 w-12 rounded-full bg-white/5 flex items-center justify-center border border-white/10">
                        {searchQuery ? (
                          <Search className="h-6 w-6 text-muted-foreground" />
                        ) : (
                          <FolderOpen className="h-6 w-6 text-muted-foreground" />
                        )}
                      </div>
                      <div className="space-y-1">
                        <h3 className="font-medium text-foreground">
                          {searchQuery ? "No results found" : "This folder is empty"}
                        </h3>
                        <p className="text-sm text-muted-foreground max-w-xs mx-auto">
                          {searchQuery
                            ? "Try a different search term or navigate to another folder."
                            : "Upload files or connect a data source to add content."}
                        </p>
                      </div>
                    </div>
                  </TableCell>
                </TableRow>
              ) : (
                paginatedItems.map((item, index) => {
                  const isFolder = isFolderNode(item);
                  const isFocused = focusedIndex === index;

                  if (isFolder) {
                    return (
                      <TableRow
                        key={item.id}
                        className={cn(
                          "group cursor-pointer transition-colors border-b border-white/5",
                          "hover:bg-white/5",
                          isFocused && "bg-white/10 ring-1 ring-primary/50"
                        )}
                        onDoubleClick={() => navigateToFolder(item)}
                        onClick={() => setFocusedIndex(index)}
                      >
                        <TableCell className="pl-4">
                          {/* Folders can't be individually selected */}
                        </TableCell>
                        <TableCell className="pl-2 py-4">
                          <div className="flex items-center gap-3">
                            <div className="h-9 w-9 rounded-lg bg-primary/10 border border-primary/20 flex items-center justify-center shrink-0">
                              <Folder className="h-5 w-5 text-primary" />
                            </div>
                            <div className="flex flex-col min-w-0">
                              <span className="font-medium text-sm truncate max-w-[300px] lg:max-w-[400px] text-foreground">
                                {item.name}
                              </span>
                              <span className="text-xs text-muted-foreground">
                                Double-click to open
                              </span>
                            </div>
                          </div>
                        </TableCell>
                        <TableCell className="text-sm text-muted-foreground">
                          Folder
                        </TableCell>
                        <TableCell className="text-sm text-muted-foreground">
                          {item.documentCount} {item.documentCount === 1 ? "item" : "items"}
                        </TableCell>
                        <TableCell>
                          {/* Folders don't have status */}
                        </TableCell>
                        <TableCell className="text-right pr-6 text-sm text-muted-foreground">
                          —
                        </TableCell>
                        <TableCell>
                          <DropdownMenu>
                            <DropdownMenuTrigger asChild>
                              <Button variant="ghost" size="icon" className="h-8 w-8 opacity-0 group-hover:opacity-100 transition-opacity">
                                <MoreVertical className="h-4 w-4 text-muted-foreground" />
                              </Button>
                            </DropdownMenuTrigger>
                            <DropdownMenuContent align="end" className="bg-sidebar/90 backdrop-blur-xl border border-white/10">
                              <DropdownMenuLabel>Actions</DropdownMenuLabel>
                              <DropdownMenuItem onClick={() => navigateToFolder(item)}>
                                <FolderOpen className="mr-2 h-4 w-4" /> Open folder
                              </DropdownMenuItem>
                              <DropdownMenuSeparator />
                              {!isViewer ? (
                                <DropdownMenuItem
                                  className="text-destructive focus:text-destructive"
                                  onClick={() => setDeleteFolderId(item.id)}
                                >
                                  <Trash2 className="mr-2 h-4 w-4" /> Delete all contents ({item.documentCount})
                                </DropdownMenuItem>
                              ) : (
                                <DropdownMenuItem disabled className="text-muted-foreground opacity-50">
                                  <Trash2 className="mr-2 h-4 w-4" /> Delete (Read Only)
                                </DropdownMenuItem>
                              )}
                            </DropdownMenuContent>
                          </DropdownMenu>
                        </TableCell>
                      </TableRow>
                    );
                  }

                  // Document row
                  const doc = item.document;
                  return (
                    <TableRow
                      key={item.id}
                      className={cn(
                        "group transition-colors border-b border-white/5",
                        "hover:bg-white/5",
                        isFocused && "bg-white/10 ring-1 ring-primary/50",
                        selectedIds.has(item.id) && "bg-primary/5"
                      )}
                      onClick={() => setFocusedIndex(index)}
                    >
                      <TableCell className="pl-4">
                        <Checkbox
                          aria-label={`Select ${item.name}`}
                          checked={selectedIds.has(item.id)}
                          onCheckedChange={(checked) => toggleSelectOne(item.id, !!checked)}
                          disabled={isViewer}
                        />
                      </TableCell>
                      <TableCell className="pl-2 py-4">
                        <div className="flex items-center gap-3">
                          <div className="h-9 w-9 rounded-lg bg-white/5 border border-white/10 flex items-center justify-center shrink-0">
                            <FileText className="h-4 w-4 text-muted-foreground" />
                          </div>
                          <div className="flex flex-col min-w-0">
                            <span className="font-medium text-sm truncate max-w-[300px] lg:max-w-[400px] text-foreground">
                              {item.name}
                            </span>
                            <span className="text-xs text-muted-foreground truncate">
                              ID: {doc.id.slice(0, 8)}
                            </span>
                          </div>
                        </div>
                      </TableCell>
                      <TableCell className="text-sm text-muted-foreground capitalize">
                        {doc.source}
                      </TableCell>
                      <TableCell className="font-mono text-sm text-muted-foreground">
                        {formatSize(doc.size)}
                      </TableCell>
                      <TableCell>
                        <StatusBadge
                          status={doc.indexingStatus}
                          errorMessage={doc.errorMessage}
                        />
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
                          <DropdownMenuContent align="end" className="bg-sidebar/90 backdrop-blur-xl border border-white/10">
                            <DropdownMenuLabel>Actions</DropdownMenuLabel>
                            {doc.sourceType === 'file_upload' && (
                              <DropdownMenuItem>
                                <Download className="mr-2 h-4 w-4" /> Download
                              </DropdownMenuItem>
                            )}
                            <DropdownMenuItem
                              onClick={() => doc.sourceUrl && window.open(doc.sourceUrl, '_blank', 'noopener,noreferrer')}
                              disabled={!doc.sourceUrl}
                            >
                              <ExternalLink className="mr-2 h-4 w-4" /> View Source
                            </DropdownMenuItem>
                            <DropdownMenuSeparator />
                            {!isViewer ? (
                              <DropdownMenuItem
                                className="text-destructive focus:text-destructive"
                                onClick={() => setDeleteId(doc.id)}
                              >
                                <Trash2 className="mr-2 h-4 w-4" /> Delete
                              </DropdownMenuItem>
                            ) : (
                              <DropdownMenuItem disabled className="text-muted-foreground opacity-50">
                                <Trash2 className="mr-2 h-4 w-4" /> Delete (Read Only)
                              </DropdownMenuItem>
                            )}
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
        <div className="p-4 border-t border-white/10 bg-white/5 backdrop-blur-sm flex items-center justify-between">
          <div className="flex items-center gap-2 text-sm text-muted-foreground">
            <span>Rows per page</span>
            <Select
              value={pageSize.toString()}
              onValueChange={(value) => {
                setPageSize(Number(value));
                setCurrentPage(1);
              }}
            >
              <SelectTrigger className="w-[70px] h-8 bg-background/60 border-white/10">
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
              {totalItems > 0
                ? `${(currentPage - 1) * pageSize + 1}-${Math.min(currentPage * pageSize, totalItems)} of ${totalItems}`
                : "0 items"
              }
            </span>
            <div className="flex items-center gap-1">
              <Button
                variant="outline"
                size="icon"
                className="h-8 w-8 bg-background/60 border-white/10"
                onClick={() => setCurrentPage((p) => Math.max(1, p - 1))}
                disabled={currentPage === 1}
              >
                <ChevronLeft className="h-4 w-4" />
              </Button>
              <Button
                variant="outline"
                size="icon"
                className="h-8 w-8 bg-background/60 border-white/10"
                onClick={() => setCurrentPage((p) => Math.min(totalPages, p + 1))}
                disabled={currentPage === totalPages}
              >
                <ChevronRight className="h-4 w-4" />
              </Button>
            </div>
          </div>
        </div>
      </div>

      {/* Delete Document Dialog */}
      <AlertDialog open={!!deleteId} onOpenChange={(open) => !open && setDeleteId(null)}>
        <AlertDialogContent>
          <AlertDialogHeader>
            <AlertDialogTitle>Delete Document</AlertDialogTitle>
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

      {/* Delete Folder Dialog */}
      <AlertDialog open={!!deleteFolderId} onOpenChange={(open) => !open && setDeleteFolderId(null)}>
        <AlertDialogContent>
          <AlertDialogHeader>
            <AlertDialogTitle>Delete All Folder Contents</AlertDialogTitle>
            <AlertDialogDescription>
              This will permanently delete all documents in this folder and its subfolders.
              This action cannot be undone.
            </AlertDialogDescription>
          </AlertDialogHeader>
          <AlertDialogFooter>
            <AlertDialogCancel>Cancel</AlertDialogCancel>
            <AlertDialogAction
              onClick={handleDeleteFolder}
              className="bg-destructive text-destructive-foreground hover:bg-destructive/90"
            >
              Delete All
            </AlertDialogAction>
          </AlertDialogFooter>
        </AlertDialogContent>
      </AlertDialog>
    </div>
  );
}
