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

interface ComplianceReportRaw {
  organization_id: string;
  report_generated_at: string;
  organization_consent: Record<string, unknown>;
  scope_overrides: number;
  document_overrides: number;
  total_documents: number;
  compliance_status: string;
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

// =============================================================================
// API Functions
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
    const consentPromises = scopes.map(async (scope) => {
      try {
        const response = await api.get<ScopeConsentRaw>(`/consent/scope/${scope.id}`);
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

async function fetchComplianceReport(): Promise<ComplianceReport> {
  const response = await api.get<ComplianceReportRaw>('/consent/report');
  return transformComplianceReport(response.data);
}

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
  const response = await api.patch<{ status: string }>(`/consent/scope/${scopeId}`, {
    consent_type: consentType,
    allowed: enabled,
    inherit_org_consent: inheritOrgConsent,
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
// Hook
// =============================================================================

export function useConsent() {
  const queryClient = useQueryClient();

  // Queries
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

  // Mutations
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

  return {
    // Data
    orgConsent: orgConsentQuery.data ?? null,
    scopeConsents: scopeConsentsQuery.data ?? null,
    documentConsents: [] as DocumentConsent[], // Empty until document-level consent UI is implemented
    complianceReport: complianceReportQuery.data ?? null,

    // Loading states
    isLoading:
      orgConsentQuery.isLoading ||
      scopeConsentsQuery.isLoading,
    isError: orgConsentQuery.isError || scopeConsentsQuery.isError,
    error: orgConsentQuery.error || scopeConsentsQuery.error,

    // Update functions
    updateOrgConsent: (consentType: 'ai_learning' | 'external_agents', enabled: boolean) =>
      updateOrgMutation.mutateAsync({ consentType, enabled }),
    isUpdatingOrg: updateOrgMutation.isPending,

    updateScopeConsent: (
      scopeId: string,
      consentType: 'ai_learning' | 'external_agents',
      enabled: boolean | null,
      inheritOrgConsent?: boolean
    ) => updateScopeMutation.mutateAsync({ scopeId, consentType, enabled, inheritOrgConsent }),
    isUpdatingScope: updateScopeMutation.isPending,

    updateDocumentConsent: (
      documentId: string,
      consentType: 'ai_learning' | 'external_agents',
      enabled: boolean | null,
      inheritScopeConsent?: boolean
    ) => updateDocumentMutation.mutateAsync({ documentId, consentType, enabled, inheritScopeConsent }),
    isUpdatingDocument: updateDocumentMutation.isPending,

    // Refetch
    refetch: () => {
      queryClient.invalidateQueries({ queryKey: ['consent'] });
    },
  };
}

export default useConsent;
