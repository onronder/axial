'use client';

import { CheckCircle2, Info, Shield } from 'lucide-react';
import { Badge } from '@/components/ui/badge';
import {
  Tooltip,
  TooltipContent,
  TooltipTrigger,
} from '@/components/ui/tooltip';
import { cn } from '@/lib/utils';

interface WipeVerificationBadgeProps {
  wipedAt: string;
  pattern: 'dod_5220_22_m' | 'random';
  verified: boolean;
  variant?: 'default' | 'compact' | 'inline';
  className?: string;
}

function formatDate(dateString: string): string {
  try {
    return new Date(dateString).toISOString().replace('T', ' ').slice(0, 23);
  } catch {
    return dateString;
  }
}

export function WipeVerificationBadge({
  wipedAt,
  pattern,
  verified,
  variant = 'default',
  className,
}: WipeVerificationBadgeProps) {
  const formattedDate = formatDate(wipedAt);
  const patternLabel = pattern === 'dod_5220_22_m' ? 'DoD 5220.22-M' : 'Random';

  if (variant === 'compact') {
    return (
      <Tooltip>
        <TooltipTrigger asChild>
          <div className={cn('inline-flex items-center gap-1', className)}>
            <Shield className="h-3 w-3 text-green-400" />
            <span className="text-[10px] text-green-400 font-mono">FW</span>
          </div>
        </TooltipTrigger>
        <TooltipContent side="top" className="font-mono text-xs">
          <p>Forensic Wiped ({patternLabel})</p>
          <p className="text-muted-foreground">{formattedDate}</p>
        </TooltipContent>
      </Tooltip>
    );
  }

  if (variant === 'inline') {
    return (
      <span className={cn(
        'inline-flex items-center gap-1 text-xs text-green-400',
        className
      )}>
        <CheckCircle2 className="h-3 w-3" />
        <span className="font-mono">Wiped</span>
      </span>
    );
  }

  return (
    <Tooltip>
      <TooltipTrigger asChild>
        <Badge
          variant="outline"
          className={cn(
            'gap-1.5 border-green-500/30 bg-green-500/10 text-green-400',
            'hover:bg-green-500/20 hover:border-green-500/50',
            'transition-all duration-200 cursor-help',
            className
          )}
        >
          {verified ? (
            <CheckCircle2 className="h-3 w-3" />
          ) : (
            <Shield className="h-3 w-3" />
          )}
          <span className="font-mono text-[10px]">
            Forensic Wiped
          </span>
          <Info className="h-3 w-3 opacity-50" />
        </Badge>
      </TooltipTrigger>
      <TooltipContent
        side="top"
        className="max-w-xs bg-black/95 border-green-500/30"
      >
        <div className="space-y-2 font-mono text-xs">
          <div className="flex items-center gap-2">
            <Shield className="h-4 w-4 text-green-400" />
            <span className="font-semibold text-green-400">
              {patternLabel} Compliant
            </span>
          </div>

          <div className="space-y-1 text-muted-foreground">
            <p>3-pass secure wipe completed:</p>
            <ul className="list-disc list-inside text-[10px] space-y-0.5">
              <li>Pass 1: Zero fill (0x00)</li>
              <li>Pass 2: One fill (0xFF)</li>
              <li>Pass 3: Random data</li>
            </ul>
          </div>

          <div className="pt-1 border-t border-green-500/20">
            <span className="text-muted-foreground">Wiped at: </span>
            <span className="text-green-400">{formattedDate}</span>
          </div>

          {verified && (
            <div className="flex items-center gap-1 text-green-400">
              <CheckCircle2 className="h-3 w-3" />
              <span>Post-wipe verification passed</span>
            </div>
          )}
        </div>
      </TooltipContent>
    </Tooltip>
  );
}

export default WipeVerificationBadge;
