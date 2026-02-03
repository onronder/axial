'use client';

import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import { api } from '@/lib/api';

// =============================================================================
// Types - Match backend response structure with frontend-friendly versions
// =============================================================================

// Backend response types (snake_case)
interface OrgConsentRaw {
  organization_id: string;
  allow_ai_learning: boolean;
  ai_learning_consent_at: string | null;
  allow_external_agents: boolean;
  external_agents_consent_at: string | null;
}

interface ScopeConsentRaw {
  scope_id: string;
  organization_id: string;
  inherit_org_consent: boolean;
  allow_ai_learning: boolean | null;
  allow_external_agents: boolean | null;
  allowed_agent_ids: string[];
  blocked_agent_ids: string[];
}

interface DocumentConsentRaw {
  document_id: string;
  organization_id: string;
  inherit_scope_consent: boolean;
  allow_ai_learning: boolean | null;
  allow_external_agents: boolean | null;
  allowed_agent_ids: string[];
  blocked_agent_ids: string[];
}

interface ComplianceReportRaw {
  organization_id: string;
  report_generated_at: string;
  organization_consent: Record<string, unknown>;
  scope_overrides: number;
  document_overrides: number;
  total_documents: number;
  compliance_status: string;
}

// Agent access response (backend format)
interface AgentAccessResponseRaw {
  status: string;
  scope_id?: string;
  document_id?: string;
  action: string;
  agent_id: string;
  allowed_agent_ids: string[];
  blocked_agent_ids: string[];
}

// Consent reset response (backend format)
interface ConsentResetResponse {
  status: string;
  message: string;
  reset_to: string;
}

// Frontend types (camelCase)
export interface OrgConsent {
  orgId: string;
  allowAiLearning: boolean;
  aiLearningConsentAt: string | null;
  allowExternalAgents: boolean;
  externalAgentsConsentAt: string | null;
}

export interface ScopeConsent {
  scopeId: string;
  scopeName: string;
  allowAiLearning: boolean | null;
  allowExternalAgents: boolean | null;
  inherits: boolean;
  allowedAgentIds: string[];
  blockedAgentIds: string[];
}

export interface DocumentConsent {
  documentId: string;
  documentName?: string;
  scopeId: string;
  allowAiLearning: boolean | null;
  allowExternalAgents: boolean | null;
  inherits: boolean;
  allowedAgentIds: string[];
  blockedAgentIds: string[];
}

export interface ComplianceReport {
  organizationId: string;
  reportGeneratedAt: string;
  complianceScore: number;
  totalDocuments: number;
  scopeOverrides: number;
  documentOverrides: number;
  complianceStatus: string;
}

// Agent access types for frontend
export type AgentAction = 'allow' | 'block' | 'remove';

export interface AgentAccessResult {
  status: string;
  action: AgentAction;
  agentId: string;
  allowedAgentIds: string[];
  blockedAgentIds: string[];
}

// =============================================================================
// Transform Functions
// =============================================================================

function transformOrgConsent(raw: OrgConsentRaw): OrgConsent {
  return {
    orgId: raw.organization_id,
    allowAiLearning: raw.allow_ai_learning,
    aiLearningConsentAt: raw.ai_learning_consent_at,
    allowExternalAgents: raw.allow_external_agents,
    externalAgentsConsentAt: raw.external_agents_consent_at,
  };
}

function transformScopeConsent(raw: ScopeConsentRaw, scopeName: string = ''): ScopeConsent {
  return {
    scopeId: raw.scope_id,
    scopeName: scopeName || raw.scope_id,
    allowAiLearning: raw.allow_ai_learning,
    allowExternalAgents: raw.allow_external_agents,
    inherits: raw.inherit_org_consent,
    allowedAgentIds: raw.allowed_agent_ids || [],
    blockedAgentIds: raw.blocked_agent_ids || [],
  };
}

