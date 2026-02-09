import { describe, it, expect, vi, beforeEach, afterEach } from 'vitest';
import { render, screen, fireEvent, waitFor, cleanup } from '@testing-library/react';
import { PaywallGuard } from '@/components/PaywallGuard';

// Mock useUsage hook
const mockUseUsage = vi.fn();
const mockUsePlans = vi.fn();
const mockToast = vi.fn();
const mockUsePathname = vi.fn();

vi.mock('@/hooks/useUsage', () => ({
    useUsage: () => mockUseUsage(),
}));

// Mock useAuth hook
const mockUseAuth = vi.fn();

vi.mock('@/hooks/useAuth', () => ({
    useAuth: () => mockUseAuth(),
}));

vi.mock('@/hooks/useProfile', () => ({
    useProfile: () => ({
        profile: { first_name: 'Test', last_name: 'User' },
        isLoading: false,
        error: null,
        updateProfile: vi.fn(),
        refresh: vi.fn(),
    }),
}));

// Mock usePlans hook
vi.mock('@/hooks/usePlans', () => ({
    usePlans: () => mockUsePlans(),
}));

vi.mock('@/components/ui/use-toast', () => ({
    useToast: () => ({ toast: mockToast }),
}));

// Mock Next.js navigation (if needed for internal routing or links)
vi.mock('next/navigation', () => ({
    useRouter: () => ({
        push: vi.fn(),
    }),
    usePathname: () => mockUsePathname(),
}));

// Mock Api
const mockPost = vi.fn();
vi.mock('@/lib/api', () => ({
    api: {
        post: (...args: any[]) => mockPost(...args)
    },
    clearAuthCache: vi.fn(),
}));

vi.mock('@/components/billing/EnterpriseContactModal', () => ({
    EnterpriseContactModal: ({ open }: { open: boolean }) => (
        open ? <div data-testid="enterprise-modal">Enterprise Modal</div> : null
    ),
}));

