"use client";

import { useState, useEffect, useCallback } from "react";
import { format, parseISO, subDays } from "date-fns";
import {
  ScrollText,
  Filter,
  RefreshCw,
  Calendar,
  User,
  FileText,
  MessageSquare,
  Link2,
  Settings,
  Users,
  Shield,
  Download,
} from "lucide-react";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { SettingsPageHeader } from "@/components/settings/SettingsPageHeader";
import { SettingsToolbar } from "@/components/settings/SettingsToolbar";
import { SettingsStatCard } from "@/components/settings/SettingsStatCard";
import { SettingsEmptyState } from "@/components/settings/SettingsEmptyState";
import { SettingsPagination } from "@/components/settings/SettingsPagination";
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
import { Badge } from "@/components/ui/badge";
import { Spinner } from "@/components/ui/spinner";
import { useProfile } from "@/hooks/useProfile";
import { useRouter } from "next/navigation";
import { api } from "@/lib/api";
import { useToast } from "@/hooks/use-toast";
import { cn } from "@/lib/utils";

interface AuditLogEntry {
  id: string;
  user_id: string | null;
  user_email: string | null;
  user_name: string | null;
  action: string;
  resource_type: string | null;
  resource_id: string | null;
  details: Record<string, unknown>;
  ip_address: string | null;
  created_at: string;
}

interface AuditLogResponse {
  items: AuditLogEntry[];
  total: number;
  has_more: boolean;
}

// Action type to icon mapping
const actionIcons: Record<string, React.ElementType> = {
  "document.delete": FileText,
  "document.update": FileText,
  "chat.delete": MessageSquare,
  "connector.sync_start": Link2,
  "connector.sync_success": Link2,
  "connector.sync_fail": Link2,
  "settings.update": Settings,
  "team.member_invite": Users,
  "team.member_remove": Users,
  "gdpr.anonymization_requested": Shield,
  "gdpr.anonymization_completed": Shield,
};

// Action type to color mapping
const actionColors: Record<string, string> = {
  "document.delete": "bg-red-500/10 text-red-600 dark:text-red-400",
  "document.update": "bg-blue-500/10 text-blue-600 dark:text-blue-400",
  "chat.delete": "bg-orange-500/10 text-orange-600 dark:text-orange-400",
  "connector.sync_start": "bg-cyan-500/10 text-cyan-600 dark:text-cyan-400",
  "connector.sync_success": "bg-green-500/10 text-green-600 dark:text-green-400",
  "connector.sync_fail": "bg-red-500/10 text-red-600 dark:text-red-400",
  "settings.update": "bg-purple-500/10 text-purple-600 dark:text-purple-400",
  "team.member_invite": "bg-emerald-500/10 text-emerald-600 dark:text-emerald-400",
  "team.member_remove": "bg-amber-500/10 text-amber-600 dark:text-amber-400",
  "gdpr.anonymization_requested": "bg-amber-500/10 text-amber-600 dark:text-amber-400",
  "gdpr.anonymization_completed": "bg-green-500/10 text-green-600 dark:text-green-400",
};

const PAGE_SIZE = 20;