function transformDocumentConsent(raw: DocumentConsentRaw, documentName?: string, scopeId?: string): DocumentConsent {
  return {
    documentId: raw.document_id,
    documentName: documentName,
    scopeId: scopeId || '',
    allowAiLearning: raw.allow_ai_learning,
    allowExternalAgents: raw.allow_external_agents,
    inherits: raw.inherit_scope_consent,
    allowedAgentIds: raw.allowed_agent_ids || [],
    blockedAgentIds: raw.blocked_agent_ids || [],
  };
}

function transformComplianceReport(raw: ComplianceReportRaw): ComplianceReport {
  // Calculate compliance score based on configuration
  const orgConsent = raw.organization_consent || {};
  let score = 50; // Base score

  // Add points for having consent configured
  if (orgConsent) score += 20;
  if (raw.scope_overrides > 0) score += 15;
  if (raw.document_overrides > 0) score += 15;

  // Cap at 100
  score = Math.min(score, 100);

  return {
    organizationId: raw.organization_id,
    reportGeneratedAt: raw.report_generated_at,
    complianceScore: score,
    totalDocuments: raw.total_documents,
    scopeOverrides: raw.scope_overrides,
    documentOverrides: raw.document_overrides,
    complianceStatus: raw.compliance_status,
  };
}

function transformAgentAccessResponse(raw: AgentAccessResponseRaw): AgentAccessResult {
  return {
    status: raw.status,
    action: raw.action as AgentAction,
    agentId: raw.agent_id,
    allowedAgentIds: raw.allowed_agent_ids || [],
    blockedAgentIds: raw.blocked_agent_ids || [],
  };
}

// =============================================================================
// API Functions - Fetch
// =============================================================================

async function fetchOrgConsent(): Promise<OrgConsent> {
  const response = await api.get<OrgConsentRaw>('/consent/organization');
  return transformOrgConsent(response.data);
}

async function fetchScopeConsents(): Promise<ScopeConsent[]> {
  // Fetch list of scopes first, then get consent for each
  try {
    const scopesResponse = await api.get<Array<{ id: string; label: string }>>('/scopes');
    const scopes = scopesResponse.data;

    // Fetch consent for each scope in parallel
    // Using query parameters to handle special characters in scope IDs (e.g., "gdrive://...")
    const consentPromises = scopes.map(async (scope) => {
      try {
        const response = await api.get<ScopeConsentRaw>('/consent/scope', {
          params: { scope_id: scope.id },
        });
        return transformScopeConsent(response.data, scope.label);
      } catch {
        // Return default consent if not found
        return {
          scopeId: scope.id,
          scopeName: scope.label,
          allowAiLearning: null,
          allowExternalAgents: null,
          inherits: true,
          allowedAgentIds: [],
          blockedAgentIds: [],
        } as ScopeConsent;
      }
    });

    return Promise.all(consentPromises);
  } catch (error) {
    // If scopes endpoint doesn't exist, return empty array
    if ((error as { response?: { status?: number } })?.response?.status === 404) return [];
    throw new Error('Failed to fetch scopes');
  }
}

async function fetchDocumentConsent(documentId: string): Promise<DocumentConsent | null> {
  try {
    const response = await api.get<DocumentConsentRaw>(`/consent/document/${documentId}`);
    return transformDocumentConsent(response.data);
  } catch (error) {
    if ((error as { response?: { status?: number } })?.response?.status === 404) return null;
    throw error;
  }
}

async function fetchComplianceReport(): Promise<ComplianceReport> {
  const response = await api.get<ComplianceReportRaw>('/consent/report');
  return transformComplianceReport(response.data);
}

// =============================================================================
// API Functions - Update (PATCH)
// =============================================================================

async function updateOrgConsentApi(
  consentType: 'ai_learning' | 'external_agents',
  enabled: boolean
): Promise<{ status: string }> {
  const response = await api.patch<{ status: string }>('/consent/organization', {
    consent_type: consentType,
    allowed: enabled,
  });
  return response.data;
}

