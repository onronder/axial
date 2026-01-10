/**
 * Unit Tests for BillingSettings Component
 * 
 * Comprehensive tests covering:
 * - Loading state
 * - Current plan display
 * - Plan inheritance badge
 * - Pricing cards rendering
 * - Upgrade button behavior
 * - Feature lists
 */

import { describe, it, expect, vi, beforeEach } from 'vitest';
import { render, screen, fireEvent, waitFor, within } from '@testing-library/react';
import { BillingSettings } from '@/components/settings/BillingSettings';

// Mock dependencies
const mockProfile = vi.fn();
const mockUseUsage = vi.fn();
const mockApiGet = vi.fn();
const mockApiPost = vi.fn();
const mockApiDelete = vi.fn();
const { mockToast } = vi.hoisted(() => ({
    mockToast: { error: vi.fn(), success: vi.fn() },
}));

vi.mock('@/hooks/useProfile', () => ({
    useProfile: () => mockProfile(),
}));

vi.mock('@/hooks/useUsage', () => ({
    useUsage: () => mockUseUsage(),
}));

vi.mock('@/lib/api', () => ({
    api: {
        get: (...args: unknown[]) => mockApiGet(...args),
        post: (...args: unknown[]) => mockApiPost(...args),
        delete: (...args: unknown[]) => mockApiDelete(...args),
    },
}));

vi.mock('@/components/branding/AxioLogo', () => ({
    AxioLogo: () => <div data-testid="axio-logo">Logo</div>,
}));

vi.mock('sonner', () => ({
    toast: mockToast,
}));

// Mock window.open
const mockWindowOpen = vi.fn();
Object.defineProperty(window, 'open', {
    value: mockWindowOpen,
    writable: true,
});

