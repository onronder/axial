
"use client";

import { useState, useEffect, useCallback, useRef } from "react";
import Link from "next/link";
import { cn } from "@/lib/utils";
import { UserPlus, Upload, MoreHorizontal, Users, Clock, Mail, UserCog, UserX, Send, Filter, Download, Lock, Sparkles, RefreshCw, AlertTriangle, Ban, UserCheck, FileDown } from "lucide-react";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { Badge } from "@/components/ui/badge";
import { Card, CardContent } from "@/components/ui/card";
import { SettingsPageHeader } from "@/components/settings/SettingsPageHeader";
import { SettingsToolbar } from "@/components/settings/SettingsToolbar";
import { SettingsStatCard } from "@/components/settings/SettingsStatCard";
import { SettingsEmptyState } from "@/components/settings/SettingsEmptyState";
import { SettingsPagination } from "@/components/settings/SettingsPagination";
import { Avatar, AvatarFallback } from "@/components/ui/avatar";
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogFooter,
  DialogHeader,
  DialogTitle,
  DialogTrigger,
} from "@/components/ui/dialog";
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "@/components/ui/select";
import {
  DropdownMenu,
  DropdownMenuContent,
  DropdownMenuItem,
  DropdownMenuSeparator,
  DropdownMenuTrigger,
} from "@/components/ui/dropdown-menu";
import {
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from "@/components/ui/table";
import {
  Tooltip,
  TooltipContent,
  TooltipProvider,
  TooltipTrigger,
} from "@/components/ui/tooltip";
import { Alert, AlertDescription, AlertTitle } from "@/components/ui/alert";
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
import { formatDistanceToNow } from "date-fns";
import { useTeamMembers, Role, MemberStatus, TeamMember } from "@/hooks/useTeamMembers";
import { useProfile } from "@/hooks/useProfile";
import { useUsage } from "@/hooks/useUsage";
import { api, bulkInvite } from "@/lib/api";
import { useToast } from "@/hooks/use-toast";
import { Spinner } from "@/components/ui/spinner";

// Email validation regex - requires at least 2 chars in TLD (Bug 14: moved to module scope)
const EMAIL_REGEX = /^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$/;

const statusStyles: Record<MemberStatus, { label: string; className: string }> = {
  active: { label: "Active", className: "bg-success/10 text-success border-success/20" },
  pending: { label: "Pending", className: "bg-warning/10 text-warning border-warning/20" },
  suspended: { label: "Suspended", className: "bg-destructive/10 text-destructive border-destructive/20" },
};

export function TeamSettings() {
  const { toast } = useToast();
  const { teamEnabled, plan, isLoading: usageLoading } = useUsage();
  const { profile, isLoading: profileLoading } = useProfile();

  const {
    members,
    stats,
    total,
    isLoading,
    error,
    inviteMember,
    updateMemberRole,
    updateMemberStatus,
    removeMember,
    resendInvite,
    refresh: refreshMembers,
  } = useTeamMembers();

  const [inviteDialogOpen, setInviteDialogOpen] = useState(false);
  const [inviteEmail, setInviteEmail] = useState("");
  const [inviteRole, setInviteRole] = useState<Role>("viewer");
  const [isInviting, setIsInviting] = useState(false);

  const [emailError, setEmailError] = useState<string | null>(null);
  
  const validateEmail = (email: string): string | null => {
    if (!email.trim()) return null; // Don't show error for empty
    if (!EMAIL_REGEX.test(email.trim())) {
      return 'Please enter a valid email address';
    }
    return null;
  };
  
  const handleEmailChange = (value: string) => {
    setInviteEmail(value);
    setEmailError(validateEmail(value));
  };
  
  const isEmailValid = inviteEmail.trim() !== '' && !emailError;

  // Bulk CSV import state
  const [bulkDialogOpen, setBulkDialogOpen] = useState(false);
  const [isBulkImporting, setIsBulkImporting] = useState(false);
  const [bulkFile, setBulkFile] = useState<File | null>(null);

  // Search and filter state
  const [searchQuery, setSearchQuery] = useState("");
  const [roleFilter, setRoleFilter] = useState<Role | "all">("all");
  const [statusFilter, setStatusFilter] = useState<MemberStatus | "all">("all");

  // Edit role modal state
  const [editRoleDialogOpen, setEditRoleDialogOpen] = useState(false);
  const [editingMember, setEditingMember] = useState<TeamMember | null>(null);
  const [selectedRole, setSelectedRole] = useState<Role>("viewer");

  // Revoke access confirmation state (Bug 4)
  const [revokeTargetId, setRevokeTargetId] = useState<string | null>(null);
  const revokeTargetMember = members.find(m => m.id === revokeTargetId);

  // Admin promotion confirmation state (Bug 11)
  const [pendingPromotion, setPendingPromotion] = useState<{ memberId: string; email: string } | null>(null);

  // Pagination state
  const [currentPage, setCurrentPage] = useState(1);
  const [pageSize, setPageSize] = useState(10);
  const PAGE_SIZE_OPTIONS = [5, 10, 25, 50];

  // Debounce timer ref for search
  const searchTimerRef = useRef<ReturnType<typeof setTimeout> | null>(null);

  // CSV Template data URI
  const CSV_TEMPLATE = "data:text/csv;charset=utf-8,email,role,name%0Aalice%40example.com,editor,Alice%0Abob%40example.com,viewer,Bob";

  const role = profile?.role;
  const isTeamMember = !!role;
  const isViewer = role === "viewer";
  const isAdmin = role === "admin" || !isTeamMember; // treat solo owners as admin
  const canManageMembers = teamEnabled && isAdmin && !isViewer;
  const managementLockedReason = !teamEnabled
    ? `Team management is locked on your ${plan || "current"} plan. Upgrade to enable invites and role changes.`
    : isViewer
      ? "View-only members cannot invite or modify teammates."
      : !isAdmin
        ? "Only team admins can manage members."
        : null;

  const ensureCanManage = (action: string) => {
    if (!canManageMembers) {
      toast({
        title: "Action blocked",
        description: managementLockedReason || `You don't have permission to ${action}.`,
        variant: "destructive",
      });
      return false;
    }
    return true;
  };

  // Helper function to check if a member is the last admin
  const isLastAdmin = (memberId: string): boolean => {
    const activeAdmins = members.filter(m => m.role === 'admin' && m.status === 'active');
    return activeAdmins.length === 1 && activeAdmins[0].id === memberId;
  };

  // Handle bulk CSV upload
  const handleBulkImport = async () => {
    if (!ensureCanManage("import team members")) return;

    if (!bulkFile) return;

    setIsBulkImporting(true);
    try {
      const result = await bulkInvite(bulkFile);

      if (result.success) {
        toast({
          title: "Bulk import complete",
          description: `${result.invited} member(s) invited successfully. ${result.failed} failed.`,
        });
        refreshMembers();
        setBulkDialogOpen(false);
        setBulkFile(null);
      } else {
        toast({
          title: "Import failed",
          description: result.errors?.[0]?.error || "Unknown error",
          variant: "destructive",
        });
      }
    } catch (error: unknown) {
      const message = error instanceof Error ? error.message : "Upload failed";
      toast({
        title: "Import error",
        description: message,
        variant: "destructive",
      });
    } finally {
      setIsBulkImporting(false);
    }
  };

  const handleFileChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    const file = e.target.files?.[0];
    if (file) {
      setBulkFile(file);
    }
  };

  // Server-side pagination: total pages computed from API total
  const totalPages = Math.ceil(total / pageSize);

  // Fetch members from server when filters/pagination change
  const fetchWithCurrentParams = useCallback(() => {
    const offset = (currentPage - 1) * pageSize;
    refreshMembers(
      { role: roleFilter, status: statusFilter, search: searchQuery },
      pageSize,
      offset,
    );
  }, [refreshMembers, currentPage, pageSize, roleFilter, statusFilter, searchQuery]);

  useEffect(() => {
    fetchWithCurrentParams();
  }, [fetchWithCurrentParams]);

  const handleInvite = async () => {
    if (!ensureCanManage("invite team members")) return;

    if (!inviteEmail.trim() || !isEmailValid) return;

    setIsInviting(true);
    const success = await inviteMember(inviteEmail, inviteRole);
    setIsInviting(false);

    if (success) {
      setInviteEmail("");
      setInviteRole("viewer");
      setInviteDialogOpen(false);
    }
  };

  const openEditRoleDialog = (member: TeamMember) => {
    if (!ensureCanManage("edit team roles")) return;
    setEditingMember(member);
    setSelectedRole(member.role);
    setEditRoleDialogOpen(true);
  };

  const handleSaveRole = async () => {
    if (!ensureCanManage("edit team roles")) return;
    if (editingMember) {
      await updateMemberRole(editingMember.id, selectedRole);
    }
    setEditRoleDialogOpen(false);
    setEditingMember(null);
  };

  const handleRevokeAccess = (memberId: string) => {
    if (!ensureCanManage("remove team members")) return;
    setRevokeTargetId(memberId);
  };

  const confirmRevokeAccess = async () => {
    if (revokeTargetId) {
      await removeMember(revokeTargetId);
      setRevokeTargetId(null);
    }
  };

  const handleResendInvite = async (member: TeamMember) => {
    if (!ensureCanManage("resend invitations")) return;
    await resendInvite(member.id, member.email);
  };

  const formatDate = (dateString: string | null) => {
    if (!dateString) return "Never";
    return new Date(dateString).toLocaleDateString("en-US", {
      month: "short",
      day: "numeric",
      year: "numeric",
    });
  };

  const clearFilters = () => {
    setSearchQuery("");
    setRoleFilter("all");
    setStatusFilter("all");
    setCurrentPage(1);
  };

  const handleSearchChange = (value: string) => {
    setSearchQuery(value);
    setCurrentPage(1);
    // Debounce the API call for search (300ms)
    if (searchTimerRef.current) clearTimeout(searchTimerRef.current);
    searchTimerRef.current = setTimeout(() => {
      refreshMembers(
        { role: roleFilter, status: statusFilter, search: value },
        pageSize,
        0,
      );
    }, 300);
  };

  const handleRoleFilterChange = (value: Role | "all") => {
    setRoleFilter(value);
    setCurrentPage(1);
  };

  const handleStatusFilterChange = (value: MemberStatus | "all") => {
    setStatusFilter(value);
    setCurrentPage(1);
  };

  const hasActiveFilters = searchQuery || roleFilter !== "all" || statusFilter !== "all";

  // CSV export handler (Bug 8)
  const handleExportCSV = async () => {
    try {
      const { data } = await api.get('/team/members', { params: { limit: '10000', offset: '0' } });
      const allMembers = data.items || [];
      const escapeCSV = (field: string) => `"${String(field).replace(/"/g, '""')}"`;
      const header = ["name","email","role","status","last_active","created_at"].map(escapeCSV).join(",");
      const rows = allMembers.map((m: TeamMember) =>
        [m.name || "", m.email, m.role, m.status, m.last_active || "", m.created_at].map(escapeCSV).join(",")
      );
      const csv = [header, ...rows].join("\n");
      const blob = new Blob([csv], { type: "text/csv;charset=utf-8;" });
      const url = URL.createObjectURL(blob);
      const link = document.createElement("a");
      link.href = url;
      link.download = `team-members-${new Date().toISOString().slice(0, 10)}.csv`;
      document.body.appendChild(link);
      link.click();
      document.body.removeChild(link);
      URL.revokeObjectURL(url);
      toast({ title: "Export complete", description: `Exported ${allMembers.length} members to CSV.` });
    } catch {
      toast({ title: "Export failed", description: "Failed to export team members.", variant: "destructive" });
    }
  };

  // Suspend/Reactivate handler (Bug 10)
  const handleSuspendMember = async (memberId: string) => {
    if (!ensureCanManage("suspend members")) return;
    const success = await updateMemberStatus(memberId, "suspended");
    if (success) {
      toast({ title: "Member suspended", description: "The member has been suspended." });
    }
  };

  const handleReactivateMember = async (memberId: string) => {
    if (!ensureCanManage("reactivate members")) return;
    const success = await updateMemberStatus(memberId, "active");
    if (success) {
      toast({ title: "Member reactivated", description: "The member has been reactivated." });
    }
  };

  const getAvatarInitials = (member: TeamMember) => {
    if (member.name) {
      return member.name.slice(0, 2).toUpperCase();
    }
    return member.email.slice(0, 2).toUpperCase();
  };

  if (isLoading || profileLoading || usageLoading) {
    return (
      <div className="flex items-center justify-center py-12">
        <Spinner className="h-8 w-8 animate-spin text-muted-foreground" />
      </div>
    );
  }

  if (error) {
    return (
      <div className="space-y-6">
        <SettingsPageHeader
          icon={Users}
          title="Team Members"
          description="Manage access and roles for your organization"
        />
        <Alert variant="destructive">
          <AlertTriangle className="h-4 w-4" />
          <AlertTitle>Failed to load team members</AlertTitle>
          <AlertDescription className="flex items-center justify-between">
            <span>{error}</span>
            <Button variant="outline" size="sm" onClick={() => fetchWithCurrentParams()}>
              Try Again
            </Button>
          </AlertDescription>
        </Alert>
      </div>
    );
  }

  return (
    <div className="space-y-6">
      <SettingsPageHeader
        icon={Users}
        title="Team Members"
        description="Manage access and roles for your organization"
        actions={
          <div className="flex flex-wrap gap-3">
            <TooltipProvider>
              <Tooltip>
                <TooltipTrigger asChild>
                  <Button variant="outline" size="icon" onClick={() => fetchWithCurrentParams()}>
                    <RefreshCw className="h-4 w-4" />
                  </Button>
                </TooltipTrigger>
                <TooltipContent><p>Refresh members</p></TooltipContent>
              </Tooltip>
            </TooltipProvider>
            <Button variant="outline" className="gap-2" onClick={handleExportCSV}>
              <FileDown className="h-4 w-4" />
              Export CSV
            </Button>
            <Dialog open={inviteDialogOpen} onOpenChange={setInviteDialogOpen}>
              <DialogTrigger asChild>
                <Button
                  className="gap-2"
                  disabled={!canManageMembers}
                  title={!canManageMembers ? managementLockedReason ?? "Team management locked" : undefined}
                >
                  <UserPlus className="h-4 w-4" />
                  Invite Member
                </Button>
              </DialogTrigger>
              <DialogContent>
                <DialogHeader>
                  <DialogTitle>Invite Team Member</DialogTitle>
                  <DialogDescription>
                    Send an invitation to join your organization
                  </DialogDescription>
                </DialogHeader>
                <div className="space-y-4 py-4">
                  <div className="space-y-2">
                    <Label htmlFor="invite-email">Email Address</Label>
                    <Input
                      id="invite-email"
                      type="email"
                      placeholder="colleague@company.com"
                      value={inviteEmail}
                      onChange={(e) => handleEmailChange(e.target.value)}
                      className={cn(emailError && "border-destructive")}
                    />
                    {emailError && (
                      <p className="text-xs text-destructive">{emailError}</p>
                    )}
                  </div>
                  <div className="space-y-2">
                    <Label htmlFor="invite-role">Role</Label>
                    <Select value={inviteRole} onValueChange={(v) => setInviteRole(v as Role)}>
                      <SelectTrigger id="invite-role">
                        <SelectValue />
                      </SelectTrigger>
                      <SelectContent>
                        <SelectItem value="admin">Admin</SelectItem>
                        <SelectItem value="editor">Editor</SelectItem>
                        <SelectItem value="viewer">Viewer</SelectItem>
                      </SelectContent>
                    </Select>
                  </div>
                </div>
                <DialogFooter>
                  <Button variant="outline" onClick={() => setInviteDialogOpen(false)}>
                    Cancel
                  </Button>
                  <Button
                    onClick={handleInvite}
                    className="gap-2"
                    disabled={isInviting || !inviteEmail.trim() || !isEmailValid || !canManageMembers}
                  >
                    {isInviting ? (
                      <Spinner className="h-4 w-4 animate-spin" />
                    ) : (
                      <Send className="h-4 w-4" />
                    )}
                    Send Invitation
                  </Button>
                </DialogFooter>
              </DialogContent>
            </Dialog>

            <Dialog open={bulkDialogOpen} onOpenChange={setBulkDialogOpen}>
              <DialogTrigger asChild>
                <TooltipProvider>
                  <Tooltip>
                    <TooltipTrigger asChild>
                      <Button
                        variant="outline"
                        className="gap-2"
                        disabled={!canManageMembers}
                        title={!canManageMembers ? managementLockedReason ?? "Team management locked" : undefined}
                      >
                        <Upload className="h-4 w-4" />
                        Bulk Import
                      </Button>
                    </TooltipTrigger>
                    <TooltipContent>
                      <p>{canManageMembers ? "Upload a CSV list for large teams" : managementLockedReason || "Team management locked"}</p>
                    </TooltipContent>
                  </Tooltip>
                </TooltipProvider>
              </DialogTrigger>
              <DialogContent>
                <DialogHeader>
                  <DialogTitle>Bulk Import Team Members</DialogTitle>
                  <DialogDescription>
                    Upload a CSV file to invite multiple members at once
                  </DialogDescription>
                </DialogHeader>
                <div className="space-y-4 py-4">
                  <div className="space-y-2">
                    <Label htmlFor="csv-file">CSV File</Label>
                    <Input
                      id="csv-file"
                      type="file"
                      accept=".csv"
                      onChange={handleFileChange}
                      className="cursor-pointer"
                      disabled={!canManageMembers}
                    />
                    {bulkFile && (
                      <p className="text-sm text-muted-foreground">
                        Selected: {bulkFile.name}
                      </p>
                    )}
                  </div>
                  <div className="text-sm text-muted-foreground">
                    <p className="mb-2">Expected format:</p>
                    <code className="block bg-muted p-2 rounded text-xs">
                      email,role,name<br />
                      alice@example.com,editor,Alice<br />
                      bob@example.com,viewer,Bob
                    </code>
                  </div>
                  <p className="text-xs text-muted-foreground">Maximum file size: 1MB</p>
                  <a
                    href={CSV_TEMPLATE}
                    download="team_invite_template.csv"
                    className="inline-flex items-center gap-1 text-sm text-primary hover:underline"
                  >
                    <Download className="h-3 w-3" />
                    Download CSV Template
                  </a>
                </div>
                <DialogFooter>
                  <Button variant="outline" onClick={() => setBulkDialogOpen(false)}>
                    Cancel
                  </Button>
                  <Button
                    onClick={handleBulkImport}
                    className="gap-2"
                    disabled={!bulkFile || isBulkImporting || !canManageMembers}
                  >
                    {isBulkImporting ? (
                      <Spinner className="h-4 w-4 animate-spin" />
                    ) : (
                      <Upload className="h-4 w-4" />
                    )}
                    Import Members
                  </Button>
                </DialogFooter>
              </DialogContent>
            </Dialog>
          </div>
        }
      />

      {/* Enterprise Upgrade Banner - shows when team features are disabled */}
      {!teamEnabled && (
        <Card className="relative overflow-hidden border-primary/30 bg-gradient-to-r from-primary/5 via-transparent to-accent/5">
          <CardContent className="flex items-center justify-between p-6">
            <div className="flex items-center gap-4">
              <div className="flex h-12 w-12 items-center justify-center rounded-lg bg-primary/10">
                <Lock className="h-6 w-6 text-primary" />
              </div>
              <div>
                <h3 className="font-semibold text-foreground flex items-center gap-2">
                  <Sparkles className="h-4 w-4 text-primary" />
                  Upgrade to Enterprise for Team Features
                </h3>
                <p className="text-sm text-muted-foreground">
                  Your current plan ({plan}) doesn&apos;t include team management. Upgrade to invite team members and collaborate.
                </p>
              </div>
            </div>
            <Link href="/dashboard/settings/billing">
              <Button className="gap-2 shrink-0">
                <Sparkles className="h-4 w-4" />
                Upgrade Now
              </Button>
            </Link>
          </CardContent>
        </Card>
      )}

      {managementLockedReason && teamEnabled && (
        <Alert className="border-amber-400/40 bg-amber-500/5">
          <AlertTitle className="flex items-center gap-2">
            <Lock className="h-4 w-4 text-amber-400" />
            Team access restricted
          </AlertTitle>
          <AlertDescription className="text-sm text-amber-100">
            {managementLockedReason}
          </AlertDescription>
        </Alert>
      )}

      {/* Stats Cards */}
      <div className="grid gap-4 grid-cols-2 md:grid-cols-4">
        <SettingsStatCard
          icon={Users}
          iconColorClass="text-primary"
          iconBgClass="bg-primary/10"
          label="Total Seats"
          value={<>{stats.active_members + stats.pending_invites}<span className="text-muted-foreground text-lg">/{stats.total_seats}</span></>}
        />
        <SettingsStatCard
          icon={Clock}
          iconColorClass="text-success"
          iconBgClass="bg-success/10"
          label="Active Members"
          value={stats.active_members}
        />
        <SettingsStatCard
          icon={Mail}
          iconColorClass="text-warning"
          iconBgClass="bg-warning/10"
          label="Pending Invites"
          value={stats.pending_invites}
        />
        <SettingsStatCard
          icon={Ban}
          iconColorClass="text-destructive"
          iconBgClass="bg-destructive/10"
          label="Suspended"
          value={stats.suspended_members}
        />
      </div>

      {/* Search and Filter */}
      <SettingsToolbar
        searchPlaceholder="Search by name or email..."
        searchValue={searchQuery}
        onSearchChange={handleSearchChange}
      >
        <div className="flex gap-2">
          <Select value={roleFilter} onValueChange={handleRoleFilterChange}>
            <SelectTrigger className="w-[130px]">
              <Filter className="mr-2 h-4 w-4" />
              <SelectValue placeholder="Role" />
            </SelectTrigger>
            <SelectContent>
              <SelectItem value="all">All Roles</SelectItem>
              <SelectItem value="admin">Admin</SelectItem>
              <SelectItem value="editor">Editor</SelectItem>
              <SelectItem value="viewer">Viewer</SelectItem>
            </SelectContent>
          </Select>
          <Select value={statusFilter} onValueChange={handleStatusFilterChange}>
            <SelectTrigger className="w-[140px]">
              <SelectValue placeholder="Status" />
            </SelectTrigger>
            <SelectContent>
              <SelectItem value="all">All Status</SelectItem>
              <SelectItem value="active">Active</SelectItem>
              <SelectItem value="pending">Pending</SelectItem>
              <SelectItem value="suspended">Suspended</SelectItem>
            </SelectContent>
          </Select>
          {hasActiveFilters && (
            <Button variant="ghost" size="sm" onClick={clearFilters}>
              Clear
            </Button>
          )}
        </div>
      </SettingsToolbar>

      {/* Members Table */}
      <div className="rounded-lg border border-border">
        <Table>
          <TableHeader>
            <TableRow>
              <TableHead>User</TableHead>
              <TableHead className="w-28">Role</TableHead>
              <TableHead className="w-28">Status</TableHead>
              <TableHead className="w-32">Last Active</TableHead>
              <TableHead className="w-16"></TableHead>
            </TableRow>
          </TableHeader>
          <TableBody>
            {members.length === 0 ? (
              <TableRow>
                <TableCell colSpan={5} className="h-40 text-center">
                  <SettingsEmptyState
                    icon={Users}
                    title={total === 0 && !hasActiveFilters ? "No team members yet" : "No members match your filters"}
                    description={
                      total === 0 && !hasActiveFilters
                        ? "You haven't invited anyone yet. Start collaborating by adding your team."
                        : "Try adjusting your search or filter criteria."
                    }
                    action={
                      hasActiveFilters ? (
                        <Button variant="outline" size="sm" onClick={clearFilters}>
                          Clear Filters
                        </Button>
                      ) : undefined
                    }
                    className="py-4"
                  />
                </TableCell>
              </TableRow>
            ) : (
              members.map((member) => {
                const statusStyle = statusStyles[member.status];
                return (
                  <TableRow key={member.id}>
                    <TableCell>
                      <div className="flex items-center gap-3">
                        <Avatar className="h-8 w-8">
                          <AvatarFallback className="bg-primary/10 text-primary text-xs">
                            {getAvatarInitials(member)}
                          </AvatarFallback>
                        </Avatar>
                        <div>
                          <p className="font-medium">{member.name || member.email.split("@")[0]}</p>
                          <p className="text-sm text-muted-foreground">{member.email}</p>
                        </div>
                      </div>
                    </TableCell>
                    <TableCell>
                      <div className="flex items-center gap-2">
                        <Select
                          value={member.role}
                          onValueChange={(value) => {
                            if (!ensureCanManage("change roles")) return;
                            // Bug 11: Confirm before promoting to admin
                            if (value === "admin" && member.role !== "admin") {
                              setPendingPromotion({ memberId: member.id, email: member.email });
                              return;
                            }
                            updateMemberRole(member.id, value as Role);
                          }}
                          disabled={!canManageMembers || isLastAdmin(member.id)}
                        >
                          <SelectTrigger className="w-[110px] h-8">
                            <SelectValue />
                          </SelectTrigger>
                          <SelectContent>
                            <SelectItem value="admin">Admin</SelectItem>
                            <SelectItem value="editor">Editor</SelectItem>
                            <SelectItem value="viewer">Viewer</SelectItem>
                          </SelectContent>
                        </Select>
                        {isLastAdmin(member.id) && (
                          <TooltipProvider>
                            <Tooltip>
                              <TooltipTrigger asChild>
                                <Lock className="h-4 w-4 text-muted-foreground cursor-help" />
                              </TooltipTrigger>
                              <TooltipContent>
                                <p>Cannot change role of the last admin</p>
                              </TooltipContent>
                            </Tooltip>
                          </TooltipProvider>
                        )}
                      </div>
                    </TableCell>
                    <TableCell>
                      <div className="flex items-center gap-1">
                        <Badge variant="outline" className={statusStyle.className}>
                          {statusStyle.label}
                        </Badge>
                        {member.status === "pending" && member.expires_at && (
                          <span className="text-xs text-muted-foreground">
                            (expires {formatDistanceToNow(new Date(member.expires_at), { addSuffix: true })})
                          </span>
                        )}
                      </div>
                    </TableCell>
                    <TableCell className="text-muted-foreground">
                      {formatDate(member.last_active)}
                    </TableCell>
                    <TableCell>
                      <DropdownMenu>
                        <DropdownMenuTrigger asChild>
                          <Button
                            variant="ghost"
                            size="icon"
                            className="h-8 w-8"
                            disabled={!canManageMembers}
                            title={!canManageMembers ? managementLockedReason ?? "Team management locked" : undefined}
                          >
                            <MoreHorizontal className="h-4 w-4" />
                          </Button>
                        </DropdownMenuTrigger>
                        <DropdownMenuContent align="end" className="bg-popover">
                          <DropdownMenuItem
                            onClick={() => openEditRoleDialog(member)}
                            disabled={!canManageMembers}
                          >
                            <UserCog className="mr-2 h-4 w-4" />
                            Edit Role
                          </DropdownMenuItem>
                          {member.status === "pending" && (
                            <DropdownMenuItem
                              onClick={() => handleResendInvite(member)}
                              disabled={!canManageMembers}
                            >
                              <Send className="mr-2 h-4 w-4" />
                              Resend Invite
                            </DropdownMenuItem>
                          )}
                          {/* Bug 10: Suspend/Reactivate actions */}
                          {member.status === "active" && (
                            <DropdownMenuItem
                              onClick={() => handleSuspendMember(member.id)}
                              disabled={!canManageMembers || isLastAdmin(member.id)}
                            >
                              <Ban className="mr-2 h-4 w-4" />
                              Suspend Member
                            </DropdownMenuItem>
                          )}
                          {member.status === "suspended" && (
                            <DropdownMenuItem
                              onClick={() => handleReactivateMember(member.id)}
                              disabled={!canManageMembers}
                            >
                              <UserCheck className="mr-2 h-4 w-4" />
                              Reactivate
                            </DropdownMenuItem>
                          )}
                          <DropdownMenuSeparator />
                          <DropdownMenuItem
                            onClick={() => handleRevokeAccess(member.id)}
                            className="text-destructive focus:text-destructive"
                            disabled={!canManageMembers}
                          >
                            <UserX className="mr-2 h-4 w-4" />
                            Revoke Access
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

      {/* Pagination */}
      {total > 0 && (
        <SettingsPagination
          currentPage={currentPage}
          totalPages={totalPages}
          pageSize={pageSize}
          totalItems={total}
          onPageChange={setCurrentPage}
          onPageSizeChange={(size) => {
            setPageSize(size);
            setCurrentPage(1);
          }}
          pageSizeOptions={PAGE_SIZE_OPTIONS}
          itemLabel="member"
        />
      )}

      {/* Edit Role Dialog */}
      <Dialog open={editRoleDialogOpen} onOpenChange={setEditRoleDialogOpen}>
        <DialogContent>
          <DialogHeader>
            <DialogTitle>Edit Role</DialogTitle>
            <DialogDescription>
              Change the role for {editingMember?.name || editingMember?.email}
            </DialogDescription>
          </DialogHeader>
          <div className="py-4">
            <div className="flex items-center gap-3 mb-4 p-3 rounded-lg bg-muted/50">
              <Avatar className="h-10 w-10">
                <AvatarFallback className="bg-primary/10 text-primary">
                  {editingMember ? getAvatarInitials(editingMember) : ""}
                </AvatarFallback>
              </Avatar>
              <div>
                <p className="font-medium">{editingMember?.name || editingMember?.email?.split("@")[0]}</p>
                <p className="text-sm text-muted-foreground">{editingMember?.email}</p>
              </div>
            </div>
            <div className="space-y-2">
              <Label htmlFor="edit-role">New Role</Label>
              <Select
                value={selectedRole}
                onValueChange={(v) => setSelectedRole(v as Role)}
                disabled={!canManageMembers}
              >
                <SelectTrigger id="edit-role">
                  <SelectValue />
                </SelectTrigger>
                <SelectContent>
                  <SelectItem value="admin">
                    <div className="flex flex-col">
                      <span>Admin</span>
                      <span className="text-xs text-muted-foreground">Full access to all settings</span>
                    </div>
                  </SelectItem>
                  <SelectItem value="editor">
                    <div className="flex flex-col">
                      <span>Editor</span>
                      <span className="text-xs text-muted-foreground">Can edit content and data</span>
                    </div>
                  </SelectItem>
                  <SelectItem value="viewer">
                    <div className="flex flex-col">
                      <span>Viewer</span>
                      <span className="text-xs text-muted-foreground">Read-only access</span>
                    </div>
                  </SelectItem>
                </SelectContent>
              </Select>
            </div>
          </div>
          <DialogFooter>
            <Button variant="outline" onClick={() => setEditRoleDialogOpen(false)}>
              Cancel
            </Button>
            <Button onClick={handleSaveRole} disabled={!canManageMembers}>
              Save Changes
            </Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>

      {/* Revoke Access Confirmation Dialog (Bug 4) */}
      <AlertDialog open={!!revokeTargetId} onOpenChange={(open) => !open && setRevokeTargetId(null)}>
        <AlertDialogContent>
          <AlertDialogHeader>
            <AlertDialogTitle>Revoke Access</AlertDialogTitle>
            <AlertDialogDescription>
              Are you sure you want to remove{" "}
              <strong>{revokeTargetMember?.name || revokeTargetMember?.email}</strong> from the team?
              This will revoke access for this member.
            </AlertDialogDescription>
          </AlertDialogHeader>
          <AlertDialogFooter>
            <AlertDialogCancel>Cancel</AlertDialogCancel>
            <AlertDialogAction
              onClick={confirmRevokeAccess}
              className="bg-destructive text-destructive-foreground hover:bg-destructive/90"
            >
              Revoke Access
            </AlertDialogAction>
          </AlertDialogFooter>
        </AlertDialogContent>
      </AlertDialog>

      {/* Admin Promotion Confirmation Dialog (Bug 11) */}
      <AlertDialog open={!!pendingPromotion} onOpenChange={(open) => !open && setPendingPromotion(null)}>
        <AlertDialogContent>
          <AlertDialogHeader>
            <AlertDialogTitle>Promote to Admin</AlertDialogTitle>
            <AlertDialogDescription>
              Are you sure you want to promote{" "}
              <strong>{pendingPromotion?.email}</strong> to Admin?
              Admins have full access to all team settings, member management, and billing.
            </AlertDialogDescription>
          </AlertDialogHeader>
          <AlertDialogFooter>
            <AlertDialogCancel>Cancel</AlertDialogCancel>
            <AlertDialogAction
              onClick={async () => {
                if (pendingPromotion) {
                  await updateMemberRole(pendingPromotion.memberId, "admin");
                  setPendingPromotion(null);
                }
              }}
            >
              Promote to Admin
            </AlertDialogAction>
          </AlertDialogFooter>
        </AlertDialogContent>
      </AlertDialog>
    </div>
  );
}