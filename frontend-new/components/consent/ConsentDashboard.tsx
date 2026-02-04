'use client';

import { useState, useMemo, useCallback } from 'react';
import { Shield, Building, Folder, FileText, Settings, RotateCcw, History } from 'lucide-react';
import { Card, CardContent, CardHeader, CardTitle, CardDescription } from '@/components/ui/card';
import { Tabs, TabsContent, TabsList, TabsTrigger } from '@/components/ui/tabs';
import { Button } from '@/components/ui/button';
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from '@/components/ui/select';
import { ConsentToggle } from './ConsentToggle';
import { InheritanceTree } from './InheritanceTree';
import { AgentAccessPanel } from './AgentAccessPanel';
import { ComplianceScoreWidget } from './ComplianceScoreWidget';
import { ConsentAuditPanel } from './ConsentAuditPanel';
import { SettingsPageHeader } from '@/components/settings/SettingsPageHeader';
import { useConsent, type AgentAction, type ScopeConsent } from '@/hooks/useConsent';
import { useToast } from '@/hooks/use-toast';

// =============================================================================
// Types
// =============================================================================

interface Agent {
  id: string;
  name: string;
  agentId: string;
  isAllowed: boolean;
  createdAt: string;
  lastAccess?: string;
}

// =============================================================================
// Helper Functions
// =============================================================================

/**
 * Transform scope consent agent lists into Agent objects for AgentAccessPanel
 */
function transformScopeAgentsToDisplayFormat(scope: ScopeConsent): Agent[] {
  const agents: Agent[] = [];
  const now = new Date().toISOString();

  // Add allowed agents
  for (const agentId of scope.allowedAgentIds) {
    agents.push({
      id: agentId,
      name: formatAgentName(agentId),
      agentId,
      isAllowed: true,
      createdAt: now,
    });
  }

  // Add blocked agents
  for (const agentId of scope.blockedAgentIds) {
    // Skip if already in allowed (shouldn't happen, but safety check)
    if (scope.allowedAgentIds.includes(agentId)) continue;
    agents.push({
      id: agentId,
      name: formatAgentName(agentId),
      agentId,
      isAllowed: false,
      createdAt: now,
    });
  }

  return agents;
}

/**
 * Format agent ID into a display-friendly name
 * e.g., "agent_claude_desktop_abc123" -> "Claude Desktop"
 */
function formatAgentName(agentId: string): string {
  // Remove common prefixes
  let name = agentId
    .replace(/^agent_/i, '')
    .replace(/^mcp_/i, '')
    .replace(/_[a-z0-9]{6,}$/i, ''); // Remove trailing hash

  // Convert snake_case to Title Case
  name = name
    .split('_')
    .map((word) => word.charAt(0).toUpperCase() + word.slice(1).toLowerCase())
    .join(' ');

  return name || agentId;
}

// =============================================================================
// Component
// =============================================================================

