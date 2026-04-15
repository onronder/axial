
"use client";

import { useState, Suspense } from "react";
import { Search, Filter, RefreshCw, Database, Youtube } from "lucide-react";
import { Input } from "@/components/ui/input";
import { SettingsPageHeader } from "@/components/settings/SettingsPageHeader";
import { SettingsToolbar } from "@/components/settings/SettingsToolbar";
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
import { YoutubeInput } from "./YoutubeInput";
import { FileUploadZone } from "./FileUploadZone";
import { ComingSoonIntegrations, type ComingSoonIntegration } from "./ComingSoonIntegrations";
import { LazySftpConnectModal, LazyS3ConnectModal } from "@/components/lazy";
import { useDataSources } from "@/hooks/useDataSources";
import { useProfile } from "@/hooks/useProfile";
import { useUsage } from "@/hooks/useUsage";
import { useQuotaStatus } from "@/hooks/useQuotaStatus";
import { isYoutubeIngestionEnabled } from "@/lib/features";
import type { DataSourceCategory, MergedDataSource } from "@/types";
import { Spinner } from "@/components/ui/spinner";

// Category labels for display
const CATEGORY_LABELS: Record<string, string> = {
  cloud: "Cloud Storage",
  files: "Files",
  web: "Web Resources",
  database: "Databases",
  productivity: "Productivity Tools",
  apps: "Applications",
  knowledge_base: "Wiki & Docs",
  development: "Code & Dev",
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
  cloud: ["google_drive", "dropbox", "onedrive", "sharepoint", "s3"],
  files: ["sftp", "file_upload", "file-upload", "local"],
  web: ["web", "youtube"],  // Web crawler first, then YouTube
};

// Enterprise-only connectors (require Enterprise plan to connect)
const ENTERPRISE_ONLY_SOURCES = new Set(["s3"]);

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
  const [s3ConnectOpen, setS3ConnectOpen] = useState(false);
  const isViewer = profile?.role === "viewer";
  const { canWebCrawl, plan, refresh: refreshUsage } = useUsage();
  const { isProviderQuotaExceeded } = useQuotaStatus();
  const canRunWebCrawl = canWebCrawl && !isViewer;
  const youtubeIngestionEnabled = isYoutubeIngestionEnabled();
  
  // Wrapper to refresh usage stats after disconnecting
  const handleDisconnect = async (type: string) => {
    await disconnect(type);
    refreshUsage(true);
  };
  const webCrawlDisabledReason = isViewer
    ? "View-only members cannot run crawls or ingest data."
    : !canWebCrawl
      ? "Web crawling is available on Starter and above."
      : undefined;

  const connectedCount = connectedSources.length;
  
  // Virtual data source for local file uploads (shown if not already in backend sources)
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
  
  // Virtual data source for YouTube video ingestion
  const youtubeSource: MergedDataSource = {
    id: "youtube-video",
    definitionId: "youtube-video",
    type: "youtube",
    name: "YouTube Video",
    description: "Transcribe and chat with YouTube videos",
    iconPath: null,
    category: "web",
    isConnected: false,
    lastSyncAt: null,
    integrationId: null,
  };

  const youtubeComingSoon: ComingSoonIntegration = {
    id: "youtube",
    name: "YouTube Video",
    description: "Transcript ingestion is paused in production while reliability improvements are in progress.",
    icon: <Youtube className="h-6 w-6" />,
    category: "Web Resources",
    badge: "Coming Soon",
  };
  
  const baseSources = youtubeIngestionEnabled
    ? dataSources
    : dataSources.filter((source) => source.type !== "youtube");

  const hasLocalUpload = baseSources.some((source) => LOCAL_UPLOAD_TYPES.has(source.type));
  const hasYoutubeSource = baseSources.some((source) => source.type === "youtube");
  
  // Combine backend sources with virtual sources (if not already present)
  const displaySources = [
    ...baseSources,
    ...(hasLocalUpload ? [] : [localUploadSource]),
    ...(youtubeIngestionEnabled && !hasYoutubeSource ? [youtubeSource] : []),
  ];

  const handleConnect = (type: string) => {
    if (type === "sftp") {
      setSftpConnectOpen(true);
      return;
    }
    if (type === "s3") {
      setS3ConnectOpen(true);
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
        <Spinner className="h-8 w-8 animate-spin text-primary" />
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
      <SettingsPageHeader
        icon={Database}
        title="Data Sources"
        description="Connect your data to enhance AI knowledge"
        actions={
          <Button onClick={refresh} variant="outline" size="sm" aria-label="Refresh data sources">
            <RefreshCw className="h-4 w-4 mr-2" />
            Refresh
          </Button>
        }
      />

      {isViewer && (
        <div className="rounded-lg border border-amber-200 bg-amber-50 px-4 py-3 text-sm text-amber-900">
          You have view-only access. Connect, ingest, and sync actions are disabled.
        </div>
      )}

      {/* Filters */}
      <SettingsToolbar
        searchPlaceholder="Search sources..."
        searchValue={searchQuery}
        onSearchChange={setSearchQuery}
      >
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
      </SettingsToolbar>

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
                // Use YoutubeInput for YouTube, URLCrawlerInput for web, FileUploadZone for local upload, DataSourceCard for others
                source.type === "youtube" ? (
                  <YoutubeInput
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
                ) : source.type === "web" ? (
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
                    onDisconnect={handleDisconnect}
                    onSync={syncIntegration}
                    disabled={isViewer}
                    quotaExceeded={isProviderQuotaExceeded(source.type)}
                    enterpriseOnly={ENTERPRISE_ONLY_SOURCES.has(source.type)}
                    userPlan={plan}
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

      <Suspense fallback={null}>
        <LazySftpConnectModal
          open={sftpConnectOpen}
          onOpenChange={setSftpConnectOpen}
          onConnected={refresh}
        />
      </Suspense>

      <Suspense fallback={null}>
        <LazyS3ConnectModal
          open={s3ConnectOpen}
          onOpenChange={setS3ConnectOpen}
          onConnected={refresh}
        />
      </Suspense>

      {/* Coming Soon Section */}
      <ComingSoonIntegrations extraIntegrations={youtubeIngestionEnabled ? [] : [youtubeComingSoon]} />
    </div>
  );
}
