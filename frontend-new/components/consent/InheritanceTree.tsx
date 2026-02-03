'use client';

import { useState } from 'react';
import { motion, AnimatePresence } from 'framer-motion';
import {
  Building,
  Folder,
  FileText,
  ChevronRight,
  ChevronDown,
  Check,
  X,
  Minus,
} from 'lucide-react';
import { Badge } from '@/components/ui/badge';
import { Button } from '@/components/ui/button';
import { cn } from '@/lib/utils';

import type { OrgConsent, ScopeConsent, DocumentConsent } from '@/hooks/useConsent';

interface InheritanceTreeProps {
  orgConsent: OrgConsent | null;
  scopeConsents: ScopeConsent[] | null;
  documentConsents: DocumentConsent[] | null;
  onScopeClick?: (scopeId: string) => void;
  onDocumentClick?: (documentId: string) => void;
}

function ConsentIndicator({ value }: { value: boolean | null }) {
  if (value === null) {
    return (
      <div className="flex items-center gap-1 text-muted-foreground">
        <Minus className="h-3 w-3" />
        <span className="text-[10px]">Inherited</span>
      </div>
    );
  }
  return value ? (
    <div className="flex items-center gap-1 text-green-400">
      <Check className="h-3 w-3" />
      <span className="text-[10px]">ON</span>
    </div>
  ) : (
    <div className="flex items-center gap-1 text-red-400">
      <X className="h-3 w-3" />
      <span className="text-[10px]">OFF</span>
    </div>
  );
}

function TreeNode({
  icon: Icon,
  label,
  level,
  isExpanded,
  onToggle,
  hasChildren,
  aiLearning,
  externalAgents,
  inherits,
  onClick,
}: {
  icon: typeof Building;
  label: string;
  level: number;
  isExpanded?: boolean;
  onToggle?: () => void;
  hasChildren?: boolean;
  aiLearning: boolean | null;
  externalAgents: boolean | null;
  inherits?: boolean;
  onClick?: () => void;
}) {
  const paddingLeft = level * 24;

  return (
    <div
      className={cn(
        'flex items-center gap-2 py-2 px-3 rounded-lg transition-colors',
        'hover:bg-muted/20 cursor-pointer group',
        level === 0 && 'bg-cyan-500/5 border border-cyan-500/20'
      )}
      style={{ paddingLeft: `${paddingLeft + 12}px` }}
      onClick={onClick}
    >
      {/* Expand/collapse button */}
      {hasChildren && (
        <Button
          variant="ghost"
          size="icon"
          className="h-5 w-5 p-0"
          onClick={(e) => {
            e.stopPropagation();
            onToggle?.();
          }}
        >
          {isExpanded ? (
            <ChevronDown className="h-4 w-4" />
          ) : (
            <ChevronRight className="h-4 w-4" />
          )}
        </Button>
      )}
      {!hasChildren && <div className="w-5" />}

      {/* Icon */}
      <Icon className={cn(
        'h-4 w-4',
        level === 0 ? 'text-cyan-400' :
        level === 1 ? 'text-violet-400' :
        'text-muted-foreground'
      )} />

      {/* Label */}
      <span className="flex-1 text-sm truncate">{label}</span>

      {/* Inheritance badge */}
      {inherits && (
        <Badge variant="outline" className="text-[9px] px-1.5 py-0">
          Inherits
        </Badge>
      )}

      {/* Consent indicators */}
      <div className="flex items-center gap-4 opacity-70 group-hover:opacity-100">
        <div className="flex items-center gap-1">
          <span className="text-[9px] text-muted-foreground">AI:</span>
          <ConsentIndicator value={aiLearning} />
        </div>
        <div className="flex items-center gap-1">
          <span className="text-[9px] text-muted-foreground">Agents:</span>
          <ConsentIndicator value={externalAgents} />
        </div>
      </div>
    </div>
  );
}

export function InheritanceTree({
  orgConsent,
  scopeConsents,
  documentConsents,
  onScopeClick,
  onDocumentClick,
}: InheritanceTreeProps) {
  const [expandedScopes, setExpandedScopes] = useState<Set<string>>(new Set());

  const toggleScope = (scopeId: string) => {
    setExpandedScopes(prev => {
      const next = new Set(prev);
      if (next.has(scopeId)) {
        next.delete(scopeId);
      } else {
        next.add(scopeId);
      }
      return next;
    });
  };

  const getDocumentsForScope = (scopeId: string) => {
    return documentConsents?.filter(doc => doc.scopeId === scopeId) || [];
  };

  return (
    <div className="space-y-1 rounded-lg border border-border/50 p-4">
      {/* Organization level */}
      {orgConsent && (
        <TreeNode
          icon={Building}
          label="Organization Default"
          level={0}
          aiLearning={orgConsent.allowAiLearning}
          externalAgents={orgConsent.allowExternalAgents}
        />
      )}

      {/* Scopes */}
      {scopeConsents?.map((scope) => {
        const isExpanded = expandedScopes.has(scope.scopeId);
        const documents = getDocumentsForScope(scope.scopeId);
        const hasDocuments = documents.length > 0;

        return (
          <div key={scope.scopeId}>
            <TreeNode
              icon={Folder}
              label={scope.scopeName}
              level={1}
              isExpanded={isExpanded}
              onToggle={() => toggleScope(scope.scopeId)}
              hasChildren={hasDocuments}
              aiLearning={scope.allowAiLearning}
              externalAgents={scope.allowExternalAgents}
              inherits={scope.inherits}
              onClick={() => onScopeClick?.(scope.scopeId)}
            />

            {/* Documents under this scope */}
            <AnimatePresence>
              {isExpanded && hasDocuments && (
                <motion.div
                  initial={{ height: 0, opacity: 0 }}
                  animate={{ height: 'auto', opacity: 1 }}
                  exit={{ height: 0, opacity: 0 }}
                  className="overflow-hidden"
                >
                  {documents.map((doc) => (
                    <TreeNode
                      key={doc.documentId}
                      icon={FileText}
                      label={doc.documentName || doc.documentId.slice(0, 12) + '...'}
                      level={2}
                      aiLearning={doc.allowAiLearning}
                      externalAgents={doc.allowExternalAgents}
                      inherits={doc.inherits}
                      onClick={() => onDocumentClick?.(doc.documentId)}
                    />
                  ))}
                </motion.div>
              )}
            </AnimatePresence>
          </div>
        );
      })}

      {/* Empty state */}
      {(!scopeConsents || scopeConsents.length === 0) && (
        <div className="text-center py-8 text-muted-foreground">
          <Folder className="h-8 w-8 mx-auto mb-2 opacity-50" />
          <p className="text-sm">No scopes configured</p>
          <p className="text-xs">All data inherits organization defaults</p>
        </div>
      )}
    </div>
  );
}

export default InheritanceTree;
