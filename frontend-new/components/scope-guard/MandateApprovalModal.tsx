'use client';

import { useEffect, useState, useCallback } from 'react';
import { motion, AnimatePresence } from 'framer-motion';
import {
  AlertTriangle,
  Clock,
  Shield,
  Bot,
  Folder,
  Trash2,
  X,
} from 'lucide-react';
import { Button } from '@/components/ui/button';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { SignatureAnimation } from './SignatureAnimation';
import { IntentExplanationCard } from './IntentExplanationCard';
import { cn } from '@/lib/utils';

interface Approval {
  id: string;
  action_type: 'delete_scope' | 'bulk_delete' | 'purge_all' | 'revoke_access';
  resource_type: string;
  resource_id: string;
  resource_name?: string;
  requested_by: string;
  requested_by_name?: string;
  expires_at: string;
  request_context: {
    reason?: string;
    affected_count?: number;
    affected_documents?: Array<{ id: string; name: string }>;
  };
}

interface MandateApprovalModalProps {
  approval: Approval;
  onApprove: () => Promise<void>;
  onReject: () => Promise<void>;
  isOpen: boolean;
  onClose: () => void;
}

const ACTION_CONFIG = {
  delete_scope: {
    icon: Folder,
    label: 'Delete Scope',
    color: 'text-orange-400',
    bgColor: 'bg-orange-500/10',
    borderColor: 'border-orange-500/50',
  },
  bulk_delete: {
    icon: Trash2,
    label: 'Bulk Delete',
    color: 'text-red-400',
    bgColor: 'bg-red-500/10',
    borderColor: 'border-red-500/50',
  },
  purge_all: {
    icon: AlertTriangle,
    label: 'Purge All Data',
    color: 'text-red-500',
    bgColor: 'bg-red-500/20',
    borderColor: 'border-red-500',
  },
  revoke_access: {
    icon: Shield,
    label: 'Revoke Access',
    color: 'text-amber-400',
    bgColor: 'bg-amber-500/10',
    borderColor: 'border-amber-500/50',
  },
};

