/**
 * Unit Tests for UsageIndicator Component
 * 
 * Comprehensive tests covering:
 * - Loading state rendering
 * - Enterprise unlimited display
 * - Normal usage display with progress bars
 * - Color coding thresholds (green, yellow, red)
 * - Tooltip content
 * - Compact variant
 */

import { describe, it, expect, vi, beforeEach } from 'vitest';
import { render, screen } from '@testing-library/react';
import { UsageIndicator, UsageIndicatorCompact } from '@/components/UsageIndicator';

// Mock useUsage hook
const mockUseUsage = vi.fn();

vi.mock('@/hooks/useUsage', () => ({
    useUsage: () => mockUseUsage(),
    formatBytes: (bytes: number) => {
        if (bytes === 0) return '0 B';
        const units = ['B', 'KB', 'MB', 'GB'];
        const k = 1024;
        const i = Math.floor(Math.log(bytes) / Math.log(k));
        return `${Math.round(bytes / Math.pow(k, i))} ${units[i]}`;
    },
}));

// Mock Tooltip components to simplify testing
vi.mock('@/components/ui/tooltip', () => ({
    Tooltip: ({ children }: { children: React.ReactNode }) => <div data-testid="tooltip">{children}</div>,
    TooltipTrigger: ({ children }: { children: React.ReactNode }) => <div data-testid="tooltip-trigger">{children}</div>,
    TooltipContent: ({ children }: { children: React.ReactNode }) => <div data-testid="tooltip-content">{children}</div>,
    TooltipProvider: ({ children }: { children: React.ReactNode }) => <div data-testid="tooltip-provider">{children}</div>,
}));

