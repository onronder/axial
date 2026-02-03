'use client';

import { Eye, Image as ImageIcon } from 'lucide-react';
import { Badge } from '@/components/ui/badge';
import {
  Tooltip,
  TooltipContent,
  TooltipTrigger,
} from '@/components/ui/tooltip';
import { cn } from '@/lib/utils';

interface VisionVerifiedBadgeProps {
  diagramType: 'flowchart' | 'architecture' | 'chart' | 'schematic' | 'er_diagram' | 'uml' | 'unknown';
  confidence: number;
  modelUsed: string;
  onClick?: () => void;
  className?: string;
}

const DIAGRAM_LABELS: Record<string, string> = {
  flowchart: 'Flowchart',
  architecture: 'Architecture Diagram',
  chart: 'Chart/Graph',
  schematic: 'Technical Schematic',
  er_diagram: 'ER Diagram',
  uml: 'UML Diagram',
  unknown: 'Visual',
};

export function VisionVerifiedBadge({
  diagramType,
  confidence,
  modelUsed,
  onClick,
  className,
}: VisionVerifiedBadgeProps) {
  return (
    <Tooltip>
      <TooltipTrigger asChild>
        <Badge
          variant="outline"
          className={cn(
            'gap-1.5 cursor-pointer',
            'border-violet-500/30 bg-violet-500/10 text-violet-400',
            'hover:bg-violet-500/20 hover:border-violet-500/50',
            'transition-all duration-200',
            className
          )}
          onClick={onClick}
        >
          <Eye className="h-3 w-3" />
          <span className="text-[10px] font-mono">
            Vision Verified
          </span>
        </Badge>
      </TooltipTrigger>
      <TooltipContent
        side="top"
        className="max-w-xs bg-black/95 border-violet-500/30"
      >
        <div className="space-y-2 text-xs">
          <div className="flex items-center gap-2">
            <ImageIcon className="h-4 w-4 text-violet-400" />
            <span className="font-semibold text-violet-400">
              {DIAGRAM_LABELS[diagramType]}
            </span>
          </div>

          <div className="space-y-1 text-muted-foreground">
            <p>This source contains visual content that was</p>
            <p>semantically analyzed by AI vision model.</p>
          </div>

          <div className="flex items-center justify-between pt-1 border-t border-violet-500/20 text-[10px]">
            <span className="text-muted-foreground">
              Model: <span className="text-violet-400">{modelUsed}</span>
            </span>
            <span className="text-muted-foreground">
              Confidence: <span className="text-violet-400">{Math.round(confidence * 100)}%</span>
            </span>
          </div>

          <p className="text-[10px] text-violet-400/60">
            Click to view semantic description
          </p>
        </div>
      </TooltipContent>
    </Tooltip>
  );
}

export default VisionVerifiedBadge;
