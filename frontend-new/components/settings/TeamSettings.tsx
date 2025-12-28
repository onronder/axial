"use client";

import { useState, useMemo } from "react";
import Link from "next/link";
import {
  UserPlus,
  Upload,
  MoreHorizontal,
  Users,
  Clock,
  Mail,
  UserCog,
  UserX,
  Send,
  Search,
  Filter,
  ChevronLeft,
  ChevronRight,
  Loader2,
  Download,
  Lock,
  Sparkles,
} from "lucide-react";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { Badge } from "@/components/ui/badge";
import { Card, CardContent } from "@/components/ui/card";
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
  TooltipTrigger,
} from "@/components/ui/tooltip";
import { useTeamMembers, Role, MemberStatus, TeamMember } from "@/hooks/useTeamMembers";
import { useUsage } from "@/hooks/useUsage";
import { bulkInvite } from "@/lib/api";
import { useToast } from "@/hooks/use-toast";

const roleStyles: Record<Role, string> = {
  admin: "bg-accent/10 text-accent border-accent/20",
  editor: "bg-primary/10 text-primary border-primary/20",
  viewer: "bg-muted text-muted-foreground border-border",
};

const statusStyles: Record<MemberStatus, { label: string; className: string }> = {
  active: { label: "Active", className: "bg-success/10 text-success border-success/20" },
  pending: { label: "Pending", className: "bg-warning/10 text-warning border-warning/20" },
  suspended: { label: "Suspended", className: "bg-destructive/10 text-destructive border-destructive/20" },
};

