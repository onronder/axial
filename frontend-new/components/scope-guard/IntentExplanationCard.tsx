'use client';

import { useState } from 'react';
import { motion, AnimatePresence } from 'framer-motion';
import { Brain, FileText, ChevronDown, ChevronUp } from 'lucide-react';
import { Button } from '@/components/ui/button';
import { cn } from '@/lib/utils';

interface IntentExplanationCardProps {
  reason: string;
  affectedDocuments?: Array<{ id: string; name: string }>;
  className?: string;
}

export function IntentExplanationCard({
  reason,
  affectedDocuments,
  className,
}: IntentExplanationCardProps) {
  const [showDocuments, setShowDocuments] = useState(false);

  return (
    <div className={cn(
      'p-4 rounded-lg bg-violet-500/10 border border-violet-500/30',
      className
    )}>
      <div className="flex items-start gap-3">
        <Brain className="h-5 w-5 text-violet-400 mt-0.5" />
        <div className="space-y-3 flex-1">
          <div className="flex items-center gap-2">
            <span className="text-sm font-medium text-violet-400">
              Agent&apos;s Reasoning
            </span>
          </div>

          <p className="text-sm text-muted-foreground leading-relaxed">
            &ldquo;{reason}&rdquo;
          </p>

          {/* Affected documents list */}
          {affectedDocuments && affectedDocuments.length > 0 && (
            <div className="space-y-2">
              <Button
                variant="ghost"
                size="sm"
                className="h-auto p-0 text-violet-400 hover:text-violet-300"
                onClick={() => setShowDocuments(!showDocuments)}
              >
                <FileText className="h-4 w-4 mr-1" />
                <span className="text-xs">
                  {affectedDocuments.length} documents affected
                </span>
                {showDocuments ? (
                  <ChevronUp className="h-3 w-3 ml-1" />
                ) : (
                  <ChevronDown className="h-3 w-3 ml-1" />
                )}
              </Button>

              <AnimatePresence>
                {showDocuments && (
                  <motion.div
                    initial={{ height: 0, opacity: 0 }}
                    animate={{ height: 'auto', opacity: 1 }}
                    exit={{ height: 0, opacity: 0 }}
                    className="overflow-hidden"
                  >
                    <ul className="text-xs text-muted-foreground space-y-1 pl-4 border-l border-violet-500/30">
                      {affectedDocuments.slice(0, 5).map((doc) => (
                        <li key={doc.id} className="truncate">
                          &bull; {doc.name}
                        </li>
                      ))}
                      {affectedDocuments.length > 5 && (
                        <li className="text-violet-400">
                          +{affectedDocuments.length - 5} more...
                        </li>
                      )}
                    </ul>
                  </motion.div>
                )}
              </AnimatePresence>
            </div>
          )}
        </div>
      </div>
    </div>
  );
}

export default IntentExplanationCard;
