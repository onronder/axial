'use client';

import { useState } from 'react';
import { motion, AnimatePresence } from 'framer-motion';
import { ExternalLink, Image as ImageIcon, Table2, BarChart3 } from 'lucide-react';
import {
  Tooltip,
  TooltipContent,
  TooltipTrigger,
} from '@/components/ui/tooltip';
import { cn } from '@/lib/utils';

type ReferenceType = 'table' | 'figure' | 'chart' | 'diagram';

interface SmartLinkProps {
  type: ReferenceType;
  number: number;
  documentId: string;
  label?: string;
  description?: string;
  onClick?: () => void;
  className?: string;
}

const TYPE_CONFIG: Record<ReferenceType, { icon: typeof Table2; label: string; color: string }> = {
  table: { icon: Table2, label: 'Table', color: 'text-cyan-400 border-cyan-500/30 bg-cyan-500/10' },
  figure: { icon: ImageIcon, label: 'Figure', color: 'text-violet-400 border-violet-500/30 bg-violet-500/10' },
  chart: { icon: BarChart3, label: 'Chart', color: 'text-amber-400 border-amber-500/30 bg-amber-500/10' },
  diagram: { icon: ImageIcon, label: 'Diagram', color: 'text-green-400 border-green-500/30 bg-green-500/10' },
};

// Regex pattern to detect references in text
export const REFERENCE_PATTERN = /(Table|Figure|Chart|Diagram)\s+(\d+)/gi;

// Helper function to parse references from text
export function parseReferences(text: string): Array<{ type: ReferenceType; number: number; match: string }> {
  const references: Array<{ type: ReferenceType; number: number; match: string }> = [];
  let match;

  while ((match = REFERENCE_PATTERN.exec(text)) !== null) {
    references.push({
      type: match[1].toLowerCase() as ReferenceType,
      number: parseInt(match[2], 10),
      match: match[0],
    });
  }

  return references;
}

export function SmartLink({
  type,
  number,
  documentId,
  label,
  description,
  onClick,
  className,
}: SmartLinkProps) {
  const [isHovered, setIsHovered] = useState(false);
  const config = TYPE_CONFIG[type];
  const Icon = config.icon;
  const displayLabel = label || `${config.label} ${number}`;

  return (
    <Tooltip>
      <TooltipTrigger asChild>
        <motion.button
          className={cn(
            'inline-flex items-center gap-1 px-1.5 py-0.5 rounded border text-xs font-medium',
            'transition-all duration-200 cursor-pointer',
            'hover:scale-105',
            config.color,
            className
          )}
          onClick={onClick}
          onMouseEnter={() => setIsHovered(true)}
          onMouseLeave={() => setIsHovered(false)}
          whileHover={{ scale: 1.02 }}
          whileTap={{ scale: 0.98 }}
        >
          <Icon className="h-3 w-3" />
          <span>{displayLabel}</span>
          <AnimatePresence>
            {isHovered && (
              <motion.span
                initial={{ opacity: 0, width: 0 }}
                animate={{ opacity: 1, width: 'auto' }}
                exit={{ opacity: 0, width: 0 }}
              >
                <ExternalLink className="h-3 w-3" />
              </motion.span>
            )}
          </AnimatePresence>
        </motion.button>
      </TooltipTrigger>
      <TooltipContent side="top" className="max-w-xs">
        <div className="space-y-1">
          <p className="font-medium">{displayLabel}</p>
          {description && (
            <p className="text-xs text-muted-foreground">{description}</p>
          )}
          <p className="text-[10px] text-muted-foreground">
            Click to view in document
          </p>
        </div>
      </TooltipContent>
    </Tooltip>
  );
}

// Component to render text with smart links
interface SmartTextProps {
  text: string;
  documentId: string;
  onReferenceClick?: (type: ReferenceType, number: number) => void;
}

export function SmartText({ text, documentId, onReferenceClick }: SmartTextProps) {
  const parts: Array<{ text: string; isReference: boolean; type?: ReferenceType; number?: number }> = [];
  let lastIndex = 0;
  let match;

  // Reset regex state
  REFERENCE_PATTERN.lastIndex = 0;

  while ((match = REFERENCE_PATTERN.exec(text)) !== null) {
    // Add text before the match
    if (match.index > lastIndex) {
      parts.push({ text: text.slice(lastIndex, match.index), isReference: false });
    }

    // Add the reference
    parts.push({
      text: match[0],
      isReference: true,
      type: match[1].toLowerCase() as ReferenceType,
      number: parseInt(match[2], 10),
    });

    lastIndex = match.index + match[0].length;
  }

  // Add remaining text
  if (lastIndex < text.length) {
    parts.push({ text: text.slice(lastIndex), isReference: false });
  }

  return (
    <span>
      {parts.map((part, index) =>
        part.isReference ? (
          <SmartLink
            key={index}
            type={part.type!}
            number={part.number!}
            documentId={documentId}
            onClick={() => onReferenceClick?.(part.type!, part.number!)}
          />
        ) : (
          <span key={index}>{part.text}</span>
        )
      )}
    </span>
  );
}

export default SmartLink;
