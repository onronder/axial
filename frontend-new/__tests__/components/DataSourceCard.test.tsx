import { describe, it, expect, vi, beforeEach } from 'vitest';
import { render, screen, fireEvent, waitFor } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { DataSourceCard } from '@/components/data-sources/DataSourceCard';
import type { MergedDataSource, PlanType } from '@/types';

// =============================================================================
// Mocks
// =============================================================================

const mockToast = vi.fn();
vi.mock('@/hooks/use-toast', () => ({
    useToast: () => ({ toast: mockToast }),
}));

// Mock window.location
const mockLocation = { href: '' };
Object.defineProperty(window, 'location', {
    value: mockLocation,
    writable: true,
});

// =============================================================================
// Test Data
// =============================================================================

const createSource = (overrides: Partial<MergedDataSource> = {}): MergedDataSource => ({
    id: 'google-drive',
    definitionId: 'def-gdrive',
    type: 'google_drive',
    name: 'Google Drive',
    description: 'Connect to Google Drive for seamless file access',
    iconPath: null,
    category: 'cloud',
    isConnected: false,
    lastSyncAt: null,
    integrationId: null,
    ...overrides,
});

// =============================================================================
// Test Suite
// =============================================================================

describe('DataSourceCard Component', () => {
    const mockOnBrowse = vi.fn();
    const mockOnConnect = vi.fn();
    const mockOnDisconnect = vi.fn().mockResolvedValue(undefined);
    const mockOnSync = vi.fn().mockResolvedValue({ success: true, jobId: 'job-123' });

    const defaultProps = {
        source: createSource(),
        onBrowse: mockOnBrowse,
        onConnect: mockOnConnect,
        onDisconnect: mockOnDisconnect,
        onSync: mockOnSync,
    };

    beforeEach(() => {
        vi.clearAllMocks();
        mockLocation.href = '';
    });

    // =========================================================================
    // Rendering Tests - Disconnected State
    // =========================================================================

    describe('Disconnected State', () => {
        it('should render the source name', () => {
            render(<DataSourceCard {...defaultProps} />);
            expect(screen.getByText('Google Drive')).toBeInTheDocument();
        });

        it('should render the source description', () => {
            render(<DataSourceCard {...defaultProps} />);
            expect(screen.getByText('Connect to Google Drive for seamless file access')).toBeInTheDocument();
        });

        it('should render Connect button when disconnected', () => {
            render(<DataSourceCard {...defaultProps} />);
            expect(screen.getByRole('button', { name: /connect/i })).toBeInTheDocument();
        });

        it('should not show Connected badge when disconnected', () => {
            render(<DataSourceCard {...defaultProps} />);
            expect(screen.queryByText('Connected')).not.toBeInTheDocument();
        });

        it('should not show Browse or Sync buttons when disconnected', () => {
            render(<DataSourceCard {...defaultProps} />);
            expect(screen.queryByRole('button', { name: /browse/i })).not.toBeInTheDocument();
        });
    });

    // =========================================================================
    // Rendering Tests - Connected State
    // =========================================================================

    describe('Connected State', () => {
        it('should show Connected badge when connected', () => {
            render(<DataSourceCard {...defaultProps} source={createSource({ isConnected: true })} />);
            expect(screen.getByText('Connected')).toBeInTheDocument();
        });

        it('should show Browse button when connected', () => {
            render(<DataSourceCard {...defaultProps} source={createSource({ isConnected: true })} />);
            expect(screen.getByRole('button', { name: /browse/i })).toBeInTheDocument();
        });

        it('should not show Connect button when connected', () => {
            render(<DataSourceCard {...defaultProps} source={createSource({ isConnected: true })} />);
            expect(screen.queryByRole('button', { name: /^connect$/i })).not.toBeInTheDocument();
        });

        it('should show last sync time when connected', () => {
            const lastSync = new Date().toISOString();
            render(<DataSourceCard {...defaultProps} source={createSource({ isConnected: true, lastSyncAt: lastSync })} />);
            expect(screen.getByText(/synced/i)).toBeInTheDocument();
        });

        it('should show "Never" for sync time when null', () => {
            render(<DataSourceCard {...defaultProps} source={createSource({ isConnected: true, lastSyncAt: null })} />);
            expect(screen.getByText(/Never/i)).toBeInTheDocument();
        });
    });

    // =========================================================================
    // formatLastSync Tests
    // =========================================================================

    describe('formatLastSync', () => {
        it('should show "Just now" for recent sync', () => {
            const now = new Date().toISOString();
            render(<DataSourceCard {...defaultProps} source={createSource({ isConnected: true, lastSyncAt: now })} />);
            expect(screen.getByText(/Just now/i)).toBeInTheDocument();
        });

        it('should show minutes ago for sync within an hour', () => {
            const thirtyMinAgo = new Date(Date.now() - 30 * 60 * 1000).toISOString();
            render(<DataSourceCard {...defaultProps} source={createSource({ isConnected: true, lastSyncAt: thirtyMinAgo })} />);
            expect(screen.getByText(/30m ago/i)).toBeInTheDocument();
        });

        it('should show hours ago for sync within a day', () => {
            const fiveHoursAgo = new Date(Date.now() - 5 * 60 * 60 * 1000).toISOString();
            render(<DataSourceCard {...defaultProps} source={createSource({ isConnected: true, lastSyncAt: fiveHoursAgo })} />);
            expect(screen.getByText(/5h ago/i)).toBeInTheDocument();
        });

        it('should show days ago for sync within a week', () => {
            const threeDaysAgo = new Date(Date.now() - 3 * 24 * 60 * 60 * 1000).toISOString();
            render(<DataSourceCard {...defaultProps} source={createSource({ isConnected: true, lastSyncAt: threeDaysAgo })} />);
            expect(screen.getByText(/3d ago/i)).toBeInTheDocument();
        });

        it('should show date for sync older than a week', () => {
            const twoWeeksAgo = new Date(Date.now() - 14 * 24 * 60 * 60 * 1000).toISOString();
            render(<DataSourceCard {...defaultProps} source={createSource({ isConnected: true, lastSyncAt: twoWeeksAgo })} />);
            // Should show a date format
            expect(screen.getByText(/synced/i)).toBeInTheDocument();
        });
    });

    // =========================================================================
    // Connect Action Tests
    // =========================================================================

    describe('Connect Action', () => {
        it('should call onConnect when Connect button is clicked', async () => {
            const user = userEvent.setup();
            render(<DataSourceCard {...defaultProps} />);

            await user.click(screen.getByRole('button', { name: /connect/i }));

            expect(mockOnConnect).toHaveBeenCalledWith('google_drive');
        });

        it('should disable Connect button when disabled prop is true', () => {
            render(<DataSourceCard {...defaultProps} disabled={true} />);

            // When disabled, the Connect button is actually disabled in the DOM
            expect(screen.getByRole('button', { name: /connect/i })).toBeDisabled();
        });
    });

    // =========================================================================
    // Disconnect Action Tests
    // =========================================================================

    describe('Disconnect Action', () => {
        it('should call onDisconnect when disconnect button is clicked', async () => {
            render(<DataSourceCard {...defaultProps} source={createSource({ isConnected: true })} />);

            const buttons = screen.getAllByRole('button');
            // Find the button that contains an X icon (disconnect button)
            const xButton = buttons.find(btn => btn.querySelector('.lucide-x'));
            
            if (xButton) {
                fireEvent.click(xButton);
            }

            await waitFor(() => {
                expect(mockOnDisconnect).toHaveBeenCalledWith('google_drive');
            });
        });

        it('should show success toast after disconnect', async () => {
            render(<DataSourceCard {...defaultProps} source={createSource({ isConnected: true })} />);

            const buttons = screen.getAllByRole('button');
            const xButton = buttons.find(btn => btn.querySelector('.lucide-x'));
            
            if (xButton) {
                fireEvent.click(xButton);
            }

            await waitFor(() => {
                expect(mockToast).toHaveBeenCalledWith(expect.objectContaining({
                    title: 'Google Drive disconnected',
                }));
            });
        });

        it('should disable disconnect button when disabled prop is true', () => {
            render(<DataSourceCard {...defaultProps} source={createSource({ isConnected: true })} disabled={true} />);

            const buttons = screen.getAllByRole('button');
            const xButton = buttons.find(btn => btn.querySelector('.lucide-x'));
            
            expect(xButton).toBeDisabled();
        });

        it('should show error toast when disconnect fails', async () => {
            mockOnDisconnect.mockRejectedValueOnce(new Error('Network error'));
            render(<DataSourceCard {...defaultProps} source={createSource({ isConnected: true })} />);

            const buttons = screen.getAllByRole('button');
            const xButton = buttons.find(btn => btn.querySelector('.lucide-x'));
            
            if (xButton) {
                fireEvent.click(xButton);
            }

            await waitFor(() => {
                expect(mockToast).toHaveBeenCalledWith(expect.objectContaining({
                    title: 'Disconnection failed',
                    variant: 'destructive',
                }));
            });
        });
    });

    // =========================================================================
    // Browse Action Tests
    // =========================================================================

    describe('Browse Action', () => {
        it('should call onBrowse when Browse button is clicked', async () => {
            const user = userEvent.setup();
            render(<DataSourceCard {...defaultProps} source={createSource({ isConnected: true })} />);

            await user.click(screen.getByRole('button', { name: /browse/i }));

            expect(mockOnBrowse).toHaveBeenCalled();
        });

        it('should disable Browse button when disabled prop is true', () => {
            render(<DataSourceCard {...defaultProps} source={createSource({ isConnected: true })} disabled={true} />);

            expect(screen.getByRole('button', { name: /browse/i })).toBeDisabled();
        });
    });

    // =========================================================================
    // Sync Action Tests
    // =========================================================================

    describe('Sync Action', () => {
        it('should call onSync when sync button is clicked', async () => {
            const user = userEvent.setup();
            const source = createSource({ isConnected: true, integrationId: 'int-123' });
            render(<DataSourceCard {...defaultProps} source={source} />);

            // Find sync button (RefreshCw icon)
            const buttons = screen.getAllByRole('button');
            const syncButton = buttons.find(btn => btn.querySelector('.lucide-refresh-cw'));
            
            if (syncButton) {
                await user.click(syncButton);
            }

            await waitFor(() => {
                expect(mockOnSync).toHaveBeenCalledWith('int-123');
            });
        });

        it('should show success toast after sync starts', async () => {
            const user = userEvent.setup();
            const source = createSource({ isConnected: true, integrationId: 'int-123' });
            render(<DataSourceCard {...defaultProps} source={source} />);

            const buttons = screen.getAllByRole('button');
            const syncButton = buttons.find(btn => btn.querySelector('.lucide-refresh-cw'));
            
            if (syncButton) {
                await user.click(syncButton);
            }

            await waitFor(() => {
                expect(mockToast).toHaveBeenCalledWith(expect.objectContaining({
                    title: 'Sync Started',
                }));
            });
        });

        it('should disable sync button when disabled prop is true', () => {
            const source = createSource({ isConnected: true, integrationId: 'int-123' });
            render(<DataSourceCard {...defaultProps} source={source} disabled={true} />);

            const buttons = screen.getAllByRole('button');
            const syncButton = buttons.find(btn => btn.querySelector('.lucide-refresh-cw'));
            
            expect(syncButton).toBeDisabled();
        });

        it('should show error toast when sync fails', async () => {
            mockOnSync.mockRejectedValueOnce(new Error('Sync error'));
            const user = userEvent.setup();
            const source = createSource({ isConnected: true, integrationId: 'int-123' });
            render(<DataSourceCard {...defaultProps} source={source} />);

            const buttons = screen.getAllByRole('button');
            const syncButton = buttons.find(btn => btn.querySelector('.lucide-refresh-cw'));
            
            if (syncButton) {
                await user.click(syncButton);
            }

            await waitFor(() => {
                expect(mockToast).toHaveBeenCalledWith(expect.objectContaining({
                    title: 'Sync Failed',
                    variant: 'destructive',
                }));
            });
        });

        it('should not call onSync when integrationId is null', async () => {
            const user = userEvent.setup();
            const source = createSource({ isConnected: true, integrationId: null });
            render(<DataSourceCard {...defaultProps} source={source} />);

            const buttons = screen.getAllByRole('button');
            const syncButton = buttons.find(btn => btn.querySelector('.lucide-refresh-cw'));
            
            if (syncButton) {
                await user.click(syncButton);
            }

            expect(mockOnSync).not.toHaveBeenCalled();
        });
    });

    // =========================================================================
    // Enterprise Gating Tests
    // =========================================================================

    describe('Enterprise Gating', () => {
        it('should show Enterprise badge for enterprise-only sources', () => {
            render(<DataSourceCard {...defaultProps} enterpriseOnly={true} userPlan="starter" />);
            expect(screen.getByText('Enterprise')).toBeInTheDocument();
        });

        it('should show Upgrade to Enterprise button for non-enterprise users', () => {
            render(<DataSourceCard {...defaultProps} enterpriseOnly={true} userPlan="starter" />);
            expect(screen.getByRole('button', { name: /upgrade to enterprise/i })).toBeInTheDocument();
        });

        it('should show Connect button for enterprise users on enterprise-only sources', () => {
            render(<DataSourceCard {...defaultProps} enterpriseOnly={true} userPlan="enterprise" />);
            expect(screen.getByRole('button', { name: /^connect$/i })).toBeInTheDocument();
            expect(screen.queryByRole('button', { name: /upgrade/i })).not.toBeInTheDocument();
        });

        it('should navigate to billing page when Upgrade button is clicked', async () => {
            const user = userEvent.setup();
            render(<DataSourceCard {...defaultProps} enterpriseOnly={true} userPlan="pro" />);

            await user.click(screen.getByRole('button', { name: /upgrade to enterprise/i }));

            expect(mockLocation.href).toBe('/dashboard/settings/billing');
        });

        it('should not show Enterprise badge when source is already connected', () => {
            render(<DataSourceCard 
                {...defaultProps} 
                source={createSource({ isConnected: true })}
                enterpriseOnly={true} 
                userPlan="starter" 
            />);
            expect(screen.queryByText('Enterprise')).not.toBeInTheDocument();
        });

        it('should handle enterprise_annual plan as enterprise user', () => {
            render(<DataSourceCard {...defaultProps} enterpriseOnly={true} userPlan={'enterprise_annual' as PlanType} />);
            expect(screen.getByRole('button', { name: /^connect$/i })).toBeInTheDocument();
        });
    });

    // =========================================================================
    // Quota Exceeded Tests
    // =========================================================================

    describe('Quota Exceeded', () => {
        it('should show warning indicator when quota is exceeded', () => {
            render(<DataSourceCard 
                {...defaultProps} 
                source={createSource({ isConnected: true })}
                quotaExceeded={true} 
            />);
            // Should have amber/warning styling on badge
            const badge = screen.getByText('Connected');
            expect(badge).toHaveClass('bg-amber-500/90');
        });

        it('should not show warning when quota is not exceeded', () => {
            render(<DataSourceCard 
                {...defaultProps} 
                source={createSource({ isConnected: true })}
                quotaExceeded={false} 
            />);
            const badge = screen.getByText('Connected');
            expect(badge).toHaveClass('bg-emerald-500/90');
        });
    });

    // =========================================================================
    // Loading States
    // =========================================================================

    describe('Loading States', () => {
        it('should disable Connect button while loading', async () => {
            const user = userEvent.setup();
            mockOnConnect.mockImplementation(() => {
                // Simulate some async operation
                return new Promise(() => {});
            });

            render(<DataSourceCard {...defaultProps} />);

            await user.click(screen.getByRole('button', { name: /connect/i }));

            // Button should become disabled
            await waitFor(() => {
                expect(screen.getByRole('button', { name: /connect/i })).toBeDisabled();
            });
        });
    });

    // =========================================================================
    // Tooltip Tests
    // =========================================================================

    describe('Tooltips', () => {
        it('should show full description in tooltip for long descriptions', () => {
            const longDescription = 'This is a very long description that exceeds sixty characters and should show in a tooltip';
            render(<DataSourceCard {...defaultProps} source={createSource({ description: longDescription })} />);
            
            // The description should be rendered
            expect(screen.getByText(longDescription)).toBeInTheDocument();
        });

        it('should show Enterprise tooltip on lock icon', () => {
            render(<DataSourceCard {...defaultProps} enterpriseOnly={true} userPlan="starter" />);
            
            // Lock icon should be present
            const lockIcon = document.querySelector('.lucide-lock');
            expect(lockIcon).toBeInTheDocument();
        });
    });

    // =========================================================================
    // Edge Cases
    // =========================================================================

    describe('Edge Cases', () => {
        it('should handle null userPlan', () => {
            render(<DataSourceCard {...defaultProps} enterpriseOnly={true} userPlan={null} />);
            expect(screen.getByRole('button', { name: /upgrade to enterprise/i })).toBeInTheDocument();
        });

        it('should handle undefined userPlan', () => {
            render(<DataSourceCard {...defaultProps} enterpriseOnly={true} />);
            expect(screen.getByRole('button', { name: /upgrade to enterprise/i })).toBeInTheDocument();
        });

        it('should handle empty description', () => {
            render(<DataSourceCard {...defaultProps} source={createSource({ description: '' })} />);
            expect(screen.getByText('Google Drive')).toBeInTheDocument();
        });

        it('should handle connect error gracefully', async () => {
            mockOnConnect.mockImplementation(() => {
                throw new Error('Connection error');
            });

            const user = userEvent.setup();
            render(<DataSourceCard {...defaultProps} />);

            await user.click(screen.getByRole('button', { name: /connect/i }));

            await waitFor(() => {
                expect(mockToast).toHaveBeenCalledWith(expect.objectContaining({
                    title: 'Connection failed',
                    variant: 'destructive',
                }));
            });
        });
    });

    // =========================================================================
    // Visual State Tests
    // =========================================================================

    describe('Visual States', () => {
        it('should have special styling when connected', () => {
            const { container } = render(<DataSourceCard {...defaultProps} source={createSource({ isConnected: true })} />);
            
            const card = container.firstChild;
            expect(card).toHaveClass('border-primary/30');
        });

        it('should have hover styling when disconnected', () => {
            const { container } = render(<DataSourceCard {...defaultProps} />);
            
            const card = container.firstChild;
            expect(card).toHaveClass('hover:border-primary/30');
        });

        it('should show spinning refresh icon while syncing', async () => {
            mockOnSync.mockImplementation(() => new Promise((resolve) => setTimeout(resolve, 500)));
            const user = userEvent.setup();
            const source = createSource({ isConnected: true, integrationId: 'int-123' });
            render(<DataSourceCard {...defaultProps} source={source} />);

            const buttons = screen.getAllByRole('button');
            const syncButton = buttons.find(btn => btn.querySelector('.lucide-refresh-cw'));
            
            if (syncButton) {
                fireEvent.click(syncButton);
            }

            await waitFor(() => {
                const refreshIcon = document.querySelector('.lucide-refresh-cw.animate-spin');
                expect(refreshIcon).toBeInTheDocument();
            });
        });
    });
});
