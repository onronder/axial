'use client';

import {
  Dialog,
  DialogContent,
  DialogHeader,
  DialogTitle,
} from '@/components/ui/dialog';
import { Badge } from '@/components/ui/badge';
import { Separator } from '@/components/ui/separator';
import {
  Eye,
  Image as ImageIcon,
  Shield,
  Brain,
} from 'lucide-react';

interface DiagramPreviewModalProps {
  isOpen: boolean;
  onClose: () => void;
  documentTitle: string;
  diagramType: string;
  description: string;
  entities: string[];
  relationships: string[];
  confidence: number;
  modelUsed: string;
}

export function DiagramPreviewModal({
  isOpen,
  onClose,
  documentTitle,
  diagramType,
  description,
  entities,
  relationships,
  confidence,
  modelUsed,
}: DiagramPreviewModalProps) {
  return (
    <Dialog open={isOpen} onOpenChange={(open) => !open && onClose()}>
      <DialogContent className="max-w-2xl bg-black/95 border-violet-500/30">
        <DialogHeader>
          <DialogTitle className="flex items-center gap-2 text-violet-400">
            <Eye className="h-5 w-5" />
            Vision Analysis: {documentTitle}
          </DialogTitle>
        </DialogHeader>

        <div className="grid grid-cols-1 md:grid-cols-[1fr,1.5fr] gap-6">
          {/* Left: Placeholder / Info */}
          <div className="space-y-4">
            {/* Image placeholder */}
            <div className="aspect-[4/5] rounded-lg border border-dashed border-violet-500/30 bg-violet-500/5 flex flex-col items-center justify-center gap-3">
              <ImageIcon className="h-12 w-12 text-violet-500/30" />
              <p className="text-xs text-center text-muted-foreground px-4">
                Original image securely wiped after processing
              </p>
              <Badge variant="outline" className="text-green-400 border-green-500/30">
                <Shield className="h-3 w-3 mr-1" />
                Ghost Protocol
              </Badge>
            </div>

            {/* Metadata */}
            <div className="space-y-2 text-xs">
              <div className="flex justify-between">
                <span className="text-muted-foreground">Diagram Type</span>
                <Badge variant="secondary" className="capitalize">
                  {diagramType.replace('_', ' ')}
                </Badge>
              </div>
              <div className="flex justify-between">
                <span className="text-muted-foreground">Confidence</span>
                <span className="text-violet-400 font-mono">
                  {Math.round(confidence * 100)}%
                </span>
              </div>
              <div className="flex justify-between">
                <span className="text-muted-foreground">Analyzed by</span>
                <span className="text-violet-400">{modelUsed}</span>
              </div>
            </div>
          </div>

          {/* Right: Semantic Description */}
          <div className="space-y-4">
            {/* Description */}
            <div className="space-y-2">
              <h4 className="text-sm font-medium flex items-center gap-2">
                <Brain className="h-4 w-4 text-violet-400" />
                Semantic Description
              </h4>
              <p className="text-sm text-muted-foreground leading-relaxed">
                {description}
              </p>
            </div>

            <Separator className="bg-violet-500/20" />

            {/* Entities */}
            {entities.length > 0 && (
              <div className="space-y-2">
                <h4 className="text-sm font-medium">Identified Entities</h4>
                <div className="flex flex-wrap gap-2">
                  {entities.map((entity, i) => (
                    <Badge
                      key={i}
                      variant="outline"
                      className="bg-violet-500/10 border-violet-500/30"
                    >
                      {entity}
                    </Badge>
                  ))}
                </div>
              </div>
            )}

            {/* Relationships */}
            {relationships.length > 0 && (
              <div className="space-y-2">
                <h4 className="text-sm font-medium">Relationships</h4>
                <ul className="text-sm text-muted-foreground space-y-1">
                  {relationships.map((rel, i) => (
                    <li key={i} className="flex items-start gap-2">
                      <span className="text-violet-400">&rarr;</span>
                      {rel}
                    </li>
                  ))}
                </ul>
              </div>
            )}
          </div>
        </div>
      </DialogContent>
    </Dialog>
  );
}

export default DiagramPreviewModal;
