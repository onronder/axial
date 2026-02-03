'use client';

/**
 * PendingInvitesBanner Component
 * 
 * Displays a banner when the user has pending team invites.
 * Shown at the top of the dashboard to encourage users to accept/decline invites.
 */

import { useState } from 'react';
import { Users, Check, X, ChevronDown, ChevronUp, Loader2 } from 'lucide-react';
import { Button } from '@/components/ui/button';
import { Card, CardContent } from '@/components/ui/card';
import { Badge } from '@/components/ui/badge';
import { usePendingInvites, PendingInvite } from '@/hooks/usePendingInvites';
import { cn } from '@/lib/utils';
import { formatDistanceToNow } from 'date-fns';

// Role display config
const ROLE_BADGES: Record<string, { label: string; className: string }> = {
  owner: { label: 'Owner', className: 'bg-purple-500/10 text-purple-600 dark:text-purple-400' },
  admin: { label: 'Admin', className: 'bg-blue-500/10 text-blue-600 dark:text-blue-400' },
  editor: { label: 'Editor', className: 'bg-green-500/10 text-green-600 dark:text-green-400' },
  viewer: { label: 'Viewer', className: 'bg-gray-500/10 text-gray-600 dark:text-gray-400' },
};

function formatInviteDate(dateString: string): string {
  try {
    return formatDistanceToNow(new Date(dateString), { addSuffix: true });
  } catch {
    return 'recently';
  }
}

interface InviteCardProps {
  invite: PendingInvite;
  onAccept: (id: string) => Promise<unknown>;
  onDecline: (id: string) => Promise<unknown>;
  isAccepting: boolean;
  isDeclining: boolean;
}

function InviteCard({ invite, onAccept, onDecline, isAccepting, isDeclining }: InviteCardProps) {
  const [processingAction, setProcessingAction] = useState<'accept' | 'decline' | null>(null);
  const roleConfig = ROLE_BADGES[invite.role] || ROLE_BADGES.viewer;

  const handleAccept = async () => {
    setProcessingAction('accept');
    try {
      await onAccept(invite.id);
    } finally {
      setProcessingAction(null);
    }
  };

  const handleDecline = async () => {
    setProcessingAction('decline');
    try {
      await onDecline(invite.id);
    } finally {
      setProcessingAction(null);
    }
  };

  const isProcessing = processingAction !== null;

  return (
    <div className="flex items-center justify-between gap-4 py-3 px-4 bg-muted/30 rounded-lg">
      <div className="flex items-center gap-3 min-w-0">
        <div className="flex h-10 w-10 items-center justify-center rounded-full bg-primary/10 shrink-0">
          <Users className="h-5 w-5 text-primary" />
        </div>
        <div className="min-w-0">
          <div className="flex items-center gap-2">
            <span className="font-medium truncate">{invite.team_name}</span>
            <Badge variant="secondary" className={cn('shrink-0', roleConfig.className)}>
              {roleConfig.label}
            </Badge>
          </div>
          <p className="text-xs text-muted-foreground">
            Invited {formatInviteDate(invite.invited_at)}
          </p>
        </div>
      </div>
      <div className="flex items-center gap-2 shrink-0">
        <Button
          variant="outline"
          size="sm"
          onClick={handleDecline}
          disabled={isProcessing || isAccepting || isDeclining}
          className="gap-1"
        >
          {processingAction === 'decline' ? (
            <Loader2 className="h-3 w-3 animate-spin" />
          ) : (
            <X className="h-3 w-3" />
          )}
          Decline
        </Button>
        <Button
          size="sm"
          onClick={handleAccept}
          disabled={isProcessing || isAccepting || isDeclining}
          className="gap-1"
        >
          {processingAction === 'accept' ? (
            <Loader2 className="h-3 w-3 animate-spin" />
          ) : (
            <Check className="h-3 w-3" />
          )}
          Accept
        </Button>
      </div>
    </div>
  );
}

export function PendingInvitesBanner() {
  const { invites, hasInvites, isLoading, isAccepting, isDeclining, acceptInvite, declineInvite } = usePendingInvites();
  const [isExpanded, setIsExpanded] = useState(true);

  // Don't render if no invites or loading
  if (isLoading || !hasInvites) {
    return null;
  }

  return (
    <Card className="border-primary/20 bg-gradient-to-r from-primary/5 to-transparent mb-6">
      <CardContent className="p-4">
        {/* Header */}
        <button
          className="flex items-center justify-between w-full text-left"
          onClick={() => setIsExpanded(!isExpanded)}
        >
          <div className="flex items-center gap-3">
            <div className="flex h-8 w-8 items-center justify-center rounded-lg bg-primary/10">
              <Users className="h-4 w-4 text-primary" />
            </div>
            <div>
              <h3 className="font-semibold text-sm">
                You have {invites.length} pending team {invites.length === 1 ? 'invitation' : 'invitations'}
              </h3>
              <p className="text-xs text-muted-foreground">
                Join a team to collaborate with others
              </p>
            </div>
          </div>
          <Button variant="ghost" size="icon" className="h-8 w-8 shrink-0">
            {isExpanded ? (
              <ChevronUp className="h-4 w-4" />
            ) : (
              <ChevronDown className="h-4 w-4" />
            )}
          </Button>
        </button>

        {/* Invites List */}
        {isExpanded && (
          <div className="mt-4 space-y-2">
            {invites.map((invite) => (
              <InviteCard
                key={invite.id}
                invite={invite}
                onAccept={acceptInvite}
                onDecline={declineInvite}
                isAccepting={isAccepting}
                isDeclining={isDeclining}
              />
            ))}
          </div>
        )}
      </CardContent>
    </Card>
  );
}

export default PendingInvitesBanner;