async function updateScopeConsentApi(
  scopeId: string,
  consentType: 'ai_learning' | 'external_agents',
  enabled: boolean | null,
  inheritOrgConsent: boolean = true
): Promise<{ status: string }> {
  // Using query parameters to handle special characters in scope IDs (e.g., "gdrive://...")
  const response = await api.patch<{ status: string }>('/consent/scope', {
    consent_type: consentType,
    allowed: enabled,
    inherit_org_consent: inheritOrgConsent,
  }, {
    params: { scope_id: scopeId },
  });
  return response.data;
}

async function updateDocumentConsentApi(
  documentId: string,
  consentType: 'ai_learning' | 'external_agents',
  enabled: boolean | null,
  inheritScopeConsent: boolean = true
): Promise<{ status: string }> {
  const response = await api.patch<{ status: string }>(`/consent/document/${documentId}`, {
    consent_type: consentType,
    allowed: enabled,
    inherit_scope_consent: inheritScopeConsent,
  });
  return response.data;
}

// =============================================================================
// API Functions - Bulk Operations
// =============================================================================

interface BulkScopeConsentItem {
  scopeId: string;
  consentType: 'ai_learning' | 'external_agents';
  enabled: boolean | null;
}

interface BulkScopeConsentResponse {
  success: number;
  failed: number;
  errors: Array<{ scope_id: string; error: string }>;
}

/**
 * Bulk update multiple scope consents in a single request.
 * Maximum 50 updates per request.
 */
async function bulkUpdateScopeConsentApi(
  updates: BulkScopeConsentItem[]
): Promise<BulkScopeConsentResponse> {
  const response = await api.post<BulkScopeConsentResponse>('/consent/scope/bulk', {
    updates: updates.map((u) => ({
      scope_id: u.scopeId,
      consent_type: u.consentType,
      allowed: u.enabled,
    })),
  });
  return response.data;
}

// =============================================================================
// API Functions - Delete (Reset to Inherit)
// =============================================================================

/**
 * Delete scope consent override, reverting to organization defaults.
 * Removes any custom consent settings for the scope.
 */
async function deleteScopeConsentApi(scopeId: string): Promise<ConsentResetResponse> {
  // Using query parameters to handle special characters in scope IDs (e.g., "gdrive://...")
  const response = await api.delete<ConsentResetResponse>('/consent/scope', {
    params: { scope_id: scopeId },
  });
  return response.data;
}

/**
 * Delete document consent override, reverting to scope/org defaults.
 * Removes any custom consent settings for the document.
 */
async function deleteDocumentConsentApi(documentId: string): Promise<ConsentResetResponse> {
  const response = await api.delete<ConsentResetResponse>(`/consent/document/${documentId}`);
  return response.data;
}

// =============================================================================
// API Functions - Agent Access Management (PATCH)
// =============================================================================

/**
 * Manage which MCP agents can access a scope.
 * @param scopeId - The scope to update
 * @param action - "allow" | "block" | "remove"
 * @param agentId - The agent identifier to modify access for
 */
async function updateScopeAgentAccessApi(
  scopeId: string,
  action: AgentAction,
  agentId: string
): Promise<AgentAccessResult> {
  // Using query parameters to handle special characters in scope IDs (e.g., "gdrive://...")
  const response = await api.patch<AgentAccessResponseRaw>('/consent/scope/agents', {
    action,
    agent_id: agentId,
  }, {
    params: { scope_id: scopeId },
  });
  return transformAgentAccessResponse(response.data);
}

/**
 * Manage which MCP agents can access a document.
 * @param documentId - The document to update
 * @param action - "allow" | "block" | "remove"
 * @param agentId - The agent identifier to modify access for
 */
