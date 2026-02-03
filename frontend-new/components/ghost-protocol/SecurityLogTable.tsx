'use client';

import { useState } from 'react';
import {
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from '@/components/ui/table';
import { Button } from '@/components/ui/button';
import { Input } from '@/components/ui/input';
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from '@/components/ui/select';
import {
  Shield,
  FileText,
  Folder,
  Database,
  Download,
  Search,
} from 'lucide-react';
import { WipeVerificationBadge } from './WipeVerificationBadge';
import { useSecurityLog } from '@/hooks/useSecurityLog';

interface SecurityEvent {
  id: string;
  event_type: 'document_wiped' | 'scope_deleted' | 'chunk_purged' | 'organization_purged';
  resource_type: string;
  resource_name: string;
  resource_id: string;
  wipe_pattern: 'dod_5220_22_m' | 'random';
  wipe_verified: boolean;
  performed_by: string;
  performed_at: string;
  duration_ms: number;
}

const EVENT_ICONS = {
  document_wiped: FileText,
  scope_deleted: Folder,
  chunk_purged: Database,
  organization_purged: Shield,
};

const EVENT_LABELS = {
  document_wiped: 'Document Wiped',
  scope_deleted: 'Scope Deleted',
  chunk_purged: 'Chunk Purged',
  organization_purged: 'Organization Purged',
};

function formatTime(dateString: string): string {
  try {
    return new Date(dateString).toISOString().slice(11, 23);
  } catch {
    return dateString;
  }
}

function formatRelativeTime(dateString: string): string {
  try {
    const date = new Date(dateString);
    const now = new Date();
    const diffMs = now.getTime() - date.getTime();
    const diffMins = Math.floor(diffMs / 60000);
    const diffHours = Math.floor(diffMins / 60);
    const diffDays = Math.floor(diffHours / 24);

    if (diffMins < 1) return 'just now';
    if (diffMins < 60) return `${diffMins}m ago`;
    if (diffHours < 24) return `${diffHours}h ago`;
    return `${diffDays}d ago`;
  } catch {
    return '';
  }
}

function formatDateForFilename(date: Date): string {
  return date.toISOString().slice(0, 10);
}

export function SecurityLogTable() {
  const [search, setSearch] = useState('');
  const [eventTypeFilter, setEventTypeFilter] = useState<string>('all');

  const { data: events, isLoading } = useSecurityLog({
    search,
    eventType: eventTypeFilter !== 'all' ? eventTypeFilter : undefined,
  });

  const handleExport = () => {
    const csv = [
      ['Timestamp', 'Event Type', 'Resource', 'Pattern', 'Verified', 'Duration (ms)'],
      ...(events || []).map((e: SecurityEvent) => [
        e.performed_at,
        e.event_type,
        e.resource_name,
        e.wipe_pattern,
        e.wipe_verified ? 'Yes' : 'No',
        e.duration_ms,
      ]),
    ].map(row => row.join(',')).join('\n');

    const blob = new Blob([csv], { type: 'text/csv' });
    const url = URL.createObjectURL(blob);
    const a = document.createElement('a');
    a.href = url;
    a.download = `security-log-${formatDateForFilename(new Date())}.csv`;
    a.click();
    URL.revokeObjectURL(url);
  };

  return (
    <div className="space-y-4">
      {/* Header */}
      <div className="flex items-center justify-between">
        <div className="flex items-center gap-2">
          <Shield className="h-5 w-5 text-cyan-400" />
          <h2 className="text-lg font-semibold">Security Log</h2>
        </div>
        <Button
          variant="outline"
          size="sm"
          onClick={handleExport}
          className="gap-2"
        >
          <Download className="h-4 w-4" />
          Export CSV
        </Button>
      </div>

      {/* Filters */}
      <div className="flex gap-4">
        <div className="relative flex-1 max-w-sm">
          <Search className="absolute left-3 top-1/2 -translate-y-1/2 h-4 w-4 text-muted-foreground" />
          <Input
            placeholder="Search by resource name..."
            value={search}
            onChange={(e) => setSearch(e.target.value)}
            className="pl-9"
          />
        </div>
        <Select value={eventTypeFilter} onValueChange={setEventTypeFilter}>
          <SelectTrigger className="w-48">
            <SelectValue placeholder="Event type" />
          </SelectTrigger>
          <SelectContent>
            <SelectItem value="all">All Events</SelectItem>
            <SelectItem value="document_wiped">Document Wiped</SelectItem>
            <SelectItem value="scope_deleted">Scope Deleted</SelectItem>
            <SelectItem value="chunk_purged">Chunk Purged</SelectItem>
          </SelectContent>
        </Select>
      </div>

      {/* Table */}
      <div className="rounded-lg border border-border/50 overflow-hidden">
        <Table>
          <TableHeader>
            <TableRow className="bg-muted/30">
              <TableHead className="w-48">Timestamp</TableHead>
              <TableHead>Event</TableHead>
              <TableHead>Resource</TableHead>
              <TableHead className="text-center">Compliance</TableHead>
              <TableHead className="text-right">Duration</TableHead>
            </TableRow>
          </TableHeader>
          <TableBody>
            {isLoading ? (
              <TableRow>
                <TableCell colSpan={5} className="text-center py-8">
                  Loading security events...
                </TableCell>
              </TableRow>
            ) : !events || events.length === 0 ? (
              <TableRow>
                <TableCell colSpan={5} className="text-center py-8 text-muted-foreground">
                  No security events found
                </TableCell>
              </TableRow>
            ) : (
              events.map((event: SecurityEvent) => {
                const Icon = EVENT_ICONS[event.event_type];
                return (
                  <TableRow key={event.id} className="hover:bg-muted/20">
                    <TableCell className="font-mono text-xs">
                      <div>{formatTime(event.performed_at)}</div>
                      <div className="text-muted-foreground">
                        {formatRelativeTime(event.performed_at)}
                      </div>
                    </TableCell>
                    <TableCell>
                      <div className="flex items-center gap-2">
                        <Icon className="h-4 w-4 text-muted-foreground" />
                        <span className="text-sm">{EVENT_LABELS[event.event_type]}</span>
                      </div>
                    </TableCell>
                    <TableCell>
                      <div className="max-w-[200px]">
                        <div className="truncate text-sm">{event.resource_name}</div>
                        <div className="text-[10px] font-mono text-muted-foreground">
                          {event.resource_id.slice(0, 12)}...
                        </div>
                      </div>
                    </TableCell>
                    <TableCell className="text-center">
                      <WipeVerificationBadge
                        wipedAt={event.performed_at}
                        pattern={event.wipe_pattern}
                        verified={event.wipe_verified}
                        variant="compact"
                      />
                    </TableCell>
                    <TableCell className="text-right font-mono text-xs">
                      {event.duration_ms}ms
                    </TableCell>
                  </TableRow>
                );
              })
            )}
          </TableBody>
        </Table>
      </div>
    </div>
  );
}

export default SecurityLogTable;
