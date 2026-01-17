/**
 * Schema Synchronization Tests
 * 
 * These tests verify that frontend TypeScript types match the actual
 * backend API responses. This catches drift between frontend and backend.
 * 
 * IMPORTANT: Update these tests when making schema changes to ensure
 * frontend types stay in sync with backend API contracts.
 * 
 * Run with: npm test -- --testPathPattern=schema-sync
 */

import { describe, it, expect } from 'vitest';

// Import all frontend types
import type { 
    UserUsage, 
    EffectivePlan, 
    Team,
    PlanType,
    Document,
    ChatConversation,
    Message,
    Source,
} from '@/types';

/**
 * Type definitions for backend API responses
 * These should match what the backend actually returns
 */

// From GET /api/v1/usage
interface BackendUsageResponse {
    plan: string;
    files: {
        used: number;
        limit: number;
    };
    storage: {
        used_bytes: number;
        limit_bytes: number;
    };
    features: {
        web_crawl: boolean;
        team?: boolean;
        team_enabled?: boolean;
        premium_models?: boolean;
    };
    model_tier?: string;
    subscription_status: string; // From subscriptions table (NOT user_profiles)
}

// From GET /api/v1/team/effective-plan
interface BackendEffectivePlanResponse {
    plan: string;
    inherited: boolean;
    team_id: string | null;
    team_name: string | null;
}

// From GET /api/v1/team
interface BackendTeamResponse {
    id: string;
    name: string;
    slug: string;
    owner_id: string;
    is_owner?: boolean;
    role?: string;
    created_at: string;
}

describe('Schema Synchronization', () => {
    
    describe('UserUsage Type', () => {
        it('should have all required fields from backend', () => {
            // This test documents the expected fields
            const mockBackendResponse: BackendUsageResponse = {
                plan: 'pro',
                files: { used: 5, limit: 100 },
                storage: { used_bytes: 1024, limit_bytes: 1073741824 },
                features: { web_crawl: true, team: true, team_enabled: true, premium_models: true },
                model_tier: 'hybrid',
                subscription_status: 'active', // NOW comes from subscriptions table
            };
            
            // Verify frontend type can receive this data
            const frontendUsage: UserUsage = {
                plan: mockBackendResponse.plan as PlanType,
                files: mockBackendResponse.files,
                storage: mockBackendResponse.storage,
                features: mockBackendResponse.features,
                model_tier: mockBackendResponse.model_tier,
                subscription_status: mockBackendResponse.subscription_status,
            };
            
            expect(frontendUsage.plan).toBeDefined();
            expect(frontendUsage.subscription_status).toBeDefined();
        });
        
        it('should accept valid subscription_status values', () => {
            // Document valid subscription_status values
            // These come from subscriptions.status column
            const validStatuses = ['active', 'trialing', 'canceled', 'past_due', 'inactive'];
            
            validStatuses.forEach(status => {
                const usage: Partial<UserUsage> = {
                    subscription_status: status,
                };
                expect(usage.subscription_status).toBe(status);
            });
        });
    });
    
    describe('EffectivePlan Type', () => {
        it('should match backend response structure', () => {
            const mockBackendResponse: BackendEffectivePlanResponse = {
                plan: 'enterprise',
                inherited: true,
                team_id: 'team-123',
                team_name: 'Acme Corp',
            };
            
            const frontendPlan: EffectivePlan = mockBackendResponse as EffectivePlan;
            
            expect(frontendPlan.plan).toBe('enterprise');
            expect(frontendPlan.inherited).toBe(true);
        });
        
        it('should accept all valid plan types', () => {
            const validPlans: PlanType[] = ['none', 'free', 'starter', 'pro', 'enterprise'];
            
            validPlans.forEach(plan => {
                const effectivePlan: Partial<EffectivePlan> = { plan };
                expect(effectivePlan.plan).toBe(plan);
            });
        });
    });
    
    describe('Team Type', () => {
        it('should match backend response structure', () => {
            const mockBackendResponse: BackendTeamResponse = {
                id: 'team-123',
                name: 'Acme Corp',
                slug: 'acme-corp',
                owner_id: 'user-456',
                is_owner: true,
                role: 'admin',
                created_at: '2024-01-01T00:00:00Z',
            };
            
            const frontendTeam: Team = mockBackendResponse as Team;
            
            expect(frontendTeam.id).toBeDefined();
            expect(frontendTeam.name).toBeDefined();
        });
    });
    
    describe('Schema Change Documentation', () => {
        /**
         * IMPORTANT: Document schema changes here to prevent future issues
         */
        
        it('subscription_status column removal is documented', () => {
            // Migration 20251231130000 REMOVED subscription_status from user_profiles
            // Now the status comes from subscriptions.status instead
            // 
            // OLD SCHEMA (DEPRECATED):
            // - user_profiles.subscription_status
            // 
            // NEW SCHEMA (CURRENT):
            // - subscriptions.status (source of truth)
            // - subscriptions.plan_type
            // 
            // The API still returns subscription_status to frontend,
            // but it's now sourced from subscriptions table
            
            expect(true).toBe(true); // Documentation test
        });
        
        it('plan hierarchy is documented', () => {
            // PLAN HIERARCHY (from get_effective_plan):
            // 1. Check subscriptions.plan_type (team-based, from Polar webhooks)
            // 2. Fallback to user_profiles.plan (legacy)
            // 3. Default to 'free'
            //
            // Valid plans: none < free < starter < pro < enterprise
            
            const planHierarchy: PlanType[] = ['none', 'free', 'starter', 'pro', 'enterprise'];
            expect(planHierarchy).toHaveLength(5);
        });
    });
});

describe('API Response Contract Tests', () => {
    /**
     * These tests document the expected API response shapes.
     * They don't make actual API calls but ensure type compatibility.
     */
    
    it('GET /api/v1/usage response shape', () => {
        // Document the expected response shape
        type ExpectedResponse = {
            plan: PlanType;
            files: { used: number; limit: number };
            storage: { used_bytes: number; limit_bytes: number };
            features: {
                web_crawl: boolean;
                team?: boolean;
                team_enabled?: boolean;
                premium_models?: boolean;
            };
            model_tier?: string;
            subscription_status: string;
        };
        
        // This is a compile-time check - if types don't match, TS will error
        const _typeCheck: ExpectedResponse extends UserUsage ? true : false = true;
        expect(_typeCheck).toBe(true);
    });
    
    it('GET /api/v1/team/effective-plan response shape', () => {
        type ExpectedResponse = {
            plan: PlanType;
            inherited: boolean;
            team_id: string | null;
            team_name: string | null;
        };
        
        const _typeCheck: ExpectedResponse extends EffectivePlan ? true : false = true;
        expect(_typeCheck).toBe(true);
    });
    
    it('Chat message response includes scope context', () => {
        // Document that chat messages may include scope context
        const messageWithScope: Message = {
            id: 'msg-1',
            role: 'assistant',
            content: 'Answer based on documents...',
            sources: [{ index: 1, type: 'File', label: 'report.pdf' }],
            scope_context: {
                scope_id: 'upload://user/manual',
                scope_name: 'Manual Uploads',
                dominance_ratio: 0.95,
                classification: 'dominant',
            },
        };
        
        expect(messageWithScope.scope_context).toBeDefined();
        expect(messageWithScope.scope_context?.classification).toBe('dominant');
    });
});
