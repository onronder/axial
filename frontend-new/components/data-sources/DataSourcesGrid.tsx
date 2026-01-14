"use client";

import { useState } from "react";
import { Search, Filter, Loader2, RefreshCw } from "lucide-react";
import { Input } from "@/components/ui/input";
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "@/components/ui/select";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { DataSourceCard } from "./DataSourceCard";
import { FileBrowser } from "./FileBrowser";
import { URLCrawlerInput } from "./URLCrawlerInput";
import { FileUploadZone } from "./FileUploadZone";
import { ComingSoonIntegrations } from "./ComingSoonIntegrations";
import { SftpConnectModal } from "./SftpConnectModal";
import { useDataSources } from "@/hooks/useDataSources";
import { useProfile } from "@/hooks/useProfile";
import { useUsage } from "@/hooks/useUsage";
import type { DataSourceCategory, MergedDataSource } from "@/types";

// Category labels for display
const CATEGORY_LABELS: Record<string, string> = {
  cloud: "Cloud Storage",
  files: "Files",
  web: "Web Resources",
  database: "Databases",
  productivity: "Productivity Tools",
  apps: "Applications",
  knowledge_base: "Knowledge Base",
  other: "Other",
};
const CATEGORY_ORDER = ["cloud", "files", "productivity", "web", "database", "apps", "other"];

type FilterStatus = "all" | "connected" | "not-connected";

const DATA_SOURCE_CATEGORIES: DataSourceCategory[] = [
  "cloud",
  "files",
  "web",
  "database",
  "productivity",
  "apps",
];

const isDataSourceCategory = (value: string | null | undefined): value is DataSourceCategory =>
  !!value && DATA_SOURCE_CATEGORIES.includes(value as DataSourceCategory);

const LOCAL_UPLOAD_TYPES = new Set(["file_upload", "file-upload", "local"]);
const CATEGORY_SOURCE_ORDER: Record<string, string[]> = {
  cloud: ["google_drive", "onedrive", "sharepoint"],
  files: ["sftp", "file_upload", "file-upload", "local"],
};

const normalizeType = (value: string) => value.toLowerCase().replace(/-/g, "_");