describe('PaywallGuard Component', () => {
    beforeEach(() => {
        vi.clearAllMocks();
        mockUsePathname.mockReturnValue('/dashboard');

        // Default auth
        mockUseAuth.mockReturnValue({
            user: { id: 'test-user', email: 'test@example.com' },
        });

        mockUsePlans.mockReturnValue({
            plans: [
                {
                    id: 'starter',
                    type: 'starter',
                    name: 'Starter',
                    price: 900,
                    price_amount: 900,
                    price_currency: 'USD',
                    interval: 'month',
                    polar_product_id: 'starter-id',
                    description: 'Starter plan',
                    features: ['Basic RAG search'],
                    button_text: 'Get Started',
                    button_variant: 'outline',
                    popular: false
                },
                {
                    id: 'pro',
                    type: 'pro',
                    name: 'Pro',
                    price: 2900,
                    price_amount: 2900,
                    price_currency: 'USD',
                    interval: 'month',
                    polar_product_id: 'pro-id',
                    description: 'Pro plan',
                    features: ['Unlimited queries'],
                    button_text: 'Start Free Trial',
                    button_variant: 'default',
                    popular: true
                },
                {
                    id: 'enterprise',
                    type: 'enterprise',
                    name: 'Enterprise',
                    price: 0,
                    price_amount: 0,
                    price_currency: 'USD',
                    interval: '',
                    polar_product_id: 'enterprise-id',
                    description: 'Enterprise plan',
                    features: ['Dedicated support'],
                    button_text: 'Contact Sales',
                    button_variant: 'outline',
                    popular: false
                }
            ],
            isLoading: false,
            error: null
        });
    });

    afterEach(() => {
        cleanup();
    });

    it('should render loader when loading', () => {
        mockUseUsage.mockReturnValue({
            isLoading: true,
            plan: 'starter',
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

    it('should render loader when plan is null', () => {
        mockUseUsage.mockReturnValue({
            isLoading: false,
            plan: null,
            usage: { subscription_status: 'active' },
        });

        const { container } = render(
            <PaywallGuard>
                <div>Dashboard Content</div>
            </PaywallGuard>
        );

        expect(container.querySelector('.animate-spin')).toBeInTheDocument();
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

    it('should render PAYWALL when plan is free', () => {
        mockUseUsage.mockReturnValue({
            isLoading: false,
            plan: 'free',
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
        expect(screen.getByRole('heading', { name: /Simple pricing/i })).toBeInTheDocument();
        // Multiple buttons may appear for plan cards
        const trialButtons = screen.getAllByRole('button', { name: /Start Free Trial/i });
        expect(trialButtons.length).toBeGreaterThan(0);
        expect(screen.getByText('Contact Us')).toBeInTheDocument();
        expect(screen.getByText('Unlimited queries')).toBeInTheDocument();
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
        expect(screen.getByRole('heading', { name: /Simple pricing/i })).toBeInTheDocument();
    });

    it('should allow free users to access billing settings', () => {
        mockUsePathname.mockReturnValue('/dashboard/settings/billing');
        mockUseUsage.mockReturnValue({
            isLoading: false,
            plan: 'free',
            usage: { subscription_status: 'inactive' },
        });

        render(
            <PaywallGuard>
                <div>Billing Content</div>
            </PaywallGuard>
        );

        expect(screen.getByText('Billing Content')).toBeInTheDocument();
        // Use queryAllByRole to avoid errors on multiple matches
        const pricingHeadings = screen.queryAllByRole('heading', { name: /Simple pricing/i });
        expect(pricingHeadings.length).toBe(0);
    });

    it('should mark current plan for starter tier', () => {
        mockUseUsage.mockReturnValue({
            isLoading: false,
            plan: 'starter',
            usage: { subscription_status: 'inactive' },
        });

        mockUsePlans.mockReturnValue({
            plans: [
                {
                    id: 'starter',
                    type: 'starter',
                    name: 'Starter',
                    price: 900,
                    price_amount: 900,
                    price_currency: 'USD',
                    interval: 'month',
                    polar_product_id: 'starter-id',
                    description: 'Starter plan',
                    features: [],
                    button_text: 'Get Started',
                    button_variant: 'outline',
                    popular: false
                },
            ],
            isLoading: false,
            error: null
        });

        render(
            <PaywallGuard>
                <div>Dashboard Content</div>
            </PaywallGuard>
        );

        // Multiple "Starter" texts may appear (badge + card title)
        const starterElements = screen.getAllByText('Starter');
        expect(starterElements.length).toBeGreaterThan(0);
        // Multiple "Current Plan" buttons may appear
        const currentPlanButtons = screen.getAllByRole('button', { name: /Current Plan/i });
        expect(currentPlanButtons.length).toBeGreaterThan(0);
    });

    it('should open enterprise modal when clicking enterprise plan', async () => {
        mockUseUsage.mockReturnValue({
            isLoading: false,
            plan: 'free',
            usage: { subscription_status: 'inactive' },
        });

        render(
            <PaywallGuard>
                <div>Dashboard Content</div>
            </PaywallGuard>
        );

        // Multiple "Contact Sales" buttons may appear
        const enterpriseButtons = screen.getAllByRole('button', { name: /Contact Sales/i });
        fireEvent.click(enterpriseButtons[0]);

        expect(screen.getByTestId('enterprise-modal')).toBeInTheDocument();
    });

    it('should show toast on checkout failure', async () => {
        mockUseUsage.mockReturnValue({
            isLoading: false,
            plan: 'free',
            usage: { subscription_status: 'inactive' },
        });

        mockPost.mockResolvedValue({ data: {} });

        render(
            <PaywallGuard>
                <div>Dashboard Content</div>
            </PaywallGuard>
        );

        // Multiple trial buttons may appear
        const proButtons = screen.getAllByRole('button', { name: /Start Free Trial/i });
        fireEvent.click(proButtons[0]);

        await waitFor(() => {
            expect(mockToast).toHaveBeenCalledWith(
                expect.objectContaining({
                    title: 'Error',
                    variant: 'destructive',
                })
            );
        });
    });

    it('should handle checkout click correctly', async () => {
        mockUseUsage.mockReturnValue({
            isLoading: false,
            plan: 'free',
            usage: { subscription_status: 'inactive' },
        });

        // Mock window.location
        const originalLocation = window.location;
        delete (window as any).location;
        (window as any).location = { href: '' };

        mockPost.mockResolvedValue({
            data: { url: 'https://polar.sh/checkout/pro?metadata%5Buser_id%5D=test-user' }
        });

        render(
            <PaywallGuard>
                <div>Dashboard Content</div>
            </PaywallGuard>
        );

        // Click Pro plan button - there may be multiple buttons, click the first matching one
        const proButtons = screen.getAllByRole('button', { name: /Start Free Trial/i });
        fireEvent.click(proButtons[0]);

        // Verify redirect URL contains user metadata
        await waitFor(() => {
            expect(window.location.href).toContain('polar.sh/checkout/pro');
            expect(window.location.href).toContain('metadata%5Buser_id%5D=test-user');
        });

        // Cleanup
        (window as any).location = originalLocation;
    });
});
