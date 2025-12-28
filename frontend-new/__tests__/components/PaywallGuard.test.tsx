import { describe, it, expect, vi, beforeEach } from 'vitest';
import { render, screen, fireEvent } from '@testing-library/react';
import { PaywallGuard } from '@/components/PaywallGuard';

// Mock useUsage hook
const mockUseUsage = vi.fn();

vi.mock('@/hooks/useUsage', () => ({
    useUsage: () => mockUseUsage(),
}));

// Mock useAuth hook
const mockUseAuth = vi.fn();

vi.mock('@/hooks/useAuth', () => ({
    useAuth: () => mockUseAuth(),
}));

// Mock Next.js navigation (if needed for internal routing or links)
vi.mock('next/navigation', () => ({
    useRouter: () => ({
        push: vi.fn(),
        pathname: '/dashboard',
    }),
}));

// Mock AxioLogo to avoid complex SVG rendering issues
vi.mock('@/components/branding/AxioLogo', () => ({
    AxioLogo: () => <div data-testid="axio-logo">Axio Logo</div>,
}));

describe('PaywallGuard Component', () => {
    beforeEach(() => {
        vi.clearAllMocks();

        // Default auth
        mockUseAuth.mockReturnValue({
            user: { id: 'test-user', email: 'test@example.com' },
        });
    });

    it('should render loader when loading', () => {
        mockUseUsage.mockReturnValue({
            isLoading: true,
            plan: 'free',
            usage: { subscription_status: 'active' },
        });

        const { container } = render(
            <PaywallGuard>
                <div>Dashboard Content</div>
            </PaywallGuard>
        );

        // Should verify loader exists
        expect(container.querySelector('.animate-spin')).toBeInTheDocument();
        // Should NOT show content
        expect(screen.queryByText('Dashboard Content')).not.toBeInTheDocument();
    });

    it('should render children when user has active subscription', () => {
        mockUseUsage.mockReturnValue({
            isLoading: false,
            plan: 'pro',
            usage: { subscription_status: 'active' },
        });

        render(
            <PaywallGuard>
                <div>Dashboard Content</div>
            </PaywallGuard>
        );

        expect(screen.getByText('Dashboard Content')).toBeInTheDocument();
        expect(screen.queryByText('Choose Your Plan')).not.toBeInTheDocument();
    });

    it('should render children when user is trialing', () => {
        mockUseUsage.mockReturnValue({
            isLoading: false,
            plan: 'pro',
            usage: { subscription_status: 'trialing' },
        });

        render(
            <PaywallGuard>
                <div>Dashboard Content</div>
            </PaywallGuard>
        );

        expect(screen.getByText('Dashboard Content')).toBeInTheDocument();
    });

    it('should render PAYWALL when plan is none', () => {
        mockUseUsage.mockReturnValue({
            isLoading: false,
            plan: 'none',
            usage: { subscription_status: 'inactive' },
        });

        render(
            <PaywallGuard>
                <div>Dashboard Content</div>
            </PaywallGuard>
        );

        // Content blocked
        expect(screen.queryByText('Dashboard Content')).not.toBeInTheDocument();

        // Paywall shown
        expect(screen.getByText('Choose Your Plan')).toBeInTheDocument();
        expect(screen.getAllByText('Start Free Trial').length).toBeGreaterThan(0); // from buttons
    });

    it('should render PAYWALL when subscription is inactive (even if plan says pro)', () => {
        // This case might happen if cache is stale or logic mismatch, logic prioritizes status check
        mockUseUsage.mockReturnValue({
            isLoading: false,
            plan: 'pro',
            usage: { subscription_status: 'inactive' },
        });

        render(
            <PaywallGuard>
                <div>Dashboard Content</div>
            </PaywallGuard>
        );

        expect(screen.queryByText('Dashboard Content')).not.toBeInTheDocument();
        expect(screen.getByText('Choose Your Plan')).toBeInTheDocument();
    });

    it('should handle checkout click correctly', () => {
        mockUseUsage.mockReturnValue({
            isLoading: false,
            plan: 'none',
            usage: { subscription_status: 'inactive' },
        });

        // Mock window.location
        const originalLocation = window.location;
        delete (window as any).location;
        (window as any).location = { href: '' };

        render(
            <PaywallGuard>
                <div>Dashboard Content</div>
            </PaywallGuard>
        );

        // Click Pro plan button (assuming it's the second card or we find by likely text)
        // Plans: Starter ($9), Pro ($29), Enterprise ($99)
        const proButton = screen.getAllByRole('button', { name: /Start Free Trial/i })[1];
        fireEvent.click(proButton);

        // Verify redirect URL contains user metadata
        expect(window.location.href).toContain('polar.sh/checkout/pro'); // Assuming default env
        expect(window.location.href).toContain('metadata%5Buser_id%5D=test-user');

        // Cleanup
        window.location = originalLocation;
    });
});
