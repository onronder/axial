'use client';

import { motion } from 'framer-motion';
import { Clock, AlertTriangle, ArrowRight } from 'lucide-react';
import { Card, CardContent } from '@/components/ui/card';
import { Button } from '@/components/ui/button';
import { Badge } from '@/components/ui/badge';
import { useApprovals } from '@/hooks/useApprovals';
import { useRouter } from 'next/navigation';
import { cn } from '@/lib/utils';

export function PendingApprovalsWidget() {
  const router = useRouter();
  const { pending, isLoading } = useApprovals();
  const count = pending?.length || 0;

  if (isLoading) {
    return (
      <Card className="animate-pulse">
        <CardContent className="p-6">
          <div className="h-24 bg-muted/20 rounded" />
        </CardContent>
      </Card>
    );
  }

  if (count === 0) {
    return null;
  }

  return (
    <motion.div
      initial={{ opacity: 0, y: 20 }}
      animate={{ opacity: 1, y: 0 }}
    >
      <Card className={cn(
        'border-2 overflow-hidden',
        count > 0 ? 'border-orange-500/50 bg-orange-500/5' : 'border-border'
      )}>
        {/* Pulsing top border */}
        <div className="h-1 bg-gradient-to-r from-orange-500 via-amber-500 to-orange-500 animate-pulse" />

        <CardContent className="p-6">
          <div className="flex items-center justify-between">
            <div className="flex items-center gap-4">
              <div className="relative">
                <div className="p-3 rounded-full bg-orange-500/10">
                  <Clock className="h-6 w-6 text-orange-400" />
                </div>
                {/* Notification dot */}
                <span className="absolute -top-1 -right-1 w-4 h-4 bg-red-500 rounded-full flex items-center justify-center">
                  <span className="text-[10px] font-bold text-white">
                    {count > 9 ? '9+' : count}
                  </span>
                </span>
              </div>

              <div>
                <h3 className="font-semibold text-orange-400">
                  Pending Approvals
                </h3>
                <p className="text-sm text-muted-foreground">
                  {count} action{count !== 1 ? 's' : ''} awaiting your approval
                </p>
              </div>
            </div>

            <Button
              variant="outline"
              className="gap-2 border-orange-500/30 hover:bg-orange-500/10"
              onClick={() => router.push('/dashboard/settings/approvals')}
            >
              Review Now
              <ArrowRight className="h-4 w-4" />
            </Button>
          </div>

          {/* Urgent item preview */}
          {pending && pending[0] && (
            <div className="mt-4 p-3 rounded-lg bg-black/20 flex items-center gap-3">
              <AlertTriangle className="h-4 w-4 text-amber-400" />
              <span className="text-sm truncate flex-1">
                {pending[0].resource_name || pending[0].resource_id}
              </span>
              <Badge variant="outline" className="text-amber-400 border-amber-500/30">
                {pending[0].action_type.replace('_', ' ')}
              </Badge>
            </div>
          )}
        </CardContent>
      </Card>
    </motion.div>
  );
}

export default PendingApprovalsWidget;