describe('UsageIndicator Component', () => {
    beforeEach(() => {
        vi.clearAllMocks();
    });

    describe('Loading State', () => {
        it('should render loading skeleton when isLoading is true', () => {
            mockUseUsage.mockReturnValue({
                isLoading: true,
                plan: 'free',
                filesUsed: 0,
                filesLimit: 10,
                filesPercent: 0,
                storageUsed: 0,
                storageLimit: 100,
                storagePercent: 0,
            });

            render(<UsageIndicator />);

            const skeletons = document.querySelectorAll('.animate-pulse');
            expect(skeletons.length).toBeGreaterThan(0);
        });

        it('should not render usage bars when loading', () => {
            mockUseUsage.mockReturnValue({
                isLoading: true,
                plan: 'free',
                filesUsed: 0,
                filesLimit: 10,
                filesPercent: 0,
                storageUsed: 0,
                storageLimit: 100,
                storagePercent: 0,
            });

            render(<UsageIndicator />);

            expect(screen.queryByText('Files')).not.toBeInTheDocument();
            expect(screen.queryByText('Storage')).not.toBeInTheDocument();
        });
    });

    describe('Enterprise Plan', () => {
        it('should show "Unlimited resources" for enterprise plan', () => {
            mockUseUsage.mockReturnValue({
                isLoading: false,
                plan: 'enterprise',
                filesUsed: 0,
                filesLimit: 1000,
                filesPercent: 0,
                storageUsed: 0,
                storageLimit: 1000000000,
                storagePercent: 0,
            });

            render(<UsageIndicator />);

            expect(screen.getByText('Enterprise')).toBeInTheDocument();
            expect(screen.getByText('Unlimited resources')).toBeInTheDocument();
        });

        it('should not show progress bars for enterprise', () => {
            mockUseUsage.mockReturnValue({
                isLoading: false,
                plan: 'enterprise',
                filesUsed: 500,
                filesLimit: 1000,
                filesPercent: 50,
                storageUsed: 500000,
                storageLimit: 1000000,
                storagePercent: 50,
            });

            render(<UsageIndicator />);

            expect(screen.queryByText('Files')).not.toBeInTheDocument();
            expect(screen.queryByText('Storage')).not.toBeInTheDocument();
        });
    });

    describe('Normal Usage Display', () => {
        it('should render Files label', () => {
            mockUseUsage.mockReturnValue({
                isLoading: false,
                plan: 'pro',
                filesUsed: 25,
                filesLimit: 100,
                filesPercent: 25,
                storageUsed: 52428800,
                storageLimit: 1073741824,
                storagePercent: 5,
            });

            render(<UsageIndicator />);

            expect(screen.getByText('Files')).toBeInTheDocument();
        });

        it('should render Storage label', () => {
            mockUseUsage.mockReturnValue({
                isLoading: false,
                plan: 'pro',
                filesUsed: 25,
                filesLimit: 100,
                filesPercent: 25,
                storageUsed: 52428800,
                storageLimit: 1073741824,
                storagePercent: 5,
            });

            render(<UsageIndicator />);

            expect(screen.getByText('Storage')).toBeInTheDocument();
        });

        it('should show files count X/Y format', () => {
            mockUseUsage.mockReturnValue({
                isLoading: false,
                plan: 'pro',
                filesUsed: 25,
                filesLimit: 100,
                filesPercent: 25,
                storageUsed: 52428800,
                storageLimit: 1073741824,
                storagePercent: 5,
            });

            render(<UsageIndicator />);

            expect(screen.getByText('25/100')).toBeInTheDocument();
        });

        it('should render progress bars', () => {
            mockUseUsage.mockReturnValue({
                isLoading: false,
                plan: 'starter',
                filesUsed: 10,
                filesLimit: 50,
                filesPercent: 20,
                storageUsed: 100000,
                storageLimit: 500000,
                storagePercent: 20,
            });

            render(<UsageIndicator />);

            // Progress bars should have width style
            const progressBars = document.querySelectorAll('[style*="width"]');
            expect(progressBars.length).toBeGreaterThan(0);
        });
    });

    describe('Color Coding - Green (< 75%)', () => {
        it('should apply green color for low usage', () => {
            mockUseUsage.mockReturnValue({
                isLoading: false,
                plan: 'pro',
                filesUsed: 10,
                filesLimit: 100,
                filesPercent: 10,
                storageUsed: 100000,
                storageLimit: 1000000,
                storagePercent: 10,
            });

            const { container } = render(<UsageIndicator />);

            // Check for success/green classes
            expect(container.innerHTML).toContain('text-success');
            expect(container.innerHTML).toContain('bg-success');
        });
    });

    describe('Color Coding - Yellow (75-90%)', () => {
        it('should apply warning color for medium-high usage', () => {
            mockUseUsage.mockReturnValue({
                isLoading: false,
                plan: 'pro',
                filesUsed: 80,
                filesLimit: 100,
                filesPercent: 80,
                storageUsed: 800000,
                storageLimit: 1000000,
                storagePercent: 80,
            });

            const { container } = render(<UsageIndicator />);

            // Check for warning/yellow classes
            expect(container.innerHTML).toContain('text-warning');
            expect(container.innerHTML).toContain('bg-warning');
        });
    });

    describe('Color Coding - Red (> 90%)', () => {
        it('should apply destructive color for high usage', () => {
            mockUseUsage.mockReturnValue({
                isLoading: false,
                plan: 'starter',
                filesUsed: 48,
                filesLimit: 50,
                filesPercent: 96,
                storageUsed: 950000,
                storageLimit: 1000000,
                storagePercent: 95,
            });

            const { container } = render(<UsageIndicator />);

            // Check for destructive/red classes
            expect(container.innerHTML).toContain('text-destructive');
            expect(container.innerHTML).toContain('bg-destructive');
        });

        it('should apply red for exactly 90%', () => {
            mockUseUsage.mockReturnValue({
                isLoading: false,
                plan: 'starter',
                filesUsed: 45,
                filesLimit: 50,
                filesPercent: 90,
                storageUsed: 900000,
                storageLimit: 1000000,
                storagePercent: 90,
            });

            const { container } = render(<UsageIndicator />);

            expect(container.innerHTML).toContain('text-destructive');
        });
    });

    describe('Mixed Usage Levels', () => {
        it('should show different colors for files vs storage', () => {
            mockUseUsage.mockReturnValue({
                isLoading: false,
                plan: 'pro',
                filesUsed: 20,
                filesLimit: 100,
                filesPercent: 20, // Green
                storageUsed: 950000,
                storageLimit: 1000000,
                storagePercent: 95, // Red
            });

            const { container } = render(<UsageIndicator />);

            // Should have both green and red
            expect(container.innerHTML).toContain('bg-success');
            expect(container.innerHTML).toContain('bg-destructive');
        });
    });

    describe('Progress Bar Width', () => {
        it('should set correct width for 50% usage', () => {
            mockUseUsage.mockReturnValue({
                isLoading: false,
                plan: 'pro',
                filesUsed: 50,
                filesLimit: 100,
                filesPercent: 50,
                storageUsed: 500000,
                storageLimit: 1000000,
                storagePercent: 50,
            });

            const { container } = render(<UsageIndicator />);

            const progressBar = container.querySelector('[style*="width: 50%"]');
            expect(progressBar).toBeInTheDocument();
        });

        it('should handle 0% usage', () => {
            mockUseUsage.mockReturnValue({
                isLoading: false,
                plan: 'free',
                filesUsed: 0,
                filesLimit: 10,
                filesPercent: 0,
                storageUsed: 0,
                storageLimit: 100000,
                storagePercent: 0,
            });

            const { container } = render(<UsageIndicator />);

            const progressBar = container.querySelector('[style*="width: 0%"]');
            expect(progressBar).toBeInTheDocument();
        });

        it('should cap width at 100%', () => {
            mockUseUsage.mockReturnValue({
                isLoading: false,
                plan: 'free',
                filesUsed: 15,
                filesLimit: 10,
                filesPercent: 150, // Over limit
                storageUsed: 0,
                storageLimit: 100000,
                storagePercent: 0,
            });

            const { container } = render(<UsageIndicator />);

            // Should be capped at 100%
            const progressBar = container.querySelector('[style*="width: 100%"]');
            expect(progressBar).toBeInTheDocument();
        });
    });
});

