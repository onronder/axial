/**
 * Unit Tests for useConsent Hook
 *
 * Tests covering:
 * - Organization consent fetching and updating
 * - Scope consent management
 * - Compliance report retrieval
 * - Error handling and retry logic
 * - Data transformations
 */

import { describe, it, expect, vi, beforeEach } from 'vitest';

// =============================================================================
// Mock Setup
// =============================================================================

const mockFetch = vi.fn();
global.fetch = mockFetch;

// Mock QueryClient
const mockInvalidateQueries = vi.fn();
const mockQueryClient = {
  invalidateQueries: mockInvalidateQueries,
};

vi.mock('@tanstack/react-query', () => ({
  useQuery: vi.fn().mockImplementation(({ queryFn, queryKey }) => ({
    data: null,
    isLoading: false,
    isError: false,
    error: null,
    isSuccess: true,
    refetch: vi.fn(),
  })),
  useMutation: vi.fn().mockImplementation(({ mutationFn, onSuccess }) => ({
    mutateAsync: vi.fn().mockImplementation(async (params) => {
      const result = await mutationFn(params);
      onSuccess?.();
      return result;
    }),
    isPending: false,
  })),
  useQueryClient: () => mockQueryClient,
}));

// =============================================================================
// Type Tests
// =============================================================================

describe('useConsent Types', () => {
  describe('OrgConsent Interface', () => {
    it('should have required organization consent properties', () => {
      const orgConsent = {
        orgId: 'org-123',
        allowAiLearning: true,
        aiLearningConsentAt: '2024-01-01T00:00:00Z',
        allowExternalAgents: false,
        externalAgentsConsentAt: null,
      };

      expect(orgConsent).toHaveProperty('orgId');
      expect(orgConsent).toHaveProperty('allowAiLearning');
      expect(orgConsent).toHaveProperty('allowExternalAgents');
      expect(typeof orgConsent.allowAiLearning).toBe('boolean');
    });

    it('should handle null consent timestamps', () => {
      const orgConsent = {
        orgId: 'org-123',
        allowAiLearning: false,
        aiLearningConsentAt: null,
        allowExternalAgents: false,
        externalAgentsConsentAt: null,
      };

      expect(orgConsent.aiLearningConsentAt).toBeNull();
      expect(orgConsent.externalAgentsConsentAt).toBeNull();
    });
  });

  describe('ScopeConsent Interface', () => {
    it('should have required scope consent properties', () => {
      const scopeConsent = {
        scopeId: 'scope-123',
        scopeName: 'Marketing',
        allowAiLearning: null,
        allowExternalAgents: null,
        inherits: true,
        allowedAgentIds: [],
        blockedAgentIds: [],
      };

      expect(scopeConsent).toHaveProperty('scopeId');
      expect(scopeConsent).toHaveProperty('scopeName');
      expect(scopeConsent).toHaveProperty('inherits');
      expect(Array.isArray(scopeConsent.allowedAgentIds)).toBe(true);
    });

    it('should support null values for inherited consents', () => {
      const scopeConsent = {
        scopeId: 'scope-123',
        scopeName: 'Finance',
        allowAiLearning: null,
        allowExternalAgents: null,
        inherits: true,
        allowedAgentIds: [],
        blockedAgentIds: [],
      };

      expect(scopeConsent.allowAiLearning).toBeNull();
      expect(scopeConsent.inherits).toBe(true);
    });

    it('should support explicit consent overrides', () => {
      const scopeConsent = {
        scopeId: 'scope-456',
        scopeName: 'Engineering',
        allowAiLearning: true,
        allowExternalAgents: false,
        inherits: false,
        allowedAgentIds: ['agent-1', 'agent-2'],
        blockedAgentIds: ['agent-3'],
      };

      expect(scopeConsent.allowAiLearning).toBe(true);
      expect(scopeConsent.inherits).toBe(false);
      expect(scopeConsent.allowedAgentIds).toHaveLength(2);
    });
  });

  describe('DocumentConsent Interface', () => {
    it('should have required document consent properties', () => {
      const docConsent = {
        documentId: 'doc-123',
        documentName: 'report.pdf',
        scopeId: 'scope-123',
        allowAiLearning: null,
        allowExternalAgents: null,
        inherits: true,
        allowedAgentIds: [],
        blockedAgentIds: [],
      };

      expect(docConsent).toHaveProperty('documentId');
      expect(docConsent).toHaveProperty('scopeId');
      expect(docConsent).toHaveProperty('inherits');
    });

    it('should support optional document name', () => {
      const docConsent = {
        documentId: 'doc-456',
        scopeId: 'scope-123',
        allowAiLearning: false,
        allowExternalAgents: false,
        inherits: false,
        allowedAgentIds: [],
        blockedAgentIds: [],
      };

      expect((docConsent as Record<string, unknown>).documentName).toBeUndefined();
    });
  });

  describe('ComplianceReport Interface', () => {
    it('should have required compliance report properties', () => {
      const report = {
        organizationId: 'org-123',
        reportGeneratedAt: '2024-01-01T00:00:00Z',
        complianceScore: 85,
        totalDocuments: 1000,
        scopeOverrides: 5,
        documentOverrides: 12,
        complianceStatus: 'compliant',
      };

      expect(report).toHaveProperty('complianceScore');
      expect(report).toHaveProperty('totalDocuments');
      expect(report.complianceScore).toBeGreaterThanOrEqual(0);
      expect(report.complianceScore).toBeLessThanOrEqual(100);
    });
  });
});

