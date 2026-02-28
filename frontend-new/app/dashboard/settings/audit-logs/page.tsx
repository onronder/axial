"use client";

import { useState, useEffect, useCallback, useRef, useDeferredValue } from "react";
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
  Loader2,
  CheckCircle,
  XCircle,
  Lock,
  Database,
  Folder,
  Key,
  Upload,
  Ban,
  Clock,
  RotateCcw,
  Send,
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
  // Document
  "document.create": FileText,
  "document.update": FileText,
  "document.delete": FileText,
  "document.wipe": Ban,
  // Chat
  "chat.create": MessageSquare,
  "chat.delete": MessageSquare,
  // Connector
  "connector.create": Link2,
  "connector.update": Link2,
  "connector.delete": Link2,
  "connector.connect": Link2,
  "connector.disconnect": Link2,
  "connector.sync_start": Link2,
  "connector.sync_success": CheckCircle,
  "connector.sync_fail": XCircle,
  // Scope
  "scope.create": Folder,
  "scope.update": Folder,
  "scope.delete": Folder,
  "scope.wipe": Ban,
  // Ingestion
  "ingestion.queued": Clock,
  "ingestion.started": Upload,
  "ingestion.completed": CheckCircle,
  "ingestion.failed": XCircle,
  "ingestion.skipped": Ban,
  "ingestion.timeout": Clock,
  // Chunk / Org
  "chunk.purge": Database,
  "organization.purge": Database,
  // Security / Ghost Protocol
  "security.document_wiped": Shield,
  "security.scope_deleted": Shield,
  "security.chunk_purged": Shield,
  "security.organization_purged": Shield,
  "security.ghost_protocol_activated": Lock,
  "security.ghost_protocol_completed": Lock,
  // Settings
  "settings.update": Settings,
  "settings.configure": Settings,
  // Team
  "team.create": Users,
  "team.update": Users,
  "team.member_invite": Users,
  "team.member_remove": Users,
  "team.member_role_change": Users,
  "team.member_status_change": Users,
  "team.member_resend_invite": Send,
  // Approval
  "approval.request": Shield,
  "approval.approve": CheckCircle,
  "approval.reject": XCircle,
  "approval.execute": Shield,
  "approval.approval_requested": Shield,
  // Consent
  "consent.granted": CheckCircle,
  "consent.revoked": Ban,
  "consent.updated": Settings,
  // GDPR
  "gdpr.anonymization_requested": Shield,
  "gdpr.anonymization_completed": Shield,
  "gdpr.data_export_requested": Download,
  "gdpr.data_export_completed": Download,
  "gdpr.deletion_requested": Ban,
  "gdpr.deletion_completed": Ban,
  // Compliance
  "compliance.audit_requested": ScrollText,
  "compliance.audit_completed": ScrollText,
  // MCP
  "mcp.api_key_created": Key,
  "mcp.api_key_rotated": RotateCcw,
  "mcp.api_key_revoked": Ban,
  // Safety
  "safety.content_flagged": Shield,
  "safety.content_blocked": Ban,
};