describe('UsageIndicatorCompact Component', () => {
    beforeEach(() => {
        vi.clearAllMocks();
    });

    it('should return null when loading', () => {
        mockUseUsage.mockReturnValue({
            isLoading: true,
            plan: 'pro',
            filesPercent: 50,
            storagePercent: 50,
        });

        const { container } = render(<UsageIndicatorCompact />);
        expect(container.firstChild).toBeNull();
    });

    it('should return null for enterprise plan', () => {
        mockUseUsage.mockReturnValue({
            isLoading: false,
            plan: 'enterprise',
            filesPercent: 50,
            storagePercent: 50,
        });

        const { container } = render(<UsageIndicatorCompact />);
        expect(container.firstChild).toBeNull();
    });

    it('should render dot indicator for non-enterprise', () => {
        mockUseUsage.mockReturnValue({
            isLoading: false,
            plan: 'pro',
            filesPercent: 50,
            storagePercent: 50,
        });

        const { container } = render(<UsageIndicatorCompact />);

        const dot = container.querySelector('.rounded-full');
        expect(dot).toBeInTheDocument();
    });

    it('should use worst percentage for color', () => {
        mockUseUsage.mockReturnValue({
            isLoading: false,
            plan: 'pro',
            filesPercent: 20, // Green
            storagePercent: 95, // Red - should use this
        });

        const { container } = render(<UsageIndicatorCompact />);

        expect(container.innerHTML).toContain('bg-destructive');
    });

    it('should show green when both usages are low', () => {
        mockUseUsage.mockReturnValue({
            isLoading: false,
            plan: 'starter',
            filesPercent: 30,
            storagePercent: 40,
        });

        const { container } = render(<UsageIndicatorCompact />);

        expect(container.innerHTML).toContain('bg-success');
    });
});