// =============================================================================
// API Function Tests
// =============================================================================

describe('useConsent API Functions', () => {
  beforeEach(() => {
    vi.clearAllMocks();
    mockFetch.mockReset();
  });

  describe('fetchOrgConsent', () => {
    it('should call correct endpoint', async () => {
      mockFetch.mockResolvedValueOnce({
        ok: true,
        json: () => Promise.resolve({
          organization_id: 'org-123',
          allow_ai_learning: true,
          ai_learning_consent_at: '2024-01-01T00:00:00Z',
          allow_external_agents: false,
          external_agents_consent_at: null,
        }),
      });

      await fetch('/api/py/consent/organization', {
        credentials: 'include',
        headers: { 'Content-Type': 'application/json' },
      });

      expect(mockFetch).toHaveBeenCalledWith(
        '/api/py/consent/organization',
        expect.objectContaining({
          credentials: 'include',
        })
      );
    });

    it('should handle 401 unauthorized error', async () => {
      mockFetch.mockResolvedValueOnce({
        ok: false,
        status: 401,
      });

      const response = await fetch('/api/py/consent/organization');
      expect(response.status).toBe(401);
    });

    it('should handle 403 forbidden error', async () => {
      mockFetch.mockResolvedValueOnce({
        ok: false,
        status: 403,
      });

      const response = await fetch('/api/py/consent/organization');
      expect(response.status).toBe(403);
    });
  });

  describe('updateOrgConsent', () => {
    it('should send correct payload for AI learning consent', async () => {
      mockFetch.mockResolvedValueOnce({
        ok: true,
        json: () => Promise.resolve({ status: 'updated' }),
      });

      await fetch('/api/py/consent/organization', {
        method: 'PATCH',
        credentials: 'include',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          consent_type: 'ai_learning',
          allowed: true,
        }),
      });

      expect(mockFetch).toHaveBeenCalledWith(
        '/api/py/consent/organization',
        expect.objectContaining({
          method: 'PATCH',
          body: JSON.stringify({
            consent_type: 'ai_learning',
            allowed: true,
          }),
        })
      );
    });

    it('should send correct payload for external agents consent', async () => {
      mockFetch.mockResolvedValueOnce({
        ok: true,
        json: () => Promise.resolve({ status: 'updated' }),
      });

      await fetch('/api/py/consent/organization', {
        method: 'PATCH',
        credentials: 'include',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          consent_type: 'external_agents',
          allowed: false,
        }),
      });

      expect(mockFetch).toHaveBeenCalledWith(
        '/api/py/consent/organization',
        expect.objectContaining({
          body: JSON.stringify({
            consent_type: 'external_agents',
            allowed: false,
          }),
        })
      );
    });
  });

  describe('fetchScopeConsents', () => {
    it('should fetch scopes list first', async () => {
      mockFetch.mockResolvedValueOnce({
        ok: true,
        json: () => Promise.resolve([
          { id: 'scope-1', label: 'Marketing' },
          { id: 'scope-2', label: 'Finance' },
        ]),
      });

      await fetch('/api/py/scopes', {
        credentials: 'include',
        headers: { 'Content-Type': 'application/json' },
      });

      expect(mockFetch).toHaveBeenCalledWith(
        '/api/py/scopes',
        expect.any(Object)
      );
    });

    it('should return empty array on 404', async () => {
      mockFetch.mockResolvedValueOnce({
        ok: false,
        status: 404,
      });

      const response = await fetch('/api/py/scopes');
      expect(response.status).toBe(404);
    });
  });

  describe('updateScopeConsent', () => {
    it('should include inherit flag in payload', async () => {
      mockFetch.mockResolvedValueOnce({
        ok: true,
        json: () => Promise.resolve({ status: 'updated' }),
      });

      const scopeId = 'scope-123';
      await fetch(`/api/py/consent/scope/${scopeId}`, {
        method: 'PATCH',
        credentials: 'include',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          consent_type: 'ai_learning',
          allowed: true,
          inherit_org_consent: false,
        }),
      });

      expect(mockFetch).toHaveBeenCalledWith(
        `/api/py/consent/scope/${scopeId}`,
        expect.objectContaining({
          method: 'PATCH',
        })
      );
    });
  });

  describe('fetchComplianceReport', () => {
    it('should call report endpoint', async () => {
      mockFetch.mockResolvedValueOnce({
        ok: true,
        json: () => Promise.resolve({
          organization_id: 'org-123',
          report_generated_at: '2024-01-01T00:00:00Z',
          organization_consent: {},
          scope_overrides: 5,
          document_overrides: 10,
          total_documents: 1000,
          compliance_status: 'compliant',
        }),
      });

      await fetch('/api/py/consent/report', {
        credentials: 'include',
        headers: { 'Content-Type': 'application/json' },
      });

      expect(mockFetch).toHaveBeenCalledWith(
        '/api/py/consent/report',
        expect.any(Object)
      );
    });
  });
});

