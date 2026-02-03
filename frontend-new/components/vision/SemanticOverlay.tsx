'use client';

import { useState } from 'react';
import { motion, AnimatePresence } from 'framer-motion';
import { Eye, X } from 'lucide-react';
import { Badge } from '@/components/ui/badge';
import { Button } from '@/components/ui/button';
import { cn } from '@/lib/utils';

interface Entity {
  id: string;
  name: string;
  type: string;
  boundingBox?: {
    x: number;
    y: number;
    width: number;
    height: number;
  };
  description?: string;
}

interface SemanticOverlayProps {
  entities: Entity[];
  isActive: boolean;
  onToggle: () => void;
  onEntityClick?: (entity: Entity) => void;
  className?: string;
}

export function SemanticOverlay({
  entities,
  isActive,
  onToggle,
  onEntityClick,
  className,
}: SemanticOverlayProps) {
  const [hoveredEntity, setHoveredEntity] = useState<string | null>(null);

  return (
    <div className={cn('relative', className)}>
      {/* Toggle button */}
      <Button
        variant="ghost"
        size="sm"
        onClick={onToggle}
        className={cn(
          'absolute top-2 right-2 z-10 gap-1.5',
          isActive && 'bg-violet-500/20 text-violet-400'
        )}
      >
        {isActive ? (
          <X className="h-4 w-4" />
        ) : (
          <Eye className="h-4 w-4" />
        )}
        <span className="text-xs">{isActive ? 'Hide' : 'Show'} Entities</span>
      </Button>

      {/* Entity overlays */}
      <AnimatePresence>
        {isActive && entities.map((entity) => {
          if (!entity.boundingBox) return null;

          const isHovered = hoveredEntity === entity.id;

          return (
            <motion.div
              key={entity.id}
              initial={{ opacity: 0 }}
              animate={{ opacity: 1 }}
              exit={{ opacity: 0 }}
              className={cn(
                'absolute cursor-pointer transition-all duration-200',
                'border-2 rounded',
                isHovered
                  ? 'border-violet-400 bg-violet-500/20'
                  : 'border-violet-500/40 bg-violet-500/10'
              )}
              style={{
                left: `${entity.boundingBox.x}%`,
                top: `${entity.boundingBox.y}%`,
                width: `${entity.boundingBox.width}%`,
                height: `${entity.boundingBox.height}%`,
              }}
              onMouseEnter={() => setHoveredEntity(entity.id)}
              onMouseLeave={() => setHoveredEntity(null)}
              onClick={() => onEntityClick?.(entity)}
            >
              {/* Entity label */}
              <div className={cn(
                'absolute -top-6 left-0 transition-all duration-200',
                isHovered ? 'opacity-100' : 'opacity-70'
              )}>
                <Badge
                  variant="outline"
                  className={cn(
                    'text-[10px] whitespace-nowrap',
                    'bg-black/80 border-violet-500/50 text-violet-400'
                  )}
                >
                  {entity.name}
                </Badge>
              </div>

              {/* Hover tooltip */}
              <AnimatePresence>
                {isHovered && entity.description && (
                  <motion.div
                    initial={{ opacity: 0, y: 5 }}
                    animate={{ opacity: 1, y: 0 }}
                    exit={{ opacity: 0, y: 5 }}
                    className="absolute top-full left-0 mt-2 z-20 w-48"
                  >
                    <div className="bg-black/95 border border-violet-500/30 rounded-lg p-2 text-xs">
                      <p className="text-violet-400 font-medium mb-1">{entity.type}</p>
                      <p className="text-muted-foreground">{entity.description}</p>
                    </div>
                  </motion.div>
                )}
              </AnimatePresence>
            </motion.div>
          );
        })}
      </AnimatePresence>

      {/* Entity count indicator */}
      {isActive && entities.length > 0 && (
        <div className="absolute bottom-2 left-2">
          <Badge variant="secondary" className="text-xs">
            {entities.length} entities detected
          </Badge>
        </div>
      )}
    </div>
  );
}

export default SemanticOverlay;
