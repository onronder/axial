'use client';

import { motion } from 'framer-motion';
import { Shield, ArrowRight, CheckCircle2, AlertTriangle } from 'lucide-react';
import { Card, CardContent } from '@/components/ui/card';
import { Button } from '@/components/ui/button';
import { Progress } from '@/components/ui/progress';
import { cn } from '@/lib/utils';

interface ComplianceScoreWidgetProps {
  score: number;
  variant?: 'default' | 'compact' | 'dashboard';
  onViewReport?: () => void;
}

function getScoreColor(score: number): string {
  if (score >= 90) return 'text-green-400';
  if (score >= 70) return 'text-amber-400';
  return 'text-red-400';
}

function getScoreLabel(score: number): string {
  if (score >= 90) return 'Excellent';
  if (score >= 70) return 'Good';
  if (score >= 50) return 'Needs Attention';
  return 'Critical';
}

function getProgressColor(score: number): string {
  if (score >= 90) return 'bg-green-500';
  if (score >= 70) return 'bg-amber-500';
  return 'bg-red-500';
}

export function ComplianceScoreWidget({
  score,
  variant = 'default',
  onViewReport,
}: ComplianceScoreWidgetProps) {
  const scoreColor = getScoreColor(score);
  const scoreLabel = getScoreLabel(score);

  if (variant === 'compact') {
    return (
      <div className="flex items-center gap-2">
        <Shield className={cn('h-4 w-4', scoreColor)} />
        <span className={cn('text-sm font-mono font-bold', scoreColor)}>
          {score}%
        </span>
      </div>
    );
  }

  if (variant === 'dashboard') {
    return (
      <motion.div
        initial={{ opacity: 0, y: 20 }}
        animate={{ opacity: 1, y: 0 }}
      >
        <Card className="border-cyan-500/20 bg-cyan-500/5">
          <CardContent className="p-6">
            <div className="flex items-center justify-between mb-4">
              <div className="flex items-center gap-2">
                <Shield className="h-5 w-5 text-cyan-400" />
                <span className="font-medium">Data Sovereignty</span>
              </div>
              {score >= 90 ? (
                <CheckCircle2 className="h-5 w-5 text-green-400" />
              ) : (
                <AlertTriangle className={cn('h-5 w-5', scoreColor)} />
              )}
            </div>

            <div className="space-y-4">
              <div className="text-center">
                <span className={cn('text-4xl font-bold font-mono', scoreColor)}>
                  {score}%
                </span>
                <p className="text-sm text-muted-foreground mt-1">
                  {scoreLabel}
                </p>
              </div>

              <div className="relative">
                <Progress
                  value={score}
                  className="h-2"
                />
                <div
                  className={cn(
                    'absolute inset-0 h-2 rounded-full transition-all',
                    getProgressColor(score)
                  )}
                  style={{ width: `${score}%` }}
                />
              </div>

              <p className="text-xs text-muted-foreground text-center">
                KVKK 2026 Compliant
              </p>

              {onViewReport && (
                <Button
                  variant="outline"
                  size="sm"
                  className="w-full gap-2 border-cyan-500/30 hover:bg-cyan-500/10"
                  onClick={onViewReport}
                >
                  View Report
                  <ArrowRight className="h-4 w-4" />
                </Button>
              )}
            </div>
          </CardContent>
        </Card>
      </motion.div>
    );
  }

  // Default variant - inline badge style
  return (
    <div className={cn(
      'flex items-center gap-3 px-4 py-2 rounded-lg border',
      score >= 90 ? 'border-green-500/30 bg-green-500/5' :
      score >= 70 ? 'border-amber-500/30 bg-amber-500/5' :
      'border-red-500/30 bg-red-500/5'
    )}>
      <Shield className={cn('h-5 w-5', scoreColor)} />
      <div>
        <span className={cn('text-2xl font-bold font-mono', scoreColor)}>
          {score}%
        </span>
        <p className="text-[10px] text-muted-foreground">
          Compliance Score
        </p>
      </div>
    </div>
  );
}

export default ComplianceScoreWidget;