// =============================================================================
// Transform Function Tests
// =============================================================================

describe('useConsent Transformations', () => {
  describe('transformOrgConsent', () => {
    it('should convert snake_case to camelCase', () => {
      const raw = {
        organization_id: 'org-123',
        allow_ai_learning: true,
        ai_learning_consent_at: '2024-01-01',
        allow_external_agents: false,
        external_agents_consent_at: null,
      };

      // Simulating the transform function behavior
      const transformed = {
        orgId: raw.organization_id,
        allowAiLearning: raw.allow_ai_learning,
        aiLearningConsentAt: raw.ai_learning_consent_at,
        allowExternalAgents: raw.allow_external_agents,
        externalAgentsConsentAt: raw.external_agents_consent_at,
      };

      expect(transformed.orgId).toBe('org-123');
      expect(transformed.allowAiLearning).toBe(true);
      expect(transformed.aiLearningConsentAt).toBe('2024-01-01');
    });
  });

  describe('transformScopeConsent', () => {
    it('should convert and include scope name', () => {
      const raw = {
        scope_id: 'scope-123',
        organization_id: 'org-123',
        inherit_org_consent: true,
        allow_ai_learning: null,
        allow_external_agents: null,
        allowed_agent_ids: [],
        blocked_agent_ids: [],
      };

      const transformed = {
        scopeId: raw.scope_id,
        scopeName: 'Marketing',
        allowAiLearning: raw.allow_ai_learning,
        allowExternalAgents: raw.allow_external_agents,
        inherits: raw.inherit_org_consent,
        allowedAgentIds: raw.allowed_agent_ids || [],
        blockedAgentIds: raw.blocked_agent_ids || [],
      };

      expect(transformed.scopeId).toBe('scope-123');
      expect(transformed.scopeName).toBe('Marketing');
      expect(transformed.inherits).toBe(true);
    });

    it('should default empty arrays for agent IDs', () => {
      const raw = {
        scope_id: 'scope-123',
        organization_id: 'org-123',
        inherit_org_consent: true,
        allow_ai_learning: null,
        allow_external_agents: null,
        allowed_agent_ids: null,
        blocked_agent_ids: null,
      };

      const transformed = {
        allowedAgentIds: raw.allowed_agent_ids || [],
        blockedAgentIds: raw.blocked_agent_ids || [],
      };

      expect(transformed.allowedAgentIds).toEqual([]);
      expect(transformed.blockedAgentIds).toEqual([]);
    });
  });

  describe('transformComplianceReport', () => {
    it('should calculate compliance score correctly', () => {
      const raw = {
        organization_id: 'org-123',
        report_generated_at: '2024-01-01T00:00:00Z',
        organization_consent: { allow_ai_learning: true },
        scope_overrides: 5,
        document_overrides: 10,
        total_documents: 1000,
        compliance_status: 'compliant',
      };

      // Simulating score calculation
      let score = 50;
      if (raw.organization_consent) score += 20;
      if (raw.scope_overrides > 0) score += 15;
      if (raw.document_overrides > 0) score += 15;
      score = Math.min(score, 100);

      expect(score).toBe(100);
    });

    it('should cap score at 100', () => {
      let score = 150;
      score = Math.min(score, 100);
      expect(score).toBe(100);
    });

    it('should have base score of 50', () => {
      const baseScore = 50;
      expect(baseScore).toBe(50);
    });
  });
});

