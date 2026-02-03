'use client';

import { useEffect, useState } from 'react';
import { motion, AnimatePresence } from 'framer-motion';
import { Shield, Clock, CheckCircle2, Loader2 } from 'lucide-react';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { cn } from '@/lib/utils';

interface WipePass {
  name: string;
  description: string;
  status: 'pending' | 'active' | 'completed';
  progress: number;
  color: string;
  glowColor: string;
}

interface WipeProgressCardProps {
  documentName: string;
  currentPass: 1 | 2 | 3;
  passProgress: number;
  isComplete: boolean;
  onComplete?: () => void;
  className?: string;
}

const WIPE_PASSES: WipePass[] = [
  {
    name: 'Pass 1: Zero Fill',
    description: '0x00 - Writing zeros to entire file',
    status: 'pending',
    progress: 0,
    color: 'from-cyan-500 to-cyan-400',
    glowColor: 'shadow-cyan-500/50',
  },
  {
    name: 'Pass 2: One Fill',
    description: '0xFF - Writing ones to entire file',
    status: 'pending',
    progress: 0,
    color: 'from-orange-500 to-amber-400',
    glowColor: 'shadow-orange-500/50',
  },
  {
    name: 'Pass 3: Random Data',
    description: 'Cryptographically random bytes',
    status: 'pending',
    progress: 0,
    color: 'from-green-500 to-emerald-400',
    glowColor: 'shadow-green-500/50',
  },
];

export function WipeProgressCard({
  documentName,
  currentPass,
  passProgress,
  isComplete,
  onComplete,
  className,
}: WipeProgressCardProps) {
  const [passes, setPasses] = useState<WipePass[]>(WIPE_PASSES);

  useEffect(() => {
    setPasses(prev =>
      prev.map((pass, index) => {
        const passNum = index + 1;
        if (passNum < currentPass) {
          return { ...pass, status: 'completed', progress: 100 };
        } else if (passNum === currentPass) {
          return { ...pass, status: 'active', progress: passProgress };
        }
        return { ...pass, status: 'pending', progress: 0 };
      })
    );
  }, [currentPass, passProgress]);

  useEffect(() => {
    if (isComplete && onComplete) {
      const timer = setTimeout(onComplete, 1500);
      return () => clearTimeout(timer);
    }
  }, [isComplete, onComplete]);

  return (
    <motion.div
      initial={{ opacity: 0, scale: 0.95 }}
      animate={{ opacity: 1, scale: 1 }}
      exit={{ opacity: 0, scale: 0.95 }}
      className={cn('w-full max-w-md', className)}
    >
      <Card className="border-2 border-cyan-500/30 bg-black/80 backdrop-blur-xl overflow-hidden">
        {/* Animated border glow */}
        <div className="absolute inset-0 rounded-lg bg-gradient-to-r from-cyan-500/20 via-transparent to-green-500/20 animate-pulse pointer-events-none" />

        <CardHeader className="relative pb-2">
          <CardTitle className="flex items-center gap-2 text-cyan-400">
            <Shield className="h-5 w-5 animate-pulse" />
            <span className="font-mono text-sm tracking-wider">
              SECURE DELETION IN PROGRESS
            </span>
          </CardTitle>
          <p className="text-sm text-muted-foreground truncate font-mono">
            {documentName}
          </p>
        </CardHeader>

        <CardContent className="relative space-y-4">
          {passes.map((pass, index) => (
            <WipePassProgress
              key={index}
              pass={pass}
              isActive={pass.status === 'active'}
            />
          ))}

          {/* Estimated time */}
          {!isComplete && (
            <div className="flex items-center gap-2 text-sm text-muted-foreground">
              <Clock className="h-4 w-4" />
              <span>Estimated: {Math.ceil((3 - currentPass + 1) * (100 - passProgress) / 100)} seconds remaining</span>
            </div>
          )}

          {/* Completion state */}
          <AnimatePresence>
            {isComplete && (
              <motion.div
                initial={{ opacity: 0, y: 10 }}
                animate={{ opacity: 1, y: 0 }}
                className="flex items-center gap-2 text-green-400 font-mono text-sm"
              >
                <CheckCircle2 className="h-5 w-5" />
                <span>DoD 5220.22-M Compliant - Forensic Wipe Complete</span>
              </motion.div>
            )}
          </AnimatePresence>
        </CardContent>
      </Card>
    </motion.div>
  );
}

function WipePassProgress({ pass, isActive }: { pass: WipePass; isActive: boolean }) {
  return (
    <div className="space-y-1">
      <div className="flex items-center justify-between text-xs">
        <span className={cn(
          'font-mono',
          pass.status === 'completed' && 'text-green-400',
          pass.status === 'active' && 'text-cyan-400',
          pass.status === 'pending' && 'text-muted-foreground'
        )}>
          {pass.name}
        </span>
        <span className="text-muted-foreground">
          {pass.status === 'completed' && <CheckCircle2 className="h-4 w-4 text-green-400" />}
          {pass.status === 'active' && <Loader2 className="h-4 w-4 animate-spin text-cyan-400" />}
          {pass.status === 'pending' && <span className="text-[10px]">Pending</span>}
        </span>
      </div>

      <div className="relative h-2 overflow-hidden rounded-full bg-black/50">
        {/* Background pattern for active pass */}
        {isActive && (
          <div className="absolute inset-0 bg-[linear-gradient(90deg,transparent_25%,rgba(6,182,212,0.1)_50%,transparent_75%)] animate-shimmer bg-[length:200%_100%]" />
        )}

        <motion.div
          className={cn(
            'h-full rounded-full bg-gradient-to-r',
            pass.color,
            isActive && `shadow-lg ${pass.glowColor}`
          )}
          initial={{ width: 0 }}
          animate={{ width: `${pass.progress}%` }}
          transition={{ duration: 0.3, ease: 'easeOut' }}
        />
      </div>

      <p className="text-[10px] text-muted-foreground font-mono">
        {pass.description}
      </p>
    </div>
  );
}

export default WipeProgressCard;