async function updateDocumentAgentAccessApi(
  documentId: string,
  action: AgentAction,
  agentId: string
): Promise<AgentAccessResult> {
  const response = await api.patch<AgentAccessResponseRaw>(`/consent/document/${documentId}/agents`, {
    action,
    agent_id: agentId,
  });
  return transformAgentAccessResponse(response.data);
}

// =============================================================================
// Hook
// =============================================================================

export function useConsent() {
  const queryClient = useQueryClient();

  // =========================================================================
  // Queries
  // =========================================================================
  
  const orgConsentQuery = useQuery({
    queryKey: ['consent', 'organization'],
    queryFn: fetchOrgConsent,
    staleTime: 30000,
    retry: (failureCount, error) => {
      if (error instanceof Error && error.message.includes('Unauthorized')) return false;
      return failureCount < 2;
    },
  });

  const scopeConsentsQuery = useQuery({
    queryKey: ['consent', 'scopes'],
    queryFn: fetchScopeConsents,
    staleTime: 60000,
    enabled: orgConsentQuery.isSuccess,
  });

  const complianceReportQuery = useQuery({
    queryKey: ['consent', 'report'],
    queryFn: fetchComplianceReport,
    staleTime: 60000,
    enabled: orgConsentQuery.isSuccess,
  });

  // =========================================================================
  // Mutations - Consent Update
  // =========================================================================
  
  const updateOrgMutation = useMutation({
    mutationFn: ({ consentType, enabled }: { consentType: 'ai_learning' | 'external_agents'; enabled: boolean }) =>
      updateOrgConsentApi(consentType, enabled),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['consent'] });
    },
  });

  const updateScopeMutation = useMutation({
    mutationFn: ({
      scopeId,
      consentType,
      enabled,
      inheritOrgConsent,
    }: {
      scopeId: string;
      consentType: 'ai_learning' | 'external_agents';
      enabled: boolean | null;
      inheritOrgConsent?: boolean;
    }) => updateScopeConsentApi(scopeId, consentType, enabled, inheritOrgConsent),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['consent'] });
    },
  });

  const updateDocumentMutation = useMutation({
    mutationFn: ({
      documentId,
      consentType,
      enabled,
      inheritScopeConsent,
    }: {
      documentId: string;
      consentType: 'ai_learning' | 'external_agents';
      enabled: boolean | null;
      inheritScopeConsent?: boolean;
    }) => updateDocumentConsentApi(documentId, consentType, enabled, inheritScopeConsent),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['consent'] });
    },
  });

  // =========================================================================
  // Mutations - Consent Reset (DELETE)
  // =========================================================================

  const resetScopeMutation = useMutation({
    mutationFn: (scopeId: string) => deleteScopeConsentApi(scopeId),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['consent'] });
    },
  });

  const resetDocumentMutation = useMutation({
    mutationFn: (documentId: string) => deleteDocumentConsentApi(documentId),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['consent'] });
    },
  });

  // =========================================================================
  // Mutations - Agent Access Management
  // =========================================================================

  const updateScopeAgentMutation = useMutation({
    mutationFn: ({
      scopeId,
      action,
      agentId,
    }: {
      scopeId: string;
      action: AgentAction;
      agentId: string;
    }) => updateScopeAgentAccessApi(scopeId, action, agentId),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['consent'] });
    },
  });

  const updateDocumentAgentMutation = useMutation({
    mutationFn: ({
      documentId,
      action,
      agentId,
    }: {
      documentId: string;
      action: AgentAction;
      agentId: string;
    }) => updateDocumentAgentAccessApi(documentId, action, agentId),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['consent'] });
    },
  });

  // =========================================================================
  // Mutations - Bulk Operations
  // =========================================================================

  const bulkUpdateScopeMutation = useMutation({
    mutationFn: (updates: BulkScopeConsentItem[]) => bulkUpdateScopeConsentApi(updates),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['consent'] });
    },
  });

  // =========================================================================
  // Return
  // =========================================================================

  return {
    // Data
    orgConsent: orgConsentQuery.data ?? null,
    scopeConsents: scopeConsentsQuery.data ?? null,
    documentConsents: [] as DocumentConsent[], // Empty until document-level consent UI is implemented
    complianceReport: complianceReportQuery.data ?? null,

    // Loading states
    isLoading: orgConsentQuery.isLoading || scopeConsentsQuery.isLoading,
    isError: orgConsentQuery.isError || scopeConsentsQuery.isError,
    error: orgConsentQuery.error || scopeConsentsQuery.error,

    // =========================================================================
    // Update Functions - Consent Settings
    // =========================================================================

    /** Update organization-level consent (AI learning or external agents) */
    updateOrgConsent: (consentType: 'ai_learning' | 'external_agents', enabled: boolean) =>
      updateOrgMutation.mutateAsync({ consentType, enabled }),
    isUpdatingOrg: updateOrgMutation.isPending,

    /** Update scope-level consent override */
    updateScopeConsent: (
      scopeId: string,
      consentType: 'ai_learning' | 'external_agents',
      enabled: boolean | null,
      inheritOrgConsent?: boolean
    ) => updateScopeMutation.mutateAsync({ scopeId, consentType, enabled, inheritOrgConsent }),
    isUpdatingScope: updateScopeMutation.isPending,

    /** Update document-level consent override */
    updateDocumentConsent: (
      documentId: string,
      consentType: 'ai_learning' | 'external_agents',
      enabled: boolean | null,
      inheritScopeConsent?: boolean
    ) => updateDocumentMutation.mutateAsync({ documentId, consentType, enabled, inheritScopeConsent }),
    isUpdatingDocument: updateDocumentMutation.isPending,

    /** Bulk update multiple scope consents at once (max 50) */
    bulkUpdateScopeConsent: (
      updates: Array<{
        scopeId: string;
        consentType: 'ai_learning' | 'external_agents';
        enabled: boolean | null;
      }>
    ) => bulkUpdateScopeMutation.mutateAsync(updates),
    isBulkUpdating: bulkUpdateScopeMutation.isPending,

    // =========================================================================
    // Reset Functions - Delete consent override (revert to inherit)
    // =========================================================================

    /** Reset scope consent to inherit from organization defaults */
    resetScopeConsent: (scopeId: string) => resetScopeMutation.mutateAsync(scopeId),
    isResettingScope: resetScopeMutation.isPending,

    /** Reset document consent to inherit from scope/org defaults */
    resetDocumentConsent: (documentId: string) => resetDocumentMutation.mutateAsync(documentId),
    isResettingDocument: resetDocumentMutation.isPending,

    // =========================================================================
    // Agent Access Management
    // =========================================================================

    /**
     * Update agent access for a scope.
     * @param scopeId - Target scope
     * @param action - "allow" to whitelist, "block" to blacklist, "remove" to clear
     * @param agentId - The MCP agent identifier
     */
    updateScopeAgentAccess: (scopeId: string, action: AgentAction, agentId: string) =>
      updateScopeAgentMutation.mutateAsync({ scopeId, action, agentId }),
    isUpdatingScopeAgent: updateScopeAgentMutation.isPending,

    /**
     * Update agent access for a document.
     * @param documentId - Target document
     * @param action - "allow" to whitelist, "block" to blacklist, "remove" to clear
     * @param agentId - The MCP agent identifier
     */
    updateDocumentAgentAccess: (documentId: string, action: AgentAction, agentId: string) =>
      updateDocumentAgentMutation.mutateAsync({ documentId, action, agentId }),
    isUpdatingDocumentAgent: updateDocumentAgentMutation.isPending,

    // =========================================================================
    // Utilities
    // =========================================================================

    /** Fetch consent for a specific document */
    fetchDocumentConsent,

    /** Refetch all consent data */
    refetch: () => {
      queryClient.invalidateQueries({ queryKey: ['consent'] });
    },
  };
}

export default useConsent;