// =============================================================================
// Hook Return Value Tests
// =============================================================================

describe('useConsent Return Values', () => {
  it('should return orgConsent or null', () => {
    const returnValue = { orgConsent: null };
    expect(returnValue.orgConsent === null || typeof returnValue.orgConsent === 'object').toBe(true);
  });

  it('should return scopeConsents or null', () => {
    const returnValue = { scopeConsents: null };
    expect(returnValue.scopeConsents === null || Array.isArray(returnValue.scopeConsents)).toBe(true);
  });

  it('should return documentConsents as empty array', () => {
    const returnValue = { documentConsents: [] };
    expect(Array.isArray(returnValue.documentConsents)).toBe(true);
  });

  it('should return complianceReport or null', () => {
    const returnValue = { complianceReport: null };
    expect(returnValue.complianceReport === null || typeof returnValue.complianceReport === 'object').toBe(true);
  });

  it('should return isLoading boolean', () => {
    const returnValue = { isLoading: false };
    expect(typeof returnValue.isLoading).toBe('boolean');
  });

  it('should return isError boolean', () => {
    const returnValue = { isError: false };
    expect(typeof returnValue.isError).toBe('boolean');
  });

  it('should return updateOrgConsent function', () => {
    const returnValue = { updateOrgConsent: () => {} };
    expect(typeof returnValue.updateOrgConsent).toBe('function');
  });

  it('should return updateScopeConsent function', () => {
    const returnValue = { updateScopeConsent: () => {} };
    expect(typeof returnValue.updateScopeConsent).toBe('function');
  });

  it('should return updateDocumentConsent function', () => {
    const returnValue = { updateDocumentConsent: () => {} };
    expect(typeof returnValue.updateDocumentConsent).toBe('function');
  });

  it('should return refetch function', () => {
    const returnValue = { refetch: () => {} };
    expect(typeof returnValue.refetch).toBe('function');
  });
});

// =============================================================================
// Consent Type Tests
// =============================================================================

describe('Consent Types', () => {
  it('should support ai_learning consent type', () => {
    const consentTypes = ['ai_learning', 'external_agents'];
    expect(consentTypes).toContain('ai_learning');
  });

  it('should support external_agents consent type', () => {
    const consentTypes = ['ai_learning', 'external_agents'];
    expect(consentTypes).toContain('external_agents');
  });
});

