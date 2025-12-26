/**
 * Unit Tests for useNotificationSettings Hook
 * 
 * Tests the notification settings hook including:
 * - Fetching settings on mount
 * - Toggle functionality with optimistic updates
 * - Error handling and rollback
 * - Category filtering
 */

import { describe, it, expect, beforeEach, vi } from 'vitest';
import { renderHook, act, waitFor } from '@testing-library/react';
import { useNotificationSettings, NotificationSetting } from '@/hooks/useNotificationSettings';
import { api } from '@/lib/api';

// Mock the api module
vi.mock('@/lib/api', () => ({
    api: {
        get: vi.fn(),
        patch: vi.fn(),
    },
}));

// Mock the toast hook
const mockToast = vi.fn();
vi.mock('@/hooks/use-toast', () => ({
    useToast: () => ({ toast: mockToast }),
}));

const mockApi = api as unknown as { get: ReturnType<typeof vi.fn>; patch: ReturnType<typeof vi.fn> };

const mockSettings: NotificationSetting[] = [
    {
        id: '1',
        setting_key: 'email_on_ingestion_complete',
        setting_label: 'Ingestion Complete Emails',
        setting_description: 'Receive email when processing finishes',
        category: 'email',
        enabled: true,
    },
    {
        id: '2',
        setting_key: 'weekly-digest',
        setting_label: 'Weekly Digest',
        setting_description: 'Receive weekly summary',
        category: 'email',
        enabled: false,
    },
    {
        id: '3',
        setting_key: 'ingestion-completed',
        setting_label: 'Ingestion Completed',
        setting_description: 'System notification when file finishes',
        category: 'system',
        enabled: true,
    },
];