export function MandateApprovalModal({
  approval,
  onApprove,
  onReject,
  isOpen,
  onClose,
}: MandateApprovalModalProps) {
  const [timeRemaining, setTimeRemaining] = useState<number>(0);
  const [isSigning, setIsSigning] = useState(false);
  const [isRejecting, setIsRejecting] = useState(false);

  const config = ACTION_CONFIG[approval.action_type];
  const ActionIcon = config.icon;

  // Countdown timer
  useEffect(() => {
    if (!isOpen) return;

    const updateTimer = () => {
      const now = new Date().getTime();
      const expires = new Date(approval.expires_at).getTime();
      const remaining = Math.max(0, Math.floor((expires - now) / 1000));
      setTimeRemaining(remaining);

      if (remaining === 0) {
        onClose();
      }
    };

    updateTimer();
    const interval = setInterval(updateTimer, 1000);
    return () => clearInterval(interval);
  }, [isOpen, approval.expires_at, onClose]);

  const formatTime = (seconds: number) => {
    const mins = Math.floor(seconds / 60);
    const secs = seconds % 60;
    return `${mins}:${secs.toString().padStart(2, '0')}`;
  };

  const handleApprove = useCallback(async () => {
    setIsSigning(true);
    try {
      await onApprove();
    } finally {
      setIsSigning(false);
    }
  }, [onApprove]);

  const handleReject = useCallback(async () => {
    setIsRejecting(true);
    try {
      await onReject();
    } finally {
      setIsRejecting(false);
    }
  }, [onReject]);

  return (
    <AnimatePresence>
      {isOpen && (
        <motion.div
          initial={{ opacity: 0 }}
          animate={{ opacity: 1 }}
          exit={{ opacity: 0 }}
          className="fixed inset-0 z-50 flex items-center justify-center"
        >
          {/* Backdrop with blur */}
          <div className="absolute inset-0 bg-black/80 backdrop-blur-md" />

          {/* Animated border pulse */}
          <div className={cn(
            'absolute inset-4 rounded-2xl opacity-30 pointer-events-none',
            'bg-gradient-to-r from-orange-500 via-red-500 to-orange-500',
            'animate-pulse bg-[length:200%_100%]'
          )} />

          {/* Main content */}
          <motion.div
            initial={{ scale: 0.9, opacity: 0 }}
            animate={{ scale: 1, opacity: 1 }}
            exit={{ scale: 0.9, opacity: 0 }}
            className="relative w-full max-w-2xl mx-4"
          >
            <Card className={cn(
              'border-2 bg-black/95 backdrop-blur-xl',
              config.borderColor
            )}>
              <CardHeader className="relative pb-4">
                {/* Close button (only for non-critical) */}
                {approval.action_type !== 'purge_all' && (
                  <Button
                    variant="ghost"
                    size="icon"
                    className="absolute right-4 top-4"
                    onClick={onClose}
                  >
                    <X className="h-4 w-4" />
                  </Button>
                )}

                {/* Warning header */}
                <div className="flex items-center gap-3">
                  <div className={cn(
                    'p-3 rounded-full',
                    config.bgColor
                  )}>
                    <AlertTriangle className={cn('h-6 w-6', config.color)} />
                  </div>
                  <div>
                    <CardTitle className={cn('text-xl', config.color)}>
                      ACTION REQUIRES APPROVAL
                    </CardTitle>
                    <p className="text-sm text-muted-foreground">
                      Mandate expires in:{' '}
                      <span className={cn(
                        'font-mono font-bold',
                        timeRemaining < 60 ? 'text-red-400' : 'text-amber-400'
                      )}>
                        {formatTime(timeRemaining)}
                      </span>
                    </p>
                  </div>
                </div>
              </CardHeader>

              <CardContent className="space-y-6">
                {/* Action details */}
                <div className={cn(
                  'p-4 rounded-lg border',
                  config.bgColor,
                  config.borderColor
                )}>
                  <div className="flex items-start gap-3">
                    <Bot className="h-5 w-5 text-violet-400 mt-0.5" />
                    <div className="space-y-2 flex-1">
                      <p className="text-sm text-muted-foreground">
                        AI Agent wants to:
                      </p>
                      <div className="flex items-center gap-2">
                        <ActionIcon className={cn('h-5 w-5', config.color)} />
                        <span className={cn('font-semibold', config.color)}>
                          {config.label}
                        </span>
                      </div>
                      <p className="text-lg font-medium">
                        &ldquo;{approval.resource_name || approval.resource_id}&rdquo;
                      </p>
                      {approval.request_context.affected_count && (
                        <p className="text-sm text-muted-foreground">
                          This will permanently remove{' '}
                          <span className="font-semibold text-foreground">
                            {approval.request_context.affected_count}
                          </span>{' '}
                          documents.
                        </p>
                      )}
                    </div>
                  </div>
                </div>

                {/* Intent explanation */}
                {approval.request_context.reason && (
                  <IntentExplanationCard
                    reason={approval.request_context.reason}
                    affectedDocuments={approval.request_context.affected_documents}
                  />
                )}

                {/* Signing animation overlay */}
                <AnimatePresence>
                  {isSigning && (
                    <SignatureAnimation />
                  )}
                </AnimatePresence>

                {/* Action buttons */}
                <div className="flex gap-4 pt-4">
                  <Button
                    variant="outline"
                    className="flex-1 h-12"
                    onClick={handleReject}
                    disabled={isSigning || isRejecting}
                  >
                    {isRejecting ? 'Rejecting...' : 'Reject'}
                  </Button>
                  <Button
                    className={cn(
                      'flex-1 h-12 gap-2',
                      'bg-gradient-to-r from-amber-500 to-orange-500',
                      'hover:from-amber-600 hover:to-orange-600',
                      'text-black font-semibold'
                    )}
                    onClick={handleApprove}
                    disabled={isSigning || isRejecting}
                  >
                    <Shield className="h-4 w-4" />
                    {isSigning ? 'Signing...' : 'Approve & Sign'}
                  </Button>
                </div>
              </CardContent>
            </Card>
          </motion.div>
        </motion.div>
      )}
    </AnimatePresence>
  );
}

export default MandateApprovalModal;
