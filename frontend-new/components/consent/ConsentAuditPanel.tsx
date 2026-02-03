'use client';

/**
 * ConsentAuditPanel Component
 * 
 * Displays the consent change audit log with filtering and export capabilities.
 * Shows all consent-related changes at organization, scope, and document levels.
 */

import { useState, useMemo } from 'react';
import { useQuery } from '@tanstack/react-query';
import { formatDistanceToNow, format } from 'date-fns';
import {
  History,
  Search,
  Download,
  Building,
  Folder,
  FileText,
  ChevronLeft,
  ChevronRight,
  RefreshCw,
} from 'lucide-react';
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card';
import { Button } from '@/components/ui/button';
import { Input } from '@/components/ui/input';
import { Badge } from '@/components/ui/badge';
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from '@/components/ui/select';
import {
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from '@/components/ui/table';
import { Skeleton } from '@/components/ui/skeleton';
import { api } from '@/lib/api';

// =============================================================================
// Types
// =============================================================================

interface ConsentAuditEntry {
  id: string;
  consent_level: 'organization' | 'scope' | 'document';
  resource_id: string;
  field_changed: string;
  old_value: string | null;
  new_value: string | null;
  changed_by: string;
  changed_at: string;
  ip_address: string | null;
}

// =============================================================================
// API
// =============================================================================

async function fetchConsentAudit(
  limit: number = 50,
  offset: number = 0
): Promise<ConsentAuditEntry[]> {
  const params = new URLSearchParams();
  params.set('limit', String(limit));
  params.set('offset', String(offset));
  
  const response = await api.get<ConsentAuditEntry[]>(`/consent/audit?${params.toString()}`);
  return response.data;
}

// =============================================================================
// Constants
// =============================================================================

const LEVEL_CONFIG: Record<string, { icon: typeof Building; label: string; color: string }> = {
  organization: { icon: Building, label: 'Organization', color: 'text-blue-500' },
  scope: { icon: Folder, label: 'Scope', color: 'text-amber-500' },
  document: { icon: FileText, label: 'Document', color: 'text-green-500' },
};

const FIELD_LABELS: Record<string, string> = {
  allow_ai_learning: 'AI Learning',
  allow_external_agents: 'External Agents',
  allowed_agent_ids: 'Allowed Agents',
  blocked_agent_ids: 'Blocked Agents',
  inherit_org_consent: 'Inherit Organization',
  inherit_scope_consent: 'Inherit Scope',
};

const PAGE_SIZE = 20;

// =============================================================================
// Component
// =============================================================================

export function ConsentAuditPanel() {
  const [page, setPage] = useState(0);
  const [searchQuery, setSearchQuery] = useState('');
  const [levelFilter, setLevelFilter] = useState<string>('all');

  const { data: auditEntries, isLoading, isFetching, refetch } = useQuery({
    queryKey: ['consent-audit', page],
    queryFn: () => fetchConsentAudit(PAGE_SIZE, page * PAGE_SIZE),
    staleTime: 30000,
  });

  // Filter entries based on search and level
  const filteredEntries = useMemo(() => {
    if (!auditEntries) return [];
    
    return auditEntries.filter((entry) => {
      // Level filter
      if (levelFilter !== 'all' && entry.consent_level !== levelFilter) {
        return false;
      }
      
      // Search filter
      if (searchQuery) {
        const query = searchQuery.toLowerCase();
        return (
          entry.resource_id.toLowerCase().includes(query) ||
          entry.field_changed.toLowerCase().includes(query) ||
          entry.changed_by.toLowerCase().includes(query) ||
          (entry.new_value?.toLowerCase().includes(query) ?? false) ||
          (entry.old_value?.toLowerCase().includes(query) ?? false)
        );
      }
      
      return true;
    });
  }, [auditEntries, searchQuery, levelFilter]);

  // Export to CSV
  const handleExport = () => {
    if (!auditEntries || auditEntries.length === 0) return;

    const csvRows = [
      ['Timestamp', 'Level', 'Resource ID', 'Field Changed', 'Old Value', 'New Value', 'Changed By', 'IP Address'],
      ...filteredEntries.map((entry) => [
        entry.changed_at,
        entry.consent_level,
        entry.resource_id,
        entry.field_changed,
        entry.old_value || '',
        entry.new_value || '',
        entry.changed_by,
        entry.ip_address || '',
      ]),
    ];

    const csvContent = csvRows
      .map((row) => row.map((cell) => `"${String(cell).replace(/"/g, '""')}"`).join(','))
      .join('\n');

    const blob = new Blob([csvContent], { type: 'text/csv;charset=utf-8;' });
    const link = document.createElement('a');
    link.href = URL.createObjectURL(blob);
    link.download = `consent-audit-${format(new Date(), 'yyyy-MM-dd')}.csv`;
    link.click();
  };

  // Format the change value for display
  const formatValue = (value: string | null): string => {
    if (value === null || value === '') return '—';
    if (value === 'true') return 'Enabled';
    if (value === 'false') return 'Disabled';
    // Check if it's a JSON array
    try {
      const parsed = JSON.parse(value);
      if (Array.isArray(parsed)) {
        return parsed.length > 0 ? parsed.join(', ') : 'None';
      }
    } catch {
      // Not JSON, return as-is
    }
    return value;
  };

  return (
    <Card className="border-cyan-500/20">
      <CardHeader className="pb-4">
        <div className="flex items-center justify-between">
          <div className="flex items-center gap-3">
            <div className="p-2 rounded-lg bg-cyan-500/10">
              <History className="h-5 w-5 text-cyan-400" />
            </div>
            <div>
              <CardTitle className="text-lg">Consent Audit Log</CardTitle>
              <CardDescription>Track all consent setting changes</CardDescription>
            </div>
          </div>
          <div className="flex items-center gap-2">
            <Button
              variant="outline"
              size="sm"
              onClick={() => refetch()}
              disabled={isFetching}
            >
              <RefreshCw className={`h-4 w-4 ${isFetching ? 'animate-spin' : ''}`} />
            </Button>
            <Button
              variant="outline"
              size="sm"
              onClick={handleExport}
              disabled={!auditEntries || auditEntries.length === 0}
            >
              <Download className="h-4 w-4 mr-2" />
              Export
            </Button>
          </div>
        </div>
      </CardHeader>

      <CardContent className="space-y-4">
        {/* Filters */}
        <div className="flex gap-4">
          <div className="relative flex-1 max-w-sm">
            <Search className="absolute left-3 top-1/2 -translate-y-1/2 h-4 w-4 text-muted-foreground" />
            <Input
              placeholder="Search audit log..."
              value={searchQuery}
              onChange={(e) => setSearchQuery(e.target.value)}
              className="pl-9"
            />
          </div>
          <Select value={levelFilter} onValueChange={setLevelFilter}>
            <SelectTrigger className="w-[160px]">
              <SelectValue placeholder="Filter by level" />
            </SelectTrigger>
            <SelectContent>
              <SelectItem value="all">All Levels</SelectItem>
              <SelectItem value="organization">Organization</SelectItem>
              <SelectItem value="scope">Scope</SelectItem>
              <SelectItem value="document">Document</SelectItem>
            </SelectContent>
          </Select>
        </div>

        {/* Table */}
        <div className="rounded-lg border">
          <Table>
            <TableHeader>
              <TableRow className="bg-muted/30">
                <TableHead className="w-[140px]">When</TableHead>
                <TableHead className="w-[100px]">Level</TableHead>
                <TableHead className="w-[160px]">Field</TableHead>
                <TableHead>Change</TableHead>
                <TableHead className="w-[120px]">Changed By</TableHead>
              </TableRow>
            </TableHeader>
            <TableBody>
              {isLoading ? (
                [...Array(5)].map((_, i) => (
                  <TableRow key={i}>
                    <TableCell><Skeleton className="h-4 w-24" /></TableCell>
                    <TableCell><Skeleton className="h-4 w-16" /></TableCell>
                    <TableCell><Skeleton className="h-4 w-24" /></TableCell>
                    <TableCell><Skeleton className="h-4 w-32" /></TableCell>
                    <TableCell><Skeleton className="h-4 w-20" /></TableCell>
                  </TableRow>
                ))
              ) : filteredEntries.length === 0 ? (
                <TableRow>
                  <TableCell colSpan={5} className="text-center py-8 text-muted-foreground">
                    {searchQuery || levelFilter !== 'all'
                      ? 'No audit entries match your filters'
                      : 'No consent changes recorded yet'}
                  </TableCell>
                </TableRow>
              ) : (
                filteredEntries.map((entry) => {
                  const levelConfig = LEVEL_CONFIG[entry.consent_level] || LEVEL_CONFIG.organization;
                  const LevelIcon = levelConfig.icon;

                  return (
                    <TableRow key={entry.id}>
                      <TableCell className="text-xs">
                        <div title={format(new Date(entry.changed_at), 'PPpp')}>
                          {formatDistanceToNow(new Date(entry.changed_at), { addSuffix: true })}
                        </div>
                      </TableCell>
                      <TableCell>
                        <Badge variant="outline" className="gap-1 text-xs">
                          <LevelIcon className={`h-3 w-3 ${levelConfig.color}`} />
                          {levelConfig.label}
                        </Badge>
                      </TableCell>
                      <TableCell className="text-sm">
                        {FIELD_LABELS[entry.field_changed] || entry.field_changed}
                      </TableCell>
                      <TableCell>
                        <div className="flex items-center gap-2 text-sm">
                          <span className="text-red-500 line-through">
                            {formatValue(entry.old_value)}
                          </span>
                          <span className="text-muted-foreground">→</span>
                          <span className="text-green-500 font-medium">
                            {formatValue(entry.new_value)}
                          </span>
                        </div>
                      </TableCell>
                      <TableCell className="text-xs text-muted-foreground truncate max-w-[120px]">
                        {entry.changed_by.slice(0, 8)}...
                      </TableCell>
                    </TableRow>
                  );
                })
              )}
            </TableBody>
          </Table>
        </div>

        {/* Pagination */}
        {(auditEntries?.length ?? 0) > 0 && (
          <div className="flex items-center justify-between">
            <p className="text-sm text-muted-foreground">
              Showing {filteredEntries.length} of {auditEntries?.length ?? 0} entries
            </p>
            <div className="flex items-center gap-2">
              <Button
                variant="outline"
                size="sm"
                onClick={() => setPage((p) => Math.max(0, p - 1))}
                disabled={page === 0}
              >
                <ChevronLeft className="h-4 w-4" />
                Previous
              </Button>
              <span className="text-sm text-muted-foreground">Page {page + 1}</span>
              <Button
                variant="outline"
                size="sm"
                onClick={() => setPage((p) => p + 1)}
                disabled={(auditEntries?.length ?? 0) < PAGE_SIZE}
              >
                Next
                <ChevronRight className="h-4 w-4" />
              </Button>
            </div>
          </div>
        )}
      </CardContent>
    </Card>
  );
}

export default ConsentAuditPanel;