// Action type to color mapping
const actionColors: Record<string, string> = {
  // Document
  "document.create": "bg-green-500/10 text-green-600 dark:text-green-400",
  "document.update": "bg-blue-500/10 text-blue-600 dark:text-blue-400",
  "document.delete": "bg-red-500/10 text-red-600 dark:text-red-400",
  "document.wipe": "bg-red-500/10 text-red-600 dark:text-red-400",
  // Chat
  "chat.create": "bg-green-500/10 text-green-600 dark:text-green-400",
  "chat.delete": "bg-orange-500/10 text-orange-600 dark:text-orange-400",
  // Connector
  "connector.create": "bg-green-500/10 text-green-600 dark:text-green-400",
  "connector.update": "bg-blue-500/10 text-blue-600 dark:text-blue-400",
  "connector.delete": "bg-red-500/10 text-red-600 dark:text-red-400",
  "connector.connect": "bg-green-500/10 text-green-600 dark:text-green-400",
  "connector.disconnect": "bg-red-500/10 text-red-600 dark:text-red-400",
  "connector.sync_start": "bg-blue-500/10 text-blue-600 dark:text-blue-400",
  "connector.sync_success": "bg-green-500/10 text-green-600 dark:text-green-400",
  "connector.sync_fail": "bg-red-500/10 text-red-600 dark:text-red-400",
  // Scope
  "scope.create": "bg-green-500/10 text-green-600 dark:text-green-400",
  "scope.update": "bg-blue-500/10 text-blue-600 dark:text-blue-400",
  "scope.delete": "bg-red-500/10 text-red-600 dark:text-red-400",
  "scope.wipe": "bg-red-500/10 text-red-600 dark:text-red-400",
  // Ingestion
  "ingestion.queued": "bg-blue-500/10 text-blue-600 dark:text-blue-400",
  "ingestion.started": "bg-blue-500/10 text-blue-600 dark:text-blue-400",
  "ingestion.completed": "bg-green-500/10 text-green-600 dark:text-green-400",
  "ingestion.failed": "bg-red-500/10 text-red-600 dark:text-red-400",
  "ingestion.skipped": "bg-amber-500/10 text-amber-600 dark:text-amber-400",
  "ingestion.timeout": "bg-amber-500/10 text-amber-600 dark:text-amber-400",
  // Chunk / Org
  "chunk.purge": "bg-red-500/10 text-red-600 dark:text-red-400",
  "organization.purge": "bg-red-500/10 text-red-600 dark:text-red-400",
  // Security / Ghost Protocol
  "security.document_wiped": "bg-violet-500/10 text-violet-600 dark:text-violet-400",
  "security.scope_deleted": "bg-violet-500/10 text-violet-600 dark:text-violet-400",
  "security.chunk_purged": "bg-violet-500/10 text-violet-600 dark:text-violet-400",
  "security.organization_purged": "bg-violet-500/10 text-violet-600 dark:text-violet-400",
  "security.ghost_protocol_activated": "bg-violet-500/10 text-violet-600 dark:text-violet-400",
  "security.ghost_protocol_completed": "bg-violet-500/10 text-violet-600 dark:text-violet-400",
  // Settings
  "settings.update": "bg-purple-500/10 text-purple-600 dark:text-purple-400",
  "settings.configure": "bg-blue-500/10 text-blue-600 dark:text-blue-400",
  // Team
  "team.create": "bg-green-500/10 text-green-600 dark:text-green-400",
  "team.update": "bg-blue-500/10 text-blue-600 dark:text-blue-400",
  "team.member_invite": "bg-emerald-500/10 text-emerald-600 dark:text-emerald-400",
  "team.member_remove": "bg-amber-500/10 text-amber-600 dark:text-amber-400",
  "team.member_role_change": "bg-blue-500/10 text-blue-600 dark:text-blue-400",
  "team.member_status_change": "bg-amber-500/10 text-amber-600 dark:text-amber-400",
  "team.member_resend_invite": "bg-blue-500/10 text-blue-600 dark:text-blue-400",
  // Approval
  "approval.request": "bg-amber-500/10 text-amber-600 dark:text-amber-400",
  "approval.approve": "bg-green-500/10 text-green-600 dark:text-green-400",
  "approval.reject": "bg-red-500/10 text-red-600 dark:text-red-400",
  "approval.execute": "bg-green-500/10 text-green-600 dark:text-green-400",
  "approval.approval_requested": "bg-amber-500/10 text-amber-600 dark:text-amber-400",
  // Consent
  "consent.granted": "bg-indigo-500/10 text-indigo-600 dark:text-indigo-400",
  "consent.revoked": "bg-red-500/10 text-red-600 dark:text-red-400",
  "consent.updated": "bg-indigo-500/10 text-indigo-600 dark:text-indigo-400",
  // GDPR
  "gdpr.anonymization_requested": "bg-amber-500/10 text-amber-600 dark:text-amber-400",
  "gdpr.anonymization_completed": "bg-green-500/10 text-green-600 dark:text-green-400",
  "gdpr.data_export_requested": "bg-amber-500/10 text-amber-600 dark:text-amber-400",
  "gdpr.data_export_completed": "bg-green-500/10 text-green-600 dark:text-green-400",
  "gdpr.deletion_requested": "bg-amber-500/10 text-amber-600 dark:text-amber-400",
  "gdpr.deletion_completed": "bg-red-500/10 text-red-600 dark:text-red-400",
  // Compliance
  "compliance.audit_requested": "bg-amber-500/10 text-amber-600 dark:text-amber-400",
  "compliance.audit_completed": "bg-green-500/10 text-green-600 dark:text-green-400",
  // MCP
  "mcp.api_key_created": "bg-green-500/10 text-green-600 dark:text-green-400",
  "mcp.api_key_rotated": "bg-blue-500/10 text-blue-600 dark:text-blue-400",
  "mcp.api_key_revoked": "bg-red-500/10 text-red-600 dark:text-red-400",
  // Safety
  "safety.content_flagged": "bg-amber-500/10 text-amber-600 dark:text-amber-400",
  "safety.content_blocked": "bg-red-500/10 text-red-600 dark:text-red-400",
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
  const [isExporting, setIsExporting] = useState(false);
  const [page, setPage] = useState(0);

  // Filters
  const [actionFilter, setActionFilter] = useState<string>("all");
  const [resourceFilter, setResourceFilter] = useState<string>("all");
  const [dateRange, setDateRange] = useState<string>("7d");
  const [searchQuery, setSearchQuery] = useState("");
  const [debouncedSearch, setDebouncedSearch] = useState("");
  const deferredSearch = useDeferredValue(debouncedSearch);
  const debounceTimerRef = useRef<ReturnType<typeof setTimeout> | null>(null);

  // Available actions for filter (complete list matching backend)
  const availableActions = [
    { value: "all", label: "All Actions" },
    // Document
    { value: "document.create", label: "Document Create" },
    { value: "document.update", label: "Document Update" },
    { value: "document.delete", label: "Document Delete" },
    { value: "document.wipe", label: "Document Wipe" },
    // Chat
    { value: "chat.create", label: "Chat Create" },
    { value: "chat.delete", label: "Chat Delete" },
    // Connector
    { value: "connector.create", label: "Connector Create" },
    { value: "connector.update", label: "Connector Update" },
    { value: "connector.delete", label: "Connector Delete" },
    { value: "connector.connect", label: "Connector Connect" },
    { value: "connector.disconnect", label: "Connector Disconnect" },
    { value: "connector.sync_start", label: "Sync Started" },
    { value: "connector.sync_success", label: "Sync Success" },
    { value: "connector.sync_fail", label: "Sync Failed" },
    // Scope
    { value: "scope.create", label: "Scope Create" },
    { value: "scope.update", label: "Scope Update" },
    { value: "scope.delete", label: "Scope Delete" },
    { value: "scope.wipe", label: "Scope Wipe" },
    // Ingestion
    { value: "ingestion.queued", label: "Ingestion Queued" },
    { value: "ingestion.started", label: "Ingestion Started" },
    { value: "ingestion.completed", label: "Ingestion Completed" },
    { value: "ingestion.failed", label: "Ingestion Failed" },
    { value: "ingestion.skipped", label: "Ingestion Skipped" },
    { value: "ingestion.timeout", label: "Ingestion Timeout" },
    // Chunk / Org
    { value: "chunk.purge", label: "Chunk Purge" },
    { value: "organization.purge", label: "Organization Purge" },
    // Security / Ghost Protocol
    { value: "security.document_wiped", label: "Document Wiped" },
    { value: "security.scope_deleted", label: "Scope Deleted" },
    { value: "security.chunk_purged", label: "Chunk Purged" },
    { value: "security.organization_purged", label: "Org Purged" },
    { value: "security.ghost_protocol_activated", label: "Ghost Protocol Activated" },
    { value: "security.ghost_protocol_completed", label: "Ghost Protocol Completed" },
    // Settings
    { value: "settings.update", label: "Settings Update" },
    { value: "settings.configure", label: "Settings Configure" },
    // Team
    { value: "team.create", label: "Team Create" },
    { value: "team.update", label: "Team Update" },
    { value: "team.member_invite", label: "Team Invite" },
    { value: "team.member_remove", label: "Team Remove" },
    { value: "team.member_role_change", label: "Team Role Change" },
    { value: "team.member_status_change", label: "Team Status Change" },
    { value: "team.member_resend_invite", label: "Team Resend Invite" },
    // Approval
    { value: "approval.request", label: "Approval Request" },
    { value: "approval.approve", label: "Approval Approve" },
    { value: "approval.reject", label: "Approval Reject" },
    { value: "approval.execute", label: "Approval Execute" },
    { value: "approval.approval_requested", label: "Approval Requested" },
    // Consent
    { value: "consent.granted", label: "Consent Granted" },
    { value: "consent.revoked", label: "Consent Revoked" },
    { value: "consent.updated", label: "Consent Updated" },
    // GDPR
    { value: "gdpr.anonymization_requested", label: "GDPR Anonymization Requested" },
    { value: "gdpr.anonymization_completed", label: "GDPR Anonymization Completed" },
    { value: "gdpr.data_export_requested", label: "GDPR Export Requested" },
    { value: "gdpr.data_export_completed", label: "GDPR Export Completed" },
    { value: "gdpr.deletion_requested", label: "GDPR Deletion Requested" },
    { value: "gdpr.deletion_completed", label: "GDPR Deletion Completed" },
    // Compliance
    { value: "compliance.audit_requested", label: "Compliance Audit Requested" },
    { value: "compliance.audit_completed", label: "Compliance Audit Completed" },
    // MCP
    { value: "mcp.api_key_created", label: "MCP Key Created" },
    { value: "mcp.api_key_rotated", label: "MCP Key Rotated" },
    { value: "mcp.api_key_revoked", label: "MCP Key Revoked" },
    // Safety
    { value: "safety.content_flagged", label: "Content Flagged" },
    { value: "safety.content_blocked", label: "Content Blocked" },
  ];

  const resourceTypes = [
    { value: "all", label: "All Resources" },
    { value: "document", label: "Documents" },
    { value: "chat", label: "Chats" },
    { value: "connector", label: "Connectors" },
    { value: "user", label: "Users" },
    { value: "team", label: "Team" },
    { value: "scope", label: "Scopes" },
    { value: "settings", label: "Settings" },
    { value: "organization", label: "Organization" },
    { value: "mcp_api_key", label: "MCP API Keys" },
    { value: "mcp", label: "MCP" },
    { value: "ingestion_job", label: "Ingestion Jobs" },
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

  // Search debounce handler
  const handleSearchChange = useCallback((value: string) => {
    setSearchQuery(value);
    setPage(0);
    if (debounceTimerRef.current) {
      clearTimeout(debounceTimerRef.current);
    }
    debounceTimerRef.current = setTimeout(() => {
      setDebouncedSearch(value);
    }, 300);
  }, []);

  // Cleanup debounce timer
  useEffect(() => {
    return () => {
      if (debounceTimerRef.current) {
        clearTimeout(debounceTimerRef.current);
      }
    };
  }, []);

  // Filter change handlers that reset page
  const handleActionFilterChange = useCallback((value: string) => {
    setPage(0);
    setActionFilter(value);
  }, []);

  const handleResourceFilterChange = useCallback((value: string) => {
    setPage(0);
    setResourceFilter(value);
  }, []);

  const handleDateRangeChange = useCallback((value: string) => {
    setPage(0);
    setDateRange(value);
  }, []);

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
      if (deferredSearch) {
        params.set("search", deferredSearch);
      }

      const response = await api.get<AuditLogResponse>(
        `/admin/audit-logs?${params.toString()}`
      );
      setLogs(response.data.items);
      setTotal(response.data.total);
      setHasMore(response.data.has_more);
    } catch (error) {
      if (process.env.NODE_ENV !== 'production') {
        console.error("Failed to fetch audit logs:", error);
      }
      toast({
        title: "Error",
        description: "Failed to load audit logs. Please try again.",
        variant: "destructive",
      });
    } finally {
      setIsLoading(false);
      setIsRefreshing(false);
    }
  }, [page, actionFilter, resourceFilter, dateRange, deferredSearch, toast]);

  // Initial fetch and refetch on filter changes
  useEffect(() => {
    if (profile?.role === "admin") {
      fetchLogs();
    }
  }, [fetchLogs, profile?.role]);

  // Use server-filtered logs directly (no client-side filtering)
  const filteredLogs = logs;

  // Format action for display
  const formatAction = (action: string) => {
    return action.split(".").map((word) =>
      word.charAt(0).toUpperCase() + word.slice(1)
    ).join(" ");
  };

  // Export logs as CSV — fetches ALL matching events from API
  const exportLogs = async () => {
    setIsExporting(true);
    try {
      const params = new URLSearchParams();
      params.set("limit", "10000");
      params.set("offset", "0");

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
      if (deferredSearch) {
        params.set("search", deferredSearch);
      }

      const response = await api.get<AuditLogResponse>(
        `/admin/audit-logs?${params.toString()}`
      );
      const allLogs = response.data.items;

      const csvContent = [
        ["Timestamp", "User Name", "User Email", "Action", "Resource Type", "Resource ID", "Details", "IP Address"],
        ...allLogs.map((log) => [
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
      URL.revokeObjectURL(link.href);
    } catch (error) {
      if (process.env.NODE_ENV !== 'production') {
        console.error("Failed to export audit logs:", error);
      }
      toast({
        title: "Error",
        description: "Failed to export audit logs. Please try again.",
        variant: "destructive",
      });
    } finally {
      setIsExporting(false);
    }
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
              disabled={isExporting || total === 0}
            >
              {isExporting ? (
                <Loader2 className="h-4 w-4 mr-2 animate-spin" />
              ) : (
                <Download className="h-4 w-4 mr-2" />
              )}
              {isExporting ? "Exporting..." : "Export CSV"}
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
        onSearchChange={handleSearchChange}
      >
        <div className="flex flex-wrap gap-2">
          <Select value={actionFilter} onValueChange={handleActionFilterChange}>
            <SelectTrigger className="w-[200px]">
              <Filter className="h-4 w-4 mr-2" />
              <SelectValue placeholder="Action" />
            </SelectTrigger>
            <SelectContent className="max-h-[300px]">
              {availableActions.map((action) => (
                <SelectItem key={action.value} value={action.value}>
                  {action.label}
                </SelectItem>
              ))}
            </SelectContent>
          </Select>
          <Select value={resourceFilter} onValueChange={handleResourceFilterChange}>
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
          <Select value={dateRange} onValueChange={handleDateRangeChange}>
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

      {/* Summary Stats Card — only server-side total */}
      <div className="grid gap-4 grid-cols-1">
        <SettingsStatCard
          icon={ScrollText}
          iconColorClass="text-primary"
          iconBgClass="bg-primary/10"
          label="Total Matching Logs"
          value={total}
        />
      </div>
    </div>
  );
}
