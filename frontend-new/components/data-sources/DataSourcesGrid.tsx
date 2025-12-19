"use client";

import { useState } from "react";
import { Search, Filter } from "lucide-react";
import { Input } from "@/components/ui/input";
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "@/components/ui/select";
import { Badge } from "@/components/ui/badge";
import { DataSourceCard } from "./DataSourceCard";
import { FileBrowser } from "./FileBrowser";
import { URLCrawlerInput } from "./URLCrawlerInput";
import { FileUploadZone } from "./FileUploadZone";
import {
  DATA_SOURCES,
  CATEGORY_LABELS,
  DataSource,
} from "@/lib/mockData";
import { useDataSources } from "@/hooks/useDataSources";

type DataSourceCategory = "files" | "cloud" | "web" | "database" | "apps";
type FilterStatus = "all" | "connected" | "not-connected";

export function DataSourcesGrid() {
  const [searchQuery, setSearchQuery] = useState("");
  const [categoryFilter, setCategoryFilter] = useState<DataSourceCategory | "all">("all");
  const [statusFilter, setStatusFilter] = useState<FilterStatus>("all");
  const [browsing, setBrowsing] = useState<DataSource | null>(null);
  const { connectedSources } = useDataSources();

  const connectedCount = connectedSources.length;

  const filteredSources = DATA_SOURCES.filter((source) => {
    const matchesSearch = source.name.toLowerCase().includes(searchQuery.toLowerCase());
    const matchesCategory = categoryFilter === "all" || source.category === categoryFilter;
    const isConnected = connectedSources.includes(source.id);
    const matchesStatus =
      statusFilter === "all" ||
      (statusFilter === "connected" && isConnected) ||
      (statusFilter === "not-connected" && !isConnected);

    return matchesSearch && matchesCategory && matchesStatus;
  });

  const groupedSources = filteredSources.reduce((acc, source) => {
    const category = source.category as DataSourceCategory;
    if (!acc[category]) {
      acc[category] = [];
    }
    acc[category].push(source);
    return acc;
  }, {} as Record<DataSourceCategory, DataSource[]>);

  if (browsing) {
    return (
      <FileBrowser
        source={browsing}
        onBack={() => setBrowsing(null)}
      />
    );
  }

  return (
    <div className="space-y-6">
      {/* Header */}
      <div>
        <h1 className="font-display text-2xl font-bold text-foreground">Data Sources</h1>
        <p className="mt-1 text-muted-foreground">
          Connect your data to enhance AI knowledge
        </p>
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
            onValueChange={(value) => setCategoryFilter(value as DataSourceCategory | "all")}
          >
            <SelectTrigger className="w-[160px]">
              <Filter className="mr-2 h-4 w-4" />
              <SelectValue placeholder="Category" />
            </SelectTrigger>
            <SelectContent>
              <SelectItem value="all">All Categories</SelectItem>
              {Object.entries(CATEGORY_LABELS).map(([key, label]) => (
                <SelectItem key={key} value={key}>
                  {label}
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
        {(Object.entries(CATEGORY_LABELS) as [DataSourceCategory, string][]).map(
          ([category, label]) => {
            const sources = groupedSources[category];
            if (!sources?.length) return null;

            return (
              <div key={category} className="space-y-4">
                <h2 className="font-medium text-foreground border-b border-border pb-2">
                  {label}
                </h2>
                <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-3 xl:grid-cols-4">
                  {sources.map((source) => {
                    if (source.id === "url-crawler") {
                      return <URLCrawlerInput key={source.id} source={source} />;
                    }
                    if (source.id === "file-upload") {
                      return <FileUploadZone key={source.id} source={source} />;
                    }
                    return (
                      <DataSourceCard
                        key={source.id}
                        source={source}
                        onBrowse={() => setBrowsing(source)}
                      />
                    );
                  })}
                </div>
              </div>
            );
          }
        )}
      </div>
    </div>
  );
}