export function TeamSettings() {
  const { toast } = useToast();
  const { teamEnabled, plan } = useUsage();

  const {
    members,
    stats,
    isLoading,
    inviteMember,
    updateMemberRole,
    removeMember,
    resendInvite,
    refresh: refreshMembers,
  } = useTeamMembers();

  const [inviteDialogOpen, setInviteDialogOpen] = useState(false);
  const [inviteEmail, setInviteEmail] = useState("");
  const [inviteRole, setInviteRole] = useState<Role>("viewer");
  const [isInviting, setIsInviting] = useState(false);

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

  // Pagination state
  const [currentPage, setCurrentPage] = useState(1);
  const [pageSize, setPageSize] = useState(10);
  const PAGE_SIZE_OPTIONS = [5, 10, 25, 50];

  // CSV Template data URI
  const CSV_TEMPLATE = "data:text/csv;charset=utf-8,email,role,name%0Aalice%40example.com,editor,Alice%0Abob%40example.com,viewer,Bob";

  // Handle bulk CSV upload
  const handleBulkImport = async () => {
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

  // Filtered members (client-side filtering for immediate responsiveness)
  const filteredMembers = useMemo(() => {
    return members.filter((member) => {
      const matchesSearch =
        (member.name?.toLowerCase() || "").includes(searchQuery.toLowerCase()) ||
        member.email.toLowerCase().includes(searchQuery.toLowerCase());
      const matchesRole = roleFilter === "all" || member.role === roleFilter;
      const matchesStatus = statusFilter === "all" || member.status === statusFilter;
      return matchesSearch && matchesRole && matchesStatus;
    });
  }, [members, searchQuery, roleFilter, statusFilter]);

  // Pagination
  const totalPages = Math.ceil(filteredMembers.length / pageSize);
  const paginatedMembers = useMemo(() => {
    const start = (currentPage - 1) * pageSize;
    return filteredMembers.slice(start, start + pageSize);
  }, [filteredMembers, currentPage, pageSize]);

  const handleInvite = async () => {
    if (!inviteEmail.trim()) return;

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
    setEditingMember(member);
    setSelectedRole(member.role);
    setEditRoleDialogOpen(true);
  };

  const handleSaveRole = async () => {
    if (editingMember) {
      await updateMemberRole(editingMember.id, selectedRole);
    }
    setEditRoleDialogOpen(false);
    setEditingMember(null);
  };

  const handleRevokeAccess = async (memberId: string) => {
    await removeMember(memberId);
  };

  const handleResendInvite = async (member: TeamMember) => {
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

  const getAvatarInitials = (member: TeamMember) => {
    if (member.name) {
      return member.name.slice(0, 2).toUpperCase();
    }
    return member.email.slice(0, 2).toUpperCase();
  };

  if (isLoading) {
    return (
      <div className="flex items-center justify-center py-12">
        <Loader2 className="h-8 w-8 animate-spin text-muted-foreground" />
      </div>
    );
  }

  return (
    <div className="space-y-6">
      {/* Header */}
      <div>
        <h1 className="font-display text-2xl font-bold text-foreground">Team Management</h1>
        <p className="mt-1 text-muted-foreground">
          Manage access and roles for your organization
        </p>
      </div>

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

      {/* Stats Cards */}
      <div className="grid gap-4 sm:grid-cols-3">
        <Card>
          <CardContent className="flex items-center gap-4 p-4">
            <div className="flex h-10 w-10 items-center justify-center rounded-lg bg-primary/10">
              <Users className="h-5 w-5 text-primary" />
            </div>
            <div>
              <p className="text-sm text-muted-foreground">Total Seats</p>
              <p className="text-2xl font-semibold">
                {stats.active_members + stats.pending_invites}
                <span className="text-muted-foreground text-lg">/{stats.total_seats}</span>
              </p>
            </div>
          </CardContent>
        </Card>

        <Card>
          <CardContent className="flex items-center gap-4 p-4">
            <div className="flex h-10 w-10 items-center justify-center rounded-lg bg-warning/10">
              <Mail className="h-5 w-5 text-warning" />
            </div>
            <div>
              <p className="text-sm text-muted-foreground">Pending Invites</p>
              <p className="text-2xl font-semibold">{stats.pending_invites}</p>
            </div>
          </CardContent>
        </Card>

        <Card>
          <CardContent className="flex items-center gap-4 p-4">
            <div className="flex h-10 w-10 items-center justify-center rounded-lg bg-success/10">
              <Clock className="h-5 w-5 text-success" />
            </div>
            <div>
              <p className="text-sm text-muted-foreground">Active Members</p>
              <p className="text-2xl font-semibold">{stats.active_members}</p>
            </div>
          </CardContent>
        </Card>
      </div>

      {/* Action Area */}
      <div className="flex flex-wrap gap-3">
        <Dialog open={inviteDialogOpen} onOpenChange={setInviteDialogOpen}>
          <DialogTrigger asChild>
            <Button className="gap-2">
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
                  onChange={(e) => setInviteEmail(e.target.value)}
                />
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
              <Button onClick={handleInvite} className="gap-2" disabled={isInviting}>
                {isInviting ? (
                  <Loader2 className="h-4 w-4 animate-spin" />
                ) : (
                  <Send className="h-4 w-4" />
                )}
                Send Invitation
              </Button>
            </DialogFooter>
          </DialogContent>
        </Dialog>

        {/* Bulk Import Dialog */}
        <Dialog open={bulkDialogOpen} onOpenChange={setBulkDialogOpen}>
          <DialogTrigger asChild>
            <Tooltip>
              <TooltipTrigger asChild>
                <Button variant="outline" className="gap-2" disabled={!teamEnabled}>
                  <Upload className="h-4 w-4" />
                  Bulk Import (.csv)
                </Button>
              </TooltipTrigger>
              <TooltipContent>
                <p>{teamEnabled ? "Upload a CSV list for large teams" : "Upgrade to use bulk import"}</p>
              </TooltipContent>
            </Tooltip>
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
              <Button onClick={handleBulkImport} className="gap-2" disabled={!bulkFile || isBulkImporting}>
                {isBulkImporting ? (
                  <Loader2 className="h-4 w-4 animate-spin" />
                ) : (
                  <Upload className="h-4 w-4" />
                )}
                Import Members
              </Button>
            </DialogFooter>
          </DialogContent>
        </Dialog>
      </div>

      {/* Search and Filter */}
      <div className="flex flex-col gap-4 sm:flex-row sm:items-center">
        <div className="relative flex-1 max-w-md">
          <Search className="absolute left-3 top-1/2 h-4 w-4 -translate-y-1/2 text-muted-foreground" />
          <Input
            placeholder="Search by name or email..."
            value={searchQuery}
            onChange={(e) => handleSearchChange(e.target.value)}
            className="pl-9"
          />
        </div>
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
      </div>

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
            {paginatedMembers.length === 0 ? (
              <TableRow>
                <TableCell colSpan={5} className="h-40 text-center">
                  <div className="space-y-2">
                    <Users className="mx-auto h-10 w-10 text-muted-foreground/40" />
                    <p className="font-medium text-foreground">
                      {members.length === 0
                        ? "No team members yet"
                        : "No members match your filters"}
                    </p>
                    <p className="text-sm text-muted-foreground">
                      {members.length === 0
                        ? "You haven't invited anyone yet. Start collaborating by adding your team."
                        : "Try adjusting your search or filter criteria."}
                    </p>
                    {hasActiveFilters && (
                      <Button variant="outline" size="sm" onClick={clearFilters}>
                        Clear Filters
                      </Button>
                    )}
                  </div>
                </TableCell>
              </TableRow>
            ) : (
              paginatedMembers.map((member) => {
                const status = statusStyles[member.status];
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
                      <Badge variant="outline" className={roleStyles[member.role]}>
                        {member.role.charAt(0).toUpperCase() + member.role.slice(1)}
                      </Badge>
                    </TableCell>
                    <TableCell>
                      <Badge variant="outline" className={status.className}>
                        {status.label}
                      </Badge>
                    </TableCell>
                    <TableCell className="text-muted-foreground">
                      {formatDate(member.last_active)}
                    </TableCell>
                    <TableCell>
                      <DropdownMenu>
                        <DropdownMenuTrigger asChild>
                          <Button variant="ghost" size="icon" className="h-8 w-8">
                            <MoreHorizontal className="h-4 w-4" />
                          </Button>
                        </DropdownMenuTrigger>
                        <DropdownMenuContent align="end" className="bg-popover">
                          <DropdownMenuItem onClick={() => openEditRoleDialog(member)}>
                            <UserCog className="mr-2 h-4 w-4" />
                            Edit Role
                          </DropdownMenuItem>
                          {member.status === "pending" && (
                            <DropdownMenuItem onClick={() => handleResendInvite(member)}>
                              <Send className="mr-2 h-4 w-4" />
                              Resend Invite
                            </DropdownMenuItem>
                          )}
                          <DropdownMenuSeparator />
                          <DropdownMenuItem
                            onClick={() => handleRevokeAccess(member.id)}
                            className="text-destructive focus:text-destructive"
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
      {filteredMembers.length > 0 && (
        <div className="flex flex-col gap-4 sm:flex-row sm:items-center sm:justify-between">
          <div className="flex items-center gap-2 text-sm text-muted-foreground">
            <span>Showing</span>
            <Select
              value={pageSize.toString()}
              onValueChange={(value) => {
                setPageSize(Number(value));
                setCurrentPage(1);
              }}
            >
              <SelectTrigger className="w-[70px] h-8">
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
            <span>
              of {filteredMembers.length} member{filteredMembers.length !== 1 ? "s" : ""}
            </span>
          </div>

          {totalPages > 1 && (
            <div className="flex items-center gap-2">
              <Button
                variant="outline"
                size="icon"
                className="h-8 w-8"
                onClick={() => setCurrentPage((p) => Math.max(1, p - 1))}
                disabled={currentPage === 1}
              >
                <ChevronLeft className="h-4 w-4" />
              </Button>
              <div className="flex items-center gap-1">
                {Array.from({ length: Math.min(totalPages, 5) }, (_, i) => {
                  let page: number;
                  if (totalPages <= 5) {
                    page = i + 1;
                  } else if (currentPage <= 3) {
                    page = i + 1;
                  } else if (currentPage >= totalPages - 2) {
                    page = totalPages - 4 + i;
                  } else {
                    page = currentPage - 2 + i;
                  }
                  return (
                    <Button
                      key={page}
                      variant={currentPage === page ? "default" : "outline"}
                      size="icon"
                      className="h-8 w-8"
                      onClick={() => setCurrentPage(page)}
                    >
                      {page}
                    </Button>
                  );
                })}
              </div>
              <Button
                variant="outline"
                size="icon"
                className="h-8 w-8"
                onClick={() => setCurrentPage((p) => Math.min(totalPages, p + 1))}
                disabled={currentPage === totalPages}
              >
                <ChevronRight className="h-4 w-4" />
              </Button>
            </div>
          )}
        </div>
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
              <Select value={selectedRole} onValueChange={(v) => setSelectedRole(v as Role)}>
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
            <Button onClick={handleSaveRole}>Save Changes</Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>
    </div>
  );
}