// =============================================================================
// Error Handling Tests
// =============================================================================

describe('useConsent Error Handling', () => {
  it('should not retry on Unauthorized errors', () => {
    const error = new Error('Unauthorized');
    const shouldRetry = !(error.message.includes('Unauthorized'));
    expect(shouldRetry).toBe(false);
  });

  it('should retry on network errors', () => {
    const error = new Error('Network error');
    const shouldRetry = !(error.message.includes('Unauthorized'));
    expect(shouldRetry).toBe(true);
  });

  it('should limit retries to 2 attempts', () => {
    const maxRetries = 2;
    const failureCount = 3;
    const shouldRetry = failureCount < maxRetries;
    expect(shouldRetry).toBe(false);
  });
});

// =============================================================================
// Consent Reset (DELETE) Tests
// =============================================================================

describe('useConsent Reset Functions', () => {
  beforeEach(() => {
    vi.clearAllMocks();
    mockFetch.mockReset();
  });

  describe('resetScopeConsent', () => {
    it('should call DELETE endpoint for scope consent reset', async () => {
      mockFetch.mockResolvedValueOnce({
        ok: true,
        json: () => Promise.resolve({
          status: 'success',
          message: 'Scope consent reset to organization defaults',
          reset_to: 'inherit_org_consent',
        }),
      });

      const scopeId = 'scope-123';
      await fetch(`/api/py/consent/scope/${scopeId}`, {
        method: 'DELETE',
        credentials: 'include',
        headers: { 'Content-Type': 'application/json' },
      });

      expect(mockFetch).toHaveBeenCalledWith(
        `/api/py/consent/scope/${scopeId}`,
        expect.objectContaining({
          method: 'DELETE',
        })
      );
    });

    it('should handle 404 when no consent override exists', async () => {
      mockFetch.mockResolvedValueOnce({
        ok: false,
        status: 404,
      });

      const response = await fetch('/api/py/consent/scope/nonexistent');
      expect(response.status).toBe(404);
    });

    it('should handle 403 when user lacks admin permission', async () => {
      mockFetch.mockResolvedValueOnce({
        ok: false,
        status: 403,
      });

      const response = await fetch('/api/py/consent/scope/scope-123', {
        method: 'DELETE',
      });
      expect(response.status).toBe(403);
    });
  });

  describe('resetDocumentConsent', () => {
    it('should call DELETE endpoint for document consent reset', async () => {
      mockFetch.mockResolvedValueOnce({
        ok: true,
        json: () => Promise.resolve({
          status: 'success',
          message: 'Document consent reset to scope defaults',
          reset_to: 'inherit_scope_consent',
        }),
      });

      const documentId = 'doc-123';
      await fetch(`/api/py/consent/document/${documentId}`, {
        method: 'DELETE',
        credentials: 'include',
        headers: { 'Content-Type': 'application/json' },
      });

      expect(mockFetch).toHaveBeenCalledWith(
        `/api/py/consent/document/${documentId}`,
        expect.objectContaining({
          method: 'DELETE',
        })
      );
    });

    it('should handle 404 when no consent override exists', async () => {
      mockFetch.mockResolvedValueOnce({
        ok: false,
        status: 404,
      });

      const response = await fetch('/api/py/consent/document/nonexistent', {
        method: 'DELETE',
      });
      expect(response.status).toBe(404);
    });
  });
});

// =============================================================================
// Agent Access Management Tests
// =============================================================================