describe('useNotificationSettings', () => {
    beforeEach(() => {
        vi.clearAllMocks();
        mockApi.get.mockResolvedValue({ data: mockSettings });
        mockApi.patch.mockResolvedValue({ data: mockSettings[0] });
    });

    describe('Initial Fetch', () => {
        it('should fetch settings on mount', async () => {
            const { result } = renderHook(() => useNotificationSettings());

            expect(result.current.isLoading).toBe(true);

            await waitFor(() => {
                expect(result.current.isLoading).toBe(false);
            });

            expect(mockApi.get).toHaveBeenCalledWith('/settings/notifications');
            expect(result.current.settings).toEqual(mockSettings);
        });

        it('should set error on fetch failure', async () => {
            mockApi.get.mockRejectedValue(new Error('Network error'));

            const { result } = renderHook(() => useNotificationSettings());

            await waitFor(() => {
                expect(result.current.isLoading).toBe(false);
            });

            expect(result.current.error).toBeTruthy();
        });

        it('should start with loading state true', () => {
            const { result } = renderHook(() => useNotificationSettings());
            expect(result.current.isLoading).toBe(true);
        });
    });

    describe('Category Filtering', () => {
        it('should separate email settings', async () => {
            const { result } = renderHook(() => useNotificationSettings());

            await waitFor(() => {
                expect(result.current.isLoading).toBe(false);
            });

            expect(result.current.emailSettings).toHaveLength(2);
            expect(result.current.emailSettings.every(s => s.category === 'email')).toBe(true);
        });

        it('should separate system settings', async () => {
            const { result } = renderHook(() => useNotificationSettings());

            await waitFor(() => {
                expect(result.current.isLoading).toBe(false);
            });

            expect(result.current.systemSettings).toHaveLength(1);
            expect(result.current.systemSettings.every(s => s.category === 'system')).toBe(true);
        });

        it('should include email_on_ingestion_complete in email settings', async () => {
            const { result } = renderHook(() => useNotificationSettings());

            await waitFor(() => {
                expect(result.current.isLoading).toBe(false);
            });

            const emailIngestionSetting = result.current.emailSettings.find(
                s => s.setting_key === 'email_on_ingestion_complete'
            );
            expect(emailIngestionSetting).toBeDefined();
            expect(emailIngestionSetting?.category).toBe('email');
        });
    });

    describe('Toggle Setting', () => {
        it('should toggle setting with optimistic update', async () => {
            const { result } = renderHook(() => useNotificationSettings());

            await waitFor(() => {
                expect(result.current.isLoading).toBe(false);
            });

            const initialValue = result.current.settings[0].enabled;

            await act(async () => {
                await result.current.toggleSetting('email_on_ingestion_complete');
            });

            // API should be called with toggled value
            expect(mockApi.patch).toHaveBeenCalledWith('/settings/notifications', {
                setting_key: 'email_on_ingestion_complete',
                enabled: !initialValue,
            });
        });

        it('should show success toast on successful toggle', async () => {
            const { result } = renderHook(() => useNotificationSettings());

            await waitFor(() => {
                expect(result.current.isLoading).toBe(false);
            });

            await act(async () => {
                await result.current.toggleSetting('email_on_ingestion_complete');
            });

            expect(mockToast).toHaveBeenCalledWith(
                expect.objectContaining({
                    title: 'Preference updated',
                })
            );
        });

        it('should return true on successful toggle', async () => {
            const { result } = renderHook(() => useNotificationSettings());

            await waitFor(() => {
                expect(result.current.isLoading).toBe(false);
            });

            let success = false;
            await act(async () => {
                success = await result.current.toggleSetting('email_on_ingestion_complete');
            });

            expect(success).toBe(true);
        });

        it('should return false when setting does not exist', async () => {
            const { result } = renderHook(() => useNotificationSettings());

            await waitFor(() => {
                expect(result.current.isLoading).toBe(false);
            });

            let success = false;
            await act(async () => {
                success = await result.current.toggleSetting('nonexistent_setting');
            });

            expect(success).toBe(false);
        });
    });

    describe('Error Handling & Rollback', () => {
        it('should rollback optimistic update on API error', async () => {
            mockApi.patch.mockRejectedValue(new Error('API error'));

            const { result } = renderHook(() => useNotificationSettings());

            await waitFor(() => {
                expect(result.current.isLoading).toBe(false);
            });

            const initialValue = result.current.settings[0].enabled;

            await act(async () => {
                await result.current.toggleSetting('email_on_ingestion_complete');
            });

            // Should have rolled back to initial value
            expect(result.current.settings[0].enabled).toBe(initialValue);
        });

        it('should show error toast on API failure', async () => {
            mockApi.patch.mockRejectedValue(new Error('API error'));

            const { result } = renderHook(() => useNotificationSettings());

            await waitFor(() => {
                expect(result.current.isLoading).toBe(false);
            });

            await act(async () => {
                await result.current.toggleSetting('email_on_ingestion_complete');
            });

            expect(mockToast).toHaveBeenCalledWith(
                expect.objectContaining({
                    title: 'Error',
                    variant: 'destructive',
                })
            );
        });

        it('should return false on API error', async () => {
            mockApi.patch.mockRejectedValue(new Error('API error'));

            const { result } = renderHook(() => useNotificationSettings());

            await waitFor(() => {
                expect(result.current.isLoading).toBe(false);
            });

            let success = false;
            await act(async () => {
                success = await result.current.toggleSetting('email_on_ingestion_complete');
            });

            expect(success).toBe(false);
        });
    });

    describe('Refresh Functionality', () => {
        it('should provide refresh function', async () => {
            const { result } = renderHook(() => useNotificationSettings());

            await waitFor(() => {
                expect(result.current.isLoading).toBe(false);
            });

            expect(typeof result.current.refresh).toBe('function');
        });

        it('should refetch settings when refresh is called', async () => {
            const { result } = renderHook(() => useNotificationSettings());

            await waitFor(() => {
                expect(result.current.isLoading).toBe(false);
            });

            // Clear previous calls
            mockApi.get.mockClear();

            await act(async () => {
                await result.current.refresh();
            });

            expect(mockApi.get).toHaveBeenCalledWith('/settings/notifications');
        });
    });

    describe('NotificationSetting Interface', () => {
        it('should have correct structure for email ingestion setting', async () => {
            const { result } = renderHook(() => useNotificationSettings());

            await waitFor(() => {
                expect(result.current.isLoading).toBe(false);
            });

            const emailSetting = result.current.settings.find(
                s => s.setting_key === 'email_on_ingestion_complete'
            );

            expect(emailSetting).toMatchObject({
                id: expect.any(String),
                setting_key: 'email_on_ingestion_complete',
                setting_label: expect.any(String),
                category: 'email',
                enabled: expect.any(Boolean),
            });
        });
    });
});
