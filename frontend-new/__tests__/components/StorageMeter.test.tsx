import { describe, it, expect, vi, beforeEach } from 'vitest';
import { render, screen } from '@testing-library/react';
import { StorageMeter } from '@/components/documents/StorageMeter';

// Mock useUsage hook
const mockUseUsage = vi.fn();

vi.mock('@/hooks/useUsage', () => ({
    useUsage: () => mockUseUsage(),
    formatBytes: (bytes: number) => {
        if (bytes === 0) return '0 B';
        return `${bytes} B`; // Simplified for testing
    },
}));

// Mock Link from next/link
vi.mock('next/link', () => ({
    default: ({ children, href }: { children: React.ReactNode; href: string }) => (
        <a href={href}>{children}</a>
    ),
}));

describe('StorageMeter Component', () => {
    beforeEach(() => {
        vi.clearAllMocks();
    });

    it('should render loading skeleton when isLoading is true', () => {
        mockUseUsage.mockReturnValue({
            isLoading: true,
            plan: 'free',
            filesUsed: 0,
            storageUsed: 0,
        });

        const { container } = render(<StorageMeter />);

        // Check for pulse animation
        expect(container.querySelector('.animate-pulse')).toBeInTheDocument();
        // Should not show stats
        expect(screen.queryByText('Storage Status')).not.toBeInTheDocument();
    });

    it('should show "Unlimited Storage" for Enterprise plan', () => {
        mockUseUsage.mockReturnValue({
            isLoading: false,
            plan: 'enterprise',
            filesUsed: 1000,
            storageUsed: 5000000,
            filesPercent: 10,
            storagePercent: 10,
        });

        render(<StorageMeter />);

        expect(screen.getByText('Unlimited Storage')).toBeInTheDocument();
        expect(screen.getByText(/Your Enterprise plan includes/)).toBeInTheDocument();
        // Should show file count in grid
        expect(screen.getByText('Files')).toBeInTheDocument();
        expect(screen.getByText('1,000')).toBeInTheDocument();
    });

    it('should render normal usage correctly', () => {
        mockUseUsage.mockReturnValue({
            isLoading: false,
            plan: 'starter',
            filesUsed: 10,
            filesLimit: 20,
            filesPercent: 50,
            storageUsed: 1000,
            storageLimit: 2000,
            storagePercent: 50,
        });

        render(<StorageMeter />);

        expect(screen.getByText('Storage Status')).toBeInTheDocument();
        expect(screen.getByText('Files')).toBeInTheDocument();
        expect(screen.getByText('Storage')).toBeInTheDocument();
        expect(screen.getByText('10 / 20')).toBeInTheDocument();

        // Circular percentage
        expect(screen.getByText('50%')).toBeInTheDocument();
        // No warnings
        expect(screen.queryByText(/plan limits/)).not.toBeInTheDocument();
    });

    it('should show warning status when usage >= 75%', () => {
        mockUseUsage.mockReturnValue({
            isLoading: false,
            plan: 'starter',
            filesUsed: 15,
            filesLimit: 20,
            filesPercent: 75,
            storageUsed: 1000,
            storageLimit: 2000,
            storagePercent: 50,
        });

        const { container } = render(<StorageMeter />);

        expect(screen.getByText('You are approaching your storage limits.')).toBeInTheDocument();
        expect(screen.getByText('75%')).toBeInTheDocument();
        // Check for warning color class (amber)
        const percentText = screen.getByText('75%');
        expect(percentText.className).toContain('text-amber-600');
    });

    it('should show critical status when usage >= 90%', () => {
        mockUseUsage.mockReturnValue({
            isLoading: false,
            plan: 'starter',
            filesUsed: 18,
            filesLimit: 20,
            filesPercent: 90,
            storageUsed: 1000,
            storageLimit: 2000,
            storagePercent: 50,
        });

        const { container } = render(<StorageMeter />);

        expect(screen.getByText('You have reached your plan limits.')).toBeInTheDocument();
        expect(screen.getByText('Upgrade Plan')).toBeInTheDocument();

        // Check for critical color class (red)
        const percentText = screen.getByText('90%');
        expect(percentText.className).toContain('text-red-600');
    });

    it('should hide upgrade prompt if showUpgradePrompt is false', () => {
        mockUseUsage.mockReturnValue({
            isLoading: false,
            plan: 'starter',
            filesPercent: 95,
            storagePercent: 50,
        });

        render(<StorageMeter showUpgradePrompt={false} />);

        expect(screen.queryByText('Upgrade Plan')).not.toBeInTheDocument();
    });
});
