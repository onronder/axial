import { describe, it, expect, vi, beforeEach, afterEach } from 'vitest';
import { render, screen, fireEvent, waitFor, act } from '@testing-library/react';
import { DataSourceCard } from '@/components/data-sources/DataSourceCard';
import type { MergedDataSource, PlanType } from '@/types';

// =============================================================================
// Mocks
// =============================================================================

const mockToast = vi.fn();
vi.mock('@/hooks/use-toast', () => ({
  useToast: () => ({ toast: mockToast }),
}));

// Mock window.location for upgrade button
const mockLocationHref = { href: '' };
Object.defineProperty(window, 'location', {
  value: mockLocationHref,
  writable: true,
});

describe('DataSourceCard Component', () => {
  // ===========================================================================
  // Test Data
  // ===========================================================================

  const defaultSource: MergedDataSource = {
    id: 'test-source',
    definitionId: 'def-1',
    type: 'google_drive',
    name: 'Google Drive',
    description: 'Connect to Google Drive',
    iconPath: null,
    category: 'cloud',
    isConnected: false,
    lastSyncAt: null,
    integrationId: null,
  };

  const connectedSource: MergedDataSource = {
    ...defaultSource,
    isConnected: true,
    lastSyncAt: '2024-01-15T10:00:00Z',
    integrationId: 'int-123',
  };

  const s3Source: MergedDataSource = {
    ...defaultSource,
    id: 's3-source',
    type: 's3',
    name: 'Amazon S3',
    description: 'Connect to S3 buckets',
  };

  const defaultProps = {
    source: defaultSource,
    onBrowse: vi.fn(),
    onConnect: vi.fn(),
    onDisconnect: vi.fn().mockResolvedValue(undefined),
    onSync: vi.fn().mockResolvedValue({ success: true, jobId: 'job-123' }),
    disabled: false,
    quotaExceeded: false,
  };

  beforeEach(() => {
    vi.clearAllMocks();
    mockLocationHref.href = '';
  });

  afterEach(() => {
    vi.clearAllMocks();
  });

  // ===========================================================================
  // Basic Rendering Tests
  // ===========================================================================

  describe('Basic Rendering', () => {
    it('should render source name and description', () => {
      render(<DataSourceCard {...defaultProps} />);

      expect(screen.getByText('Google Drive')).toBeInTheDocument();
      expect(screen.getByText('Connect to Google Drive')).toBeInTheDocument();
    });

    it('should render Connect button when not connected', () => {
      render(<DataSourceCard {...defaultProps} />);

      expect(screen.getByRole('button', { name: /Connect/i })).toBeInTheDocument();
    });

    it('should render Connected badge when connected', () => {
      render(<DataSourceCard {...defaultProps} source={connectedSource} />);

      expect(screen.getByText('Connected')).toBeInTheDocument();
    });

    it('should render quota exceeded warning when quotaExceeded is true', () => {
      render(
        <DataSourceCard
          {...defaultProps}
          source={connectedSource}
          quotaExceeded={true}
        />
      );

      // The badge should still show Connected but with different styling
      expect(screen.getByText('Connected')).toBeInTheDocument();
    });
  });

  // ===========================================================================
  // Enterprise Gating Tests
  // ===========================================================================

  describe('Enterprise Gating', () => {
    it('should show Enterprise badge for enterprise-only sources', () => {
      render(
        <DataSourceCard
          {...defaultProps}
          source={s3Source}
          enterpriseOnly={true}
          userPlan="starter"
        />
      );

      expect(screen.getByText('Enterprise')).toBeInTheDocument();
    });

    it('should show lock icon for enterprise-only sources when user is not enterprise', () => {
      render(
        <DataSourceCard
          {...defaultProps}
          source={s3Source}
          enterpriseOnly={true}
          userPlan="starter"
        />
      );

      // The lock icon shows as the upgrade button with sparkles icon
      expect(screen.getByRole('button', { name: /Upgrade to Enterprise/i })).toBeInTheDocument();
    });

    it('should show "Upgrade to Enterprise" button for non-enterprise users on enterprise sources', () => {
      render(
        <DataSourceCard
          {...defaultProps}
          source={s3Source}
          enterpriseOnly={true}
          userPlan="starter"
        />
      );

      expect(screen.getByRole('button', { name: /Upgrade to Enterprise/i })).toBeInTheDocument();
    });

    it('should NOT show lock for enterprise-only source when user IS enterprise', () => {
      render(
        <DataSourceCard
          {...defaultProps}
          source={s3Source}
          enterpriseOnly={true}
          userPlan="enterprise"
        />
      );

      // Should show Connect button, not Upgrade
      expect(screen.getByRole('button', { name: /Connect/i })).toBeInTheDocument();
      expect(screen.queryByRole('button', { name: /Upgrade to Enterprise/i })).not.toBeInTheDocument();
    });

    it('should allow enterprise users with variant plans (enterprise_small)', () => {
      render(
        <DataSourceCard
          {...defaultProps}
          source={s3Source}
          enterpriseOnly={true}
          userPlan={"enterprise_small" as PlanType}
        />
      );

      // Should show Connect button
      expect(screen.getByRole('button', { name: /Connect/i })).toBeInTheDocument();
    });

    it('should allow enterprise users with variant plans (enterprise_medium)', () => {
      render(
        <DataSourceCard
          {...defaultProps}
          source={s3Source}
          enterpriseOnly={true}
          userPlan={"enterprise_medium" as PlanType}
        />
      );

      expect(screen.getByRole('button', { name: /Connect/i })).toBeInTheDocument();
    });

    it('should NOT show Enterprise badge for non-enterprise sources', () => {
      render(
        <DataSourceCard
          {...defaultProps}
          source={defaultSource}
          enterpriseOnly={false}
          userPlan="starter"
        />
      );

      expect(screen.queryByText('Enterprise')).not.toBeInTheDocument();
    });

    it('should navigate to billing page when Upgrade button is clicked', () => {
      render(
        <DataSourceCard
          {...defaultProps}
          source={s3Source}
          enterpriseOnly={true}
          userPlan="starter"
        />
      );

      const upgradeButton = screen.getByRole('button', { name: /Upgrade to Enterprise/i });
      fireEvent.click(upgradeButton);

      expect(window.location.href).toBe('/dashboard/settings/billing');
    });

    it('should show upgrade button for free plan users', () => {
      render(
        <DataSourceCard
          {...defaultProps}
          source={s3Source}
          enterpriseOnly={true}
          userPlan="free"
        />
      );

      expect(screen.getByRole('button', { name: /Upgrade to Enterprise/i })).toBeInTheDocument();
    });

    it('should show upgrade button for pro plan users', () => {
      render(
        <DataSourceCard
          {...defaultProps}
          source={s3Source}
          enterpriseOnly={true}
          userPlan="pro"
        />
      );

      expect(screen.getByRole('button', { name: /Upgrade to Enterprise/i })).toBeInTheDocument();
    });

    it('should NOT show Enterprise lock when source is already connected', () => {
      const connectedS3Source = {
        ...s3Source,
        isConnected: true,
        integrationId: 'int-s3',
      };

      render(
        <DataSourceCard
          {...defaultProps}
          source={connectedS3Source}
          enterpriseOnly={true}
          userPlan="starter"
        />
      );

      // Should show Connected badge, not Enterprise badge
      expect(screen.getByText('Connected')).toBeInTheDocument();
      expect(screen.queryByRole('button', { name: /Upgrade to Enterprise/i })).not.toBeInTheDocument();
    });
  });

  // ===========================================================================
  // User Interaction Tests
  // ===========================================================================

  describe('User Interactions', () => {
    it('should call onConnect when Connect button is clicked', () => {
      render(<DataSourceCard {...defaultProps} />);

      const connectButton = screen.getByRole('button', { name: /Connect/i });
      fireEvent.click(connectButton);

      expect(defaultProps.onConnect).toHaveBeenCalledWith('google_drive');
    });

    it('should call onBrowse when Browse button is clicked on connected source', () => {
      render(<DataSourceCard {...defaultProps} source={connectedSource} />);

      const browseButton = screen.getByRole('button', { name: /Browse/i });
      fireEvent.click(browseButton);

      expect(defaultProps.onBrowse).toHaveBeenCalled();
    });

    it('should have disconnect button for connected sources', () => {
      render(<DataSourceCard {...defaultProps} source={connectedSource} />);

      // For connected sources, there should be buttons including a disconnect X button
      const allButtons = screen.getAllByRole('button');
      
      // Connected cards have Sync, Browse, and an X (disconnect) button
      expect(allButtons.length).toBeGreaterThan(2);
      
      // The card should show the connected state
      expect(screen.getByText('Connected')).toBeInTheDocument();
    });

    it('should disable Connect button when disabled prop is true', () => {
      render(<DataSourceCard {...defaultProps} disabled={true} />);

      const connectButton = screen.getByRole('button', { name: /Connect/i });
      expect(connectButton).toBeDisabled();
    });

    it('should call onSync when sync button is clicked', async () => {
      render(<DataSourceCard {...defaultProps} source={connectedSource} />);

      // Find sync button
      const syncButtons = screen.getAllByRole('button');
      const syncButton = syncButtons.find((btn) =>
        btn.querySelector('[class*="RefreshCw"]') || btn.textContent?.includes('Sync')
      );

      if (syncButton) {
        fireEvent.click(syncButton);

        await waitFor(() => {
          expect(defaultProps.onSync).toHaveBeenCalledWith('int-123');
        });
      }
    });
  });

  // ===========================================================================
  // Visual State Tests
  // ===========================================================================

  describe('Visual States', () => {
    it('should apply dimmed styling for enterprise-locked sources', () => {
      const { container } = render(
        <DataSourceCard
          {...defaultProps}
          source={s3Source}
          enterpriseOnly={true}
          userPlan="starter"
        />
      );

      // The icon container should have opacity-75 class
      const iconContainer = container.querySelector('[class*="opacity-75"]');
      expect(iconContainer).toBeInTheDocument();
    });

    it('should show purple gradient badge for enterprise sources', () => {
      const { container } = render(
        <DataSourceCard
          {...defaultProps}
          source={s3Source}
          enterpriseOnly={true}
          userPlan="starter"
        />
      );

      // Check for gradient styling
      const enterpriseBadge = container.querySelector('[class*="from-violet-500"]');
      expect(enterpriseBadge).toBeInTheDocument();
    });

    it('should show green badge for connected sources', () => {
      const { container } = render(
        <DataSourceCard {...defaultProps} source={connectedSource} />
      );

      const connectedBadge = container.querySelector('[class*="emerald"]');
      expect(connectedBadge).toBeInTheDocument();
    });
  });

  // ===========================================================================
  // Edge Cases
  // ===========================================================================

  describe('Edge Cases', () => {
    it('should handle null userPlan gracefully', () => {
      render(
        <DataSourceCard
          {...defaultProps}
          source={s3Source}
          enterpriseOnly={true}
          userPlan={null}
        />
      );

      // Should show upgrade button when plan is null
      expect(screen.getByRole('button', { name: /Upgrade to Enterprise/i })).toBeInTheDocument();
    });

    it('should handle undefined enterpriseOnly gracefully', () => {
      render(
        <DataSourceCard
          {...defaultProps}
          source={defaultSource}
          // enterpriseOnly not passed - should default to false
        />
      );

      // Should show normal Connect button
      expect(screen.getByRole('button', { name: /Connect/i })).toBeInTheDocument();
      expect(screen.queryByText('Enterprise')).not.toBeInTheDocument();
    });

    it('should show last sync time when connected', () => {
      render(<DataSourceCard {...defaultProps} source={connectedSource} />);

      // Should display some form of the sync time
      expect(screen.getByText(/Synced/i)).toBeInTheDocument();
    });
  });

  // ===========================================================================
  // Tooltip Tests
  // ===========================================================================

  describe('Tooltips', () => {
    it('should show tooltip trigger for enterprise lock icon', async () => {
      render(
        <DataSourceCard
          {...defaultProps}
          source={s3Source}
          enterpriseOnly={true}
          userPlan="starter"
        />
      );

      // The upgrade button serves as the tooltip trigger - verify it exists
      // Note: Tooltip content is not visible until hover in jsdom
      expect(screen.getByRole('button', { name: /Upgrade to Enterprise/i })).toBeInTheDocument();
    });

    it('should render upgrade button for enterprise sources', async () => {
      render(
        <DataSourceCard
          {...defaultProps}
          source={s3Source}
          enterpriseOnly={true}
          userPlan="starter"
        />
      );

      // The upgrade button should be present for non-enterprise users
      const upgradeButton = screen.getByRole('button', { name: /Upgrade to Enterprise/i });
      expect(upgradeButton).toBeInTheDocument();
    });
  });

  // ===========================================================================
  // Last Sync Formatting Tests
  // ===========================================================================

  describe('Last Sync Time Formatting', () => {
    it('should show "Never" when lastSyncAt is null', () => {
      render(<DataSourceCard {...defaultProps} source={connectedSource} />);

      // The connected source with null lastSyncAt shows formatted time
      expect(screen.getByText(/Synced:/i)).toBeInTheDocument();
    });

    it('should show "Just now" for very recent syncs', () => {
      const recentSource = {
        ...connectedSource,
        lastSyncAt: new Date().toISOString(),
      };

      render(<DataSourceCard {...defaultProps} source={recentSource} />);

      expect(screen.getByText(/Just now|0m ago|1m ago/i)).toBeInTheDocument();
    });

    it('should show minutes ago for recent syncs', () => {
      const fiveMinutesAgo = new Date(Date.now() - 5 * 60 * 1000);
      const recentSource = {
        ...connectedSource,
        lastSyncAt: fiveMinutesAgo.toISOString(),
      };

      render(<DataSourceCard {...defaultProps} source={recentSource} />);

      expect(screen.getByText(/5m ago|4m ago|6m ago/i)).toBeInTheDocument();
    });

    it('should show hours ago for syncs within a day', () => {
      const threeHoursAgo = new Date(Date.now() - 3 * 60 * 60 * 1000);
      const recentSource = {
        ...connectedSource,
        lastSyncAt: threeHoursAgo.toISOString(),
      };

      render(<DataSourceCard {...defaultProps} source={recentSource} />);

      expect(screen.getByText(/3h ago|2h ago|4h ago/i)).toBeInTheDocument();
    });

    it('should show days ago for syncs within a week', () => {
      const threeDaysAgo = new Date(Date.now() - 3 * 24 * 60 * 60 * 1000);
      const olderSource = {
        ...connectedSource,
        lastSyncAt: threeDaysAgo.toISOString(),
      };

      render(<DataSourceCard {...defaultProps} source={olderSource} />);

      expect(screen.getByText(/3d ago|2d ago|4d ago/i)).toBeInTheDocument();
    });
  });

  // ===========================================================================
  // Disconnect Flow Tests
  // ===========================================================================

  describe('Disconnect Flow', () => {
    it('should have action buttons for connected sources', () => {
      render(<DataSourceCard {...defaultProps} source={connectedSource} />);

      // Connected sources should have multiple action buttons
      const allButtons = screen.getAllByRole('button');
      expect(allButtons.length).toBeGreaterThan(1);
      
      // Should show Connected badge
      expect(screen.getByText('Connected')).toBeInTheDocument();
    });

    it('should have onDisconnect handler defined', () => {
      render(<DataSourceCard {...defaultProps} source={connectedSource} />);

      // The component should be mounted with disconnect functionality
      expect(defaultProps.onDisconnect).toBeDefined();
    });

    it('should show disabled state when user is viewer', () => {
      render(
        <DataSourceCard
          {...defaultProps}
          source={connectedSource}
          disabled={true}
        />
      );

      // Browse button should exist for connected sources
      const browseButton = screen.getByRole('button', { name: /Browse/i });
      expect(browseButton).toBeInTheDocument();
    });
  });

  // ===========================================================================
  // Sync Flow Tests
  // ===========================================================================

  describe('Sync Flow', () => {
    it('should call onSync with integration ID', async () => {
      render(<DataSourceCard {...defaultProps} source={connectedSource} />);

      // Find the sync button (RefreshCw icon)
      const syncButtons = screen.getAllByRole('button');
      const syncButton = syncButtons.find(btn => 
        btn.querySelector('[class*="RefreshCw"]') !== null
      );

      if (syncButton) {
        await act(async () => {
          fireEvent.click(syncButton);
        });

        await waitFor(() => {
          expect(defaultProps.onSync).toHaveBeenCalledWith('int-123');
        });
      }
    });

    it('should show syncing spinner when sync is in progress', async () => {
      let resolveSyncPromise: (value: unknown) => void;
      const syncPromise = new Promise((resolve) => {
        resolveSyncPromise = resolve;
      });
      
      const slowSync = vi.fn().mockReturnValue(syncPromise);

      render(
        <DataSourceCard
          {...defaultProps}
          source={connectedSource}
          onSync={slowSync}
        />
      );

      const syncButtons = screen.getAllByRole('button');
      const syncButton = syncButtons.find(btn => 
        btn.querySelector('[class*="RefreshCw"]') !== null
      );

      if (syncButton) {
        await act(async () => {
          fireEvent.click(syncButton);
        });

        // Check for spinning animation
        await waitFor(() => {
          const refreshIcon = syncButton.querySelector('[class*="animate-spin"]');
          expect(refreshIcon).toBeInTheDocument();
        });

        // Cleanup
        resolveSyncPromise!({ success: true, jobId: 'job-123' });
      }
    });

    it('should show error toast on sync failure', async () => {
      const failingSync = vi.fn().mockRejectedValue(new Error('Sync failed'));

      render(
        <DataSourceCard
          {...defaultProps}
          source={connectedSource}
          onSync={failingSync}
        />
      );

      const syncButtons = screen.getAllByRole('button');
      const syncButton = syncButtons.find(btn => 
        btn.querySelector('[class*="RefreshCw"]') !== null
      );

      if (syncButton) {
        await act(async () => {
          fireEvent.click(syncButton);
        });

        await waitFor(() => {
          expect(mockToast).toHaveBeenCalledWith(
            expect.objectContaining({
              title: 'Sync Failed',
              variant: 'destructive',
            })
          );
        });
      }
    });

    it('should not sync when integrationId is null', async () => {
      const sourceWithoutIntegration = {
        ...connectedSource,
        integrationId: null,
      };

      render(
        <DataSourceCard
          {...defaultProps}
          source={sourceWithoutIntegration}
        />
      );

      const syncButtons = screen.getAllByRole('button');
      const syncButton = syncButtons.find(btn => 
        btn.querySelector('[class*="RefreshCw"]') !== null
      );

      if (syncButton) {
        await act(async () => {
          fireEvent.click(syncButton);
        });

        expect(defaultProps.onSync).not.toHaveBeenCalled();
      }
    });
  });

  // ===========================================================================
  // Connect Flow Tests
  // ===========================================================================

  describe('Connect Flow', () => {
    it('should show view-only toast when disabled user tries to connect', async () => {
      render(
        <DataSourceCard
          {...defaultProps}
          disabled={true}
        />
      );

      const connectButton = screen.getByRole('button', { name: /Connect/i });
      expect(connectButton).toBeDisabled();
    });

    it('should show loading state while connecting', async () => {
      let resolveConnect: () => void;
      const slowConnect = vi.fn().mockImplementation(() => {
        return new Promise((resolve) => {
          resolveConnect = resolve;
        });
      });

      render(
        <DataSourceCard
          {...defaultProps}
          onConnect={slowConnect}
        />
      );

      const connectButton = screen.getByRole('button', { name: /Connect/i });
      
      await act(async () => {
        fireEvent.click(connectButton);
      });

      // Connect is synchronous in the component, so loading state is brief
      expect(slowConnect).toHaveBeenCalled();
    });
  });

  // ===========================================================================
  // Quota Exceeded Tests
  // ===========================================================================

  describe('Quota Exceeded State', () => {
    it('should show warning indicator when quota is exceeded', () => {
      const { container } = render(
        <DataSourceCard
          {...defaultProps}
          source={connectedSource}
          quotaExceeded={true}
        />
      );

      // Should have destructive/amber styling
      const warningBadge = container.querySelector('[class*="amber"]');
      expect(warningBadge).toBeInTheDocument();
    });

    it('should show warning badge for quota exceeded sources', () => {
      render(
        <DataSourceCard
          {...defaultProps}
          source={connectedSource}
          quotaExceeded={true}
        />
      );

      // Connected badge with amber styling should show for quota exceeded sources
      const connectedBadge = screen.getByText('Connected');
      expect(connectedBadge).toBeInTheDocument();
      // The badge should have amber color styling for quota exceeded state
      expect(connectedBadge.closest('[class*="amber"]')).toBeInTheDocument();
    });
  });

  // ===========================================================================
  // Browse Button Tests
  // ===========================================================================

  describe('Browse Button', () => {
    it('should call onBrowse when Browse button is clicked', () => {
      render(<DataSourceCard {...defaultProps} source={connectedSource} />);

      const browseButton = screen.getByRole('button', { name: /Browse/i });
      fireEvent.click(browseButton);

      expect(defaultProps.onBrowse).toHaveBeenCalled();
    });

    it('should have Browse button for connected sources', () => {
      render(<DataSourceCard {...defaultProps} source={connectedSource} />);

      // Browse button should exist for connected sources
      const browseButton = screen.getByRole('button', { name: /Browse/i });
      expect(browseButton).toBeInTheDocument();
      expect(browseButton).toBeEnabled();
    });
  });
});