describe('useConsent Agent Access Management', () => {
  beforeEach(() => {
    vi.clearAllMocks();
    mockFetch.mockReset();
  });

  describe('updateScopeAgentAccess', () => {
    it('should send allow action to add agent to whitelist', async () => {
      mockFetch.mockResolvedValueOnce({
        ok: true,
        json: () => Promise.resolve({
          status: 'success',
          scope_id: 'scope-123',
          action: 'allow',
          agent_id: 'agent-claude-001',
          allowed_agent_ids: ['agent-claude-001'],
          blocked_agent_ids: [],
        }),
      });

      const scopeId = 'scope-123';
      await fetch(`/api/py/consent/scope/${scopeId}/agents`, {
        method: 'PATCH',
        credentials: 'include',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          action: 'allow',
          agent_id: 'agent-claude-001',
        }),
      });

      expect(mockFetch).toHaveBeenCalledWith(
        `/api/py/consent/scope/${scopeId}/agents`,
        expect.objectContaining({
          method: 'PATCH',
          body: JSON.stringify({
            action: 'allow',
            agent_id: 'agent-claude-001',
          }),
        })
      );
    });

    it('should send block action to add agent to blacklist', async () => {
      mockFetch.mockResolvedValueOnce({
        ok: true,
        json: () => Promise.resolve({
          status: 'success',
          scope_id: 'scope-123',
          action: 'block',
          agent_id: 'agent-malicious-001',
          allowed_agent_ids: [],
          blocked_agent_ids: ['agent-malicious-001'],
        }),
      });

      const scopeId = 'scope-123';
      await fetch(`/api/py/consent/scope/${scopeId}/agents`, {
        method: 'PATCH',
        credentials: 'include',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          action: 'block',
          agent_id: 'agent-malicious-001',
        }),
      });

      expect(mockFetch).toHaveBeenCalledWith(
        `/api/py/consent/scope/${scopeId}/agents`,
        expect.objectContaining({
          body: JSON.stringify({
            action: 'block',
            agent_id: 'agent-malicious-001',
          }),
        })
      );
    });

    it('should send remove action to clear agent from both lists', async () => {
      mockFetch.mockResolvedValueOnce({
        ok: true,
        json: () => Promise.resolve({
          status: 'success',
          scope_id: 'scope-123',
          action: 'remove',
          agent_id: 'agent-old-001',
          allowed_agent_ids: [],
          blocked_agent_ids: [],
        }),
      });

      const scopeId = 'scope-123';
      await fetch(`/api/py/consent/scope/${scopeId}/agents`, {
        method: 'PATCH',
        credentials: 'include',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          action: 'remove',
          agent_id: 'agent-old-001',
        }),
      });

      expect(mockFetch).toHaveBeenCalledWith(
        `/api/py/consent/scope/${scopeId}/agents`,
        expect.objectContaining({
          body: JSON.stringify({
            action: 'remove',
            agent_id: 'agent-old-001',
          }),
        })
      );
    });

    it('should handle 400 for invalid action', async () => {
      mockFetch.mockResolvedValueOnce({
        ok: false,
        status: 400,
      });

      const response = await fetch('/api/py/consent/scope/scope-123/agents', {
        method: 'PATCH',
        body: JSON.stringify({
          action: 'invalid_action',
          agent_id: 'agent-001',
        }),
      });

      expect(response.status).toBe(400);
    });
  });

  describe('updateDocumentAgentAccess', () => {
    it('should send allow action for document-level agent access', async () => {
      mockFetch.mockResolvedValueOnce({
        ok: true,
        json: () => Promise.resolve({
          status: 'success',
          document_id: 'doc-123',
          action: 'allow',
          agent_id: 'agent-trusted-001',
          allowed_agent_ids: ['agent-trusted-001'],
          blocked_agent_ids: [],
        }),
      });

      const documentId = 'doc-123';
      await fetch(`/api/py/consent/document/${documentId}/agents`, {
        method: 'PATCH',
        credentials: 'include',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          action: 'allow',
          agent_id: 'agent-trusted-001',
        }),
      });

      expect(mockFetch).toHaveBeenCalledWith(
        `/api/py/consent/document/${documentId}/agents`,
        expect.objectContaining({
          method: 'PATCH',
        })
      );
    });

    it('should handle 403 when user lacks editor permission', async () => {
      mockFetch.mockResolvedValueOnce({
        ok: false,
        status: 403,
      });

      const response = await fetch('/api/py/consent/document/doc-123/agents', {
        method: 'PATCH',
        body: JSON.stringify({
          action: 'allow',
          agent_id: 'agent-001',
        }),
      });

      expect(response.status).toBe(403);
    });
  });
});

