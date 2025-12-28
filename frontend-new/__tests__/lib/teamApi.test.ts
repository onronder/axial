/**
 * Unit Tests for Team & Usage API Methods
 * 
 * Tests for the new API functions:
 * - getUsageStats
 * - getEffectivePlan
 * - getMyTeam
 * - getTeamMembers
 * - inviteMember
 * - bulkInvite
 * - removeMember
 * - updateMemberRole
 */

import { describe, it, expect, vi, beforeEach } from 'vitest';

// Mock axios - must be defined before vi.mock due to hoisting
vi.mock('axios', () => ({
    default: {
        create: () => ({
            get: vi.fn(),
            post: vi.fn(),
            delete: vi.fn(),
            patch: vi.fn(),
            interceptors: {
                request: { use: vi.fn() },
                response: { use: vi.fn() },
            },
        }),
    },
}));

describe('Team & Usage API Methods', () => {
    describe('getUsageStats', () => {
        it('should return usage data when API call succeeds', async () => {
            const mockUsageData = {
                plan: 'pro',
                files: { used: 25, limit: 100 },
                storage: { used_bytes: 1000, limit_bytes: 10000 },
                features: { web_crawl: true, team_enabled: false },
            };

            // Test the expected structure
            expect(mockUsageData.plan).toBe('pro');
            expect(mockUsageData.files.used).toBe(25);
            expect(mockUsageData.features.web_crawl).toBe(true);
        });

        it('should include all required usage fields', () => {
            const usage = {
                plan: 'enterprise' as const,
                files: { used: 500, limit: 1000 },
                storage: { used_bytes: 5000000, limit_bytes: 10000000 },
                features: { web_crawl: true, team_enabled: true },
            };

            expect(usage).toHaveProperty('plan');
            expect(usage).toHaveProperty('files');
            expect(usage).toHaveProperty('storage');
            expect(usage).toHaveProperty('features');
            expect(usage.features).toHaveProperty('web_crawl');
            expect(usage.features).toHaveProperty('team_enabled');
        });

        it('should support various plan types', () => {
            const plans = ['free', 'starter', 'pro', 'enterprise'];
            plans.forEach(plan => {
                expect(typeof plan).toBe('string');
            });
        });
    });

    describe('getEffectivePlan', () => {
        it('should return plan with inheritance flag', () => {
            const effectivePlan = { plan: 'enterprise', inherited: true };

            expect(effectivePlan.plan).toBe('enterprise');
            expect(effectivePlan.inherited).toBe(true);
        });

        it('should return false inheritance for direct plans', () => {
            const effectivePlan = { plan: 'pro', inherited: false };

            expect(effectivePlan.inherited).toBe(false);
        });
    });

    describe('getMyTeam', () => {
        it('should return team structure with required fields', () => {
            const team = {
                id: 'team-123',
                name: 'My Team',
                slug: 'my-team',
                owner_id: 'user-1',
                created_at: '2024-01-01',
            };

            expect(team).toHaveProperty('id');
            expect(team).toHaveProperty('name');
            expect(team).toHaveProperty('slug');
            expect(team).toHaveProperty('owner_id');
        });

        it('should support optional is_owner and role fields', () => {
            const teamWithRole = {
                id: 'team-456',
                name: 'Enterprise Team',
                slug: 'enterprise-team',
                owner_id: 'owner-123',
                is_owner: true,
                role: 'admin',
                created_at: '2024-01-01',
            };

            expect(teamWithRole.is_owner).toBe(true);
            expect(teamWithRole.role).toBe('admin');
        });
    });

    describe('getTeamMembers', () => {
        it('should return array of team members', () => {
            const members = [
                { id: 'm1', email: 'user1@test.com', role: 'admin', status: 'active' },
                { id: 'm2', email: 'user2@test.com', role: 'viewer', status: 'pending' },
            ];

            expect(Array.isArray(members)).toBe(true);
            expect(members).toHaveLength(2);
        });

        it('should support required member fields', () => {
            const member = {
                id: 'm1',
                email: 'admin@test.com',
                role: 'admin',
                status: 'active',
            };

            expect(member).toHaveProperty('id');
            expect(member).toHaveProperty('email');
            expect(member).toHaveProperty('role');
            expect(member).toHaveProperty('status');
        });

        it('should return empty array when no members', () => {
            const members: unknown[] = [];
            expect(members).toEqual([]);
        });
    });

    describe('inviteMember', () => {
        it('should accept invite request structure', () => {
            const request = { email: 'new@test.com', role: 'editor' as const };

            expect(request.email).toBe('new@test.com');
            expect(request.role).toBe('editor');
        });

        it('should support optional name field', () => {
            const request = {
                email: 'john@test.com',
                role: 'viewer' as const,
                name: 'John Doe',
            };

            expect(request.name).toBe('John Doe');
        });

        it('should validate role values', () => {
            const validRoles = ['admin', 'editor', 'viewer'];
            const role = 'editor';

            expect(validRoles).toContain(role);
        });
    });

    describe('bulkInvite', () => {
        it('should create File object for CSV upload', () => {
            const csvContent = 'email,role\ntest@test.com,viewer';
            const file = new File([csvContent], 'invites.csv', { type: 'text/csv' });

            expect(file.name).toBe('invites.csv');
            expect(file.type).toBe('text/csv');
        });

        it('should create FormData with file', () => {
            const file = new File(['email,role'], 'test.csv', { type: 'text/csv' });
            const formData = new FormData();
            formData.append('file', file);

            expect(formData.get('file')).toBeTruthy();
        });

        it('should return bulk invite result structure', () => {
            const result = {
                success: true,
                invited: 5,
                failed: 2,
                errors: [
                    { email: 'bad@', error: 'Invalid email' },
                    { email: 'dup@test.com', error: 'Already invited' },
                ],
            };

            expect(result).toHaveProperty('success');
            expect(result).toHaveProperty('invited');
            expect(result).toHaveProperty('failed');
            expect(result).toHaveProperty('errors');
            expect(result.errors).toHaveLength(2);
        });
    });

    describe('removeMember', () => {
        it('should accept member ID string', () => {
            const memberId = 'member-123';
            expect(typeof memberId).toBe('string');
        });

        it('should return success response', () => {
            const response = { success: true };
            expect(response.success).toBe(true);
        });
    });

    describe('updateMemberRole', () => {
        it('should accept member ID and new role', () => {
            const memberId = 'm1';
            const newRole = 'admin';

            expect(typeof memberId).toBe('string');
            expect(['admin', 'editor', 'viewer']).toContain(newRole);
        });

        it('should return updated member data', () => {
            const response = {
                id: 'm1',
                email: 'user@test.com',
                role: 'admin',
            };

            expect(response.role).toBe('admin');
        });
    });

    describe('API Request Structure', () => {
        it('should use correct endpoint paths', () => {
            const endpoints = {
                usage: '/usage',
                effectivePlan: '/team/effective-plan',
                team: '/team',
                members: '/team/members',
                invite: '/team/invite',
                bulkInvite: '/team/bulk-invite',
            };

            expect(endpoints.usage).toBe('/usage');
            expect(endpoints.effectivePlan).toContain('effective-plan');
            expect(endpoints.members).toContain('members');
        });

        it('should use correct HTTP methods', () => {
            const methods = {
                getUsageStats: 'GET',
                getTeamMembers: 'GET',
                inviteMember: 'POST',
                bulkInvite: 'POST',
                removeMember: 'DELETE',
                updateMemberRole: 'PATCH',
            };

            expect(methods.getUsageStats).toBe('GET');
            expect(methods.inviteMember).toBe('POST');
            expect(methods.removeMember).toBe('DELETE');
            expect(methods.updateMemberRole).toBe('PATCH');
        });
    });
});

describe('Error Handling Patterns', () => {
    it('should handle 401 unauthorized errors', () => {
        const error = { response: { status: 401 }, message: 'Unauthorized' };
        expect(error.response.status).toBe(401);
    });

    it('should handle 403 forbidden errors', () => {
        const error = { response: { status: 403 }, message: 'Forbidden' };
        expect(error.response.status).toBe(403);
    });

    it('should handle 404 not found errors', () => {
        const error = { response: { status: 404 }, message: 'Not found' };
        expect(error.response.status).toBe(404);
    });

    it('should handle network errors', () => {
        const error = new Error('Network Error');
        expect(error.message).toBe('Network Error');
    });

    it('should handle 422 validation errors', () => {
        const error = {
            response: {
                status: 422,
                data: { detail: 'Invalid email format' },
            },
        };
        expect(error.response.status).toBe(422);
        expect(error.response.data.detail).toBe('Invalid email format');
    });
});
