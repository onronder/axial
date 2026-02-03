'use client';

import { useEffect, useState } from 'react';
import { motion } from 'framer-motion';
import { Shield, CheckCircle2 } from 'lucide-react';
import { Progress } from '@/components/ui/progress';

interface SignatureAnimationProps {
  onComplete?: () => void;
  duration?: number;
}

export function SignatureAnimation({
  onComplete,
  duration = 2000,
}: SignatureAnimationProps) {
  const [progress, setProgress] = useState(0);
  const [phase, setPhase] = useState<'signing' | 'complete'>('signing');
  const [hashChars, setHashChars] = useState('');

  // Matrix-style character animation
  useEffect(() => {
    const chars = '0123456789abcdef';
    const interval = setInterval(() => {
      const newChars = Array.from({ length: 64 }, () =>
        chars[Math.floor(Math.random() * chars.length)]
      ).join('');
      setHashChars(newChars);
    }, 50);

    return () => clearInterval(interval);
  }, []);

  // Progress animation
  useEffect(() => {
    const startTime = Date.now();
    const interval = setInterval(() => {
      const elapsed = Date.now() - startTime;
      const newProgress = Math.min((elapsed / duration) * 100, 100);
      setProgress(newProgress);

      if (newProgress >= 100) {
        clearInterval(interval);
        setPhase('complete');
        setTimeout(() => {
          onComplete?.();
        }, 500);
      }
    }, 16);

    return () => clearInterval(interval);
  }, [duration, onComplete]);

  return (
    <motion.div
      initial={{ opacity: 0 }}
      animate={{ opacity: 1 }}
      exit={{ opacity: 0 }}
      className="absolute inset-0 bg-black/90 backdrop-blur-sm flex items-center justify-center rounded-lg z-10"
    >
      <div className="text-center space-y-4 p-8">
        {phase === 'signing' ? (
          <>
            <div className="flex items-center justify-center gap-2">
              <Shield className="h-6 w-6 text-cyan-400 animate-pulse" />
              <span className="text-cyan-400 font-mono text-sm">
                Cryptographic Signature
              </span>
            </div>

            {/* Progress bar with glow */}
            <div className="relative w-64">
              <Progress
                value={progress}
                className="h-2 bg-cyan-950"
              />
              <div
                className="absolute inset-0 bg-cyan-400/20 blur-md rounded-full"
                style={{ width: `${progress}%` }}
              />
            </div>

            {/* Matrix-style hash display */}
            <div className="font-mono text-[10px] text-cyan-400/60 break-all max-w-xs">
              {hashChars}
            </div>

            <p className="text-sm text-muted-foreground">
              Signing with HMAC-SHA256...
            </p>
          </>
        ) : (
          <motion.div
            initial={{ scale: 0.8, opacity: 0 }}
            animate={{ scale: 1, opacity: 1 }}
            className="flex flex-col items-center gap-2"
          >
            <CheckCircle2 className="h-12 w-12 text-green-400" />
            <span className="text-green-400 font-semibold">
              Mandate Signed
            </span>
          </motion.div>
        )}
      </div>
    </motion.div>
  );
}

export default SignatureAnimation;