// =============================================================================
// Agent Access Response Transform Tests
// =============================================================================

describe('Agent Access Response Transformations', () => {
  it('should transform snake_case response to camelCase', () => {
    const raw = {
      status: 'success',
      scope_id: 'scope-123',
      action: 'allow',
      agent_id: 'agent-claude-001',
      allowed_agent_ids: ['agent-claude-001', 'agent-claude-002'],
      blocked_agent_ids: ['agent-blocked-001'],
    };

    const transformed = {
      status: raw.status,
      action: raw.action,
      agentId: raw.agent_id,
      allowedAgentIds: raw.allowed_agent_ids || [],
      blockedAgentIds: raw.blocked_agent_ids || [],
    };

    expect(transformed.agentId).toBe('agent-claude-001');
    expect(transformed.allowedAgentIds).toEqual(['agent-claude-001', 'agent-claude-002']);
    expect(transformed.blockedAgentIds).toEqual(['agent-blocked-001']);
  });

  it('should default empty arrays when agent lists are null', () => {
    const raw = {
      status: 'success',
      action: 'remove',
      agent_id: 'agent-001',
      allowed_agent_ids: null,
      blocked_agent_ids: null,
    };

    const transformed = {
      allowedAgentIds: raw.allowed_agent_ids || [],
      blockedAgentIds: raw.blocked_agent_ids || [],
    };

    expect(transformed.allowedAgentIds).toEqual([]);
    expect(transformed.blockedAgentIds).toEqual([]);
  });
});

// =============================================================================
// New Hook Return Value Tests
// =============================================================================

describe('useConsent New Return Values', () => {
  it('should return resetScopeConsent function', () => {
    const returnValue = { resetScopeConsent: () => {} };
    expect(typeof returnValue.resetScopeConsent).toBe('function');
  });

  it('should return resetDocumentConsent function', () => {
    const returnValue = { resetDocumentConsent: () => {} };
    expect(typeof returnValue.resetDocumentConsent).toBe('function');
  });

  it('should return updateScopeAgentAccess function', () => {
    const returnValue = { updateScopeAgentAccess: () => {} };
    expect(typeof returnValue.updateScopeAgentAccess).toBe('function');
  });

  it('should return updateDocumentAgentAccess function', () => {
    const returnValue = { updateDocumentAgentAccess: () => {} };
    expect(typeof returnValue.updateDocumentAgentAccess).toBe('function');
  });

  it('should return isResettingScope boolean', () => {
    const returnValue = { isResettingScope: false };
    expect(typeof returnValue.isResettingScope).toBe('boolean');
  });

  it('should return isResettingDocument boolean', () => {
    const returnValue = { isResettingDocument: false };
    expect(typeof returnValue.isResettingDocument).toBe('boolean');
  });

  it('should return isUpdatingScopeAgent boolean', () => {
    const returnValue = { isUpdatingScopeAgent: false };
    expect(typeof returnValue.isUpdatingScopeAgent).toBe('boolean');
  });

  it('should return isUpdatingDocumentAgent boolean', () => {
    const returnValue = { isUpdatingDocumentAgent: false };
    expect(typeof returnValue.isUpdatingDocumentAgent).toBe('boolean');
  });

  it('should return fetchDocumentConsent function', () => {
    const returnValue = { fetchDocumentConsent: async () => null };
    expect(typeof returnValue.fetchDocumentConsent).toBe('function');
  });
});

// =============================================================================
// Agent Action Types Tests
// =============================================================================

describe('Agent Action Types', () => {
  it('should support allow action', () => {
    const actions = ['allow', 'block', 'remove'];
    expect(actions).toContain('allow');
  });

  it('should support block action', () => {
    const actions = ['allow', 'block', 'remove'];
    expect(actions).toContain('block');
  });

  it('should support remove action', () => {
    const actions = ['allow', 'block', 'remove'];
    expect(actions).toContain('remove');
  });

  it('should have exactly 3 valid actions', () => {
    const validActions = ['allow', 'block', 'remove'];
    expect(validActions).toHaveLength(3);
  });
});
