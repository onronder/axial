'use client';

import { useEffect, useState } from 'react';
import { motion, AnimatePresence } from 'framer-motion';
import { FileText } from 'lucide-react';

interface ShredderAnimationProps {
  documentName: string;
  documentId: string;
  onComplete: () => void;
}

export function ShredderAnimation({
  documentName,
  documentId,
  onComplete,
}: ShredderAnimationProps) {
  const [phase, setPhase] = useState<'document' | 'shredding' | 'ghost'>('document');
  const stripCount = 12;

  useEffect(() => {
    const timer1 = setTimeout(() => setPhase('shredding'), 500);
    const timer2 = setTimeout(() => setPhase('ghost'), 2000);
    const timer3 = setTimeout(onComplete, 3500);

    return () => {
      clearTimeout(timer1);
      clearTimeout(timer2);
      clearTimeout(timer3);
    };
  }, [onComplete]);

  return (
    <div className="relative w-64 h-80 flex items-center justify-center">
      <AnimatePresence mode="wait">
        {/* Phase 1: Document */}
        {phase === 'document' && (
          <motion.div
            key="document"
            initial={{ opacity: 0, scale: 0.8 }}
            animate={{ opacity: 1, scale: 1 }}
            exit={{ opacity: 0 }}
            className="absolute inset-0 flex flex-col items-center justify-center"
          >
            <div className="relative">
              <div className="w-32 h-40 bg-white/10 rounded-lg border border-white/20 flex flex-col items-center justify-center gap-2 backdrop-blur-sm">
                <FileText className="h-12 w-12 text-cyan-400" />
                <span className="text-xs text-muted-foreground px-2 text-center truncate w-full">
                  {documentName}
                </span>
              </div>

              {/* Glow effect */}
              <div className="absolute inset-0 bg-cyan-500/20 rounded-lg blur-xl animate-pulse" />
            </div>
          </motion.div>
        )}

        {/* Phase 2: Shredding */}
        {phase === 'shredding' && (
          <motion.div
            key="shredding"
            className="absolute inset-0 flex items-center justify-center"
          >
            <div className="relative w-32 h-40 overflow-hidden">
              {Array.from({ length: stripCount }).map((_, i) => (
                <motion.div
                  key={i}
                  initial={{ y: 0, opacity: 1, rotateZ: 0 }}
                  animate={{
                    y: [0, 20, 200],
                    opacity: [1, 1, 0],
                    rotateZ: [0, (i % 2 ? 5 : -5), (i % 2 ? 15 : -15)],
                    x: [0, (i - stripCount / 2) * 2, (i - stripCount / 2) * 8],
                  }}
                  transition={{
                    duration: 1.5,
                    delay: i * 0.05,
                    ease: 'easeIn',
                  }}
                  className="absolute bg-gradient-to-b from-white/20 to-white/5 border-x border-white/10"
                  style={{
                    left: `${(i / stripCount) * 100}%`,
                    width: `${100 / stripCount}%`,
                    height: '100%',
                  }}
                />
              ))}
            </div>

            {/* Shredder visualization */}
            <div className="absolute bottom-0 w-40 h-8 bg-zinc-800 rounded-t-lg border-t-2 border-red-500/50 flex items-center justify-center">
              <div className="flex gap-0.5">
                {Array.from({ length: 20 }).map((_, i) => (
                  <div
                    key={i}
                    className="w-0.5 h-4 bg-zinc-600 animate-pulse"
                    style={{ animationDelay: `${i * 50}ms` }}
                  />
                ))}
              </div>
            </div>
          </motion.div>
        )}

        {/* Phase 3: Ghost (Vector ID remains) */}
        {phase === 'ghost' && (
          <motion.div
            key="ghost"
            initial={{ opacity: 0, scale: 0.8 }}
            animate={{ opacity: 1, scale: 1 }}
            className="absolute inset-0 flex flex-col items-center justify-center gap-4"
          >
            {/* Ghost outline */}
            <div className="relative">
              <div className="w-32 h-40 border-2 border-dashed border-cyan-500/30 rounded-lg flex items-center justify-center">
                <div className="text-center">
                  <div className="text-cyan-500/50 text-xs font-mono mb-2">
                    SECURELY WIPED
                  </div>
                  <div className="text-[10px] text-muted-foreground font-mono">
                    ID: {documentId.slice(0, 8)}...
                  </div>
                </div>
              </div>

              {/* Fading ghost effect */}
              <motion.div
                initial={{ opacity: 0.3 }}
                animate={{ opacity: 0 }}
                transition={{ duration: 2 }}
                className="absolute inset-0 bg-gradient-to-b from-cyan-500/10 to-transparent rounded-lg"
              />
            </div>

            {/* Success badge */}
            <motion.div
              initial={{ y: 10, opacity: 0 }}
              animate={{ y: 0, opacity: 1 }}
              transition={{ delay: 0.5 }}
              className="flex items-center gap-2 text-green-400 text-sm font-mono"
            >
              <span className="w-2 h-2 rounded-full bg-green-400 animate-pulse" />
              DoD 5220.22-M Verified
            </motion.div>
          </motion.div>
        )}
      </AnimatePresence>
    </div>
  );
}

export default ShredderAnimation;
