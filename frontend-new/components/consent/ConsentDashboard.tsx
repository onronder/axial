'use client';

import { Shield, Building, Folder, FileText, Settings } from 'lucide-react';
import { Card, CardContent, CardHeader, CardTitle, CardDescription } from '@/components/ui/card';
import { Tabs, TabsContent, TabsList, TabsTrigger } from '@/components/ui/tabs';
import { ConsentToggle } from './ConsentToggle';
import { InheritanceTree } from './InheritanceTree';
import { AgentAccessPanel } from './AgentAccessPanel';
import { ComplianceScoreWidget } from './ComplianceScoreWidget';
import { useConsent } from '@/hooks/useConsent';

export function ConsentDashboard() {
  const {
    orgConsent,
    scopeConsents,
    documentConsents,
    updateOrgConsent,
    complianceReport,
    isLoading,
  } = useConsent();

  if (isLoading) {
    return <ConsentDashboardSkeleton />;
  }

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="flex items-center justify-between">
        <div className="flex items-center gap-3">
          <div className="p-2 rounded-lg bg-cyan-500/10">
            <Shield className="h-6 w-6 text-cyan-400" />
          </div>
          <div>
            <h1 className="text-2xl font-semibold">Data Consent Management</h1>
            <p className="text-sm text-muted-foreground">
              KVKK 2026 Compliant Granular Controls
            </p>
          </div>
        </div>
        <ComplianceScoreWidget score={complianceReport?.complianceScore || 0} />
      </div>

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
              onChange={(enabled) => updateOrgConsent('ai_learning', enabled)}
              consentedAt={orgConsent?.aiLearningConsentAt}
            />
            <ConsentToggle
              label="External Agents"
              description="Allow external AI agents (MCP) to access data"
              enabled={orgConsent?.allowExternalAgents || false}
              onChange={(enabled) => updateOrgConsent('external_agents', enabled)}
              consentedAt={orgConsent?.externalAgentsConsentAt}
            />
          </div>
        </CardContent>
      </Card>

      {/* Tabs for Scopes, Documents, Agents */}
      <Tabs defaultValue="inheritance" className="space-y-4">
        <TabsList className="grid grid-cols-3 w-full max-w-md">
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
        </TabsList>

        <TabsContent value="inheritance">
          <InheritanceTree
            orgConsent={orgConsent}
            scopeConsents={scopeConsents}
            documentConsents={documentConsents}
          />
        </TabsContent>

        <TabsContent value="agents">
          <AgentAccessPanel />
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
                    <div key={doc.documentId} className="py-3 border-b last:border-0">
                      <div className="flex items-center justify-between">
                        <div className="flex items-center gap-2">
                          <FileText className="h-4 w-4 text-muted-foreground" />
                          <span className="text-sm truncate max-w-[200px]">
                            {doc.documentName || doc.documentId}
                          </span>
                        </div>
                        <div className="flex gap-4">
                          <ConsentToggle
                            label="AI"
                            enabled={doc.allowAiLearning ?? false}
                            onChange={() => {}}
                            compact
                          />
                          <ConsentToggle
                            label="Agents"
                            enabled={doc.allowExternalAgents ?? false}
                            onChange={() => {}}
                            compact
                          />
                        </div>
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