export default function AuditLogsPage() {
  const { profile, isLoading: profileLoading } = useProfile();
  const router = useRouter();
  const { toast } = useToast();

  // State
  const [logs, setLogs] = useState<AuditLogEntry[]>([]);
  const [total, setTotal] = useState(0);
  const [hasMore, setHasMore] = useState(false);
  const [isLoading, setIsLoading] = useState(true);
  const [isRefreshing, setIsRefreshing] = useState(false);
  const [page, setPage] = useState(0);

  // Filters
  const [actionFilter, setActionFilter] = useState<string>("all");
  const [resourceFilter, setResourceFilter] = useState<string>("all");
  const [dateRange, setDateRange] = useState<string>("7d");
  const [searchQuery, setSearchQuery] = useState("");

  // Available actions for filter
  const availableActions = [
    { value: "all", label: "All Actions" },
    { value: "document.delete", label: "Document Delete" },
    { value: "document.update", label: "Document Update" },
    { value: "chat.delete", label: "Chat Delete" },
    { value: "connector.sync_start", label: "Sync Started" },
    { value: "connector.sync_success", label: "Sync Success" },
    { value: "connector.sync_fail", label: "Sync Failed" },
    { value: "settings.update", label: "Settings Update" },
    { value: "team.member_invite", label: "Team Invite" },
    { value: "team.member_remove", label: "Team Remove" },
    { value: "gdpr.anonymization_requested", label: "GDPR Request" },
    { value: "gdpr.anonymization_completed", label: "GDPR Completed" },
  ];

  const resourceTypes = [
    { value: "all", label: "All Resources" },
    { value: "document", label: "Documents" },
    { value: "chat", label: "Chats" },
    { value: "connector", label: "Connectors" },
    { value: "user", label: "Users" },
    { value: "team", label: "Team" },
  ];

  const dateRanges = [
    { value: "1d", label: "Last 24 hours" },
    { value: "7d", label: "Last 7 days" },
    { value: "30d", label: "Last 30 days" },
    { value: "90d", label: "Last 90 days" },
    { value: "all", label: "All time" },
  ];

  // Authorization check
  useEffect(() => {
    if (!profileLoading && (!profile || profile.role !== "admin")) {
      router.push("/dashboard/settings/general");
    }
  }, [profile, profileLoading, router]);

  // Fetch audit logs
  const fetchLogs = useCallback(async (showRefreshing = false) => {
    if (showRefreshing) {
      setIsRefreshing(true);
    } else {
      setIsLoading(true);
    }

    try {
      const params = new URLSearchParams();
      params.set("limit", PAGE_SIZE.toString());
      params.set("offset", (page * PAGE_SIZE).toString());

      if (actionFilter !== "all") {
        params.set("action", actionFilter);
      }
      if (resourceFilter !== "all") {
        params.set("resource_type", resourceFilter);
      }
      if (dateRange !== "all") {
        const days = parseInt(dateRange.replace("d", ""));
        const fromDate = subDays(new Date(), days);
        params.set("from_date", fromDate.toISOString());
      }

      const response = await api.get<AuditLogResponse>(
        `/admin/audit-logs?${params.toString()}`
      );
      setLogs(response.data.items);
      setTotal(response.data.total);
      setHasMore(response.data.has_more);
    } catch (error) {
      console.error("Failed to fetch audit logs:", error);
      toast({
        title: "Error",
        description: "Failed to load audit logs. Please try again.",
        variant: "destructive",
      });
    } finally {
      setIsLoading(false);
      setIsRefreshing(false);
    }
  }, [page, actionFilter, resourceFilter, dateRange, toast]);

  // Initial fetch and refetch on filter changes
  useEffect(() => {
    if (profile?.role === "admin") {
      fetchLogs();
    }
  }, [fetchLogs, profile?.role]);

  // Filter logs by search query (client-side)
  const filteredLogs = logs.filter((log) => {
    if (!searchQuery) return true;
    const query = searchQuery.toLowerCase();
    return (
      log.action.toLowerCase().includes(query) ||
      log.resource_type?.toLowerCase().includes(query) ||
      log.resource_id?.toLowerCase().includes(query) ||
      JSON.stringify(log.details).toLowerCase().includes(query)
    );
  });

  // Format action for display
  const formatAction = (action: string) => {
    return action.split(".").map((word) =>
      word.charAt(0).toUpperCase() + word.slice(1)
    ).join(" ");
  };

  // Export logs as CSV
  const exportLogs = () => {
    const csvContent = [
      ["Timestamp", "User Name", "User Email", "Action", "Resource Type", "Resource ID", "Details", "IP Address"],
      ...filteredLogs.map((log) => [
        log.created_at,
        log.user_name || "",
        log.user_email || "",
        log.action,
        log.resource_type || "",
        log.resource_id || "",
        JSON.stringify(log.details),
        log.ip_address || "",
      ]),
    ]
      .map((row) => row.map((cell) => `"${String(cell).replace(/"/g, '""')}"`).join(","))
      .join("\n");

    const blob = new Blob([csvContent], { type: "text/csv;charset=utf-8;" });
    const link = document.createElement("a");
    link.href = URL.createObjectURL(blob);
    link.download = `audit-logs-${format(new Date(), "yyyy-MM-dd")}.csv`;
    link.click();
  };

  // Loading state
  if (profileLoading || !profile || profile.role !== "admin") {
    return (
      <div className="flex items-center justify-center py-12">
        <div className="flex flex-col items-center gap-3">
          <Spinner className="h-8 w-8 animate-spin text-primary" />
          <p className="text-sm text-muted-foreground">Loading audit logs...</p>
        </div>
      </div>
    );
  }

  return (
    <div className="space-y-6 animate-fade-in">
      <SettingsPageHeader
        icon={ScrollText}
        title="Audit Logs"
        description="Track all actions and changes in your workspace"
        actions={
          <div className="flex items-center gap-2">
            <Button
              variant="outline"
              size="sm"
              onClick={exportLogs}
              disabled={filteredLogs.length === 0}
            >
              <Download className="h-4 w-4 mr-2" />
              Export CSV
            </Button>
            <Button
              variant="outline"
              size="sm"
              onClick={() => fetchLogs(true)}
              disabled={isRefreshing}
            >
              <RefreshCw className={cn("h-4 w-4 mr-2", isRefreshing && "animate-spin")} />
              Refresh
            </Button>
          </div>
        }
      />

      {/* Filters */}
      <SettingsToolbar
        searchPlaceholder="Search logs..."
        searchValue={searchQuery}
        onSearchChange={(v) => setSearchQuery(v)}
      >
        <div className="flex flex-wrap gap-2">
          <Select value={actionFilter} onValueChange={setActionFilter}>
            <SelectTrigger className="w-[160px]">
              <Filter className="h-4 w-4 mr-2" />
              <SelectValue placeholder="Action" />
            </SelectTrigger>
            <SelectContent>
              {availableActions.map((action) => (
                <SelectItem key={action.value} value={action.value}>
                  {action.label}
                </SelectItem>
              ))}
            </SelectContent>
          </Select>
          <Select value={resourceFilter} onValueChange={setResourceFilter}>
            <SelectTrigger className="w-[150px]">
              <SelectValue placeholder="Resource" />
            </SelectTrigger>
            <SelectContent>
              {resourceTypes.map((type) => (
                <SelectItem key={type.value} value={type.value}>
                  {type.label}
                </SelectItem>
              ))}
            </SelectContent>
          </Select>
          <Select value={dateRange} onValueChange={setDateRange}>
            <SelectTrigger className="w-[140px]">
              <Calendar className="h-4 w-4 mr-2" />
              <SelectValue placeholder="Date range" />
            </SelectTrigger>
            <SelectContent>
              {dateRanges.map((range) => (
                <SelectItem key={range.value} value={range.value}>
                  {range.label}
                </SelectItem>
              ))}
            </SelectContent>
          </Select>
        </div>
      </SettingsToolbar>

      {/* Logs Table */}
      {isLoading ? (
        <div className="flex items-center justify-center py-12">
          <Spinner className="h-8 w-8 animate-spin text-primary" />
        </div>
      ) : filteredLogs.length === 0 ? (
        <SettingsEmptyState
          icon={ScrollText}
          title="No audit logs found"
          description={
            searchQuery || actionFilter !== "all" || resourceFilter !== "all"
              ? "Try adjusting your filters to see more results."
              : "Audit logs will appear here as you use the platform."
          }
        />
          ) : (
            <>
              <div className="rounded-lg border">
                <Table>
                  <TableHeader>
                    <TableRow className="bg-muted/30">
                      <TableHead className="w-[180px]">Timestamp</TableHead>
                      <TableHead className="w-[150px]">User</TableHead>
                      <TableHead className="w-[180px]">Action</TableHead>
                      <TableHead className="w-[120px]">Resource</TableHead>
                      <TableHead>Details</TableHead>
                      <TableHead className="w-[120px] text-right">IP Address</TableHead>
                    </TableRow>
                  </TableHeader>
                  <TableBody>
                    {filteredLogs.map((log) => {
                      const Icon = actionIcons[log.action] || ScrollText;
                      const colorClass = actionColors[log.action] || "bg-gray-500/10 text-gray-600";

                      return (
                        <TableRow key={log.id} className="hover:bg-muted/30">
                          <TableCell className="font-mono text-xs">
                            {format(parseISO(log.created_at), "MMM dd, yyyy HH:mm:ss")}
                          </TableCell>
                          <TableCell>
                            {log.user_name || log.user_email ? (
                              <div className="flex items-center gap-2">
                                <div className="flex h-7 w-7 items-center justify-center rounded-full bg-primary/10 text-primary">
                                  <User className="h-3.5 w-3.5" />
                                </div>
                                <div className="min-w-0">
                                  {log.user_name && (
                                    <div className="text-sm font-medium truncate max-w-[100px]" title={log.user_name}>
                                      {log.user_name}
                                    </div>
                                  )}
                                  {log.user_email && (
                                    <div className="text-xs text-muted-foreground truncate max-w-[100px]" title={log.user_email}>
                                      {log.user_email}
                                    </div>
                                  )}
                                </div>
                              </div>
                            ) : (
                              <span className="text-muted-foreground text-xs">
                                {log.user_id ? log.user_id.slice(0, 8) + "..." : "System"}
                              </span>
                            )}
                          </TableCell>
                          <TableCell>
                            <Badge variant="secondary" className={cn("gap-1.5", colorClass)}>
                              <Icon className="h-3 w-3" />
                              {formatAction(log.action)}
                            </Badge>
                          </TableCell>
                          <TableCell>
                            {log.resource_type ? (
                              <span className="text-sm text-muted-foreground">
                                {log.resource_type}
                                {log.resource_id && (
                                  <span className="font-mono text-xs block truncate max-w-[100px]">
                                    {log.resource_id.slice(0, 8)}...
                                  </span>
                                )}
                              </span>
                            ) : (
                              <span className="text-muted-foreground">—</span>
                            )}
                          </TableCell>
                          <TableCell>
                            <div className="max-w-[300px] truncate text-sm text-muted-foreground">
                              {Object.keys(log.details).length > 0 ? (
                                <code className="text-xs bg-muted px-2 py-1 rounded">
                                  {JSON.stringify(log.details).slice(0, 80)}
                                  {JSON.stringify(log.details).length > 80 && "..."}
                                </code>
                              ) : (
                                <span className="text-muted-foreground">—</span>
                              )}
                            </div>
                          </TableCell>
                          <TableCell className="text-right font-mono text-xs text-muted-foreground">
                            {log.ip_address || "—"}
                          </TableCell>
                        </TableRow>
                      );
                    })}
                  </TableBody>
                </Table>
              </div>

              {/* Pagination */}
              <SettingsPagination
                currentPage={page + 1}
                totalPages={Math.max(1, Math.ceil(total / PAGE_SIZE))}
                pageSize={PAGE_SIZE}
                totalItems={total}
                onPageChange={(p) => setPage(p - 1)}
                itemLabel="log"
              />
            </>
          )}

      {/* Summary Stats Card */}
      <div className="grid gap-4 grid-cols-2 md:grid-cols-4">
        <SettingsStatCard
          icon={ScrollText}
          iconColorClass="text-primary"
          iconBgClass="bg-primary/10"
          label="Total Logs"
          value={total}
        />
        <SettingsStatCard
          icon={Shield}
          iconColorClass="text-green-600"
          iconBgClass="bg-green-500/10"
          label="Successful Actions"
          value={logs.filter((l) => l.action.includes("success")).length}
        />
        <SettingsStatCard
          icon={FileText}
          iconColorClass="text-red-600"
          iconBgClass="bg-red-500/10"
          label="Failed/Deletions"
          value={logs.filter((l) => l.action.includes("fail") || l.action.includes("delete")).length}
        />
        <SettingsStatCard
          icon={Shield}
          iconColorClass="text-amber-600"
          iconBgClass="bg-amber-500/10"
          label="GDPR Requests"
          value={logs.filter((l) => l.action.includes("gdpr")).length}
        />
      </div>
    </div>
  );
}