describe('BillingSettings Component', () => {
    beforeEach(() => {
        vi.clearAllMocks();
        mockWindowOpen.mockClear();
        mockApiGet.mockResolvedValue({ data: [] });
        mockApiPost.mockResolvedValue({ data: { url: 'https://polar.sh/checkout/mock' } });
        mockApiDelete.mockResolvedValue({ data: { success: true } });

        mockProfile.mockReturnValue({
            profile: { plan: 'pro' },
            isLoading: false,
        });

        mockUseUsage.mockReturnValue({
            plan: 'pro',
            isPlanInherited: false,
        });
    });

    const renderBilling = async () => {
        render(<BillingSettings />);
        await waitFor(() => {
            expect(mockApiGet).toHaveBeenCalled();
        });
    };

    describe('Loading State', () => {
        it('should show loading spinner when loading', async () => {
            mockProfile.mockReturnValue({
                profile: null,
                isLoading: true,
            });

            await renderBilling();

            // Look for the Loader2 spinner (animate-spin class)
            const spinner = document.querySelector('.animate-spin');
            expect(spinner).toBeInTheDocument();
        });

        it('should not show content when loading', async () => {
            mockProfile.mockReturnValue({
                profile: null,
                isLoading: true,
            });

            await renderBilling();

            expect(screen.queryByText('Billing & Plans')).not.toBeInTheDocument();
        });
    });

    describe('Page Header', () => {
        it('should render page title', async () => {
            await renderBilling();

            expect(screen.getByText('Billing & Plans')).toBeInTheDocument();
        });

        it('should render page description', async () => {
            await renderBilling();

            expect(screen.getByText('Manage your subscription and upgrade your plan')).toBeInTheDocument();
        });
    });

    describe('Current Plan Card', () => {
        it('should display current plan section', async () => {
            await renderBilling();

            // Current Plan appears in header and on button for current plan
            const currentPlanElements = screen.getAllByText('Current Plan');
            expect(currentPlanElements.length).toBeGreaterThan(0);
        });

        it('should show Pro badge for pro plan', async () => {
            mockProfile.mockReturnValue({
                profile: { plan: 'pro' },
                isLoading: false,
            });
            mockUseUsage.mockReturnValue({
                plan: 'pro',
                isPlanInherited: false,
            });

            await renderBilling();

            // Pro appears in badge and card
            const proElements = screen.getAllByText('Pro');
            expect(proElements.length).toBeGreaterThan(0);
        });

        it('should show Free badge for free plan', async () => {
            mockProfile.mockReturnValue({
                profile: { plan: 'free' },
                isLoading: false,
            });
            mockUseUsage.mockReturnValue({
                plan: 'free',
                isPlanInherited: false,
            });

            await renderBilling();

            expect(screen.getByText('Free')).toBeInTheDocument();
        });

        it('should show Enterprise badge for enterprise plan', async () => {
            mockProfile.mockReturnValue({
                profile: { plan: 'enterprise' },
                isLoading: false,
            });
            mockUseUsage.mockReturnValue({
                plan: 'enterprise',
                isPlanInherited: false,
            });

            await renderBilling();

            // Enterprise appears in badge and card
            const enterpriseElements = screen.getAllByText('Enterprise');
            expect(enterpriseElements.length).toBeGreaterThan(0);
        });

        it('should fall back to profile plan when usage plan is missing', async () => {
            mockProfile.mockReturnValue({
                profile: { plan: 'starter' },
                isLoading: false,
            });
            mockUseUsage.mockReturnValue({
                plan: null,
                isPlanInherited: false,
            });

            await renderBilling();

            expect(screen.getByText('Starter Plan')).toBeInTheDocument();
        });

        it('should default to Free plan details when plan is unknown', async () => {
            mockProfile.mockReturnValue({
                profile: { plan: 'mystery' },
                isLoading: false,
            });
            mockUseUsage.mockReturnValue({
                plan: null,
                isPlanInherited: false,
            });

            await renderBilling();

            expect(screen.getByText('Free Plan')).toBeInTheDocument();
        });

        it('should default to Free plan when no plan is available', async () => {
            mockProfile.mockReturnValue({
                profile: null,
                isLoading: false,
            });
            mockUseUsage.mockReturnValue({
                plan: null,
                isPlanInherited: false,
            });

            await renderBilling();

            expect(screen.getByText('Free Plan')).toBeInTheDocument();
        });
    });

    describe('Plan Inheritance', () => {
        it('should show Team badge when plan is inherited', async () => {
            mockProfile.mockReturnValue({
                profile: { plan: 'pro' },
                isLoading: false,
            });
            mockUseUsage.mockReturnValue({
                plan: 'enterprise',
                isPlanInherited: true,
            });

            await renderBilling();

            expect(screen.getByText('Team')).toBeInTheDocument();
        });

        it('should show inheritance message when plan is inherited', async () => {
            mockProfile.mockReturnValue({
                profile: { plan: 'pro' },
                isLoading: false,
            });
            mockUseUsage.mockReturnValue({
                plan: 'enterprise',
                isPlanInherited: true,
            });

            await renderBilling();

            expect(screen.getByText("You're using your team owner's plan")).toBeInTheDocument();
        });

        it('should not show Team badge when not inherited', async () => {
            mockProfile.mockReturnValue({
                profile: { plan: 'pro' },
                isLoading: false,
            });
            mockUseUsage.mockReturnValue({
                plan: 'pro',
                isPlanInherited: false,
            });

            await renderBilling();

            expect(screen.queryByText('Team')).not.toBeInTheDocument();
        });
    });

    describe('Pricing Cards', () => {
        it('should render Available Plans section', async () => {
            await renderBilling();

            expect(screen.getByText('Available Plans')).toBeInTheDocument();
        });

        it('should render Starter plan card', async () => {
            await renderBilling();

            expect(screen.getByText('Starter')).toBeInTheDocument();
            expect(screen.getByText('$4.99')).toBeInTheDocument();
        });

        it('should render Pro plan card', async () => {
            await renderBilling();

            // Pro appears multiple times (badge + card)
            const proElements = screen.getAllByText('Pro');
            expect(proElements.length).toBeGreaterThan(0);
            expect(screen.getByText('$29')).toBeInTheDocument();
        });

        it('should render Enterprise plan card', async () => {
            await renderBilling();

            expect(screen.getByText('Contact Us')).toBeInTheDocument();
        });

        it('should show "Most Popular" badge on Pro plan', async () => {
            await renderBilling();

            expect(screen.getByText('Most Popular')).toBeInTheDocument();
        });

        it('should show "Current Plan" for active plan', async () => {
            mockProfile.mockReturnValue({
                profile: { plan: 'starter' },
                isLoading: false,
            });
            mockUseUsage.mockReturnValue({
                plan: 'starter',
                isPlanInherited: false,
            });

            await renderBilling();

            // Current Plan appears in header and button
            const currentPlanElements = screen.getAllByText('Current Plan');
            expect(currentPlanElements.length).toBeGreaterThan(0);
        });
    });

    describe('Feature Lists', () => {
        it('should show Starter features', async () => {
            await renderBilling();

            expect(screen.getByText('100 queries/month')).toBeInTheDocument();
            expect(screen.getByText('2 connected sources')).toBeInTheDocument();
        });

        it('should show Pro features', async () => {
            await renderBilling();

            expect(screen.getByText('Unlimited queries')).toBeInTheDocument();
            expect(screen.getByText('Priority support')).toBeInTheDocument();
        });

        it('should show Enterprise features', async () => {
            await renderBilling();

            expect(screen.getByText('Everything in Pro')).toBeInTheDocument();
            expect(screen.getByText('SSO & SAML')).toBeInTheDocument();
        });
    });

    describe('Upgrade Buttons', () => {
        it('should show Upgrade button for non-current plans', async () => {
            mockProfile.mockReturnValue({
                profile: { plan: 'free' },
                isLoading: false,
            });
            mockUseUsage.mockReturnValue({
                plan: 'free',
                isPlanInherited: false,
            });

            await renderBilling();

            expect(screen.getByText('Get Started')).toBeInTheDocument();
            expect(screen.getByText('Upgrade to Pro')).toBeInTheDocument();
            expect(screen.getByText('Contact Sales')).toBeInTheDocument();
        });

        it('should open enterprise contact modal when Contact Sales is clicked', async () => {
            mockProfile.mockReturnValue({
                profile: { plan: 'free' },
                isLoading: false,
            });
            mockUseUsage.mockReturnValue({
                plan: 'free',
                isPlanInherited: false,
            });

            await renderBilling();

            fireEvent.click(screen.getByText('Contact Sales'));

            expect(screen.getByText('Contact Enterprise Sales')).toBeInTheDocument();
        });

        it('should disable button for current plan', async () => {
            mockProfile.mockReturnValue({
                profile: { plan: 'pro' },
                isLoading: false,
            });
            mockUseUsage.mockReturnValue({
                plan: 'pro',
                isPlanInherited: false,
            });

            await renderBilling();

            // Find the disabled button with "Current Plan" text
            const currentPlanButtons = screen.getAllByText('Current Plan');
            const buttonElement = currentPlanButtons.find(el => el.closest('button'));
            expect(buttonElement?.closest('button')).toBeDisabled();
        });

        it('should open checkout URL on upgrade click', async () => {
            mockProfile.mockReturnValue({
                profile: { plan: 'free' },
                isLoading: false,
            });
            mockUseUsage.mockReturnValue({
                plan: 'free',
                isPlanInherited: false,
            });

            const originalLocation = window.location;
            delete (window as unknown as { location?: Location }).location;
            (window as unknown as { location: { href: string } }).location = { href: '' };

            await renderBilling();

            mockApiPost.mockResolvedValue({ data: { url: 'https://polar.sh/checkout/starter' } });

            const upgradeButton = screen.getByText('Upgrade to Pro');
            fireEvent.click(upgradeButton);

            await waitFor(() => {
                expect(window.location.href).toContain('polar.sh/checkout');
            });

            (window as unknown as { location: Location }).location = originalLocation;
        });

        it('should show toast when checkout URL is missing', async () => {
            mockProfile.mockReturnValue({
                profile: { plan: 'free' },
                isLoading: false,
            });
            mockUseUsage.mockReturnValue({
                plan: 'free',
                isPlanInherited: false,
            });
            mockApiPost.mockResolvedValue({ data: {} });

            await renderBilling();

            fireEvent.click(screen.getByText('Upgrade to Pro'));

            await waitFor(() => {
                expect(mockToast.error).toHaveBeenCalledWith('Failed to start checkout. Please try again.');
            });
        });
    });

    describe('Payment Methods Section', () => {
        it('should render Payment Methods section', async () => {
            await renderBilling();

            expect(screen.getByText('Payment Methods')).toBeInTheDocument();
        });

        it('should show no payment method message', async () => {
            await renderBilling();

            expect(screen.getByText('Managed by Polar')).toBeInTheDocument();
        });

        it('should show Add Payment Method button', async () => {
            await renderBilling();

            expect(screen.getByText('Manage')).toBeInTheDocument();
        });
    });

    describe('Billing History Section', () => {
        it('should render Billing History section', async () => {
            await renderBilling();

            expect(screen.getByText('Billing History')).toBeInTheDocument();
        });

        it('should show no history message', async () => {
            await renderBilling();

            expect(screen.getByText('No billing history available')).toBeInTheDocument();
        });

        it('should handle invoice fetch errors gracefully', async () => {
            const consoleSpy = vi.spyOn(console, 'error').mockImplementation(() => {});
            mockApiGet.mockRejectedValue(new Error('Invoice error'));

            await renderBilling();

            expect(consoleSpy).toHaveBeenCalled();
            consoleSpy.mockRestore();
        });

        it('should handle null invoice data', async () => {
            mockApiGet.mockResolvedValue({ data: null });

            await renderBilling();

            expect(screen.getByText('No billing history available')).toBeInTheDocument();
        });
    });

    describe('Manage Subscription Button', () => {
        it('should show Manage button for paid plans', async () => {
            mockProfile.mockReturnValue({
                profile: { plan: 'pro' },
                isLoading: false,
            });
            mockUseUsage.mockReturnValue({
                plan: 'pro',
                isPlanInherited: false,
            });

            await renderBilling();

            expect(screen.getByText('Manage Subscription')).toBeInTheDocument();
        });

        it('should not show Manage button for free plan', async () => {
            mockProfile.mockReturnValue({
                profile: { plan: 'free' },
                isLoading: false,
            });
            mockUseUsage.mockReturnValue({
                plan: 'free',
                isPlanInherited: false,
            });

            await renderBilling();

            expect(screen.queryByText('Manage Subscription')).not.toBeInTheDocument();
        });
    });

    describe('Portal Redirect', () => {
        it('should open portal URL when manage subscription is clicked', async () => {
            mockApiPost.mockResolvedValue({ data: { url: 'https://polar.sh/portal' } });

            await renderBilling();

            fireEvent.click(screen.getByText('Manage Subscription'));

            await waitFor(() => {
                expect(mockWindowOpen).toHaveBeenCalledWith('https://polar.sh/portal', '_blank');
            });
        });

        it('should show toast on portal error', async () => {
            mockApiPost.mockResolvedValue({ data: {} });

            await renderBilling();

            fireEvent.click(screen.getByText('Manage Subscription'));

            await waitFor(() => {
                expect(mockToast.error).toHaveBeenCalledWith('Failed to open subscription portal');
            });
        });
    });

    describe('Billing History Items', () => {
        it('should render invoice list and open invoice link', async () => {
            mockApiGet.mockResolvedValue({
                data: [
                    {
                        id: 'inv-1',
                        amount: 2900,
                        currency: 'usd',
                        status: 'paid',
                        created_at: '2024-01-01T00:00:00Z',
                        product_name: 'Pro Plan',
                        invoice_url: 'https://polar.sh/invoices/inv-1',
                    },
                ],
            });

            await renderBilling();

            const invoiceLabel = screen.getByText('Pro Plan', { selector: 'p' });
            expect(invoiceLabel).toBeInTheDocument();
            const invoiceRow = invoiceLabel.parentElement?.parentElement?.parentElement;
            expect(invoiceRow).toBeTruthy();
            if (!invoiceRow) {
                throw new Error('Invoice row not found');
            }
            expect(within(invoiceRow).getByText('$29')).toBeInTheDocument();

            const invoiceButton = within(invoiceRow).getByRole('button');
            fireEvent.click(invoiceButton);

            expect(mockWindowOpen).toHaveBeenCalledWith('https://polar.sh/invoices/inv-1', '_blank');
        });

        it('should render formatted invoice amount and fallback date on invalid date', async () => {
            const dateSpy = vi.spyOn(Date.prototype, 'toLocaleDateString').mockImplementation(() => {
                throw new Error('Bad date');
            });

            mockApiGet.mockResolvedValue({
                data: [
                    {
                        id: 'inv-2',
                        amount: 2950,
                        currency: 'usd',
                        status: 'open',
                        created_at: 'bad-date',
                        product_name: 'Starter Plan',
                        invoice_url: null,
                    },
                ],
            });

            await renderBilling();

            const invoiceLabel = screen.getByText('Starter Plan', { selector: 'p' });
            const invoiceRow = invoiceLabel.parentElement?.parentElement?.parentElement;
            expect(invoiceRow).toBeTruthy();
            if (!invoiceRow) {
                throw new Error('Invoice row not found');
            }

            expect(within(invoiceRow).getByText('$29.50')).toBeInTheDocument();
            expect(within(invoiceRow).getByText('bad-date')).toBeInTheDocument();
            expect(within(invoiceRow).getByText('open').className).toContain('outline');

            dateSpy.mockRestore();
        });
    });

    describe('Cancel Subscription Flow', () => {
        it('should cancel subscription when confirmed', async () => {
            await renderBilling();

            fireEvent.click(screen.getByRole('button', { name: 'Cancel Subscription' }));
            fireEvent.click(screen.getByRole('button', { name: /Yes, Cancel Subscription/i }));

            await waitFor(() => {
                expect(mockApiDelete).toHaveBeenCalledWith('/billing/subscription');
            });

            expect(mockToast.success).toHaveBeenCalled();
        });

        it('should show error toast on cancel failure', async () => {
            mockApiDelete.mockResolvedValue({ data: { success: false, message: 'Failed' } });

            await renderBilling();

            fireEvent.click(screen.getByRole('button', { name: 'Cancel Subscription' }));
            fireEvent.click(screen.getByRole('button', { name: /Yes, Cancel Subscription/i }));

            await waitFor(() => {
                expect(mockToast.error).toHaveBeenCalledWith('Failed to cancel subscription. Please try again.');
            });
        });

        it('should show error toast when cancel failure has no message', async () => {
            mockApiDelete.mockResolvedValue({ data: { success: false } });

            await renderBilling();

            fireEvent.click(screen.getByRole('button', { name: 'Cancel Subscription' }));
            fireEvent.click(screen.getByRole('button', { name: /Yes, Cancel Subscription/i }));

            await waitFor(() => {
                expect(mockToast.error).toHaveBeenCalledWith('Failed to cancel subscription. Please try again.');
            });
        });
    });
});