export function DataSourcesGrid() {
  const {
    dataSources,
    loading,
    error,
    refresh,
    connectedSources,
    connect,
    disconnect,
    syncIntegration
  } = useDataSources();
  const { profile, isLoading: profileLoading } = useProfile();
  const [searchQuery, setSearchQuery] = useState("");
  const [categoryFilter, setCategoryFilter] = useState<string>("all");
  const [statusFilter] = useState<FilterStatus>("all");
  const [browsing, setBrowsing] = useState<MergedDataSource | null>(null);
  const [sftpConnectOpen, setSftpConnectOpen] = useState(false);
  const isViewer = profile?.role === "viewer";
  const { canWebCrawl } = useUsage();
  const canRunWebCrawl = canWebCrawl && !isViewer;
  const webCrawlDisabledReason = isViewer
    ? "View-only members cannot run crawls or ingest data."
    : !canWebCrawl
      ? "Web crawling is available on Starter and above."
      : undefined;

  const connectedCount = connectedSources.length;
  const localUploadSource: MergedDataSource = {
    id: "local-upload",
    definitionId: "local-upload",
    type: "file_upload",
    name: "Local Files",
    description: "Drag & drop PDF, TXT, or DOCX files to upload",
    iconPath: null,
    category: "files",
    isConnected: false,
    lastSyncAt: null,
    integrationId: null,
  };
  const hasLocalUpload = dataSources.some((source) => LOCAL_UPLOAD_TYPES.has(source.type));
  const displaySources = hasLocalUpload ? dataSources : [...dataSources, localUploadSource];

  const handleConnect = (type: string) => {
    if (type === "sftp") {
      setSftpConnectOpen(true);
      return;
    }
    connect(type);
  };

  // Get unique categories from data
  const categories = [...new Set(displaySources.map(ds => ds.category))].filter(Boolean);

  const filteredSources = displaySources.filter((source) => {
    const matchesSearch = source.name.toLowerCase().includes(searchQuery.toLowerCase());
    const matchesCategory = categoryFilter === "all" || source.category === categoryFilter;
    const matchesStatus =
      statusFilter === "all" ||
      (statusFilter === "connected" && source.isConnected) ||
      (statusFilter === "not-connected" && !source.isConnected);

    return matchesSearch && matchesCategory && matchesStatus;
  });

  // Group by category
  const groupedSources = filteredSources.reduce((acc, source) => {
    const category = source.category || "other";
    if (!acc[category]) {
      acc[category] = [];
    }
    acc[category].push(source);
    return acc;
  }, {} as Record<string, MergedDataSource[]>);

  if (browsing) {
    return (
      <FileBrowser
          source={{
          id: browsing.id,
          name: browsing.name,
          type: browsing.type,
          status: browsing.isConnected ? "connected" : "disconnected",
          lastSync: browsing.lastSyncAt || "-",
          icon: browsing.iconPath || browsing.type,
          description: browsing.description,
          category: isDataSourceCategory(browsing.category) ? browsing.category : "files",
        }}
        onBack={() => setBrowsing(null)}
        isViewer={isViewer}
      />
    );
  }

  if (loading || profileLoading) {
    return (
      <div className="flex items-center justify-center py-12">
        <Loader2 className="h-8 w-8 animate-spin text-primary" />
      </div>
    );
  }

  if (error) {
    return (
      <div className="text-center py-12">
        <p className="text-destructive mb-4">{error}</p>
        <Button onClick={refresh} variant="outline">
          <RefreshCw className="h-4 w-4 mr-2" />
          Retry
        </Button>
      </div>
    );
  }

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="flex items-center justify-between">
        <div>
          <h1 className="font-display text-2xl font-bold text-foreground">Data Sources</h1>
          <p className="mt-1 text-muted-foreground">
            Connect your data to enhance AI knowledge
          </p>
        </div>
        <Button onClick={refresh} variant="ghost" size="icon">
          <RefreshCw className="h-4 w-4" />
        </Button>
      </div>

      {isViewer && (
        <div className="rounded-lg border border-amber-200 bg-amber-50 px-4 py-3 text-sm text-amber-900">
          You have view-only access. Connect, ingest, and sync actions are disabled.
        </div>
      )}

      {/* Filters */}
      <div className="flex flex-col gap-4 sm:flex-row sm:items-center sm:justify-between">
        <div className="relative flex-1 max-w-md">
          <Search className="absolute left-3 top-1/2 h-4 w-4 -translate-y-1/2 text-muted-foreground" />
          <Input
            placeholder="Search sources..."
            value={searchQuery}
            onChange={(e) => setSearchQuery(e.target.value)}
            className="pl-9"
          />
        </div>
        <div className="flex items-center gap-3">
          <Select
            value={categoryFilter}
            onValueChange={setCategoryFilter}
          >
            <SelectTrigger className="w-[160px]">
              <Filter className="mr-2 h-4 w-4" />
              <SelectValue placeholder="Category" />
            </SelectTrigger>
            <SelectContent>
              <SelectItem value="all">All Categories</SelectItem>
              {categories.map((cat) => (
                <SelectItem key={cat} value={cat}>
                  {CATEGORY_LABELS[cat] || cat}
                </SelectItem>
              ))}
            </SelectContent>
          </Select>
          <Badge variant="success" className="px-3 py-1">
            {connectedCount} Connected
          </Badge>
        </div>
      </div>

      {/* Grid by Category */}
      <div className="space-y-8">
        {[...CATEGORY_ORDER, ...Object.keys(groupedSources)]
          .filter((category, index, list) => list.indexOf(category) === index)
          .filter((category) => groupedSources[category])
          .map((category) => {
            const sources = groupedSources[category];
            const order = CATEGORY_SOURCE_ORDER[category] || [];
            const orderedSources = [...sources].sort((a, b) => {
              const aIndex = order.indexOf(normalizeType(a.type));
              const bIndex = order.indexOf(normalizeType(b.type));
              if (aIndex !== bIndex) {
                return (aIndex === -1 ? Number.MAX_SAFE_INTEGER : aIndex) -
                  (bIndex === -1 ? Number.MAX_SAFE_INTEGER : bIndex);
              }
              return a.name.localeCompare(b.name);
            });
            return (
          <div key={category} className="space-y-4">
            <h2 className="font-medium text-foreground border-b border-border pb-2">
              {CATEGORY_LABELS[category] || category}
            </h2>
            <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-3 xl:grid-cols-4">
              {orderedSources.map((source) => (
                // Use URLCrawlerInput for web type, FileUploadZone for local upload, DataSourceCard for others
                source.type === "web" ? (
                  <URLCrawlerInput
                    key={source.id}
                    source={{
                      id: source.id,
                      name: source.name,
                      type: source.type,
                      status: source.isConnected ? "connected" : "disconnected",
                      lastSync: source.lastSyncAt || "-",
                      icon: source.iconPath || source.type,
                      description: source.description,
                      category: isDataSourceCategory(source.category) ? source.category : "web",
                    }}
                    disabled={!canRunWebCrawl}
                    disabledReason={webCrawlDisabledReason}
                  />
                ) : LOCAL_UPLOAD_TYPES.has(source.type) ? (
                  <FileUploadZone
                    key={source.id}
                    source={{
                      id: source.id,
                      name: source.name,
                      type: "file",
                      status: "disconnected",
                      lastSync: "-",
                      icon: "upload",
                      description: source.description,
                      category: "files",
                    }}
                    disabled={isViewer}
                  />
                ) : (
                  <DataSourceCard
                    key={source.id}
                    source={source}
                    onBrowse={() => setBrowsing(source)}
                    onConnect={handleConnect}
                    onDisconnect={disconnect}
                    onSync={syncIntegration}
                    disabled={isViewer}
                  />
                )
              ))}
            </div>
          </div>
            );
          })}


        {/* Empty state */}
        {Object.keys(groupedSources).length === 0 && (
          <div className="text-center py-12 text-muted-foreground">
            No data sources available. Try adjusting your filters.
          </div>
        )}
      </div>

      <SftpConnectModal
        open={sftpConnectOpen}
        onOpenChange={setSftpConnectOpen}
        onConnected={refresh}
      />

      {/* Coming Soon Section */}
      <ComingSoonIntegrations />
    </div>
  );
}
