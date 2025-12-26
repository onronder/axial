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
import { useDataSources } from "@/hooks/useDataSources";
import type { MergedDataSource } from "@/types";

// Category labels for display
const CATEGORY_LABELS: Record<string, string> = {
  "Cloud Storage": "Cloud Storage",
  "Knowledge Base": "Knowledge Base",
  "Web": "Web Resources",
  "files": "Files",
  "other": "Other",
};

type FilterStatus = "all" | "connected" | "not-connected";

export function DataSourcesGrid() {
  const { dataSources, loading, error, refresh, connectedSources } = useDataSources();
  const [searchQuery, setSearchQuery] = useState("");
  const [categoryFilter, setCategoryFilter] = useState<string>("all");
  const [statusFilter, setStatusFilter] = useState<FilterStatus>("all");
  const [browsing, setBrowsing] = useState<MergedDataSource | null>(null);

  const connectedCount = connectedSources.length;

  // Get unique categories from data
  const categories = [...new Set(dataSources.map(ds => ds.category))].filter(Boolean);

  const filteredSources = dataSources.filter((source) => {
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
          category: browsing.category as any,
        }}
        onBack={() => setBrowsing(null)}
      />
    );
  }

  if (loading) {
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
        {Object.entries(groupedSources).map(([category, sources]) => (
          <div key={category} className="space-y-4">
            <h2 className="font-medium text-foreground border-b border-border pb-2">
              {CATEGORY_LABELS[category] || category}
            </h2>
            <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-3 xl:grid-cols-4">
              {sources.map((source) => (
                <DataSourceCard
                  key={source.id}
                  source={source}
                  onBrowse={() => setBrowsing(source)}
                />
              ))}
            </div>
          </div>
        ))}

        {/* Empty state */}
        {Object.keys(groupedSources).length === 0 && (
          <div className="text-center py-12 text-muted-foreground">
            No data sources available. Try adjusting your filters.
          </div>
        )}
      </div>

      {/* Coming Soon Section */}
      <ComingSoonIntegrations />
    </div>
  );
}