export function ConsentDashboard() {
  const { toast } = useToast();
  const {
    orgConsent,
    scopeConsents,
    documentConsents,
    updateOrgConsent,
    updateScopeConsent,
    updateDocumentConsent,
    resetScopeConsent,
    resetDocumentConsent,
    updateScopeAgentAccess,
    complianceReport,
    isLoading,
    isUpdatingOrg,
    isUpdatingScopeAgent,
    isResettingScope,
    isResettingDocument,
  } = useConsent();

  // State for selected scope in agent management
  const [selectedScopeId, setSelectedScopeId] = useState<string | null>(null);

  // Get the currently selected scope
  const selectedScope = useMemo(() => {
    if (!scopeConsents || scopeConsents.length === 0) return null;
    if (selectedScopeId) {
      return scopeConsents.find((s) => s.scopeId === selectedScopeId) || scopeConsents[0];
    }
    return scopeConsents[0];
  }, [scopeConsents, selectedScopeId]);

  // Transform selected scope's agents for display
  const scopeAgents = useMemo(() => {
    if (!selectedScope) return [];
    return transformScopeAgentsToDisplayFormat(selectedScope);
  }, [selectedScope]);

  // ==========================================================================
  // Handlers - Agent Access Management
  // ==========================================================================

  const handleToggleAgentAccess = useCallback(
    async (agentId: string, allowed: boolean) => {
      if (!selectedScope) return;

      const action: AgentAction = allowed ? 'allow' : 'block';

      try {
        await updateScopeAgentAccess(selectedScope.scopeId, action, agentId);
        toast({
          title: 'Agent access updated',
          description: `Agent ${allowed ? 'allowed' : 'blocked'} for ${selectedScope.scopeName}`,
        });
      } catch (error) {
        toast({
          title: 'Failed to update agent access',
          description: error instanceof Error ? error.message : 'Unknown error',
          variant: 'destructive',
        });
      }
    },
    [selectedScope, updateScopeAgentAccess, toast]
  );

  const handleAddAgent = useCallback(
    async (name: string, agentId: string) => {
      if (!selectedScope) return;

      try {
        await updateScopeAgentAccess(selectedScope.scopeId, 'allow', agentId);
        toast({
          title: 'Agent added',
          description: `${name} now has access to ${selectedScope.scopeName}`,
        });
      } catch (error) {
        toast({
          title: 'Failed to add agent',
          description: error instanceof Error ? error.message : 'Unknown error',
          variant: 'destructive',
        });
      }
    },
    [selectedScope, updateScopeAgentAccess, toast]
  );

  const handleRemoveAgent = useCallback(
    async (agentId: string) => {
      if (!selectedScope) return;

      try {
        await updateScopeAgentAccess(selectedScope.scopeId, 'remove', agentId);
        toast({
          title: 'Agent removed',
          description: `Agent removed from ${selectedScope.scopeName}`,
        });
      } catch (error) {
        toast({
          title: 'Failed to remove agent',
          description: error instanceof Error ? error.message : 'Unknown error',
          variant: 'destructive',
        });
      }
    },
    [selectedScope, updateScopeAgentAccess, toast]
  );

  // ==========================================================================
  // Handlers - Consent Reset
  // ==========================================================================

  const handleResetScopeConsent = useCallback(
    async (scopeId: string, scopeName: string) => {
      try {
        await resetScopeConsent(scopeId);
        toast({
          title: 'Consent reset',
          description: `${scopeName} now inherits organization defaults`,
        });
      } catch (error) {
        toast({
          title: 'Failed to reset consent',
          description: error instanceof Error ? error.message : 'Unknown error',
          variant: 'destructive',
        });
      }
    },
    [resetScopeConsent, toast]
  );

  const handleResetDocumentConsent = useCallback(
    async (documentId: string, documentName: string) => {
      try {
        await resetDocumentConsent(documentId);
        toast({
          title: 'Consent reset',
          description: `${documentName} now inherits scope defaults`,
        });
      } catch (error) {
        toast({
          title: 'Failed to reset consent',
          description: error instanceof Error ? error.message : 'Unknown error',
          variant: 'destructive',
        });
      }
    },
    [resetDocumentConsent, toast]
  );

  // ==========================================================================
  // Handlers - Consent Update
  // ==========================================================================

  const handleUpdateOrgConsent = useCallback(
    async (consentType: 'ai_learning' | 'external_agents', enabled: boolean) => {
      try {
        await updateOrgConsent(consentType, enabled);
        toast({
          title: 'Organization consent updated',
          description: `${consentType === 'ai_learning' ? 'AI Learning' : 'External Agents'} ${enabled ? 'enabled' : 'disabled'}`,
        });
      } catch (error) {
        toast({
          title: 'Failed to update consent',
          description: error instanceof Error ? error.message : 'Unknown error',
          variant: 'destructive',
        });
      }
    },
    [updateOrgConsent, toast]
  );

  const handleUpdateDocumentConsent = useCallback(
    async (
      documentId: string,
      consentType: 'ai_learning' | 'external_agents',
      enabled: boolean | null
    ) => {
      try {
        await updateDocumentConsent(documentId, consentType, enabled, false);
        toast({
          title: 'Document consent updated',
        });
      } catch (error) {
        toast({
          title: 'Failed to update consent',
          description: error instanceof Error ? error.message : 'Unknown error',
          variant: 'destructive',
        });
      }
    },
    [updateDocumentConsent, toast]
  );

  // ==========================================================================
  // Render
  // ==========================================================================

  if (isLoading) {
    return <ConsentDashboardSkeleton />;
  }

  return (
    <div className="space-y-6">
      <SettingsPageHeader
        icon={Shield}
        title="Consent"
        description="KVKK 2026 compliant granular controls"
        badge={<ComplianceScoreWidget score={complianceReport?.complianceScore || 0} />}
        autoSaveNote
      />

      {/* Organization Defaults */}
      <Card className="border-cyan-500/20">
        <CardHeader>
          <CardTitle className="flex items-center gap-2 text-lg">
            <Building className="h-5 w-5 text-cyan-400" />
            Organization Defaults
          </CardTitle>
          <CardDescription>
            These settings apply to all data unless overridden at scope or document level
          </CardDescription>
        </CardHeader>
        <CardContent>
          <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
            <ConsentToggle
              label="AI Learning"
              description="Allow data to be used for AI model improvement"
              enabled={orgConsent?.allowAiLearning || false}
              onChange={(enabled) => handleUpdateOrgConsent('ai_learning', enabled)}
              consentedAt={orgConsent?.aiLearningConsentAt}
              disabled={isUpdatingOrg}
            />
            <ConsentToggle
              label="External Agents"
              description="Allow external AI agents (MCP) to access data"
              enabled={orgConsent?.allowExternalAgents || false}
              onChange={(enabled) => handleUpdateOrgConsent('external_agents', enabled)}
              consentedAt={orgConsent?.externalAgentsConsentAt}
              disabled={isUpdatingOrg}
            />
          </div>
        </CardContent>
      </Card>

      {/* Tabs for Scopes, Documents, Agents, Audit */}
      <Tabs defaultValue="inheritance" className="space-y-4">
        <TabsList className="grid grid-cols-4 w-full max-w-lg">
          <TabsTrigger value="inheritance" className="gap-2">
            <Folder className="h-4 w-4" />
            Inheritance
          </TabsTrigger>
          <TabsTrigger value="agents" className="gap-2">
            <Settings className="h-4 w-4" />
            Agents
          </TabsTrigger>
          <TabsTrigger value="documents" className="gap-2">
            <FileText className="h-4 w-4" />
            Overrides
          </TabsTrigger>
          <TabsTrigger value="audit" className="gap-2">
            <History className="h-4 w-4" />
            Audit
          </TabsTrigger>
        </TabsList>

        <TabsContent value="inheritance">
          <InheritanceTree
            orgConsent={orgConsent}
            scopeConsents={scopeConsents}
            documentConsents={documentConsents}
          />
        </TabsContent>

        <TabsContent value="agents">
          {/* Scope Selector for Agent Management */}
          {scopeConsents && scopeConsents.length > 0 ? (
            <div className="space-y-4">
              <Card className="border-violet-500/20">
                <CardHeader className="pb-3">
                  <div className="flex items-center justify-between">
                    <div>
                      <CardTitle className="text-lg">Select Scope</CardTitle>
                      <CardDescription>
                        Manage agent access for a specific data scope
                      </CardDescription>
                    </div>
                    <Select
                      value={selectedScope?.scopeId || ''}
                      onValueChange={setSelectedScopeId}
                    >
                      <SelectTrigger className="w-[240px]">
                        <SelectValue placeholder="Select a scope" />
                      </SelectTrigger>
                      <SelectContent>
                        {scopeConsents.map((scope) => (
                          <SelectItem key={scope.scopeId} value={scope.scopeId}>
                            <div className="flex items-center gap-2">
                              <Folder className="h-4 w-4 text-muted-foreground" />
                              {scope.scopeName}
                            </div>
                          </SelectItem>
                        ))}
                      </SelectContent>
                    </Select>
                  </div>
                </CardHeader>
              </Card>

              <AgentAccessPanel
                agents={scopeAgents}
                onToggleAccess={handleToggleAgentAccess}
                onAddAgent={handleAddAgent}
                onRemoveAgent={handleRemoveAgent}
              />

              {/* Loading indicator */}
              {isUpdatingScopeAgent && (
                <div className="text-center text-sm text-muted-foreground">
                  Updating agent access...
                </div>
              )}
            </div>
          ) : (
            <Card>
              <CardContent className="py-8 text-center text-muted-foreground">
                <Settings className="h-8 w-8 mx-auto mb-2 opacity-50" />
                <p className="text-sm">No scopes available</p>
                <p className="text-xs">Create a scope to manage agent access</p>
              </CardContent>
            </Card>
          )}
        </TabsContent>

        <TabsContent value="documents">
          <Card>
            <CardHeader>
              <CardTitle className="text-lg">Document-Level Overrides</CardTitle>
              <CardDescription>
                {documentConsents?.length || 0} documents with custom consent settings
              </CardDescription>
            </CardHeader>
            <CardContent>
              {documentConsents && documentConsents.length > 0 ? (
                <div className="space-y-2">
                  {documentConsents.map((doc) => (
                    <div
                      key={doc.documentId}
                      className="py-3 border-b last:border-0 flex items-center justify-between"
                    >
                      <div className="flex items-center gap-2 min-w-0 flex-1">
                        <FileText className="h-4 w-4 text-muted-foreground flex-shrink-0" />
                        <span className="text-sm truncate max-w-[200px]">
                          {doc.documentName || doc.documentId}
                        </span>
                      </div>
                      <div className="flex items-center gap-4">
                        <ConsentToggle
                          label="AI"
                          enabled={doc.allowAiLearning ?? false}
                          onChange={(enabled) =>
                            handleUpdateDocumentConsent(doc.documentId, 'ai_learning', enabled)
                          }
                          compact
                        />
                        <ConsentToggle
                          label="Agents"
                          enabled={doc.allowExternalAgents ?? false}
                          onChange={(enabled) =>
                            handleUpdateDocumentConsent(doc.documentId, 'external_agents', enabled)
                          }
                          compact
                        />
                        <Button
                          variant="ghost"
                          size="sm"
                          onClick={() =>
                            handleResetDocumentConsent(
                              doc.documentId,
                              doc.documentName || doc.documentId
                            )
                          }
                          disabled={isResettingDocument}
                          title="Reset to scope defaults"
                        >
                          <RotateCcw className="h-4 w-4" />
                        </Button>
                      </div>
                    </div>
                  ))}
                </div>
              ) : (
                <div className="text-center py-8 text-muted-foreground">
                  <FileText className="h-8 w-8 mx-auto mb-2 opacity-50" />
                  <p className="text-sm">No document overrides</p>
                  <p className="text-xs">All documents inherit from their scope</p>
                </div>
              )}
            </CardContent>
          </Card>
        </TabsContent>

        <TabsContent value="audit">
          <ConsentAuditPanel />
        </TabsContent>
      </Tabs>
    </div>
  );
}

function ConsentDashboardSkeleton() {
  return (
    <div className="space-y-6 animate-pulse">
      <div className="h-20 bg-muted/20 rounded-lg" />
      <div className="h-48 bg-muted/20 rounded-lg" />
      <div className="h-64 bg-muted/20 rounded-lg" />
    </div>
  );
}

export default ConsentDashboard;
