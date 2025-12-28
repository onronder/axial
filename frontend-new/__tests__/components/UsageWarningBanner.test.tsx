import { describe, it, expect, vi, beforeEach, afterEach } from 'vitest';
import { render, screen, fireEvent } from '@testing-library/react';
import { UsageWarningBanner } from '@/components/UsageWarningBanner';

// Mock useUsage hook
const mockUseUsage = vi.fn();

vi.mock('@/hooks/useUsage', () => ({
    useUsage: () => mockUseUsage(),
}));

// Mock Link
vi.mock('next/link', () => ({
    default: ({ children, href }: { children: React.ReactNode; href: string }) => (
        <a href={href}>{children}</a>
    ),
}));

describe('UsageWarningBanner Component', () => {
    beforeEach(() => {
        vi.clearAllMocks();
        // Clear local storage
        localStorage.clear();

        // Mock default usage (safe)
        mockUseUsage.mockReturnValue({
            isLoading: false,
            plan: 'starter',
            filesPercent: 50,
            storagePercent: 50,
        });
    });

    afterEach(() => {
        vi.restoreAllMocks();
    });

    it('should NOT render when usage is < 90%', () => {
        mockUseUsage.mockReturnValue({
            isLoading: false,
            plan: 'starter',
            filesPercent: 89,
            storagePercent: 89,
        });

        const { container } = render(<UsageWarningBanner />);
        expect(container.firstChild).toBeNull();
    });

    it('should render when usage >= 90%', () => {
        mockUseUsage.mockReturnValue({
            isLoading: false,
            plan: 'starter',
            filesPercent: 91,
            storagePercent: 50,
        });

        render(<UsageWarningBanner />);

        expect(screen.getByText(/Warning:/)).toBeInTheDocument();
        expect(screen.getByText(/91%/)).toBeInTheDocument();
        expect(screen.getByText('Upgrade Plan')).toBeInTheDocument();
    });

    it('should NOT render for enterprise plan even if usage > 90%', () => {
        mockUseUsage.mockReturnValue({
            isLoading: false,
            plan: 'enterprise',
            filesPercent: 95,
            storagePercent: 95,
        });

        const { container } = render(<UsageWarningBanner />);
        expect(container.firstChild).toBeNull();
    });

    it('should show "blocked" message if usage >= 100%', () => {
        mockUseUsage.mockReturnValue({
            isLoading: false,
            plan: 'starter',
            filesPercent: 105,
            storagePercent: 50,
        });

        render(<UsageWarningBanner />);

        expect(screen.getByText(/Uploads are blocked/)).toBeInTheDocument();
    });

    it('should dismiss the banner when close button clicked', () => {
        mockUseUsage.mockReturnValue({
            isLoading: false,
            plan: 'starter',
            filesPercent: 95,
            storagePercent: 50,
        });

        render(<UsageWarningBanner />);

        // Find close button (X icon usually in a button)
        // Since we didn't add aria-label in component source, we might find by class or icon
        // Or find the button near "Upgrade Plan"
        // Let's assume it's the button with the X icon. 
        // We mocked X icon? No, actual import from lucide-react (might be rendered as svg)
        // Let's try finding the button with className containing 'text-destructive'
        const buttons = screen.getAllByRole('button');
        // Filter for the dismiss button
        const dismissButton = buttons.find(b => b.classList.contains('text-destructive'));

        if (!dismissButton) throw new Error("Dismiss button not found");

        fireEvent.click(dismissButton);

        // Should disappear
        expect(screen.queryByText(/Warning:/)).not.toBeInTheDocument();

        // Should verify localStorage was set
        expect(localStorage.getItem('usage_warning_dismissed')).toBeTruthy();
    });

    it('should respect prior dismissal from localStorage', () => {
        // Set storage with future expiry
        const futureExpiry = Date.now() + 100000;
        localStorage.setItem('usage_warning_dismissed', futureExpiry.toString());

        mockUseUsage.mockReturnValue({
            isLoading: false,
            plan: 'starter',
            filesPercent: 95,
            storagePercent: 50,
        });

        const { container } = render(<UsageWarningBanner />);

        // Should NOT render because dismissed
        expect(container.firstChild).toBeNull();
    });

    it('should reappear if dismissal expired', () => {
        // Set storage with past expiry
        const pastExpiry = Date.now() - 100000;
        localStorage.setItem('usage_warning_dismissed', pastExpiry.toString());

        mockUseUsage.mockReturnValue({
            isLoading: false,
            plan: 'starter',
            filesPercent: 95,
            storagePercent: 50,
        });

        render(<UsageWarningBanner />);

        // Should render
        expect(screen.getByText(/Warning:/)).toBeInTheDocument();
    });
});
